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
    # Change this
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = f"{prefix}-ondemand-checker-multinode-log"
    log_stream_name_chage_status = f"{variables.log_stream_name_chage_status}"
    log_stream_name_init_time = f"{variables.log_stream_name_init_time}"

    tf_project_dir = "./IaC"
    session = boto3.Session(profile_name=awscli_profile, region_name=region)
    logs_client = session.client('logs')
    create_log_stream(log_group_name, log_stream_name_chage_status, logs_client)
    create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
    os.chdir(tf_project_dir)

    session = boto3.Session(profile_name=awscli_profile, region_name=region)
    run_command(["terraform", "workspace", "new", "ondemand-checker-multinode"])
    run_command(["terraform", "init"])
    run_command(["terraform", "apply", "--parallelism=150", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name_chage_status={log_stream_name_chage_status}", "--var", f"log_stream_name_init_time={log_stream_name_init_time}"])
   
if __name__ == "__main__":
    main()
