import subprocess
import sys
import os
import pandas as pd
import variables
import boto3

def run_command(command):
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(err.decode())
        sys.exit(1)
    else:
        print(out.decode())

def create_log_stream(log_group_name, log_stream_name, logs_client):
    response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name
    )

    # log stream이 존재하지 않는 경우 생성
    if not response['logStreams'] or response['logStreams'][0]['logStreamName'] != log_stream_name:
        logs_client.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
    else:
        print(f"Log stream {log_stream_name} already exists.")

def main():
    # Change this
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = f"{prefix}-spot-availability-tester-log"
    spot_log_stream_name = f"{variables.log_stream_name}-spot"
    terminate_log_stream_name = f"{variables.log_stream_name}-terminate"
    pending_log_stream_name = f"{variables.log_stream_name}-pending"
    spawn_rate = "rate(1 minute)" if variables.spawn_rate == 1 else f"rate({variables.spawn_rate} minutes)"
    use_ec2 = variables.use_ec2
    describe_rate = variables.describe_rate

    tf_project_dir = "./IaC"
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines()]

    instance_type_data = {}
    availability_zone_data = {}
    for region in regions:
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')

        create_log_stream(log_group_name, spot_log_stream_name, logs_client)
        create_log_stream(log_group_name, terminate_log_stream_name, logs_client)
        create_log_stream(log_group_name, pending_log_stream_name, logs_client)

        tmp_data = pd.read_csv(f'./test_data/{region}.csv')
        instance_type_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['InstanceType'].tolist())
        availability_zone_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['AZ'].tolist())

    os.chdir(tf_project_dir)
    for region in regions:
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        run_command(["terraform", "workspace", "new", f"{region}"])
        run_command(["terraform", "init"])
        run_command(["terraform", "apply", "--parallelism=150", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"spot_log_stream_name={spot_log_stream_name}", "--var", f"terminate_log_stream_name={terminate_log_stream_name}", "--var", f"pending_log_stream_name={pending_log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]", "--var", f"lambda_rate={spawn_rate}", "--var", f"use_ec2={use_ec2}", "--var", f"describe_rate={describe_rate}"])

if __name__ == "__main__":
    main()
