#!/usr/bin/env python3
"""
Check running/stopped EC2 instances with spot-checker tags
"""

import boto3
import variables
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
awscli_profile = variables.awscli_profile
prefix = variables.prefix
regions = variables.region if isinstance(variables.region, list) else [variables.region]

# Tag filters
ENVIRONMENT_TAG = f'{prefix}-spot-test'
PROJECT_TAG = 'spot-checker-multinode'


def check_region(region_name):
    """Check EC2 instances in a specific region"""
    try:
        session = boto3.Session(profile_name=awscli_profile, region_name=region_name)
        ec2_client = session.client('ec2')

        # Query instances with spot-checker tags
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Environment',
                    'Values': [ENVIRONMENT_TAG]
                }
            ]
        )

        instances = []
        instance_ids = []
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instances.append(instance)
                instance_ids.append(instance['InstanceId'])

        # Get Spot Instance Request info for ValidUntil
        spot_requests = {}
        if instance_ids:
            try:
                spot_response = ec2_client.describe_spot_instance_requests(
                    Filters=[
                        {'Name': 'instance-id', 'Values': instance_ids}
                    ]
                )
                for request in spot_response.get('SpotInstanceRequests', []):
                    inst_id = request.get('InstanceId')
                    if inst_id:
                        status_info = request.get('Status', {})
                        launch_spec = request.get('LaunchSpecification', {})
                        spot_requests[inst_id] = {
                            'valid_until': request.get('ValidUntil'),
                            'spot_request_id': request.get('SpotInstanceRequestId'),
                            'status_code': status_info.get('Code'),
                            'status_message': status_info.get('Message', ''),
                            'interruption_behavior': launch_spec.get('InstanceInterruptionBehavior', 'N/A'),
                            'price': request.get('SpotPrice'),
                            'request_status': request.get('Status', {}),
                            'request_state': request.get('State')
                        }
            except Exception as e:
                pass  # Skip if Spot Request info is not available

        # Attach Spot request info to instances
        for instance in instances:
            instance['_spot_info'] = spot_requests.get(instance['InstanceId'], {})

        return region_name, instances

    except Exception as e:
        print(f"[{region_name}] Error: {str(e)}")
        return region_name, []


def format_instance_info(instance):
    """Format instance information for display"""
    instance_id = instance['InstanceId']
    instance_type = instance['InstanceType']
    state = instance['State']['Name']
    az = instance['Placement']['AvailabilityZone']
    launch_time = instance['LaunchTime']
    lifecycle = instance.get('InstanceLifecycle', 'on-demand')

    # Get tags
    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}

    # Get subnet and security groups
    subnet_id = instance.get('SubnetId', 'N/A')
    sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]

    # Get Spot Request info
    spot_info = instance.get('_spot_info', {})
    valid_until = spot_info.get('valid_until')
    if valid_until:
        valid_until_str = valid_until.strftime('%Y-%m-%d %H:%M:%S UTC')
    else:
        valid_until_str = 'N/A'

    spot_request_id = spot_info.get('spot_request_id', 'N/A')
    spot_status_code = spot_info.get('status_code', 'N/A')
    spot_status_message = spot_info.get('status_message', '')
    interruption_behavior = spot_info.get('interruption_behavior', 'N/A')
    spot_price = spot_info.get('price', 'N/A')
    request_state = spot_info.get('request_state', 'N/A')

    return {
        'id': instance_id,
        'type': instance_type,
        'state': state,
        'az': az,
        'launch_time': launch_time.strftime('%Y-%m-%d %H:%M:%S UTC') if launch_time else 'N/A',
        'valid_until': valid_until_str,
        'lifecycle': lifecycle,
        'subnet_id': subnet_id,
        'security_groups': sg_ids,
        'spot_request_id': spot_request_id,
        'spot_status_code': spot_status_code,
        'spot_status_message': spot_status_message,
        'request_state': request_state,
        'interruption_behavior': interruption_behavior,
        'spot_price': spot_price,
        'tags': tags
    }


def main():
    print("=" * 120)
    print("EC2 Instance Status - Spot Checker Tagged Instances")
    print("=" * 120)
    print(f"\nConfiguration:")
    print(f"  Profile: {awscli_profile}")
    print(f"  Prefix: {prefix}")
    print(f"  Regions: {regions}")
    print(f"  Environment Tag: {ENVIRONMENT_TAG}")
    print(f"\n{'=' * 120}\n")

    all_instances = {}
    total_count = 0
    running_count = 0
    stopped_count = 0

    # Query regions in parallel
    with ThreadPoolExecutor(max_workers=len(regions)) as executor:
        futures = [executor.submit(check_region, r) for r in regions]

        for future in as_completed(futures):
            region_name, instances = future.result()
            all_instances[region_name] = instances
            total_count += len(instances)

    # Display results by region
    for region in regions:
        instances = all_instances.get(region, [])

        if not instances:
            print(f"[{region}] No instances found")
            continue

        print(f"[{region}] {len(instances)} instance(s) found:")
        print("-" * 120)

        # State statistics
        state_count = {}
        for inst in instances:
            state = inst['State']['Name']
            state_count[state] = state_count.get(state, 0) + 1
            if state == 'running':
                running_count += 1
            elif state == 'stopped':
                stopped_count += 1

        print(f"  Status: {', '.join([f'{state}={count}' for state, count in sorted(state_count.items())])}")
        print()

        # Display each instance
        for instance in instances:
            info = format_instance_info(instance)

            print(f"  [{info['state']:<12}] {info['id']:<19} | Type: {info['type']:<12} | AZ: {info['az']}")
            print(f"    Instance Lifecycle: {info['lifecycle']:<15} | Launched: {info['launch_time']}")
            print(f"    Valid Until: {info['valid_until']:<30} | Subnet: {info['subnet_id']}")

            # Display Spot Request info (both Status and State)
            print(f"    Spot Request ID: {info['spot_request_id']:<30} | Status: {info['spot_status_code']}")
            print(f"    Request State: {info['request_state']:<45} | Interruption: {info['interruption_behavior']}")
            print(f"      Spot Price: {info['spot_price']}")
            if info['spot_status_message']:
                print(f"      Status Message: {info['spot_status_message']}")

            print(f"    Security Groups: {', '.join(info['security_groups']) if info['security_groups'] else 'N/A'}")

            # Display tags
            if info['tags']:
                tags_str = ', '.join([f"{k}={v}" for k, v in sorted(info['tags'].items())])
                print(f"    Tags: {tags_str}")

            print()

        print()

    # Summary
    print("=" * 120)
    print("Summary")
    print("=" * 120)
    print(f"  Total Instances: {total_count}")
    print(f"  Running: {running_count}")
    print(f"  Stopped: {stopped_count}")
    print(f"  Other: {total_count - running_count - stopped_count}")
    print("=" * 120)

    # Cleanup recommendations
    if total_count > 0:
        print("\n[WARNING] Cleanup commands:")
        print(f"  Terminate all: uv run clean_spot_instances.py")
        print(f"  Check details: aws ec2 describe-instances --filters \"Name=tag:Environment,Values={ENVIRONMENT_TAG}\" --region <region>")
    else:
        print("\n[OK] No instances to clean up")


if __name__ == "__main__":
    main()
