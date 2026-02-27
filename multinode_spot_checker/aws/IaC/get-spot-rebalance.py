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
        logGroupName=LOG_GROUP_NAME,
        logStreamName=LOG_STREAM_NAME,
        logEvents=[log_event]
    )


def lambda_handler(event, context):
    instance_id = event['detail']['instance-id']

    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-lifecycle', 'Values': ['spot']}],
        InstanceIds=[instance_id]
    )

    if not response['Reservations']:
        return

    instance = response['Reservations'][0]['Instances'][0]
    spot_request_id = instance.get('SpotInstanceRequestId', '')
    az = instance['Placement']['AvailabilityZone']
    instance_type = instance['InstanceType']

    log_data = {
        "EventType": "RebalanceRecommendation",
        "Timestamp": event['time'],
        "InstanceId": instance_id,
        "SpotRequestId": spot_request_id,
        "InstanceType": instance_type,
        "AZ": az
    }
    create_log_event(json.dumps(log_data))
