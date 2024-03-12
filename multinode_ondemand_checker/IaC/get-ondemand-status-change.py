import boto3
import os
import time
import json

LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']

ec2 = boto3.client('ec2')
logs_client = boto3.client('logs')

def create_log_event(result):
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': result
    }
    logs_client.put_log_events(
        logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME, logEvents=[log_event])

def lambda_handler(event, context):
    instances_to_terminate = []
    instances_to_terminate.append(event['detail']['instance-id'])
    response = ec2.describe_instances(
        InstanceIds=instances_to_terminate
    )

    if not response['Reservations']:
        return
    print(event)

    instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
    az = response['Reservations'][0]['Instances'][0]['Placement']['AvailabilityZone']
    instance_type = response['Reservations'][0]['Instances'][0]['InstanceType']
    status = response['Reservations'][0]['Instances'][0]['StateReason']
    code = status['Code']
    message = status['Message']
    update_time = response['Reservations'][0]['Instances'][0]['LaunchTime'].isoformat()

    log_data = {
        "Timestamp": event['time'],
        "SpotRequestId": instance_id,
        "InstanceState": event['detail']['state'],
        "InstanceType" : instance_type,
        "AZ" : az,
        "Code" : code,
        "Message" : message,
        "UpdateTime" : update_time
    }
    create_log_event(json.dumps(log_data))