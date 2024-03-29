import subprocess
import sys
import os
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
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = f"{prefix}-spot-checker-multinode-log"
    log_stream_name_status_change = f"{variables.log_stream_name_change_status}"
    log_stream_name_init_time = f"{variables.log_stream_name_init_time}"

    tf_project_dir = "./IaC-cloudwatchlogs"
    
    os.chdir(tf_project_dir)
    
    run_command(["terraform", "workspace", "new", "spot-checker-multinode"])
    run_command(["terraform", "init"])
    run_command(["terraform", "apply", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}"])

    session = boto3.Session(profile_name=awscli_profile, region_name="us-east-2")
    logs_client = session.client('logs')
    create_log_stream(log_group_name, log_stream_name_status_change, logs_client)
    create_log_stream(log_group_name, log_stream_name_init_time, logs_client)

if __name__ == "__main__":
    main()
