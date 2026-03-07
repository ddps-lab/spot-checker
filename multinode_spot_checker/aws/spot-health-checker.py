import time
import boto3
import pickle
import datetime
import base64
import variables
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

### Spot Checker Mapping Data
region_ami = pickle.load(open('./ami_az_data/region_ami_dict.pkl', 'rb'))  # {x86/arm: {region: (ami-id, ami-info), ...}}
az_map_dict = pickle.load(open('./ami_az_data/az_map_dict.pkl', 'rb'))  # {(region, az-id): az-name, ...}
arm64_family = ['a1', 't4g', 'c6g', 'c6gd', 'c6gn', 'c7g', 'c7gd', 'c7gn', 'im4gn', 'is4gen', 'm6g', 'm6gd', 'm7g', 'm7gd', 'm8g', 'r6g', 'r6gd', 'r7g', 'r7gd', 'r8g', 'x2gd']

### Spot Checker Arguments Parsing
prefix = variables.prefix

instance_type = variables.instance_type
iam_instance_profile_arn = variables.iam_instance_profile_arn

wait_minutes = variables.wait_minutes
time_minutes = variables.time_minutes
time_hours = variables.time_hours

instance_family = instance_type.split('.')[0]
instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'

log_group_name = f"{prefix}-spot-checker-multinode-log"
log_stream_name = f"{variables.log_stream_name_init_time}"
log_stream_name_imds = f"{variables.log_stream_name_imds_monitor}"

regions = variables.region if isinstance(variables.region, list) else [variables.region]
az_ids = variables.az_id if isinstance(variables.az_id, list) else [variables.az_id]

if len(regions) != len(az_ids):
    raise ValueError("The number of regions and az_ids in variables.py must match.")

session = boto3.session.Session(profile_name='default')

