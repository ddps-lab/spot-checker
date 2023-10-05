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
        run_command(["terraform", "workspace", "select", f"{region}"])
        run_command(["terraform", "destroy", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name={log_stream_name}", "--var", f"instance_types=[{instance_type_data[region]}]", "--var", f"instance_types_az=[{availability_zone_data[region]}]"])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}"])


if __name__ == "__main__":
    main()
