import subprocess
import sys
import os
import pandas as pd
import variables
import boto3
import time

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

def delete_cloudwatch_log_group(log_group_name, logs_client):
    try:
        response = logs_client.delete_log_group(
            logGroupName=log_group_name
        )
        print(f"Log group {log_group_name} deleted successfully.")
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group {log_group_name} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = f"{prefix}-spot-availability-tester-log"
    spot_log_stream_name = f"{variables.log_stream_name}-spot"
    terminate_log_stream_name = f"{variables.log_stream_name}-terminate"
    pending_log_stream_name = f"{variables.log_stream_name}-pending"
    spawn_rate = "rate(1 minute)" if variables.spawn_rate == 1 else f"rate({variables.spawn_rate} minutes)"
    describe_rate = variables.describe_rate

    tf_project_dir = "./IaC"
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines()]

    instance_type_data = {}
    availability_zone_data = {}
    for region in regions:
        tmp_data = pd.read_csv(f'./test_data/{region}.csv')
        instance_type_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['InstanceType'].tolist())
        availability_zone_data[f"{region}"] = ",".join(f'"{item}"' for item in tmp_data['AZ'].tolist())

    os.chdir(tf_project_dir)

    for region in regions:
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session.client('logs')
        run_command(["terraform", "workspace", "select", "-or-create", f"{region}"])
        run_command(["terraform", "destroy", "--parallelism=150", "--target=module.spot-availability-tester", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"spot_log_stream_name={spot_log_stream_name}", "--var", f"terminate_log_stream_name={terminate_log_stream_name}", "--var", f"pending_log_stream_name={pending_log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]", "--var", f"lambda_rate={spawn_rate}"])

    print("Wait for terminate all of instances...")
    time.sleep(150)
    print("Instance terimnate finished!")

    for region in regions:
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session.client('logs')
        run_command(["terraform", "workspace", "select", "-or-create", f"{region}"])
        run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"spot_log_stream_name={spot_log_stream_name}", "--var", f"terminate_log_stream_name={terminate_log_stream_name}", "--var", f"pending_log_stream_name={pending_log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]", "--var", f"lambda_rate={spawn_rate}", "--var", f"describe_rate={describe_rate}"])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}"])
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-spot-availability-tester", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-no-name-instances", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-pending-instances", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-quota-availability-updater", logs_client)


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
    print("Delete complete!")