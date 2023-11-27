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

    instance_details = ec2.describe_instances(
        InstanceIds=instances_to_terminate,
        Filters=[{'Name': 'instance-lifecycle', 'Values': ['spot']}]
    )

    if not instance_details['Reservations']:
        return

    spot_instance_request_id = instance_details['Reservations'][0]['Instances'][0]['SpotInstanceRequestId']
    spot_request_details = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_instance_request_id])
    tag = spot_request_details['SpotInstanceRequests'][0]['Tags'][0]['Value']

    if tag == 'spot-ddd':
        log_data = {
            "Timestamp": time.time(),
            "InstanceId": event['detail']['instance-id'],
            "InstanceState": event['detail']['state'],
            "Region": event['region'],
        }
        create_log_event(json.dumps(log_data))

        ec2.terminate_instances(InstanceIds=instances_to_terminate)
        print(f"Terminated instances: {event['detail']['instance-id']}")

