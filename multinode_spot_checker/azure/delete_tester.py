"""
Lambda 함수 삭제 스크립트
Terraform으로 배포된 리소스를 삭제합니다.
"""
import subprocess
import sys
import os
import variables


def run_command(command):
    """명령어 실행 헬퍼"""
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
    prefix = variables.prefix
    region = variables.region
    awscli_profile = variables.awscli_profile
    log_group_name = variables.log_group_name
    log_stream_name = variables.log_stream_name
    
    # Azure 인증 정보
    azure_subscription_id = variables.azure_subscription_id
    azure_tenant_id = variables.azure_tenant_id
    azure_client_id = variables.azure_client_id
    azure_client_secret = variables.azure_client_secret
    
    print(f"\n{'='*70}")
    print(f"Destroying AWS Lambda Infrastructure")
    print(f"{'='*70}")
    print(f"Prefix: {prefix}")
    print(f"Region: {region}")
    print(f"{'='*70}")
    print(f"Resources to be destroyed:")
    print(f"  - Lambda function (monitor-vm-status)")
    print(f"  - EventBridge schedule")
    print(f"  - Lambda Layer (Azure SDK)")
    print(f"  - S3 bucket (logs-export)")
    print(f"  - IAM roles and policies")
    print(f"{'='*70}\n")
    
    response = input("⚠️  Are you sure you want to destroy all resources? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Terraform 디렉토리로 이동
    tf_project_dir = "./IaC"
    
    if not os.path.exists(tf_project_dir):
        print(f"❌ Terraform directory not found: {tf_project_dir}")
        sys.exit(1)
    
    os.chdir(tf_project_dir)
    
    print("\nSelecting Terraform workspace...")
    run_command(["terraform", "workspace", "select", f"{prefix}-multinode"])
    
    print("\nDestroying Terraform resources...")
    run_command([
        "terraform", "destroy",
        "--parallelism=150",
        "--auto-approve",
        "--var", f"region={region}",
        "--var", f"prefix={prefix}",
        "--var", f"awscli_profile={awscli_profile}",
        "--var", f"log_group_name={log_group_name}",
        "--var", f"log_stream_name={log_stream_name}",
        "--var", f"azure_subscription_id={azure_subscription_id}",
        "--var", f"azure_tenant_id={azure_tenant_id}",
        "--var", f"azure_client_id={azure_client_id}",
        "--var", f"azure_client_secret={azure_client_secret}",
    ])
    
    print("\nDeleting Terraform workspace...")
    run_command(["terraform", "workspace", "select", "default"])
    run_command(["terraform", "workspace", "delete", f"{prefix}-multinode"])
    
    print(f"\n{'='*70}")
    print(f"✅ Destruction completed!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

