import subprocess
import sys
import variables
import os
import time
import boto3
import json

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

def azure_vm_list(resource_group_name):
    command = [
        'az', 'vm', 'list', '-g', resource_group_name,
        '--query', '[].{vm_id: vmId, vm_size: hardwareProfile.vmSize, TimeCreated: timeCreated}',
        '--output', 'json'
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout

    vms_info = json.loads(output)

    return vms_info

def main():
    # Change this
    awscli_profile = variables.awscli_profile
    azurecli_user_id = variables.azurecli_user_id
    prefix = variables.prefix
    location = variables.location
    resource_group_name = f"{prefix}-multinode-spot-checker"
    log_group_name = f"{prefix}-spot-checker-multinode-log"
    log_stream_name_change_status = f"{variables.log_stream_name_change_status}"
    log_stream_name_init_time = f"{variables.log_stream_name_init_time}"
    vm_count = variables.vm_count
    vm_size = variables.vm_size

    session = boto3.Session(profile_name=awscli_profile, region_name="us-east-2")
    logs_client = session.client('logs')
    create_log_stream(log_group_name, log_stream_name_change_status, logs_client)
    create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
    tf_project_dir = "./IaC"
    
    os.chdir(tf_project_dir)

    run_command(["terraform", "workspace", "new", "spot-checker-multinode"])
    run_command(["terraform", "init"])
    try:
        run_command(["terraform", "apply", "--parallelism=150", "--auto-approve", 
                     "--var", f"location={location}", "--var", f"prefix={prefix}", 
                     "--var", f"azurecli_user_id={azurecli_user_id}", "--var", f"resource_group_name={resource_group_name}", 
                     "--var", f"vm_size={vm_size}", "--var", f"vm_count={vm_count}"])
    except:
        run_command(["terraform", "workspace", "select", "-or-create", "spot-checker-multinode"])
        run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve", 
                     "--var", f"location={location}", "--var", f"prefix={prefix}",
                     "--var", f"azurecli_user_id={azurecli_user_id}", "--var", f"resource_group_name={resource_group_name}", 
                     "--var", f"vm_size={vm_size}", "--var", f"vm_count={vm_count}"])
        
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", "spot-checker-multinode"])

    var_if = "if1"
    vm_response = azure_vm_list(resource_group_name)
    
    os.chdir("..")
    os.mkdir(f"./log/{var_if}/{vm_size}_{location}_{vm_count}")
    json_path = f"./log/{var_if}/{vm_size}_{location}_{vm_count}/{vm_size}_{location}_{vm_count}.json"
    with open(json_path, 'w') as file:
        json.dump(vm_response, file, indent=4)

if __name__ == "__main__":
    main()
    
