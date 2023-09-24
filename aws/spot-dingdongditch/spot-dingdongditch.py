import boto3
import time
import pickle
import datetime
import argparse
import pandas as pd
import os
import pytz
from pathlib import Path
from slack_msg_sender import send_slack_message


bucket_name = ''
s3 = boto3.resource('s3', aws_access_key_id='', aws_secret_access_key='')
session = boto3.session.Session()
ec2 = session.client('ec2',  aws_access_key_id='', aws_secret_access_key='')
launch_time = datetime.datetime.utcnow()

# save log as csv. if file exists, overwrite
def save_status_code(spot_data_list, instance_type, az_id):
    filepath = f"logs/{instance_type}_{az_id}.csv"

    if os.path.exists(filepath):
        df = pd.DataFrame(spot_data_list, columns=['InstanceType', 'AZ', 'status', 'time'])
        df_existing = pd.read_csv(filepath)
        df_combined = pd.concat([df_existing, df], ignore_index=True)
        df_combined.to_csv(filepath, index=False)
    else:
        Path('./logs').mkdir(exist_ok=True)
        df = pd.DataFrame(spot_data_list, columns=['InstanceType', 'AZ', 'status', 'time'])
        df.to_csv('/tmp/spot_data.csv', index=False)

    send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), "로컬에 로그 저장 완료.")




# create spot instance
def create_spot_instance(instance_type, ami_id, az_name, az_id):
    launch_spec = {
        'ImageId': ami_id,
        'InstanceType': instance_type,
        'Placement': {'AvailabilityZone': az_name}
    }

    create_request_response = ec2.request_spot_instances(
        InstanceCount=1,
        LaunchSpecification=launch_spec,
        Type='one-time'
    )

    request_id = create_request_response['SpotInstanceRequests'][0]['SpotInstanceRequestId']

    spot_data_list = []
    wait_time = 0
    while True:
        time.sleep(5)
        wait_time += 5
        spot_request = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])['SpotInstanceRequests'][0]
        code = spot_request['Status']['Code']
        spot_data_list.append([instance_type, az_id, code, datetime.datetime.utcnow()])

        if code == 'fulfilled' or code == 'capacity-not-available':
            send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), f"{code} 됨")
            save_status_code(spot_data_list, instance_type, az_id)
            break
        if wait_time > 60:
            send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), "60초를 기다렸으나 fulfill, interrupt되지 않음")
            save_status_code(spot_data_list, instance_type, az_id)
            break

    if code == 'fulfilled':
        try:
            spot_instance_id = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])['SpotInstanceRequests'][0]['InstanceId']
            ec2.terminate_instances(InstanceIds=[spot_instance_id])
        except Exception as e:
            send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), f"!!!인스턴스 삭제 실패!!! \n{e}")

    try:
        response = ec2.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id])
    except Exception as e:
        send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), f"!!!스팟 요청 삭제 실패!!! \n{e}")

def spot_ding_dong_main(instance_type, ami_id, az_name, az_id, ding_dong_period):


    create_spot_instance(instance_type, ami_id, az_name, az_id)
    stop_time = datetime.datetime.now() + datetime.timedelta(hours=24)
    stop_time = stop_time.astimezone(pytz.UTC)
    next_ding_dong_time = launch_time.astimezone(pytz.UTC)
    while True:
        current_time = datetime.datetime.now()
        current_time = current_time.astimezone(pytz.UTC)

        if current_time > next_ding_dong_time:
            create_spot_instance(instance_type, ami_id, az_name, az_id)
            next_ding_dong_time = current_time + datetime.timedelta(minutes=ding_dong_period)

        if current_time > stop_time:
            send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), "실험 인스턴스 정지")
            break



if __name__ == "__main__":
    region_ami = pickle.load(open('../data/region_ami_dict.pkl', 'rb'))  # {x86/arm: {region: (ami-id, ami-info), ...}}
    az_map_dict = pickle.load(open('../data/az_map_dict.pkl', 'rb'))  # {(region, az-id): az-name, ...}
    arm64_family = ['a1', 't4g', 'c7g', 'c7gn', 'c6g', 'c6gd', 'c6gn', 'im4gn', 'is4gen', 'm7g', 'm6g', 'm6gd', 'r7g', 'r6g', 'r6gd', 'x2gd']

    ### Spot Checker Arguments
    parser = argparse.ArgumentParser(description='Spot Checker Workload Information')
    parser.add_argument('--instance_type', type=str, default='t2.large')
    parser.add_argument('--region', type=str, default='ap-southeast-2')
    parser.add_argument('--az_id', type=str, default='apse2-az2')
    parser.add_argument('--ding_dong_period', type=int, default=30)
    args = parser.parse_args()

    ### Spot Checker Arguments Parsing
    instance_type = args.instance_type
    instance_family = instance_type.split('.')[0]
    instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'
    region = args.region
    az_id = args.az_id
    ding_dong_period = args.ding_dong_period

    az_name = az_map_dict[(region, az_id)]
    ami_id = region_ami[instance_arch][region][0]

    send_slack_message(instance_type, az_id, launch_time.strftime('%Y-%m-%D %H:%M:%S'), "시작")
    spot_ding_dong_main(instance_type, ami_id, az_name, az_id, ding_dong_period)
