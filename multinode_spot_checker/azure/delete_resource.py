import subprocess
import sys
import os
import variables
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient

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
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = f"{prefix}-spot-checker-multinode-log"
    resource_group_name = f"{prefix}-multinode-spot-checker1"
    azurecli_user_id = variables.azurecli_user_id
    credential = AzureCliCredential()
    resource_client = ResourceManagementClient(credential, azurecli_user_id)

    try:
        resource_client.resource_groups.begin_delete(resource_group_name)
    except:
        print("Resource group already deleted or doesn't exit.\nPlease check your resource group")

    tf_project_dir = "./IaC-cloudwatchlogs"

    os.chdir(tf_project_dir)

    
    run_command(["terraform", "workspace", "select", "-or-create", "spot-checker-multinode"])
    run_command(["terraform", "destroy", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}"])
    run_command(["terraform", "workspace", "select", "default"])
    run_command(["terraform", "workspace", "delete", "spot-checker-multinode"])


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
