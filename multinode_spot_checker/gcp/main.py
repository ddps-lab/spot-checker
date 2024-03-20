
import time
import subprocess
import sys
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
    # Change this

    prefix = variables.prefix
    region = variables.region
    zone = variables.zone
    instance_type = variables.instance_type
    project_name = variables.project_name
    base_instance_name = variables.base_instance_name     
    target_size = variables.target_size

    run_command(["terraform", "workspace", "new", "gcp-spot-checker-multinode"])
    run_command(["terraform", "init"])
    try:
        run_command(["terraform", "apply", "--parallelism=150", "--auto-approve", "--var", f"region={region}", 
                    "--var", f"zone={zone}", "--var", f"prefix={prefix}", "--var", f"instance_type={instance_type}", 
                    "--var", f"project_name={project_name}", "--var", f"base_instance_name={base_instance_name}",
                    "--var", f"target_size={target_size}"])
    except:
        run_command(["terraform", "workspace", "select", "-or-create", "gcp-spot-checker-multinode"])
        run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve", "--var", f"region={region}", 
                    "--var", f"zone={zone}", "--var", f"prefix={prefix}", "--var", f"instance_type={instance_type}", 
                    "--var", f"project_name={project_name}", "--var", f"base_instance_name={base_instance_name}",
                    "--var", f"target_size={target_size}"])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", "spot-checker-multinode"])

    time.sleep(600)

    run_command(["terraform", "workspace", "select", "-or-create", "gcp-spot-checker-multinode"])
    run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve", "--var", f"region={region}", 
                "--var", f"zone={zone}", "--var", f"prefix={prefix}", "--var", f"instance_type={instance_type}", 
                "--var", f"project_name={project_name}", "--var", f"base_instance_name={base_instance_name}",
                "--var", f"target_size={target_size}"])
    run_command(["terraform", "workspace", "select", "default"])
    run_command(["terraform", "workspace", "delete", "spot-checker-multinode"])
if __name__ == "__main__":
    main()
 