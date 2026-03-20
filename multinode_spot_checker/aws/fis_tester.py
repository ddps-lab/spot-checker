#!/usr/bin/env python3
"""
AWS FIS (Fault Injection Simulator) 테스트 자동화 스크립트

Lambda 모듈의 장애 대응 능력을 FIS로 테스트합니다:
1. get-spot-status-change (EC2 Stop 실험)
2. get-spot-rebalance (Spot Rebalance Recommendation 실험)
3. get-spot-interruption (Spot Interruption Warning 실험)
4. log-instance-count (Instance Reboot 실험)
5. restart-closed-request (자동 처리)

⚠️ 실행 순서:
1. Lambda + IAM Role 생성:
    uv run create_tester.py

2. FIS 실험 템플릿 생성:
    uv run fis_tester.py --action setup

3. Spot Instance 생성:
    uv run spot-health-checker-iter.py

4. FIS 실험 실행:
    uv run fis_tester.py --action run --experiment-type ec2-stop

전체 사용법:
    # 실험 템플릿 목록 확인
    python fis_tester.py --action list

    # FIS 실험 실행
    # - ec2-stop: EC2 인스턴스 중단
    # - spot-rebalance: Spot 재할당 권고 신호
    # - spot-interruption: Spot 중단 경고 (2분)
    # - instance-reboot: 인스턴스 재부팅
    python fis_tester.py --action run --experiment-type spot-rebalance --duration 300

    # 로그 수집
    python fis_tester.py --action collect-logs

    # 보고서 생성
    python fis_tester.py --action report --output report.txt
"""

import argparse
import json
import sys
import time
import subprocess
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3

import variables


