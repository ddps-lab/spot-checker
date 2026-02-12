"""
Azure Spot VM Tester 인프라 생성 스크립트

각 AWS 리전에 독립적인 테스트 인프라를 생성합니다:
- EC2: tester.go/tester.sh 실행 (use_ec2=true)
- Lambda: Azure VM 테스트 실행
- CloudWatch Logs: 결과 저장
- Azure NIC Pool: Python asyncio로 고속 생성
"""

import subprocess
import sys
import os
import variables
import boto3
import asyncio
import time
from azure.identity.aio import ClientSecretCredential
from azure.mgmt.network.aio import NetworkManagementClient


# Azure Region 매핑 (Display Name → API Name)
AZURE_REGION_MAP = {
    "US East": "eastus",
    "US East 2": "eastus2",
    "US West": "westus",
    "US West 2": "westus2",
    "US West 3": "westus3",
    "US Central": "centralus",
    "US North Central": "northcentralus",
    "US South Central": "southcentralus",
    "US West Central": "westcentralus",
    "CA Central": "canadacentral",
    "CA East": "canadaeast",
    "BR South": "brazilsouth",
    "CL Central": "chilecentral",
    "MX Central": "mexicocentral",
    "EU North": "northeurope",
    "EU West": "westeurope",
    "UK South": "uksouth",
    "UK West": "ukwest",
    "FR Central": "francecentral",
    "FR South": "francesouth",
    "DE West Central": "germanywestcentral",
    "CH North": "switzerlandnorth",
    "CH West": "switzerlandwest",
    "NO East": "norwayeast",
    "NO West": "norwaywest",
    "SE Central": "swedencentral",
    "PL Central": "polandcentral",
    "IT North": "italynorth",
    "ES Central": "spaincentral",
    "AT East": "austriaeast",
    "GR Central": "greececentral",
    "IL Central": "israelcentral",
    "QA Central": "qatarcentral",
    "AE Central": "uaecentral",
    "AE North": "uaenorth",
    "ZA North": "southafricanorth",
    "ZA West": "southafricawest",
    "IN Central": "centralindia",
    "IN South": "southindia",
    "IN West": "westindia",
    "JA East": "japaneast",
    "JA West": "japanwest",
    "KR Central": "koreacentral",
    "KR South": "koreasouth",
    "AU East": "australiaeast",
    "AU Southeast": "australiasoutheast",
    "AU Central": "australiacentral",
    "AU Central 2": "australiacentral2",
    "NZ North": "newzealandnorth",
    "AP East": "eastasia",
    "AP Southeast": "southeastasia",
    "ID Central": "indonesiacentral",
}


def run_command(command):
    """명령어 실행"""
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
    """CloudWatch Log Stream 생성"""
    response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name
    )

    if not response['logStreams'] or response['logStreams'][0]['logStreamName'] != log_stream_name:
        logs_client.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        print(f"✅ Log stream created: {log_stream_name}")
    else:
        print(f"ℹ️  Log stream already exists: {log_stream_name}")


