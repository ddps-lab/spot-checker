import boto3
import os
import time
import json

LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
VPC_ID = os.environ['VPC_ID']

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
        Filters=[{'Name': 'instance-lifecycle', 'Values': ['spot']}],
        InstanceIds=instances_to_terminate
    )

    if not response['Reservations']:
        return

    instances_to_terminate_vpc = response['Reservations'][0]['Instances'][0]['VpcId']
    if instances_to_terminate_vpc == VPC_ID:
        log_data = {
            "Timestamp": time.time(),
            "InstanceId": event['detail']['instance-id'],
            "InstanceState": event['detail']['state'],
            "Region": event['region'],
        }
        create_log_event(json.dumps(log_data))

        ec2.terminate_instances(InstanceIds=instances_to_terminate)
        print(f"Terminated instances: {event['detail']['instance-id']}")
