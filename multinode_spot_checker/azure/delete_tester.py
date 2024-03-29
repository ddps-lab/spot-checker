import subprocess
import sys
import os
import variables
import datetime
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
    azurecli_user_id = variables.azurecli_user_id
    prefix = variables.prefix
    location = variables.location
    resource_group_name = f"{prefix}-multinode-spot-checker1"
    tf_project_dir = "./IaC"
    vm_count = variables.vm_count
    vm_size = variables.vm_size
    time_minutes = variables.time_minutes
    stop_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(time_minutes))
    stop_time = stop_time.strftime("%H%M")

    os.chdir(tf_project_dir)
    
    run_command(["terraform", "workspace", "select", "-or-create", "spot-checker-multinode"])
    run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve", 
                    "--var", f"location={location}", "--var", f"prefix={prefix}",
                    "--var", f"azurecli_user_id={azurecli_user_id}", "--var", f"resource_group_name={resource_group_name}", 
                    "--var", f"vm_size={vm_size}", "--var", f"vm_count={vm_count}",
                    "--var", f"time_minutes={stop_time}"])
    
    run_command(["terraform", "workspace", "select", "default"])
    run_command(["terraform", "workspace", "delete", "spot-checker-multinode"])


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
    print("Delete complete!")