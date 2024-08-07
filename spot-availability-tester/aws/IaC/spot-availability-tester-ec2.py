import boto3
import os
import time
import json
import base64

ec2 = boto3.client('ec2')
logs_client = boto3.client('logs')
dynamodb = boto3.client('dynamodb')

ARM_INSTANCE_TYPES = ['a1', 't4g', 'c7g', 'c7gn', 'c6g', 'c6gd', 'c6gn', 'im4gn', 'is4gen', 'm7g', 'm6g', 'm6gd', 'r7g',
                      'r6g', 'r6gd', 'x2gd']
ARM_INSTANCE_PREFIX = ['g', 'gn', 'gd', 'gen']

X86_AMI_ID = os.environ['X86_AMI_ID']
ARM_AMI_ID = os.environ['ARM_AMI_ID']
VPC_ID = os.environ['VPC_ID']
SUBNET_IDS = json.loads(os.environ['SUBNET_IDS'])
SUBNET_AZ_NAMES = json.loads(os.environ['SUBNET_AZ_NAMES'])
SECURITY_GROUP_IDS = [os.environ['SECURITY_GROUP_ID']]
LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
PREFIX = os.environ['PREFIX']
FAILED_CODES = ["capacity-not-available",
                "price-too-low",
                "not-scheduled-yet",
                "launch-group-constraint",
                "az-group-constraint",
                "placement-group-constraint",
                "constraint-not-fulfillable",
                "bad-parameters"]
SUCCESS_CODE = ["pending-fulfillment",
                "fulfilled"]



def check_throttling(instance_type):
    instance_type  = instance_type.split('.')[0]
    if instance_type[:3] == 'trn':
        instance_category = "TRN"
    elif instance_type[:3] == 'inf':
        instance_category = "INF"
    elif instance_type[:2] == 'dl':
        instance_category = "DL"
    elif instance_type[:2] == 'vt':
        instance_category = "G_VT"
    elif instance_type[:1] == 'g':
        instance_category = "G_VT"
    elif instance_type[:1] == 'p':
        if instance_type[1] == '5':
            instance_category = "P5"
        else:
            instance_category = "P2_P3_P4"
    elif instance_type[:1] == 'f':
        instance_category = "F"
    elif instance_type[:1] == 'x':
        instance_category = "X"
    else:
        instance_category = "STANDARD"
    response = dynamodb.get_item(TableName=f"{PREFIX}-DDDCHECKTABLE", Key={'TABLE':{'N':'1'}})['Item'][instance_category]['BOOL']
    return response


def create_log_event(result):
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': result
    }
    logs_client.put_log_events(
        logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME, logEvents=[log_event])


def test_spot_instance_available(instance_type, availability_zone, ddd_request_time):
    global ami_id
    instance_family = str(instance_type.split(".")[0])
    if instance_family in ARM_INSTANCE_TYPES:
        ami_id = ARM_AMI_ID
        architecture = "arm64"
    elif instance_family.endswith(tuple(ARM_INSTANCE_PREFIX)):
        ami_id = ARM_AMI_ID
        architecture = "arm64"
    else:
        ami_id = X86_AMI_ID
        architecture = "x86"

    print(f"Instance Type: {instance_type}, Architecture: {architecture}")

    user_data = """#!/bin/bash
    shutdown -h now"""
    user_data_encoded = base64.b64encode(user_data.encode()).decode()

    spot_request = ec2.request_spot_instances(
        InstanceCount=1,
        Type='one-time',
        LaunchSpecification={
            'ImageId': ami_id,
            'InstanceType': instance_type,
            'SubnetId': SUBNET_IDS[SUBNET_AZ_NAMES.index(availability_zone)],
            'SecurityGroupIds': SECURITY_GROUP_IDS,
            'Placement': {
                "AvailabilityZone": availability_zone
            },
            'UserData': user_data_encoded
        },
    )

    create_time = spot_request['SpotInstanceRequests'][0]['CreateTime']
    spot_request_id = spot_request['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    global code
    print("start describe")
    while True:
        response = ""
        while True:
            try:
                response = ec2.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_request_id])
                break
            except:
                time.sleep(0.1)
                print("retry describe")
        print("finish describe")
        request = response['SpotInstanceRequests'][0]
        if request['Status']['Code'] in FAILED_CODES:
            code = "fail"
            if request['Status']['Code'] == "bad-parameters":
                print("bad-parameters!")
                print(
                    f"Availability zone: {availability_zone}, Subnet ID: {SUBNET_IDS[ord(availability_zone[-1]) - ord('a')]}, Instance Type: {instance_type}")
            break
        elif request['Status']['Code'] in SUCCESS_CODE:
            code = "success"
            break
        else:
            time.sleep(0.1)

    status_update_time = response['SpotInstanceRequests'][0]['Status']['UpdateTime']
    cancel_spot_request = ec2.cancel_spot_instance_requests(
        SpotInstanceRequestIds=[spot_request_id]
    )

    result = {
        "InstanceType": instance_type,
        "AZ": availability_zone,
        "Timestamp": time.time(),
        "Code": code,
        "RawCode": request['Status']['Code'],
        'RequestCreateTime': create_time.timestamp(),
        'StatusUpdateTime': status_update_time.timestamp(),
        "DDDRequestTime": ddd_request_time
    }
    return result


def lambda_handler(event, context):
    json_body = json.loads(event['body'])['inputs']

    if not check_throttling(json_body['instance_type']):
        return "throttling"
    result = test_spot_instance_available(json_body['instance_type'], json_body['availability_zone'], json_body['ddd_request_time'])
    create_log_event(json.dumps(result))
    return "finish"
