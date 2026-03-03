import pytz
import time
import boto3
import pickle
import datetime
import base64
import variables

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


# userdata = """#!/bin/bash
# current_time=$(date +%s)
# current_time_ms=$((current_time * 1000))
# INSTANCE_ID=$(ec2-metadata -i | cut -d " " -f 2)
# INSTANCE_TYPE=$(ec2-metadata -t | cut -d " " -f 2)
# INSTANCE_AZ=$(ec2-metadata -z | cut -d " " -f 2)
# SPOT_REQUEST_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[].Instances[].SpotInstanceRequestId' --region %s --output text)
# SPOT_VALID_FROM=$(aws ec2 describe-spot-instance-requests --spot-instance-request-ids $SPOT_REQUEST_ID --query 'SpotInstanceRequests[*].{ValidFrom:ValidFrom}' --region %s --output text)

# log_event=$(cat <<EOF
# [
#     {
#         "timestamp": ${current_time_ms},
#         "message": "{\\"timestamp\\": \\"${current_time_ms}\\", \\"instance_id\\": \\"${INSTANCE_ID}\\", \\"instance_type\\": \\"${INSTANCE_TYPE}\\", \\"spot_request_id\\": \\"${SPOT_REQUEST_ID}\\", \\"az\\": \\"${INSTANCE_AZ}\\", \\"vail_from\\": \\"${SPOT_VALID_FROM}\\"}"
#     }
# ]
# EOF
# )
# aws logs put-log-events --log-group-name %s --log-stream-name %s --log-events "$log_event" --region %s
# sudo shutdown -P +%s

# """ % ("%s", region, region, log_group_name, log_stream_name, region, time_minutes)

# userdata_encoded = base64.b64encode(userdata.encode()).decode()

regions = variables.region if isinstance(variables.region, list) else [variables.region]
az_ids = variables.az_id if isinstance(variables.az_id, list) else [variables.az_id]

if len(regions) != len(az_ids):
    raise ValueError("The number of regions and az_ids in variables.py must match.")
### session & client
session = boto3.session.Session(profile_name='default')

### Start Spot Checker
def start_spot_checker(ec2, launch_spec, target_count):
    # Calculate fresh launch_time and stop_time for each region call
    launch_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=wait_minutes)
    stop_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=time_hours, minutes=(time_minutes + wait_minutes))

    print(f"DEBUG - launch_time type: {type(launch_time)}, value: {launch_time}")
    print(f"DEBUG - stop_time type: {type(stop_time)}, value: {stop_time}")
    print(f"DEBUG - stop_time - launch_time: {stop_time - launch_time}")

    create_request_response = ec2.request_spot_instances(
        InstanceCount=target_count,
        LaunchSpecification=launch_spec,
        #     SpotPrice=spot_price, # default value for on-demand price
        Type='persistent',  # not 'one-time', persistent request
        ValidFrom=launch_time,
        ValidUntil=stop_time,
        TagSpecifications=[
            {
                'ResourceType': 'spot-instances-request',
                'Tags': [
                    {'Key': 'Project', 'Value': 'spot-checker-multinode'},
                    {'Key': 'Environment', 'Value': f'{prefix}-spot-test'}
                ]
            }
        ]
    )

    # Extract SpotInstanceRequestIds
    spot_request_ids = [req['SpotInstanceRequestId'] for req in create_request_response['SpotInstanceRequests']]
    print(f"Spot requests created: {spot_request_ids}")

    # Poll until instances are created
    instance_ids = []
    max_retries = 30
    retry_count = 0

    while len(instance_ids) < target_count and retry_count < max_retries:
        response = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids)

        for req in response['SpotInstanceRequests']:
            if 'InstanceId' in req and req['InstanceId'] not in instance_ids:
                instance_ids.append(req['InstanceId'])

        if len(instance_ids) < target_count:
            time.sleep(1)
            retry_count += 1

    # Apply tags to actual EC2 instances
    if instance_ids:
        ec2.create_tags(
            Resources=instance_ids,
            Tags=[
                {'Key': 'Project', 'Value': 'spot-checker-multinode'},
                {'Key': 'Environment', 'Value': f'{prefix}-spot-test'}
            ]
        )
        print(f"Tags applied to instances: {instance_ids}")

if __name__ == "__main__":
    instance_count = variables.instance_count
    print(f"Target instance count per AZ: {instance_count}")
    
    for r, a in zip(regions, az_ids):
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
