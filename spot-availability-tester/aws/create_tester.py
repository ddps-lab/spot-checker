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


def main():
    # Change this
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = variables.log_group_name
    log_stream_name = variables.log_stream_name

    session = boto3.Session(profile_name=awscli_profile)
    logs_client = session.client('logs')

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
        print(f"Created log stream {log_stream_name}.")
    else:
        print(f"Log stream {log_stream_name} already exists.")

    tf_project_dir = "./IaC"
    with open('regions.txt', 'r') as file:
        regions = file.readlines()

    instance_type_data = {}
    availability_zone_data = {}
    for region in regions:
        tmp_data = pd.read_csv(f'./test_data/{region}.csv')
        instance_type_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['InstanceType'].tolist())
        availability_zone_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['AZ'].tolist())

    os.chdir(tf_project_dir)
    for region in regions:
        run_command(["terraform", "workspace", "new", f"{region}"])
        run_command(["terraform", "init"])
        run_command(["terraform", "apply", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name={log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]"])


if __name__ == "__main__":
    main()
