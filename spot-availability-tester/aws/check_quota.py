import boto3
import variables

awscli_profile = variables.awscli_profile

with open('regions.txt', 'r', encoding='utf-8') as file:
    regions = [line.strip() for line in file.readlines()]

for region in regions:
    session = boto3.Session(profile_name=awscli_profile, region_name=region)
    quota_client = session.client('service-quotas')

    response = quota_client.get_service_quota(
        ServiceCode='ec2',
        #standard
        # QuotaCode='L-34B43A08'
        #g,vt
        # QuotaCode='L-3819A6DF'
        #inf
        # QuotaCode='L-B5D1601B'
        #all f
        QuotaCode='L-88CF9481'
    )

    print(f"Region: {region}, {response['Quota']['Value']}")