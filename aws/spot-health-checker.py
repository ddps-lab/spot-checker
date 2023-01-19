import pytz
import time
import boto3
import pickle
import datetime
import argparse
from pathlib import Path
import sys
import requests

SLACK_URL = ""


# print to slack webhook
def print(msg):
    sys.stdout.write(f"{msg}\n")
    requests.post(SLACK_URL, json={"text": f"{msg}"})


# Spot Checker Mapping Data
# {x86/arm: {region: (ami-id, ami-info), ...}}
region_ami = pickle.load(open('./data/region_ami_dict.pkl', 'rb'))
# {(region, az-id): az-name, ...}
az_map_dict = pickle.load(open('./data/az_map_dict.pkl', 'rb'))
arm64_family = ['a1', 't4g', 'c6g', 'c6gd', 'c6gn',
                'im4gn', 'is4gen', 'm6g', 'm6gd', 'r6g', 'r6gd', 'x2gd']
LOG_BUCKET_NAME = 'spot-checker-data'

# Spot Checker Arguments
parser = argparse.ArgumentParser(
    description='Spot Checker Workload Information')
parser.add_argument('--instance_type', type=str, default='t2.large')
parser.add_argument('--region', type=str, default='ap-southeast-2')
parser.add_argument('--az_id', type=str, default='apse2-az2')
parser.add_argument('--wait_minutes', type=int, default='1',
                    help='wait before request, minutes')
parser.add_argument('--time_minutes', type=int, default='5',
                    help='how long check spot instance, minutes')
parser.add_argument('--time_hours', type=int, default='0',
                    help='how long check spot instance, hours')
args = parser.parse_args()


# Spot Checker Arguments Parsing
instance_type = args.instance_type
instance_family = instance_type.split('.')[0]
instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'
region = args.region
az_id = args.az_id
az_name = az_map_dict[(region, az_id)]
ami_id = region_ami[instance_arch][region][0]
launch_time = datetime.datetime.now() + datetime.timedelta(minutes=args.wait_minutes)
launch_time = launch_time.astimezone(pytz.UTC)
stop_time = datetime.datetime.now() + datetime.timedelta(hours=args.time_hours,
                                                         minutes=(args.time_minutes + args.wait_minutes))
stop_time = stop_time.astimezone(pytz.UTC)
spot_data_dict = {}


# Spot Launch Specifications
launch_spec = {
    'ImageId': ami_id,
    'InstanceType': instance_type,
    'Placement': {'AvailabilityZone': az_name}
}
launch_info = [instance_type, instance_family,
               instance_arch, region, az_id, az_name, ami_id]
print(f"""Instance Type: {instance_type}\nInstance Family: {instance_family}\nInstance Arhictecture: {instance_arch}
Region: {region}\nAZ-ID: {az_id}\nAZ-Name:{az_name}\nAMI ID: {ami_id}""")
spot_data_dict['launch_spec'] = launch_spec
spot_data_dict['launch_info'] = launch_info
spot_data_dict['start_time'] = launch_time
spot_data_dict['end_time'] = stop_time


# Start Spot Checker
session = boto3.session.Session(profile_name='default')
ec2 = session.client('ec2', region_name=region)
s3 = session.resource('s3')

try:
    create_request_response = ec2.request_spot_instances(
        InstanceCount=1,
        LaunchSpecification=launch_spec,
        #     SpotPrice=spot_price, # default value for on-demand price
        ValidFrom=launch_time,
        ValidUntil=stop_time,
        Type='persistent'  # not 'one-time', persistent request
    )
    spot_data_dict['create_request'] = create_request_response
    request_id = create_request_response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    time.sleep(5)

    # Status Log Variables
    log_list = []
    instance_tag = False
except Exception as e:
    print(e)
    raise


# Log Parser
def log_sampling(current_time, request_describe, instance_describe):
    request_state = 'error'
    request_status = 'error'
    if 'SpotInstanceRequests' in request_describe:
        if len(request_describe['SpotInstanceRequests']) == 1:
            if 'State' in request_describe['SpotInstanceRequests'][0]:
                request_state = request_describe['SpotInstanceRequests'][0]['State']
            if 'Status' in request_describe['SpotInstanceRequests'][0]:
                request_status = request_describe['SpotInstanceRequests'][0]['Status']

    instance_id = 'error'
    instance_state = 'error'
    instance_status = 'error'
    if 'InstanceStatuses' in instance_describe:
        if len(instance_describe['InstanceStatuses']) == 1:
            if 'InstanceId' in instance_describe['InstanceStatuses'][0]:
                instance_id = instance_describe['InstanceStatuses'][0]['InstanceId']
            if 'InstanceState' in instance_describe['InstanceStatuses'][0]:
                instance_state = instance_describe['InstanceStatuses'][0]['InstanceState']
            if 'InstanceStatus' in instance_describe['InstanceStatuses'][0]:
                instance_status = instance_describe['InstanceStatuses'][0]['InstanceStatus']

    return (current_time, request_state, request_status, instance_id, instance_state, instance_status)


