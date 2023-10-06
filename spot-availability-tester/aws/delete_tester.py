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

def delete_cloudwatch_log_group(log_group_name, logs_client):
    try:
        response = logs_client.delete_log_group(
            logGroupName=f"/aws/lambda/{log_group_name}"
        )
        print(f"Log group {log_group_name} deleted successfully.")
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group {log_group_name} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = variables.log_group_name
    log_stream_name = variables.log_stream_name

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
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session('logs')
        delete_cloudwatch_log_group(f"{prefix}-spot-availability-tester", logs_client)
        delete_cloudwatch_log_group(f"{prefix}-terminate-no-name-instances", logs_client)
        run_command(["terraform", "workspace", "select", f"{region}"])
        run_command(["terraform", "destroy", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name={log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]"])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}"])


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
