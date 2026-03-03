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
        """Spot Instance ID 목록 조회"""
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
                    return state == 'completed'

                time.sleep(5)
            except Exception as e:
                print(f"Error checking experiment status: {e}")
                return False

        print(f"Experiment {experiment_id} timeout")
        return False

    def start_stopped_instances(self):
        """중단된 EC2 인스턴스를 다시 시작"""
        instance_ids = self.get_spot_instances()

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

    def collect_logs(self,
                    log_group_name: str,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """CloudWatch Logs에서 테스트 결과 수집"""

        if start_time is None:
            start_time = datetime.now() - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.now()

        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)

        results = {}

        try:
            # 로그 그룹의 모든 스트림 조회
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name
            )

            log_streams = response.get('logStreams', [])

            for stream in log_streams:
                stream_name = stream['logStreamName']
                results[stream_name] = self._get_log_events(
                    log_group_name,
                    stream_name,
                    start_ms,
                    end_ms
                )

            return results
        except Exception as e:
            print(f"Error collecting logs: {e}")
            return {}

    def _get_log_events(self,
                       log_group_name: str,
                       log_stream_name: str,
                       start_time_ms: int,
                       end_time_ms: int) -> List[Dict]:
        """특정 로그 스트림에서 이벤트 수집"""

        events = []

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                logStreamNamePrefix=log_stream_name,
                startTime=start_time_ms,
                endTime=end_time_ms
            )

            for event in response.get('events', []):
                try:
                    message = json.loads(event['message'])
                except json.JSONDecodeError:
                    message = event['message']

                events.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                    'message': message
                })

            return events
        except Exception as e:
            print(f"Error getting log events from {log_stream_name}: {e}")
            return []

    def get_lambda_metrics(self,
                          function_names: List[str],
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> Dict[str, Dict]:
        """Lambda 함수의 CloudWatch 메트릭 조회"""

        if start_time is None:
            start_time = datetime.now() - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.now()

        metrics = {}

        for func_name in function_names:
            metrics[func_name] = {
                'invocations': self._get_metric_stats(
                    func_name, 'Invocations', start_time, end_time
                ),
                'errors': self._get_metric_stats(
                    func_name, 'Errors', start_time, end_time
                ),
                'duration': self._get_metric_stats(
                    func_name, 'Duration', start_time, end_time
                )
            }

        return metrics

    def _get_metric_stats(self,
                         function_name: str,
                         metric_name: str,
                         start_time: datetime,
                         end_time: datetime) -> Dict[str, Any]:
        """CloudWatch 메트릭 통계 조회"""

        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=60,
                Statistics=['Sum', 'Average', 'Maximum']
            )

            return {
                'metric_name': metric_name,
                'datapoints': response.get('Datapoints', []),
                'count': len(response.get('Datapoints', []))
            }
        except Exception as e:
            print(f"Error getting metrics for {function_name}: {e}")
            return {}

    def generate_report(self,
                       logs: Dict[str, List[Dict]],
                       metrics: Dict[str, Dict],
                       output_file: str = None) -> str:
        """테스트 결과 보고서 생성"""

        report = []
        report.append("=" * 80)
        report.append("AWS FIS Testing Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 80)
        report.append("")

        # CloudWatch Logs 요약
        report.append("CloudWatch Logs Summary:")
        report.append("-" * 80)

        for stream_name, events in logs.items():
            report.append(f"\n{stream_name}:")
            report.append(f"  Event count: {len(events)}")

            if events:
                report.append(f"  First event: {events[0]['timestamp']}")
                report.append(f"  Last event: {events[-1]['timestamp']}")

                # 이벤트 타입별 분포
                if isinstance(events[0]['message'], dict):
                    event_types = {}
                    for event in events:
                        event_type = event['message'].get('detail-type', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1

                    if event_types:
                        report.append("  Event types:")
                        for event_type, count in event_types.items():
                            report.append(f"    - {event_type}: {count}")

        # Lambda 메트릭 요약
        report.append("\n" + "=" * 80)
        report.append("Lambda Metrics Summary:")
        report.append("-" * 80)

        for func_name, func_metrics in metrics.items():
            report.append(f"\n{func_name}:")
            for metric_type, metric_data in func_metrics.items():
                if metric_data:
                    count = metric_data.get('count', 0)
                    report.append(f"  {metric_type}: {count} data points")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")

        return report_text


def main():
    parser = argparse.ArgumentParser(
        description='AWS FIS Testing Automation'
    )
    parser.add_argument(
        '--action',
        choices=['setup', 'run', 'list', 'collect-logs', 'report', 'cleanup', 'start-instances'],
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
    
    for r in regions:
        print(f"\n" + "="*80)
        print(f"PROCESSING REGION: {r}")
        print("="*80)
        
        tester = FISTester(
            profile=variables.awscli_profile,
            region=r,
            prefix=variables.prefix
        )

        if args.action == 'setup':
            print("="*80)
            print(f"Setting up FIS Infrastructure for region: {r}")
            print("="*80)

            # FIS IAM Role ARN (Lambda 역할의 FIS 권한으로 사용)
            account_id = tester._get_account_id()
            iam_role_arn = f"arn:aws:iam::{account_id}:role/{variables.prefix}-fis-role-{r}"

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

            for exp_name, exp_config in experiments.items():
                print(f"\nCreating FIS experiment: {variables.prefix}-{exp_name}")

                # JSON 파일로 저장
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    # AWS FIS API: action별 target 설정
                    if exp_name in ['spot-rebalance', 'spot-interruption']:
                        # Spot Instance 전용 targets
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
                        # 일반 EC2 인스턴스 targets
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
                    # AWS CLI로 FIS 실험 템플릿 생성
                    cmd = [
                        'aws', 'fis', 'create-experiment-template',
                        '--region', r,
                        '--profile', variables.awscli_profile,
                        '--cli-input-json', f'file://{temp_file}'
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        print(f"✓ {variables.prefix}-{exp_name} created successfully")
                    else:
                        print(f"⚠ {exp_name}: {result.stderr}")
                finally:
                    # 임시 파일 삭제
                    import os
                    os.unlink(temp_file)

            print("\n" + "="*80)
            print("FIS setup completed!")
            print("="*80 + "\n")

        elif args.action == 'run':
            if not args.experiment_type:
                print("Error: --experiment-type required for 'run' action")
                global_return_code = 1
                continue

            # 인스턴스에 태그 추가
            tester.tag_spot_instances()

            # 실험 실행
            exp_id = tester.run_experiment(args.experiment_type, args.duration)

            if exp_id:
                print(f"Waiting for experiment {exp_id} to complete...")
                tester.wait_experiment_completion(exp_id)
    
        elif args.action == 'list':
            experiments = tester.list_experiments()
            if experiments:
                print(f"Found {len(experiments)} experiments:")
                for exp in experiments:
                    print(f"  - {exp['title']} ({exp['id']})")
            else:
                print("No experiments found")

        elif args.action == 'collect-logs':
            log_group_name = f"{variables.prefix}-spot-checker-multinode-log"
    
            print(f"Collecting logs from {log_group_name}...")
            logs = tester.collect_logs(log_group_name)
    
            print("\nLog Collection Summary:")
            for stream_name, events in logs.items():
                print(f"  {stream_name}: {len(events)} events")
    
            # JSON으로 저장
            output_json = f'fis_logs_{r}.json'
            with open(output_json, 'w') as f:
                json_logs = {}
                for stream_name, events in logs.items():
                    json_logs[stream_name] = [
                        {
                            'timestamp': event['timestamp'].isoformat(),
                            'message': event['message']
                        }
                        for event in events
                    ]
                json.dump(json_logs, f, indent=2)
    
            print(f"Logs saved to {output_json}")

        elif args.action == 'report':
            log_group_name = f"{variables.prefix}-spot-checker-multinode-log"
            logs = tester.collect_logs(log_group_name)
    
            lambda_functions = [
                f"{variables.prefix}-get-spot-status-change",
                f"{variables.prefix}-get-spot-rebalance",
                f"{variables.prefix}-get-spot-interruption",
                f"{variables.prefix}-log-instance-count",
                f"{variables.prefix}-restart-closed-request"
            ]
    
            metrics = tester.get_lambda_metrics(lambda_functions)
    
            output_file = args.output or f'fis_report_{r}.txt'
            report = tester.generate_report(logs, metrics, output_file)
            print(report)
            
        elif args.action == 'cleanup':
            print("Cleaning up FIS infrastructure...")
            # IaC 디렉토리 절대 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            iac_dir = os.path.join(script_dir, 'IaC')

            destroy_result = subprocess.run(
                ['terraform', f'-chdir={iac_dir}', 'destroy', '--auto-approve'],
                capture_output=True,
                text=True
            )
            if destroy_result.returncode == 0:
                print("FIS infrastructure cleaned up successfully")
                print(destroy_result.stdout)
            else:
                print(f"Error cleaning up FIS infrastructure: {destroy_result.stderr}")
                global_return_code = 1
                continue

        elif args.action == 'start-instances':
            print("="*80)
            print(f"Starting stopped instances in region: {r}")
            print("="*80)
            tester.start_stopped_instances()

    return global_return_code


if __name__ == '__main__':
    sys.exit(main())
