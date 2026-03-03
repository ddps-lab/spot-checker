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

def main():
    # Change this
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = f"{prefix}-spot-checker-multinode-log"
    log_stream_name_change_status = f"{variables.log_stream_name_change_status}"
    log_stream_name_init_time = f"{variables.log_stream_name_init_time}"
    log_stream_name_rebalance = f"{variables.log_stream_name_rebalance}"
    log_stream_name_interruption = f"{variables.log_stream_name_interruption}"
    log_stream_name_count = f"{variables.log_stream_name_count}"
    log_stream_name_placement_failed = f"{variables.log_stream_name_placement_failed}"
    experiment_size = f"{variables.instance_count}"
    iam_instance_profile_arn = f"{variables.iam_instance_profile_arn}"
    count_interval_minutes = f"{variables.count_interval_minutes}"
    recent_window_minutes = f"{variables.recent_window_minutes}"

    print("="*80)
    print("AWS Spot Checker 인프라 생성")
    print("="*80)
    print(f"Prefix: {prefix}")
    print(f"Region(s): {region}")
    print(f"Log Group: {log_group_name}")

    if type(region)==type(list()):
        tf_project_dir = "./IaC"
        os.chdir(tf_project_dir)
        for r in region:
            session = boto3.Session(profile_name=awscli_profile, region_name=r)
            logs_client = session.client('logs')
            create_log_stream(log_group_name, log_stream_name_change_status, logs_client)
            create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
            create_log_stream(log_group_name, log_stream_name_rebalance, logs_client)
            create_log_stream(log_group_name, log_stream_name_interruption, logs_client)
            create_log_stream(log_group_name, log_stream_name_count, logs_client)
            create_log_stream(log_group_name, log_stream_name_placement_failed, logs_client)

            run_command(["terraform", "workspace", "select", "-or-create", f"{r}-spot-checker-multinode"])
            run_command(["terraform", "init"])

            print(f"\n{'='*80}")
            print(f"Creating resources for region: {r}")
            print(f"  - 5 Lambda modules (get-spot-status-change, get-spot-rebalance, etc.)")
            print(f"  - FIS IAM Role (for experiment templates)")
            print(f"  - CloudWatch events & Log streams")
            print(f"\n⚠️  FIS experiment templates will be created separately:")
            print(f"    uv run fis_tester.py --action setup")
            print(f"{'='*80}\n")

            run_command(["terraform", "apply", "--parallelism=150", "--auto-approve",
                        "--var", f"region={r}",
                        "--var", f"prefix={prefix}",
                        "--var", f"awscli_profile={awscli_profile}",
                        "--var", f"log_group_name={log_group_name}",
                        "--var", f"log_stream_name_change_status={log_stream_name_change_status}",
                        "--var", f"log_stream_name_init_time={log_stream_name_init_time}",
                        "--var", f"log_stream_name_rebalance={log_stream_name_rebalance}",
                        "--var", f"log_stream_name_interruption={log_stream_name_interruption}",
                        "--var", f"log_stream_name_count={log_stream_name_count}",
                        "--var", f"log_stream_name_placement_failed={log_stream_name_placement_failed}",
                        "--var", f"experiment_size={experiment_size}",
                        "--var", f"count_interval_minutes={count_interval_minutes}",
                        "--var", f"recent_window_minutes={recent_window_minutes}",
                        "--var", f"iam_instance_profile_arn={iam_instance_profile_arn}",
                        ])
    else:
        tf_project_dir = "./IaC"
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')
        create_log_stream(log_group_name, log_stream_name_change_status, logs_client)
        create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
        create_log_stream(log_group_name, log_stream_name_rebalance, logs_client)
        create_log_stream(log_group_name, log_stream_name_interruption, logs_client)
        create_log_stream(log_group_name, log_stream_name_count, logs_client)
        create_log_stream(log_group_name, log_stream_name_placement_failed, logs_client)
        os.chdir(tf_project_dir)

        run_command(["terraform", "workspace", "select", "-or-create", "spot-checker-multinode"])
        run_command(["terraform", "init"])

        print(f"\n{'='*80}")
        print(f"Creating resources for region: {region}")
        print(f"  - 5 Lambda modules (get-spot-status-change, get-spot-rebalance, etc.)")
        print(f"  - FIS IAM Role (for experiment templates)")
        print(f"  - CloudWatch events & Log streams")
        print(f"\n⚠️  FIS experiment templates will be created separately:")
        print(f"    uv run fis_tester.py --action setup")
        print(f"{'='*80}\n")

        run_command(["terraform", "apply", "--parallelism=150", "--auto-approve",
                    "--var", f"region={region}",
                    "--var", f"prefix={prefix}",
                    "--var", f"awscli_profile={awscli_profile}",
                    "--var", f"log_group_name={log_group_name}",
                    "--var", f"log_stream_name_change_status={log_stream_name_change_status}",
                    "--var", f"log_stream_name_init_time={log_stream_name_init_time}",
                    "--var", f"log_stream_name_rebalance={log_stream_name_rebalance}",
                    "--var", f"log_stream_name_interruption={log_stream_name_interruption}",
                    "--var", f"log_stream_name_count={log_stream_name_count}",
                    "--var", f"log_stream_name_placement_failed={log_stream_name_placement_failed}",
                    "--var", f"experiment_size={experiment_size}",
                    "--var", f"count_interval_minutes={count_interval_minutes}",
                    "--var", f"recent_window_minutes={recent_window_minutes}",
                    "--var", f"iam_instance_profile_arn={iam_instance_profile_arn}",
                    ])
   
if __name__ == "__main__":
    main()
