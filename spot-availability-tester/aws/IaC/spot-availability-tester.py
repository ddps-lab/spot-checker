import boto3
import os
import time
import json

ec2 = boto3.client('ec2')
logs_client = boto3.client('logs')

ARM_INSTANCE_TYPES = ['a1', 't4g', 'c7g', 'c7gn', 'c6g', 'c6gd', 'c6gn', 'im4gn', 'is4gen', 'm7g', 'm6g', 'm6gd', 'r7g', 'r6g', 'r6gd', 'x2gd']

X86_AMI_ID = os.environ['X86_AMI_ID']
ARM_AMI_ID = os.environ['ARM_AMI_ID']
VPC_ID = os.environ['VPC_ID']
SUBNET_IDS = json.loads(os.environ['SUBNET_IDS'])
SECURITY_GROUP_IDS = [os.environ['SECURITY_GROUP_ID']]
LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
FAILED_CODES = ["capacity-not-available",
                "price-too-low",
                "not-scheduled-yet",
                "launch-group-constraint",
                "az-group-constraint",
                "placement-group-constraint",
                "constraint-not-fulfillable"]
SUCCESS_CODE = ["pending-fulfillment",
                "fulfilled"]


def create_log_event(result):
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': result
    }
    logs_client.put_log_events(
        logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME, logEvents=[log_event])


def test_spot_instance_available(instance_type, availability_zone):
    global ami_id
    instance_family = instance_type.split(".")[0]
    if instance_family in ARM_INSTANCE_TYPES:
        ami_id = ARM_AMI_ID
    else:
        ami_id = X86_AMI_ID

    spot_request = ec2.request_spot_instances(
        InstanceCount=1,
        Type='one-time',
        LaunchSpecification={
            'ImageId': ami_id,
            'InstanceType': instance_type,
            'SubnetId': SUBNET_IDS[ord(availability_zone[-1]) - ord('a')],
            'SecurityGroupIds': SECURITY_GROUP_IDS,
            'Placement': {
                "AvailabilityZone": availability_zone
            }
        }
    )

    spot_request_id = spot_request['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    global code
    while True:
        response = ""
        while True:
            try:
                response = ec2.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_request_id])
                break
            except:
                print("retry")
        request = response['SpotInstanceRequests'][0]
        if request['Status']['Code'] in FAILED_CODES:
            code = "fail"
            break
        elif request['Status']['Code'] in SUCCESS_CODE:
            code = "success"
            break

    cancel_spot_request = ec2.cancel_spot_instance_requests(
        SpotInstanceRequestIds=[spot_request_id]
    )

    result = {
        "InstanceType": instance_type,
        "AZ": availability_zone,
        "Timestamp": time.time(),
        "Code": code,
        "RawCode": request['Status']['Code']
    }
    return result


def lambda_handler(event, context):
    result = test_spot_instance_available(
        event['instance_type'], event['availability_zone'])
    create_log_event(json.dumps(result))
    return "finish"
