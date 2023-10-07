import subprocess
import sys
import os
import pandas as pd
import variables

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
    spot_availability_tester_log_group_name = f"{prefix}-spot-availability-tester-log"
    terminate_no_name_instance_log_group_name = f"{prefix}-terminate-no-name-instance-log"

    tf_project_dir = "./IaC-cloudwatchlogs"
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines()]

    os.chdir(tf_project_dir)

    for region in regions:
        run_command(["terraform", "workspace", "select", "-or-create", f"{region}"])
        run_command(["terraform", "destroy", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"spot_availability_tester_log_group_name={spot_availability_tester_log_group_name}", "--var", f"terminate_no_name_instance_log_group_name={terminate_no_name_instance_log_group_name}"])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}"])


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
