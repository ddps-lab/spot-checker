import subprocess
import sys
import os
import variables
import boto3
import zipfile

def create_lambda_zip(function_name, source_dir):
    """Create Lambda function ZIP file"""
    zip_filename = f"{function_name}.zip"
    py_filename = os.path.join(source_dir, f"{function_name}.py")

    # Check if file exists
    if not os.path.exists(py_filename):
        print(f"  [ERROR] {py_filename} not found")
        return False

    # Remove old ZIP if exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    # Create new ZIP with Lambda handler
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(py_filename, arcname=f"{function_name}.py")
        print(f"  [OK] Created {zip_filename}")
        return True
    except Exception as e:
        print(f"  [ERROR] Error creating {zip_filename}: {e}")
        return False

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
    log_stream_name_imds_monitor = f"{variables.log_stream_name_imds_monitor}"
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

        # Create Lambda ZIP files before Terraform
        print("\n" + "="*80)
        print("Creating Lambda function ZIP files...")
        print("="*80)
        lambda_functions = [
            'get-spot-status-change',
            'get-spot-rebalance',
            'get-spot-interruption',
            'log-instance-count',
            'restart-closed-request'
        ]

        os.chdir(tf_project_dir)
        # Source files are in the same IaC directory
        for func in lambda_functions:
            create_lambda_zip(func, ".")
        os.chdir("..")

        os.chdir(tf_project_dir)
        for r in region:
            session = boto3.Session(profile_name=awscli_profile, region_name=r)
            logs_client = session.client('logs')

            # Spot Checker Log Streams
            create_log_stream(log_group_name, log_stream_name_change_status, logs_client)
            create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
            create_log_stream(log_group_name, log_stream_name_rebalance, logs_client)
            create_log_stream(log_group_name, log_stream_name_interruption, logs_client)
            create_log_stream(log_group_name, log_stream_name_count, logs_client)
            create_log_stream(log_group_name, log_stream_name_placement_failed, logs_client)

            # IMDS Monitor Log Stream (in existing log group)
            create_log_stream(log_group_name, log_stream_name_imds_monitor, logs_client)

            run_command(["terraform", "workspace", "select", "-or-create", f"{r}-spot-checker-multinode"])
            run_command(["terraform", "init"])

            print(f"\n{'='*80}")
            print(f"Creating resources for region: {r}")
            print(f"  - 5 Lambda modules (get-spot-status-change, get-spot-rebalance, etc.)")
            print(f"  - FIS IAM Role (for experiment templates)")
            print(f"  - CloudWatch events & Log streams")
            print(f"\n[INFO] FIS experiment templates will be created separately:")
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

        # Create Lambda ZIP files before Terraform
        print("\n" + "="*80)
        print("Creating Lambda function ZIP files...")
        print("="*80)
        lambda_functions = [
            'get-spot-status-change',
            'get-spot-rebalance',
            'get-spot-interruption',
            'log-instance-count',
            'restart-closed-request'
        ]

        os.chdir(tf_project_dir)
        # Source files are in the same IaC directory
        for func in lambda_functions:
            create_lambda_zip(func, ".")
        os.chdir("..")

        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')

        # Spot Checker Log Streams
        create_log_stream(log_group_name, log_stream_name_change_status, logs_client)
        create_log_stream(log_group_name, log_stream_name_init_time, logs_client)
        create_log_stream(log_group_name, log_stream_name_rebalance, logs_client)
        create_log_stream(log_group_name, log_stream_name_interruption, logs_client)
        create_log_stream(log_group_name, log_stream_name_count, logs_client)
        create_log_stream(log_group_name, log_stream_name_placement_failed, logs_client)

        # IMDS Monitor Log Stream (in existing log group)
        create_log_stream(log_group_name, log_stream_name_imds_monitor, logs_client)

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
