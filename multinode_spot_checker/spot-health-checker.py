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
arm64_family = ['a1', 't4g', 'c6g', 'c6gd', 'c6gn', 'im4gn', 'is4gen', 'm6g', 'm6gd', 'r6g', 'r6gd', 'x2gd']

### Spot Checker Arguments Parsing
prefix = variables.prefix

instance_type = variables.instance_type
region = variables.region
az_id = variables.az_id

wait_minutes = variables.wait_minutes
time_minutes = variables.time_minutes 
time_hours = variables.time_hours

instance_family = instance_type.split('.')[0]
instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'

az_name = az_map_dict[(region, az_id)]
log_group_name = f"{prefix}-spot-checker-multinode-log"
log_stream_name = f"{variables.log_stream_name_init_time}"
ami_id = region_ami[instance_arch][region][0]
launch_time = datetime.datetime.now() + datetime.timedelta(minutes=wait_minutes)
launch_time = launch_time.astimezone(pytz.UTC)
stop_time = datetime.datetime.now() + datetime.timedelta(hours=time_hours, minutes=(time_minutes + wait_minutes))
stop_time = stop_time.astimezone(pytz.UTC)


userdata = """#!/bin/bash
current_time=$(date +%s)
current_time_ms=$((current_time * 1000))
INSTANCE_ID=$(ec2-metadata -i | cut -d " " -f 2)
INSTANCE_TYPE=$(ec2-metadata -t | cut -d " " -f 2)
INSTANCE_AZ=$(ec2-metadata -z | cut -d " " -f 2)
SPOT_REQUEST_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[].Instances[].SpotInstanceRequestId' --region %s --output text)
SPOT_VALID_FROM=$(aws ec2 describe-spot-instance-requests --spot-instance-request-ids $SPOT_REQUEST_ID --query 'SpotInstanceRequests[*].{ValidFrom:ValidFrom}' --region %s --output text)

log_event=$(cat <<EOF
[
    {
        "timestamp": ${current_time_ms},
        "message": "{\\"timestamp\\": \\"${current_time_ms}\\", \\"instance_id\\": \\"${INSTANCE_ID}\\", \\"instance_type\\": \\"${INSTANCE_TYPE}\\", \\"spot_request_id\\": \\"${SPOT_REQUEST_ID}\\", \\"az\\": \\"${INSTANCE_AZ}\\", \\"vail_from\\": \\"${SPOT_VALID_FROM}\\"}"
    }
]
EOF
)
aws logs put-log-events --log-group-name %s --log-stream-name %s --log-events "$log_event" --region %s
sudo shutdown -P +%s
""" % ("%s", region, region, log_group_name, log_stream_name, region, time_minutes)

userdata_encoded = base64.b64encode(userdata.encode()).decode()

### Spot Launch Specifications
launch_spec = {
    'ImageId': ami_id,
    'InstanceType': instance_type,
    'Placement': {'AvailabilityZone': az_name},
    'IamInstanceProfile': {
            'Arn': 'arn:aws:iam::741926482963:instance-profile/EC2toEC2_CW' # IAM ARN for CloudWatch access
        },
    'UserData': userdata_encoded,
}
launch_info = [instance_type, instance_family, instance_arch, region, az_id, az_name, ami_id]
print(f"""Instance Type: {instance_type}\nInstance Family: {instance_family}\nInstance Arhictecture: {instance_arch}
Region: {region}\nAZ-ID: {az_id}\nAZ-Name:{az_name}\nAMI ID: {ami_id}""")

spot_data_dict = {}
spot_data_dict['launch_spec'] = launch_spec
spot_data_dict['launch_info'] = launch_info
spot_data_dict['start_time'] = launch_time
spot_data_dict['end_time'] = stop_time


### Start Spot Checker
def start_spot_checker(target_count):
    ### session & client
    session = boto3.session.Session(profile_name='default')
    ec2 = session.client('ec2', region_name=region)

    create_request_response = ec2.request_spot_instances(
        InstanceCount=target_count,
        LaunchSpecification=launch_spec,
        #     SpotPrice=spot_price, # default value for on-demand price
        ValidFrom=launch_time,
        ValidUntil=stop_time,
        Type='persistent'  # not 'one-time', persistent request
    )
    siri_list = []
    for rq in create_request_response['SpotInstanceRequests']:
        siri_list.append(rq['SpotInstanceRequestId'])

    spot_data_dict['create_requests'] = create_request_response
    time.sleep(1)
    return siri_list



if __name__ == "__main__":
    instance_count = variables.instance_count
    print(instance_count)
    spot_instance_request_id_list = start_spot_checker(instance_count)
