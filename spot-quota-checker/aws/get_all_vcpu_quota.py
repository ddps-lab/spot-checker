import boto3
import pickle
import variables

AWS_CLI_PROFILE_NAME = variables.awscli_profile
QUOTA_CODES = {
    "INF": "L-B5D1601B",
    "TRN": "L-6B0D517C",
    "DL": "L-85EED4F7",
    "G_VT": "L-3819A6DF",
    "P5": "L-C4BD4855",
    "P2_P3_P4": "L-7212CCBC",
    "F": "L-88CF9481",
    "X": "L-E3A00192",
    "STANDARD": "L-34B43A08"
}

with open('regions.txt.sample', 'r', encoding='utf-8') as file:
    regions = [line.strip() for line in file.readlines()]

all_region_vcpu_quota_data = {}
for region in regions:
    all_region_vcpu_quota_data[region] = {}
    session = boto3.Session(profile_name=AWS_CLI_PROFILE_NAME, region_name=region)
    quota_client = session.client('service-quotas')

    for quota_name, quota_code in QUOTA_CODES.items():
        response = quota_client.get_service_quota(
            ServiceCode='ec2',
            QuotaCode=quota_code
        )
        all_region_vcpu_quota_data[region][quota_name] = response['Quota']['Value']

with open('all_vcpu_quota_info.pkl', 'wb') as f:
    pickle.dump(all_region_vcpu_quota_data, f)

print(all_region_vcpu_quota_data)