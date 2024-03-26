import subprocess
import sys
import os
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
    region = variables.region
    log_group_name = f"{prefix}-ondemand-checker-multinode-log"

    tf_project_dir = "./IaC-cloudwatchlogs"
    
    os.chdir(tf_project_dir)
    
    run_command(["terraform", "workspace", "new", "ondemand-checker-multinode"])
    run_command(["terraform", "init"])
    run_command(["terraform", "apply", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}"])


if __name__ == "__main__":
    main()