def get_imds_monitor_userdata(log_group_name, log_stream_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    imds_monitor_path = os.path.join(script_dir, 'imds_monitor.py')

    if not os.path.exists(imds_monitor_path):
        print(f"Warning: {imds_monitor_path} not found, IMDS monitor will not be included")
        return None

    with open(imds_monitor_path, 'r') as f:
        imds_monitor_code = f.read()

    imds_monitor_code_b64 = base64.b64encode(imds_monitor_code.encode()).decode()

    userdata_script = f"""#!/bin/bash
set -e
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=${{ID}}
else
    OS="unknown"
fi
case "$OS" in
    ubuntu|debian)
        apt-get update -qq
        apt-get install -y -qq python3-pip > /dev/null 2>&1
        ;;
    amzn|amazonlinux)
        yum update -y > /dev/null 2>&1
        yum install -y python3-pip > /dev/null 2>&1
        ;;
    rhel|centos)
        yum update -y > /dev/null 2>&1
        yum install -y python3-pip > /dev/null 2>&1
        ;;
    *)
        apt-get update -qq
        apt-get install -y -qq python3-pip > /dev/null 2>&1
        ;;
esac
pip3 install -q 'urllib3<2' 'requests>=2.28' boto3
echo "{imds_monitor_code_b64}" | base64 -d > /opt/imds_monitor.py
chmod +x /opt/imds_monitor.py
export IMDS_LOG_GROUP="{log_group_name}"
export IMDS_LOG_STREAM="{log_stream_name}"
nohup python3 /opt/imds_monitor.py > /var/log/imds_monitor.log 2>&1 &
"""

    userdata_encoded = base64.b64encode(userdata_script.encode()).decode()
    return userdata_encoded


def start_spot_checker(ec2, launch_spec, target_count):
    launch_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=wait_minutes)
    stop_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=time_hours, minutes=(time_minutes + wait_minutes))

    print(f"DEBUG - launch_time {launch_time}")
    print(f"DEBUG - stop_time {stop_time}")
    print(f"DEBUG - stop_time - launch_time: {stop_time - launch_time}")

    userdata_b64 = get_imds_monitor_userdata(log_group_name, log_stream_name_imds)

    print(f"\nLaunching {target_count} Spot instance(s)...")
    run_instances_params = {
        'ImageId': launch_spec['ImageId'],
        'InstanceType': launch_spec['InstanceType'],
        'MinCount': target_count,
        'MaxCount': target_count,
        'Placement': launch_spec['Placement'],
        'IamInstanceProfile': launch_spec['IamInstanceProfile'],
        'BlockDeviceMappings': [
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {
                    'VolumeSize': 8,
                    'VolumeType': 'gp2',
                    'DeleteOnTermination': True
                }
            }
        ],
        'InstanceMarketOptions': {
            'MarketType': 'spot',
            'SpotOptions': {
                'SpotInstanceType': 'persistent',
                'InstanceInterruptionBehavior': 'stop',
                'ValidUntil': stop_time
            }
        },
        'TagSpecifications': [
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Project', 'Value': 'spot-checker-multinode'},
                    {'Key': 'Environment', 'Value': f'{prefix}-spot-test'}
                ]
            }
        ],
        'MetadataOptions': {
            'HttpTokens': 'required',
            'HttpPutResponseHopLimit': 1,
            'HttpEndpoint': 'enabled'
        }
    }

    if userdata_b64:
        run_instances_params['UserData'] = userdata_b64

    response = ec2.run_instances(**run_instances_params)
    instance_ids = [inst['InstanceId'] for inst in response['Instances']]

    print(f"✓ Spot instances launched: {instance_ids}")

    max_retries = 180
    retry_count = 0

    print(f"Waiting for instances to reach 'running' state (max {max_retries}s)...")
    while retry_count < max_retries:
        describe_response = ec2.describe_instances(InstanceIds=instance_ids)
        running_ids = []

        for reservation in describe_response['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] == 'running':
                    running_ids.append(instance['InstanceId'])
                    print(f"  ✓ Instance {instance['InstanceId']} is running")
                elif retry_count % 30 == 0:
                    print(f"  ℹ Instance {instance['InstanceId']}: {instance['State']['Name']}")

        if len(running_ids) == target_count:
            print(f"✓ All {target_count} instances are running")
            break

        time.sleep(1)
        retry_count += 1

    if instance_ids:
        try:
            ec2.create_tags(
                Resources=instance_ids,
                Tags=[
                    {'Key': 'Project', 'Value': 'spot-checker-multinode'},
                    {'Key': 'Environment', 'Value': f'{prefix}-spot-test'}
                ]
            )
            print(f"✓ Tags verified on instances: {instance_ids}")
        except Exception as e:
            print(f"✗ Error applying tags: {e}")
    else:
        print(f"✗ No instances created")

def launch_in_region(r, a, instance_count):
    az_name_mapped = az_map_dict[(r, a)]
    ami_id_mapped = region_ami[instance_arch][r][0]

    launch_spec = {
        'ImageId': ami_id_mapped,
        'InstanceType': instance_type,
        'Placement': {'AvailabilityZone': az_name_mapped},
        'IamInstanceProfile': {
            'Arn': iam_instance_profile_arn
        },
    }

    print(f"""\n--- Launching in {r} ---
            Instance Type: {instance_type}
            Instance Family: {instance_family}
            Instance Architecture: {instance_arch}
            Region: {r}
            AZ-ID: {a}
            AZ-Name:{az_name_mapped}
            AMI ID: {ami_id_mapped}"""
    )

    ec2 = session.client('ec2', region_name=r)
    start_spot_checker(ec2, launch_spec, instance_count)


if __name__ == "__main__":
    instance_count = variables.instance_count
    print(f"Target instance count per AZ: {instance_count}")
    print(f"Launching in {len(regions)} region(s) in parallel...\n")

    # boto3는 병렬 스레드로 수행해도 safe
    with ThreadPoolExecutor(max_workers=len(regions)) as executor:
        futures = [
            executor.submit(launch_in_region, r, a, instance_count)
            for r, a in zip(regions, az_ids)
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error in region launch: {e}")

    print("\n✓ All regions completed")
