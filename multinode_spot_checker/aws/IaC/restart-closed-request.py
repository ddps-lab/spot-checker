import boto3
import os
from collections import defaultdict
import time


ec2_client = boto3.client('ec2')
exp_size = int(os.getenv('EXP_SIZE', 10))

def lambda_handler(event, context):
    count_dict = defaultdict(int)
    ami_dict = {}
    valid_until_dict = {}

    response = ec2_client.describe_spot_instance_requests(
        Filters=[
            {'Name': 'state', 'Values': ['active']}, 
        ]
    )

    for request in response.get('SpotInstanceRequests', []):
        instance_type = request['LaunchSpecification']['InstanceType']
        availability_zone = request['LaunchedAvailabilityZone']
        ami_id = request['LaunchSpecification']['ImageId']
        valid_until = request.get('ValidUntil')

        count_dict[(instance_type, availability_zone)] += 1
        ami_dict[instance_type] = ami_id
        valid_until_dict[instance_type] = valid_until

    for (instance_type, az), count in count_dict.items():
        if count < exp_size:
            requests_needed = exp_size - count
            print(f"Adding {requests_needed} spot requests for {instance_type} in {az}")

            ami_id = ami_dict.get(instance_type)
            valid_until = valid_until_dict.get(instance_type)

            if not ami_id:
                print(f"No AMI found for instance type {instance_type}. Skipping...")

            for _ in range(requests_needed):
                ec2_client.request_spot_instances(
                    InstanceCount=1,
                    Type="persistent",
                    ValidUntil=valid_until,
                    LaunchSpecification={
                        'InstanceType': instance_type,
                        'ImageId': ami_id,
                        'Placement': {
                            'AvailabilityZone': az
                        },
                        'IamInstanceProfile': {
                            'Arn': 'arn:aws:iam::741926482963:instance-profile/EC2toEC2_CW' # IAM ARN for CloudWatch access
                        },
                        # ETC

                    }
                )
                time.sleep(0.1)

    return {
        'statusCode': 200,
        'body': f'Completed spot request check'
    }
