"""
Lambda 함수 배포 스크립트
Terraform을 사용하여 AWS Lambda 및 EventBridge를 배포합니다.
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
    # 설정 로드
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = variables.log_group_name
    log_stream_name = variables.log_stream_name
    
    # Azure 인증 정보
    azure_subscription_id = variables.azure_subscription_id
    azure_tenant_id = variables.azure_tenant_id
    azure_client_id = variables.azure_client_id
    azure_client_secret = variables.azure_client_secret
    
    print(f"\n{'='*70}")
    print(f"Deploying AWS Lambda Infrastructure")
    print(f"{'='*70}")
    print(f"Prefix: {prefix}")
    print(f"Region: {region}")
    print(f"Log Group: {log_group_name}")
    print(f"{'='*70}\n")
    
    # Terraform 디렉토리로 이동
    tf_project_dir = "./IaC"
    
    if not os.path.exists(tf_project_dir):
        print(f"❌ Terraform directory not found: {tf_project_dir}")
        sys.exit(1)
    
    os.chdir(tf_project_dir)
    
    # Terraform 실행
    print("Creating Terraform workspace...")
    run_command(["terraform", "workspace", "new", f"{prefix}-multinode"])
    
    print("\nInitializing Terraform...")
    run_command(["terraform", "init"])
    
    print("\nApplying Terraform configuration...")
    run_command([
        "terraform", "apply", 
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
    
    print(f"\n{'='*70}")
    print(f"✅ Deployment completed!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