# First Log
current_time = datetime.datetime.now()
current_time = current_time.astimezone(pytz.UTC)
request_describe = ec2.describe_spot_instance_requests(
    SpotInstanceRequestIds=[request_id])
request_status = request_describe['SpotInstanceRequests'][0]['Status']['Code']
instance_describe = ''
instance_id = 'checker'
sample_log = log_sampling(current_time, request_describe, instance_describe)
log_list.append(sample_log)


# Loop Log
save_idx = 0
while True:
    current_time = datetime.datetime.now()
    current_time = current_time.astimezone(pytz.UTC)
    try:
        request_describe = ec2.describe_spot_instance_requests(
            SpotInstanceRequestIds=[request_id])
        request_status = request_describe['SpotInstanceRequests'][0]['Status']['Code']
        sample_log = log_sampling(
            current_time, request_describe, instance_describe)
        log_list.append(sample_log)
    except Exception as e:
        print(e)
        log_list.append(current_time, 'loop-error', 'loop-error')

    if request_status == 'fulfilled':
        instance_id = request_describe['SpotInstanceRequests'][0]['InstanceId']
        if instance_tag == False:
            instance_tag = True
            ec2.create_tags(Resources=[instance_id], Tags=[
                            {'Key': 'Name', 'Value': 'spot-checker-target'}])
            print(f"{instance_type}-{az_id}-{instance_id} fulfilled")

        instance_describe = ec2.describe_instance_status(
            InstanceIds=[instance_id])
        instance_status = instance_describe['InstanceStatuses']

    if request_status == 'capacity-not-available':
        if instance_tag == True:
            instance_tag = False

    if current_time > stop_time:
        print(f"{instance_type}-{az_id}-{instance_id} stopped")

        if instance_id == 'checker':
            current_time = datetime.datetime.now()
            current_time = current_time.astimezone(pytz.UTC)
            request_describe = ec2.describe_spot_instance_requests(
                SpotInstanceRequestIds=[request_id])
            sample_log = log_sampling(
                current_time, request_describe, instance_describe)
            log_list.append(sample_log)

        elif (request_status == 'fulfilled') or (request_status == 'request-canceled-and-instance-running'):
            print(f"{instance_type}-{az_id}-{instance_id} terminated")
            terminate_response = ec2.terminate_instances(
                InstanceIds=[instance_id])
            spot_data_dict['terminate_response'] = terminate_response

            current_time = datetime.datetime.now()
            current_time = current_time.astimezone(pytz.UTC)
            request_describe = ec2.describe_spot_instance_requests(
                SpotInstanceRequestIds=[request_id])
            instance_describe = ec2.describe_instance_status(
                InstanceIds=[instance_id])
            sample_log = log_sampling(
                current_time, request_describe, instance_describe)
            log_list.append(sample_log)

        else:
            print(f"{instance_type}-{az_id}-{instance_id} error")
        break
    time.sleep(5)
    save_idx += 1
    if (save_idx != 0) and (save_idx % 720 == 0):
        # Save log to Local
        spot_data_dict['logs'] = log_list
        filename = f"logs/{instance_type}_{region}_{az_id}_{launch_time}.pkl"
        print(f"save log of {filename}")
        Path('./logs').mkdir(exist_ok=True)
        pickle.dump(spot_data_dict, open(filename, 'wb'))

# Save log to Local
spot_data_dict['logs'] = log_list
filename = f"logs/{instance_type}_{region}_{az_id}_{launch_time}.pkl"
print(f"save final log of {filename}")
Path('./logs').mkdir(exist_ok=True)
pickle.dump(spot_data_dict, open(filename, 'wb'))

# Upload log to S3
spot_data_dict_obj = pickle.dumps(spot_data_dict)
s3.Object(LOG_BUCKET_NAME, filename).put(Body=spot_data_dict_obj)
print(f"upload log of {filename} done")
