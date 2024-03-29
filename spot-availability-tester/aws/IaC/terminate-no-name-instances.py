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
    # Get list of instances
    response = ec2.describe_instances(Filters=[
        {'Name': 'instance-lifecycle', 'Values': ['spot']},
        {
            'Name': 'instance-state-name',
            'Values': ['pending', 'running', 'stopping', 'stopped']
        }
    ])

    if not response['Reservations']:
        return

    instances_logs = []
    instances_list = []
    instances_to_terminate = []

    # Find instances without a Name tag
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name_tags = [tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name']
            if ((not name_tags or not name_tags[0]) and (instance['Instances'][0]['VpcId'] == VPC_ID)):
                instances_list.append(instance['InstanceId'])
                launch_time = (instance['LaunchTime']).timestamp()
                terminate_time = time.time()
                tmp_data = {
                    "LaunchTime": launch_time,
                    "TerminateTime": terminate_time,
                    "BillingTime": terminate_time - launch_time,
                    "InstanceId": instance['InstanceId'],
                    "InstanceState": instance['State']['Name'],
                    "InstanceType": instance['InstanceType'],
                    "AvailabilityZone": instance['Placement']['AvailabilityZone'],
                }
                instances_logs.append(tmp_data)

    # Terminate instances without a Name tag
    if instances_to_terminate:
        ec2.terminate_instances(InstanceIds=instances_to_terminate)
        print(f"Terminated instances: {', '.join(instances_to_terminate)}")
    else:
        print("No instances to terminate.")

    for log in instances_logs:
        create_log_event(json.dumps(log))