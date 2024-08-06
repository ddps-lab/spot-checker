import boto3
import pickle
import variables

AWS_CLI_PROFILE_NAME = variables.awscli_profile


def get_all_instance_types(boto3_session):
    ec2_client = boto3_session.client('ec2')
    instance_types_data = {}
    next_token = None

    while True:
        if next_token:
            response = ec2_client.describe_instance_types(NextToken=next_token, MaxResults=100)
        else:
            response = ec2_client.describe_instance_types(MaxResults=100)

        for instance_type in response['InstanceTypes']:
            instance_type_name = instance_type['InstanceType']
            vcpu_count = instance_type['VCpuInfo']['DefaultVCpus']
            instance_types_data[instance_type_name] = vcpu_count

        next_token = response.get('NextToken')  # 다음 페이지를 가져오기 위한 토큰
        if not next_token:
            break  # 더 이상의 페이지가 없으면 루프를 종료한다.

    return instance_types_data


boto3_session_list = []
with open('regions.txt.sample', 'r', encoding='utf-8') as file:
    regions = [line.strip() for line in file.readlines()]

for region in regions:
    if AWS_CLI_PROFILE_NAME == None:
        boto3_session = boto3.Session(region_name=region)
    else:
        boto3_session = boto3.Session(
            profile_name=AWS_CLI_PROFILE_NAME, region_name=region)
    boto3_session_list.append(boto3_session)

all_instance_types_data = {}
for region_index, region in enumerate(regions):
    instance_types_data = get_all_instance_types(boto3_session_list[region_index])
    all_instance_types_data[region] = instance_types_data

with open('./IaC/quota-availability-updater-src/all_vcpu_info.pkl', 'wb') as f:
    pickle.dump(all_instance_types_data, f)