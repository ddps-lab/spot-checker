import boto3
import os
import time
import json

LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
PREFIX = os.environ.get('PREFIX')

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

    instance = response['Reservations'][0]['Instances'][0]

    # Check if instance has the test tag (Environment={PREFIX}-spot-test)
    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
    if tags.get('Environment') != f'{PREFIX}-spot-test':
        print(f"Instance {instance['InstanceId']} does not have tag Environment={PREFIX}-spot-test. Skipping.")
        return

    spot_request_id = instance['SpotInstanceRequestId']
    az = instance['Placement']['AvailabilityZone']
    instance_type = instance['InstanceType']
    request_describe = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_request_id])
    
    print(request_describe['SpotInstanceRequests'][0]['Type'])
    if request_describe['SpotInstanceRequests'][0]['Type'] == "one-time":
        return 0

    status = request_describe['SpotInstanceRequests'][0]['Status']
    code = status['Code']
    message = status['Message']
    update_time = status['UpdateTime'].isoformat()

    log_data = {
        "Timestamp": event['time'],
        "SpotRequestId": spot_request_id,
        "InstanceState": event['detail']['state'],
        "InstanceType" : instance_type,
        "AZ" : az,
        "Code" : code,
        "Message" : message,
        "UpdateTime" : update_time,
        "TagFilter": f"Environment={PREFIX}-spot-test"
    }
    create_log_event(json.dumps(log_data))

