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
arm64_family = ['a1', 't4g', 'c6g', 'c6gd', 'c6gn', 'c7gd', 'c7gn', 'im4gn', 'is4gen', 'm6g', 'm6gd', 'm7g', 'm7gd', 'r6g', 'r6gd', 'r7g', 'r7gd', 'x2gd']

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
log_group_name = f"{prefix}-ondemand-checker-multinode-log"
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
LAUNCHTIME=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[].Instances[].LaunchTime' --region %s --output text)
log_event=$(cat <<EOF
[
    {
        "timestamp": ${current_time_ms},
        "message": "{\\"timestamp\\": \\"${current_time_ms}\\", \\"instance_id\\": \\"${INSTANCE_ID}\\", \\"instance_type\\": \\"${INSTANCE_TYPE}\\", \\"az\\": \\"${INSTANCE_AZ}\\", \\"launch_time\\": \\"${LAUNCHTIME}\\"}"
    }
]
EOF
)
aws logs put-log-events --log-group-name %s --log-stream-name %s --log-events "$log_event" --region %s
sudo shutdown -P +%s
""" % ("%s", region, log_group_name, log_stream_name, region, time_minutes)

userdata_encoded = base64.b64encode(userdata.encode()).decode()


launch_info = [instance_type, instance_family, instance_arch, region, az_id, az_name, ami_id]
print(f"""Instance Type: {instance_type}\nInstance Family: {instance_family}\nInstance Arhictecture: {instance_arch}
Region: {region}\nAZ-ID: {az_id}\nAZ-Name:{az_name}\nAMI ID: {ami_id}""")

ondemand_data_dict = {}
ondemand_data_dict['launch_info'] = launch_info
ondemand_data_dict['start_time'] = launch_time
ondemand_data_dict['end_time'] = stop_time


### Start Ondemand Checker
def start_ondemand_checker(target_count):
    ### session & client
    session = boto3.session.Session(profile_name='default')
    ec2 = session.client('ec2', region_name=region)

    create_intances_response = ec2.run_instances(
        ImageId = ami_id,
        InstanceType = instance_type,
        Placement = {'AvailabilityZone': az_name},
        IamInstanceProfile = {
            'Arn': 'arn:aws:iam::741926482963:instance-profile/EC2toEC2_CW' # IAM ARN for CloudWatch access
        },
        MinCount=1,
        MaxCount=target_count,
        UserData=userdata_encoded,
        TagSpecifications=[
            { 'ResourceType': 'instance',
             'Tags': [
                 {  'Key' : 'Name',
                    'Value': f'{prefix}-multi-instance-test'
                    }
                 ]
            }
        ]
    )

    instance_list = []
    for rq in create_intances_response['Instances']:
        instance_list.append(rq['InstanceId'])


    '''
    UserData에서 shutdown을 하면 인스턴스가 stopped 상태로 변함
    3분 대기 후 terminate
    '''    
    time.sleep(180)
    terminate_response = ec2.terminate_instances(InstanceIds=instance_list)
    
    time.sleep(1)
    return instance_list



if __name__ == "__main__":
    instance_count = variables.instance_count
    print(instance_count)
    ondemand_instance_request_id_list = start_ondemand_checker(instance_count)
