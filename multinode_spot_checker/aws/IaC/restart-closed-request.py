import boto3
import os
import sys
from collections import defaultdict
import time


LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
EXP_SIZE = int(os.environ['EXP_SIZE'])
IAM_INSTANCE_PROFILE_ARN = os.environ['IAM_INSTANCE_PROFILE_ARN']

ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    count_dict = defaultdict(int)
    ami_dict = {}
    valid_until_dict = {}

    response = ec2_client.describe_spot_instance_requests(
        Filters=[
            {'Name': 'state', 'Values': ['active', 'open']},
            {'Name': 'type', 'Values': ['persistent']}
        ]
    )

    closed_response = ec2_client.describe_spot_instance_requests(
        Filters=[
            {'Name': 'state', 'Values': ['closed', 'failed']},
            {'Name': 'type', 'Values': ['persistent']}
        ]
    )

    for request in response.get('SpotInstanceRequests', []):
        # print(request)
        instance_type = request['LaunchSpecification']['InstanceType']

        try:
            availability_zone = request['LaunchedAvailabilityZone']
        except KeyError:
            availability_zone = request['LaunchSpecification']['Placement']['AvailabilityZone']

        ami_id = request['LaunchSpecification']['ImageId']
        valid_until = request.get('ValidUntil')

        count_dict[(instance_type, availability_zone)] += 1
        ami_dict[instance_type] = ami_id
        valid_until_dict[instance_type] = valid_until

    print(closed_response)
    for request in closed_response.get('SpotInstanceRequests', []):
        instance_type = request['LaunchSpecification']['InstanceType']

        try:
            availability_zone = request['LaunchedAvailabilityZone']
        except KeyError:
            availability_zone = request['LaunchSpecification']['Placement']['AvailabilityZone']

        ami_id = request['LaunchSpecification']['ImageId']
        valid_until = request.get('ValidUntil')

        if (instance_type, availability_zone) in count_dict:
            continue

        count_dict[(instance_type, availability_zone)] = 0
        ami_dict[instance_type] = ami_id
        valid_until_dict[instance_type] = valid_until


    print(count_dict)
    for (instance_type, az), count in count_dict.items():
        if count < EXP_SIZE:
            requests_needed = EXP_SIZE - count
            print(f"{requests_needed} instance missing.")
            print(f"Adding 1 spot requests for {instance_type} in {az}")

            ami_id = ami_dict.get(instance_type)
            valid_until = valid_until_dict.get(instance_type)

            if not ami_id:
                print(f"No AMI found for instance type {instance_type}. Skipping...")

            ec2_client.request_spot_instances(
                InstanceCount=requests_needed,
                Type="persistent",
                ValidUntil=valid_until,
                LaunchSpecification={
                    'InstanceType': instance_type,
                    'ImageId': ami_id,
                    'Placement': {
                        'AvailabilityZone': az
                    },
                    'IamInstanceProfile': {
                        'Arn': IAM_INSTANCE_PROFILE_ARN
                    },
                    # ETC

                },
                TagSpecifications=[
                    {
                        'ResourceType': 'spot-instances-request',
                        'Tags': [
                            {'Key': 'Project', 'Value': 'spot-checker-multinode'},
                            {'Key': 'Environment', 'Value': 'spot-test'}
                        ]
                    }
                ]
            )
            time.sleep(0.1)

    return {
        'statusCode': 200,
        'body': f'Completed spot request check'
    }