async def create_nic_pool_async(
    subscription_id,
    tenant_id,
    client_id,
    client_secret,
    prefix,
    azure_test_regions,
    azure_nic_pool_size
):
    """
    비동기로 NIC 풀 생성 (Python asyncio 기본 버전)
    
    Args:
        subscription_id: Azure Subscription ID
        tenant_id: Azure Tenant ID
        client_id: Azure Client ID
        client_secret: Azure Client Secret
        prefix: 리소스 이름 prefix
        azure_test_regions: 테스트 대상 region 리스트 (예: ["US West 3"])
        azure_nic_pool_size: region당 생성할 NIC 개수
    
    Returns:
        tuple: (success_count, failed_count)
    """
    
    total_nics = len(azure_test_regions) * azure_nic_pool_size
    print(f"\n⚡ NIC 풀 비동기 생성 시작")
    print(f"   총 {len(azure_test_regions)} 리전 × {azure_nic_pool_size}개 = {total_nics}개 NIC")
    
    # Azure 클라이언트 초기화
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    
    network_client = NetworkManagementClient(credential, subscription_id)
    
    async def create_single_nic(region_display_name, nic_index):
        """단일 NIC 생성"""
        region_normalized = region_display_name.replace(" ", "-")
        resource_group_name = f"{prefix}-{region_normalized}-rg"
        nic_name = f"{prefix}-{region_normalized}-nic-{nic_index}"
        
        # Azure API region 이름
        azure_region = AZURE_REGION_MAP.get(
            region_display_name,
            region_display_name.lower().replace(" ", "")
        )
        
        # Subnet ID 구성
        subnet_id = (
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Network/virtualNetworks/{prefix}-{region_normalized}-vnet"
            f"/subnets/default"
        )
        
        # NIC 파라미터
        nic_params = {
            "location": azure_region,
            "ip_configurations": [{
                "name": "internal",
                "subnet": {"id": subnet_id},
                "private_ip_address_allocation": "Dynamic"
            }],
            "tags": {
                "Environment": "spot-tester",
                "ManagedBy": "python-asyncio",
                "NICPool": "true",
                "Region": region_display_name,
                "Index": str(nic_index)
            }
        }
        
        try:
            # 비동기 NIC 생성 (완료 대기 안함 - fire and forget)
            await network_client.network_interfaces.begin_create_or_update(
                resource_group_name,
                nic_name,
                nic_params
            )
            return {"success": True, "nic_name": nic_name}
        except Exception as e:
            return {"success": False, "nic_name": nic_name, "error": str(e)}
    
    # 모든 NIC 생성 태스크 준비
    tasks = []
    for region in azure_test_regions:
        for i in range(azure_nic_pool_size):
            tasks.append(create_single_nic(region, i))
    
    # 진행률 추적
    start_time = time.time()
    
    print(f"\n📡 {len(tasks)}개 NIC 생성 요청 발송 중...")
    
    results = []
    completed = 0
    
    # asyncio.as_completed로 완료되는 대로 처리
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        completed += 1
        
        # 진행률 표시
        progress = (completed / len(tasks)) * 100
        print(f"\r   진행: {completed}/{len(tasks)} ({progress:.1f}%)", end='', flush=True)
    
    print()  # 줄바꿈
    
    # 결과 집계
    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count
    elapsed = time.time() - start_time
    
    print(f"\n✅ NIC 풀 생성 완료!")
    print(f"   성공: {success_count}개")
    if failed_count > 0:
        print(f"   실패: {failed_count}개")
        failed_nics = [r for r in results if not r["success"]]
        for r in failed_nics[:5]:  # 처음 5개만 표시
            print(f"     - {r['nic_name']}: {r.get('error', 'Unknown error')}")
        if failed_count > 5:
            print(f"     ... 외 {failed_count - 5}개")
    print(f"   소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    
    # 클라이언트 정리
    await network_client.close()
    await credential.close()
    
    return success_count, failed_count


def main():
    print("=" * 60)
    print("Azure Spot VM Tester 인프라 생성")
    print("=" * 60)
    
    # AWS 설정
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    
    # CloudWatch Logs 설정
    log_group_name = f"{prefix}-spot-availability-tester-log"
    spot_log_stream_name = f"{variables.log_stream_name}-spot"
    terminate_log_stream_name = f"{variables.log_stream_name}-terminate"
    pending_log_stream_name = f"{variables.log_stream_name}-pending"
    
    # Lambda 설정
    spawn_rate = "rate(1 minute)" if variables.spawn_rate == 1 else f"rate({variables.spawn_rate} minutes)"
    use_ec2 = variables.use_ec2
    describe_rate = variables.describe_rate
    
    # Azure 인증 정보
    azure_subscription_id = variables.azure_subscription_id
    azure_tenant_id = variables.azure_tenant_id
    azure_client_id = variables.azure_client_id
    azure_client_secret = variables.azure_client_secret
    azure_resource_group = getattr(variables, 'azure_resource_group', 'spot-tester-rg')
    
    # Azure 테스트 설정
    azure_test_regions = getattr(variables, 'azure_test_regions', [])
    azure_nic_pool_size = getattr(variables, 'azure_nic_pool_size', 50)
    
    # 인증 정보 검증
    if not all([azure_subscription_id, azure_tenant_id, azure_client_id, azure_client_secret]):
        print("\n❌ 오류: variables.py에 Azure 인증 정보가 설정되지 않았습니다.")
        print("\nAZURE_SETUP_GUIDE.md를 참고하여 Service Principal을 생성하세요.")
        sys.exit(1)
    
    print(f"\n✅ Azure 인증 정보 확인 완료")
    print(f"   Subscription ID: {azure_subscription_id}")
    print(f"   Resource Group: {azure_resource_group}")
    
    if azure_test_regions:
        print(f"\n✅ Azure 테스트 설정 확인 완료")
        print(f"   테스트 대상 리전: {', '.join(azure_test_regions)}")
        print(f"   NIC 풀 크기 (region별): {azure_nic_pool_size}개")
        print(f"   총 생성될 NIC 개수: {len(azure_test_regions) * azure_nic_pool_size}개")
    else:
        print("\n⚠️  경고: azure_test_regions가 비어있습니다. NIC 풀이 생성되지 않습니다.")

    # 리전 목록 읽기
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines() if line.strip()]
    
    print(f"\n📍 배포 대상 리전: {', '.join(regions)}")
    print(f"   use_ec2: {use_ec2}")
    
    # 각 리전에 CloudWatch Log Stream 생성
    print("\n📝 CloudWatch Log Streams 생성 중...")
    for region in regions:
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')

        create_log_stream(log_group_name, spot_log_stream_name, logs_client)
        create_log_stream(log_group_name, terminate_log_stream_name, logs_client)
        create_log_stream(log_group_name, pending_log_stream_name, logs_client)

    # Terraform 실행
    tf_project_dir = "./IaC"
    os.chdir(tf_project_dir)
    
    print(f"\n🚀 Terraform 배포 시작...")
    
    for idx, region in enumerate(regions):
        is_first_region = (idx == 0)  # 첫 번째 region 판별
        
        print("\n" + "=" * 60)
        print(f"📦 리전: {region} {'(Azure 리소스 생성)' if is_first_region else ''}")
        print("=" * 60)
        
        # Terraform workspace 생성
        print(f"\n1. Terraform workspace 생성: {region}")
        run_command(["terraform", "workspace", "new", f"{region}"])
        
        # Terraform 초기화
        print(f"\n2. Terraform 초기화")
        run_command(["terraform", "init"])
        
        # Terraform Apply
        print(f"\n3. 인프라 배포 중...")
        
        # 첫 번째 region에서만 Azure 리소스 생성
        if is_first_region:
            azure_test_regions_str = '["' + '","'.join(azure_test_regions) + '"]' if azure_test_regions else '[]'
        else:
            azure_test_regions_str = '[]'  # 나머지 region에서는 Azure 리소스 생성 안함
        
        terraform_vars = [
            "terraform", "apply",
            "--parallelism=150",
            "--auto-approve",
            # AWS 설정
            "--var", f"region={region}",
            "--var", f"prefix={prefix}",
            "--var", f"awscli_profile={awscli_profile}",
            # CloudWatch Logs
            "--var", f"log_group_name={log_group_name}",
            "--var", f"spot_log_stream_name={spot_log_stream_name}",
            "--var", f"terminate_log_stream_name={terminate_log_stream_name}",
            "--var", f"pending_log_stream_name={pending_log_stream_name}",
            # Lambda 설정
            "--var", f"lambda_rate={spawn_rate}",
            "--var", f"use_ec2={use_ec2}",
            "--var", f"describe_rate={describe_rate}",
            # Azure 인증 정보
            "--var", f"azure_subscription_id={azure_subscription_id}",
            "--var", f"azure_tenant_id={azure_tenant_id}",
            "--var", f"azure_client_id={azure_client_id}",
            "--var", f"azure_client_secret={azure_client_secret}",
            "--var", f"azure_resource_group={azure_resource_group}",
            # Azure 테스트 설정 (첫 번째 region에서만)
            "--var", f"azure_test_regions={azure_test_regions_str}",
            "--var", f"azure_nic_pool_size_runtime={azure_nic_pool_size}",  # Lambda 환경변수용 (실제 NIC 개수)
        ]
        
        run_command(terraform_vars)
        print(f"\n✅ {region} Terraform 배포 완료!")
        
        # 첫 번째 region의 Terraform 완료 직후 NIC 생성
        if is_first_region and azure_test_regions and azure_nic_pool_size > 0:
            print(f"\n{'=' * 60}")
            print(f"NIC 풀 고속 생성 (Python asyncio)")
            print(f"{'=' * 60}")
            
            success, failed = asyncio.run(create_nic_pool_async(
                azure_subscription_id,
                azure_tenant_id,
                azure_client_id,
                azure_client_secret,
                prefix,
                azure_test_regions,
                azure_nic_pool_size
            ))
            
            if failed > 0:
                print(f"\n⚠️  경고: {failed}개 NIC 생성 실패")
                print(f"   재시도가 필요할 수 있습니다.")
    
    print("\n" + "=" * 60)
    print("✅ 모든 인프라 배포 완료!")
    print("=" * 60)
    
    if use_ec2:
        print("\n📋 다음 단계 (EC2 사용 모드):")
        print("1. 각 리전의 EC2 인스턴스에 SSH 접속")
        print("2. tester.go, tester.sh, azure.csv 파일 복사")
        print("3. tester.sh 설정:")
        print("   - filename: 테스트할 VM 목록 CSV")
        print("   - spawnrate: 테스트 실행 주기 (분)")
        print("4. ./tester.sh 실행")
    else:
        print("\n📋 Lambda가 자동으로 테스트를 시작합니다.")
        print(f"   실행 주기: {spawn_rate}")


if __name__ == "__main__":
    main()