class FISTester:
    """AWS FIS 테스트 관리 클래스"""

    def __init__(self, profile: str, region: str, prefix: str):
        self.profile = profile
        self.region = region
        self.prefix = prefix

        # AWS 클라이언트 초기화
        session = boto3.Session(profile_name=profile, region_name=region)
        self.fis_client = session.client('fis')
        self.ec2_client = session.client('ec2')
        self.logs_client = session.client('logs')
        self.lambda_client = session.client('lambda')
        self.cloudwatch_client = session.client('cloudwatch')
        self.sts_client = session.client('sts')

    def _get_account_id(self) -> str:
        """AWS Account ID 조회"""
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            print(f"Error getting account ID: {e}")
            return ""

    def list_experiments(self) -> List[Dict[str, Any]]:
        """생성된 FIS 실험 템플릿 목록 조회"""
        try:
            response = self.fis_client.list_experiment_templates()
            experiments = response.get('experimentTemplates', [])

            filtered = []
            for exp in experiments:
                # title 필드로 먼저 확인
                if 'title' in exp and exp['title'].startswith(self.prefix):
                    filtered.append(exp)
                # tags의 Name으로도 확인 (AWS FIS에서 Name 태그를 사용하는 경우)
                elif 'tags' in exp and 'Name' in exp.get('tags', {}):
                    if exp['tags']['Name'].startswith(self.prefix):
                        filtered.append(exp)

            return filtered
        except Exception as e:
            print(f"Error listing experiments: {e}")
            return []

    def get_spot_instances(self) -> List[str]:
        """Spot Instance ID 목록 조회 (running 상태만)"""
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-lifecycle',
                        'Values': ['spot']
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    },
                    {
                        'Name': 'tag:Environment',
                        'Values': [f'{self.prefix}-spot-test']
                    }
                ]
            )

            instance_ids = []
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_ids.append(instance['InstanceId'])

            return instance_ids
        except Exception as e:
            print(f"Error getting spot instances: {e}")
            return []

    def get_stopped_test_instances(self) -> List[str]:
        """중단된 테스트 인스턴스 ID 목록 조회 (running + stopped)"""
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running', 'stopped']
                    },
                    {
                        'Name': 'tag:Environment',
                        'Values': [f'{self.prefix}-spot-test']
                    }
                ]
            )

            instance_ids = []
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_ids.append(instance['InstanceId'])

            return instance_ids
        except Exception as e:
            print(f"Error getting stopped test instances: {e}")
            return []

    def tag_spot_instances(self):
        """Spot Instance에 FIS 태그 추가"""
        instance_ids = self.get_spot_instances()

        if not instance_ids:
            print(f"⚠️  No Spot instances found with tag Environment={self.prefix}-spot-test")
            print("Please tag your Spot instances manually:")
            print(f"  aws ec2 create-tags --region {self.region} --resources <instance-id> \\")
            print(f"    --tags Key=Environment,Value={self.prefix}-spot-test")
            return False

        try:
            self.ec2_client.create_tags(
                Resources=instance_ids,
                Tags=[
                    {
                        'Key': 'Environment',
                        'Value': f'{self.prefix}-spot-test'
                    }
                ]
            )
            print(f"✓ Tagged {len(instance_ids)} instances with Environment={self.prefix}-spot-test")
            return True
        except Exception as e:
            print(f"Error tagging instances: {e}")
            return False

    def run_experiment(self,
                      experiment_type: str,
                      duration_seconds: int = 300) -> Optional[str]:
        """FIS 실험 실행"""

        # 실험 템플릿 찾기
        experiments = self.list_experiments()

        template_id = None
        for exp in experiments:
            # title 필드로 먼저 확인
            if 'title' in exp and experiment_type in exp['title']:
                template_id = exp['id']
                break
            # tags의 Name으로도 확인
            elif 'tags' in exp and 'Name' in exp.get('tags', {}):
                if experiment_type in exp['tags']['Name']:
                    template_id = exp['id']
                    break

        if not template_id:
            print(f"Experiment template not found for type: {experiment_type}")
            return None

        try:
            response = self.fis_client.start_experiment(
                experimentTemplateId=template_id,
                tags={
                    'StartTime': datetime.now().isoformat(),
                    'ExperimentType': experiment_type,
                    'Prefix': self.prefix
                }
            )

            experiment_id = response['experiment']['id']
            print(f"Started experiment: {experiment_id}")
            print(f"  Type: {experiment_type}")
            print(f"  Duration: {duration_seconds} seconds")

            return experiment_id
        except Exception as e:
            print(f"Error starting experiment: {e}")
            return None

    def wait_experiment_completion(self,
                                  experiment_id: str,
                                  timeout_seconds: int = 600) -> bool:
        """FIS 실험 완료 대기"""

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                response = self.fis_client.get_experiment(id=experiment_id)
                experiment = response['experiment']
                state = experiment['state']['status']

                print(f"Experiment {experiment_id} status: {state}")

                if state in ['completed', 'failed', 'stopped']:
                    if state == 'failed':
                        # 실패 원인 출력
                        print(f"\n✗ Experiment {experiment_id} failed")
                        state_reason = experiment.get('state', {}).get('reason', 'Unknown reason')
                        print(f"  Reason: {state_reason}")

                        # 실험 타겟 정보 출력
                        targets = experiment.get('targets', {})
                        if targets:
                            print(f"  Targets:")
                            for target_name, target_info in targets.items():
                                print(f"    - {target_name}: {target_info}")

                        # 실험 액션 정보 출력
                        actions = experiment.get('actions', {})
                        if actions:
                            print(f"  Actions:")
                            for action_name, action_info in actions.items():
                                print(f"    - {action_name}: {action_info}")
                    elif state == 'completed':
                        print(f"✓ Experiment {experiment_id} completed successfully")

                    return state == 'completed'

                time.sleep(5)
            except Exception as e:
                print(f"Error checking experiment status: {e}")
                return False

        print(f"Experiment {experiment_id} timeout")
        return False

    def start_stopped_instances(self):
        """중단된 테스트 인스턴스를 다시 시작 (running + stopped 포함)"""
        instance_ids = self.get_stopped_test_instances()

        if not instance_ids:
            print("No instances to start")
            return True

        try:
            response = self.ec2_client.start_instances(InstanceIds=instance_ids)
            started = response.get('StartingInstances', [])
            print(f"\n✓ Started {len(started)} instances:")
            for instance in started:
                print(f"  - {instance['InstanceId']} (State: {instance['CurrentState']['Name']})")
            return True
        except Exception as e:
            print(f"Error starting instances: {e}")
            return False



