# Not For Lambda, Just Run in AWS EC2
# Need regions.txt in same directory
import boto3
import spot_quota_checker_variables
import time
import pickle
import json

AWS_CLI_PROFILE_NAME = spot_quota_checker_variables.awscli_profile
LOG_GROUP_NAME = f"{spot_quota_checker_variables.prefix}-spot-quota-checker-log"
LOG_STREAM_NAME = spot_quota_checker_variables.log_stream_name
with open('all_vcpu_info.pkl', 'rb') as f:
    ALL_VCPU_INFO = pickle.load(f)
with open('all_vcpu_quota_info.pkl', 'rb') as f:
    ALL_QUOTA_INFO = pickle.load(f)

def create_log_stream(log_group_name, log_stream_name, boto3_session):
    logs_client = boto3_session.client('logs')
    response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name
    )

    # log stream이 존재하지 않는 경우 생성
    if not response['logStreams'] or response['logStreams'][0]['logStreamName'] != log_stream_name:
        logs_client.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
    else:
        print(f"Log stream {log_stream_name} already exists.")


def get_vcpu_number(region, instance_type):
    return int(ALL_VCPU_INFO.get(region, {}).get(instance_type, None))

def get_quota_number(region, quota_name):
    return int(ALL_QUOTA_INFO.get(region, {}).get(quota_name, None))

def create_log_event(result, boto3_session):
    logs_client = boto3_session.client('logs')
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': result
    }
    logs_client.put_log_events(
        logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME, logEvents=[log_event])

def check_spot_quota(region, boto3_session):
    ec2_client = boto3_session.client('ec2')
    
    vCPU_Counts = {
        "INF": 0,
        "TRN": 0,
        "DL": 0,
        "G_VT": 0,
        "P5": 0,
        "P2_P3_P4": 0,
        "F": 0,
        "X": 0,
        "STANDARD": 0
    }

    while True:
        try:
            spot_request_response = ec2_client.describe_spot_instance_requests(
                Filters=[{
                    'Name': 'state',
                    'Values': ['open', 'active', 'failed']
                }])
            break
        except:
            time.sleep(1)
    while True:
        try:
            ec2_instance_response = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': ['pending', 'running', 'shutting-down', 'stopping', 'stopped']
                    },
                    {
                        'Name': 'instance-lifecycle',
                        'Values': ['spot']
                    }
                ])
            break
        except:
            time.sleep(1)
    
    for spot_request in spot_request_response['SpotInstanceRequests']:
        instance_type = spot_request['LaunchSpecification']['InstanceType']
        vcpu_num = get_vcpu_number(region, instance_type)
        
        if instance_type[:3] == 'trn':
            vCPU_Counts['TRN'] = vCPU_Counts['TRN'] + vcpu_num
        elif instance_type[:3] == 'inf':
            vCPU_Counts['INF'] = vCPU_Counts['INF'] + vcpu_num
        elif instance_type[:2] == 'dl':
            vCPU_Counts['DL'] = vCPU_Counts['DL'] + vcpu_num
        elif instance_type[:2] == 'vt':
            vCPU_Counts['G_VT'] = vCPU_Counts['G_VT'] + vcpu_num
        elif instance_type[:1] == 'g':
            vCPU_Counts['G_VT'] = vCPU_Counts['G_VT'] + vcpu_num
        elif instance_type[:1] == 'p':
            if instance_type[1] == '5':
                vCPU_Counts['P5'] = vCPU_Counts['P5'] + vcpu_num
            else:
                vCPU_Counts['P2_P3_P4'] = vCPU_Counts['P2_P3_P4'] + vcpu_num
        elif instance_type[:1] == 'f':
            vCPU_Counts['F'] = vCPU_Counts['F'] + vcpu_num
        elif instance_type[:1] == 'x':
            vCPU_Counts['X'] = vCPU_Counts['X'] + vcpu_num
        else:
            vCPU_Counts['STANDARD'] = vCPU_Counts['STANDARD'] + vcpu_num
        
    
    for ec2_instance in ec2_instance_response['Reservations']:
        spot_duplicate_check = 0
        for spot_request in spot_request_response['SpotInstanceRequests']:
            if 'InstanceId' not in spot_request:
                continue
            if spot_request['InstanceId'] == ec2_instance['Instances'][0]['InstanceId']:
                spot_duplicate_check = 1
        if spot_duplicate_check == 1:
            continue
        instance_type = ec2_instance['Instances'][0]['InstanceType']
        vcpu_num = get_vcpu_number(region, instance_type)

        if instance_type[:3] == 'trn':
            vCPU_Counts['TRN'] = vCPU_Counts['TRN'] + vcpu_num
        elif instance_type[:3] == 'inf':
            vCPU_Counts['INF'] = vCPU_Counts['INF'] + vcpu_num
        elif instance_type[:2] == 'dl':
            vCPU_Counts['DL'] = vCPU_Counts['DL'] + vcpu_num
        elif instance_type[:2] == 'vt':
            vCPU_Counts['G_VT'] = vCPU_Counts['G_VT'] + vcpu_num
        elif instance_type[:1] == 'g':
            vCPU_Counts['G_VT'] = vCPU_Counts['G_VT'] + vcpu_num
        elif instance_type[:1] == 'p':
            if instance_type[1] == '5':
                vCPU_Counts['P5'] = vCPU_Counts['P5'] + vcpu_num
            else:
                vCPU_Counts['P2_P3_P4'] = vCPU_Counts['P2_P3_P4'] + vcpu_num
        elif instance_type[:1] == 'f':
            vCPU_Counts['F'] = vCPU_Counts['F'] + vcpu_num
        elif instance_type[:1] == 'x':
            vCPU_Counts['X'] = vCPU_Counts['X'] + vcpu_num
        else:
            vCPU_Counts['STANDARD'] = vCPU_Counts['STANDARD'] + vcpu_num

    region_vCPU_Percent = {
        key: 0 if vCPU_Counts[key] == 0 or ALL_QUOTA_INFO[region][key] == 0 else vCPU_Counts[key] / ALL_QUOTA_INFO[region][key]
        for key in vCPU_Counts
    }

    result = {
        "Region": region,
        "vCPU_Count": vCPU_Counts,
        "region_vCPU_Percent": region_vCPU_Percent,
        "Timestamp": time.time(),
    }
    return result


def main():
    boto3_session_list = []
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines()]

    for region in regions:
        if AWS_CLI_PROFILE_NAME == "":
            boto3_session = boto3.Session(region_name=region)
        else:
            boto3_session = boto3.Session(
                profile_name=AWS_CLI_PROFILE_NAME, region_name=region)
        boto3_session_list.append(boto3_session)

    for region_index, region in enumerate(regions):
        create_log_stream(LOG_GROUP_NAME, LOG_STREAM_NAME, boto3_session_list[region_index])

    while True:
        for region_index, region in enumerate(regions):
            result = check_spot_quota(region, boto3_session_list[region_index])
            create_log_event(json.dumps(result), boto3_session_list[region_index])
        time.sleep(5)


if __name__ == '__main__':
    main()
