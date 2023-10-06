import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # Get list of instances
    response = ec2.describe_instances()
    
    # Find instances without a Name tag
    instances_to_terminate = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name_tags = [tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name']
            if ((not name_tags or not name_tags[0]) and instance['State']['Name'] != "terminated"):
                instances_to_terminate.append(instance['InstanceId'])
                
    # Terminate instances without a Name tag
    if instances_to_terminate:
        ec2.terminate_instances(InstanceIds=instances_to_terminate)
        print(f"Terminated instances: {', '.join(instances_to_terminate)}")
    else:
        print("No instances to terminate.")