def setup_experiment(r: str, exp_name: str, exp_config: Dict) -> bool:
    """Setup FIS experiment template in a specific region."""
    import tempfile

    tester = FISTester(
        profile=variables.awscli_profile,
        region=r,
        prefix=variables.prefix
    )

    account_id = tester._get_account_id()
    iam_role_arn = f"arn:aws:iam::{account_id}:role/{variables.prefix}-fis-role-{r}"

    print(f"[{r}] Creating FIS experiment: {variables.prefix}-{exp_name}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        if exp_name in ['spot-rebalance', 'spot-interruption']:
            # Spot-only actions (send-spot-instance-interruptions)
            targets = {
                'SpotInstances-Target': {
                    'resourceType': 'aws:ec2:spot-instance',
                    'selectionMode': 'ALL',
                    'resourceTags': {
                        'Environment': f'{variables.prefix}-spot-test'
                    }
                }
            }
            action_targets = {'SpotInstances': 'SpotInstances-Target'}
        else:
            # General EC2 actions (stop-instances, reboot-instances)
            targets = {
                'Instances-Target': {
                    'resourceType': 'aws:ec2:instance',
                    'selectionMode': 'ALL',
                    'resourceTags': {
                        'Environment': f'{variables.prefix}-spot-test'
                    }
                }
            }
            action_targets = {'Instances': 'Instances-Target'}

        template_json = {
            'description': exp_config['description'],
            'stopConditions': [{'source': 'none'}],
            'targets': targets,
            'actions': {
                f'{exp_name}-action': {
                    'actionId': exp_config['action_id'],
                    'description': f'Action for {exp_name}',
                    'parameters': exp_config['parameters'],
                    'targets': action_targets
                }
            },
            'roleArn': iam_role_arn,
            'tags': {'Name': f'{variables.prefix}-{exp_name}'}
        }
        json.dump(template_json, f)
        temp_file = f.name

    try:
        cmd = [
            'aws', 'fis', 'create-experiment-template',
            '--region', r,
            '--profile', variables.awscli_profile,
            '--cli-input-json', f'file://{temp_file}'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✓ [{r}] {variables.prefix}-{exp_name} created successfully")
            return True
        else:
            print(f"✗ [{r}] {exp_name}: {result.stderr}")
            return False
    finally:
        os.unlink(temp_file)


def run_experiment_region(r: str, experiment_type: str, duration_seconds: int) -> Optional[str]:
    """Run FIS experiment in a specific region."""
    tester = FISTester(
        profile=variables.awscli_profile,
        region=r,
        prefix=variables.prefix
    )

    tester.tag_spot_instances()
    exp_id = tester.run_experiment(experiment_type, duration_seconds)

    if exp_id:
        print(f"[{r}] Waiting for experiment {exp_id} to complete...")
        tester.wait_experiment_completion(exp_id)
        return exp_id
    return None


def main():
    parser = argparse.ArgumentParser(
        description='AWS FIS Testing Automation'
    )
    parser.add_argument(
        '--action',
        choices=['setup', 'run', 'list', 'cleanup', 'start-instances'],
        default='list',
        help='Action to perform'
    )
    parser.add_argument(
        '--experiment-type',
        choices=['ec2-stop', 'spot-rebalance', 'spot-interruption', 'instance-reboot'],
        help='FIS experiment type'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=300,
        help='Experiment duration in seconds'
    )
    parser.add_argument(
        '--output',
        help='Output file for report'
    )

    args = parser.parse_args()

    regions = variables.region if isinstance(variables.region, list) else [variables.region]

    global_return_code = 0

    # Setup action: parallel experiment template creation
    if args.action == 'setup':
        print("="*80)
        print(f"Setting up FIS Infrastructure for {len(regions)} region(s)")
        print("="*80)

        experiments = {
            'ec2-stop': {
                'description': 'Stop EC2 instances to test get-spot-status-change Lambda',
                'action_id': 'aws:ec2:stop-instances',
                'parameters': {}
            },
            'spot-rebalance': {
                'description': 'Send Spot Instance rebalance recommendation signal to test get-spot-rebalance Lambda',
                'action_id': 'aws:ec2:send-spot-instance-interruptions',
                'parameters': {'durationBeforeInterruption': 'PT5M'}
            },
            'spot-interruption': {
                'description': 'Send Spot Instance interruption warning (2-minute notice) to test get-spot-interruption Lambda',
                'action_id': 'aws:ec2:send-spot-instance-interruptions',
                'parameters': {'durationBeforeInterruption': 'PT2M'}
            },
            'instance-reboot': {
                'description': 'Reboot EC2 instances to test log-instance-count Lambda',
                'action_id': 'aws:ec2:reboot-instances',
                'parameters': {}
            }
        }

        # Parallel: Create experiment templates across regions and experiment types
        with ThreadPoolExecutor(max_workers=len(regions) * len(experiments)) as executor:
            futures = []
            for r in regions:
                for exp_name, exp_config in experiments.items():
                    future = executor.submit(setup_experiment, r, exp_name, exp_config)
                    futures.append(future)

            success_count = 0
            for future in as_completed(futures):
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    print(f"✗ Error creating experiment template: {e}")

        print("\n" + "="*80)
        print(f"FIS setup completed! ({success_count}/{len(futures)} templates created)")
        print("="*80 + "\n")

    elif args.action == 'run':
        if not args.experiment_type:
            print("Error: --experiment-type required for 'run' action")
            return 1

        print("="*80)
        print(f"Running {args.experiment_type} experiments in {len(regions)} region(s) in parallel")
        print("="*80)

        with ThreadPoolExecutor(max_workers=len(regions)) as executor:
            futures = [
                executor.submit(run_experiment_region, r, args.experiment_type, args.duration)
                for r in regions
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"✗ Error running experiment: {e}")
                    global_return_code = 1

    elif args.action == 'list':
        print("="*80)
        print(f"Listing FIS experiments in {len(regions)} region(s)")
        print("="*80)

        for r in regions:
            tester = FISTester(
                profile=variables.awscli_profile,
                region=r,
                prefix=variables.prefix
            )
            experiments = tester.list_experiments()
            if experiments:
                print(f"\n[{r}] Found {len(experiments)} experiments:")
                for exp in experiments:
                    #print(exp)
                    print(f"  - {exp['tags']['Name']} ({exp['id']})")
            else:
                print(f"\n[{r}] No experiments found")

    elif args.action == 'cleanup':
        print("="*80)
        print("Cleaning up FIS infrastructure...")
        print("="*80)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        iac_dir = os.path.join(script_dir, 'IaC')

        destroy_result = subprocess.run(
            ['terraform', f'-chdir={iac_dir}', 'destroy', '--auto-approve'],
            capture_output=True,
            text=True
        )
        if destroy_result.returncode == 0:
            print("✓ FIS infrastructure cleaned up successfully")
            print(destroy_result.stdout)
        else:
            print(f"✗ Error cleaning up FIS infrastructure: {destroy_result.stderr}")
            global_return_code = 1

    elif args.action == 'start-instances':
        print("="*80)
        print(f"Starting stopped instances in {len(regions)} region(s) in parallel")
        print("="*80)

        def start_instances_region(r):
            tester = FISTester(
                profile=variables.awscli_profile,
                region=r,
                prefix=variables.prefix
            )
            tester.start_stopped_instances()

        with ThreadPoolExecutor(max_workers=len(regions)) as executor:
            futures = [
                executor.submit(start_instances_region, r)
                for r in regions
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"✗ Error starting instances: {e}")
                    global_return_code = 1

    return global_return_code


if __name__ == '__main__':
    sys.exit(main())
