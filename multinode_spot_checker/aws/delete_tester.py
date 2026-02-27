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
    region = variables.region
    log_group_name = f"{prefix}-spot-availability-tester-log"
    log_stream_name_change_status = f"{variables.log_stream_name_change_status}"
    log_stream_name_init_time = f"{variables.log_stream_name_init_time}"
    log_stream_name_rebalance = f"{variables.log_stream_name_rebalance}"
    log_stream_name_interruption = f"{variables.log_stream_name_interruption}"
    log_stream_name_count = f"{variables.log_stream_name_count}"
    log_stream_name_placement_failed = f"{variables.log_stream_name_placement_failed}"
    experiment_size = f"{variables.instance_count}"
    count_interval_minutes = f"{variables.count_interval_minutes}"
    recent_window_minutes = f"{variables.recent_window_minutes}"

    tf_project_dir = "./IaC"

    os.chdir(tf_project_dir)

    if type(region)==type(list()):
        for r in region:
            boto3_session = boto3.Session(profile_name=awscli_profile, region_name=r)
            logs_client = boto3_session.client('logs')
            run_command(["terraform", "workspace", "select", "-or-create", f"{r}-spot-checker-multinode"])
            run_command(["terraform", "destroy", "--parallelism=150", "--target=module.spot-availability-tester", "--auto-approve", "--var", f"region={r}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name_chage_status={log_stream_name_change_status}", "--var", f"log_stream_name_init_time={log_stream_name_init_time}"])


            run_command(["terraform", "workspace", "select", "-or-create", f"{r}-spot-checker-multinode"])
            run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve",
                        "--var", f"region={r}",
                        "--var", f"prefix={prefix}",
                        "--var", f"awscli_profile={awscli_profile}",
                        "--var", f"log_group_name={log_group_name}",
                        "--var", f"log_stream_name_chage_status={log_stream_name_change_status}",
                        "--var", f"log_stream_name_init_time={log_stream_name_init_time}",
                        "--var", f"log_stream_name_rebalance={log_stream_name_rebalance}",
                        "--var", f"log_stream_name_interruption={log_stream_name_interruption}",
                        "--var", f"log_stream_name_count={log_stream_name_count}",
                        "--var", f"log_stream_name_placement_failed={log_stream_name_placement_failed}",
                        "--var", f"experiment_size={experiment_size}",
                        "--var", f"count_interval_minutes={count_interval_minutes}",
                        "--var", f"recent_window_minutes={recent_window_minutes}",
                        ])
            run_command(["terraform", "workspace", "select", "default"])
            run_command(["terraform", "workspace", "delete", f"{r}-spot-checker-multinode"])
            delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-spot-availability-tester", logs_client)
            delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-no-name-instances", logs_client)
    
    else:
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session.client('logs')
        run_command(["terraform", "workspace", "select", "-or-create", f"spot-checker-multinode"])
        run_command(["terraform", "destroy", "--parallelism=150", "--target=module.spot-availability-tester", "--auto-approve", "--var", f"region={region}", "--var", f"prefix={prefix}","--var", f"awscli_profile={awscli_profile}", "--var", f"log_group_name={log_group_name}", "--var", f"log_stream_name_chage_status={log_stream_name_change_status}", "--var", f"log_stream_name_init_time={log_stream_name_init_time}"])

        run_command(["terraform", "workspace", "select", "-or-create", f"spot-checker-multinode"])
        run_command(["terraform", "destroy", "--parallelism=150", "--auto-approve",
                    "--var", f"region={region}",
                    "--var", f"prefix={prefix}",
                    "--var", f"awscli_profile={awscli_profile}",
                    "--var", f"log_group_name={log_group_name}",
                    "--var", f"log_stream_name_chage_status={log_stream_name_change_status}",
                    "--var", f"log_stream_name_init_time={log_stream_name_init_time}",
                    "--var", f"log_stream_name_rebalance={log_stream_name_rebalance}",
                    "--var", f"log_stream_name_interruption={log_stream_name_interruption}",
                    "--var", f"log_stream_name_count={log_stream_name_count}",
                    "--var", f"log_stream_name_placement_failed={log_stream_name_placement_failed}",
                    "--var", f"experiment_size={experiment_size}",
                    "--var", f"count_interval_minutes={count_interval_minutes}",
                    "--var", f"recent_window_minutes={recent_window_minutes}",
                    ])
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}-spot-checker-multinode"])
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-spot-availability-tester", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-no-name-instances", logs_client)


if __name__ == "__main__":
    delete_check = input("Do you want to remove all resources??? (y/n) : ")
    if delete_check != "y":
        print("Interrupted!")
        os._exit(0)
    main()
    print("Delete complete!")