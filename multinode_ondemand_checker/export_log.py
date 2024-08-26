import boto3
import variables
import json
import os

prefix = variables.prefix
awscli_profile = variables.awscli_profile
region = variables.region
log_group_name = f"{prefix}-ondemand-checker-multinode-log"
log_stream_name_chage_status = variables.log_stream_name_chage_status
log_stream_name_init_time = variables.log_stream_name_init_time
instancetype = variables.instance_type
az = variables.az_id
instance_count = variables.instance_count

# Boto3 클라이언트 초기화
session = boto3.Session(profile_name=awscli_profile, region_name=region)
client = session.client('logs')

sps = "sps1"
os.mkdir(f"./log/{sps}/{instancetype}_{az}_{instance_count}_{log_group_name}")
for log_stream_name in [log_stream_name_chage_status, log_stream_name_init_time]:
    next_token = None
    log_data = []
    # 로그 스트림에서 로그 이벤트를 반복적으로 가져오기
    while True:
        if next_token:
            response = client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                nextToken=next_token
            )
        else:
            response = client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name
            )


        log_data.extend(response['events'])
        next_token = response['nextForwardToken']
        if not response['events']:
            break

    with open(f'./log/{sps}/{instancetype}_{az}_{instance_count}_{log_group_name}/{instancetype}_{az}_{instance_count}_{log_stream_name}.json', 'w') as json_file:
        json.dump(log_data, json_file, indent=4)
    print(f'{instancetype}_{az}_{instance_count}_{log_stream_name}.json', "로그 다운로드 완료")
