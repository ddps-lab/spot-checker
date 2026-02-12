import subprocess
import sys
import os
import variables
import boto3
import time
import asyncio
from azure.identity.aio import ClientSecretCredential
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.compute.aio import ComputeManagementClient

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


async def delete_all_vms_async(
    subscription_id,
    tenant_id,
    client_id,
    client_secret,
    prefix,
    azure_test_regions
):
    """
    Python asyncio로 리소스 그룹 내 모든 VM 병렬 삭제
    
    Args:
        subscription_id: Azure 구독 ID
        tenant_id: Azure Tenant ID
        client_id: Azure Client ID (Service Principal)
        client_secret: Azure Client Secret
        prefix: 리소스 prefix
        azure_test_regions: Azure 테스트 리전 리스트 (예: ["US West 2", "US East"])
    
    Returns:
        tuple: (success_count, failed_count)
    """
    
    print(f"\n⚡ 리소스 그룹 내 모든 VM 강제 삭제 시작")
    print(f"   대상 리전: {len(azure_test_regions)}개")
    
    # Azure 클라이언트 초기화
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    
    compute_client = ComputeManagementClient(credential, subscription_id)
    
    async def delete_vm_in_region(region_display_name):
        """특정 리전의 모든 VM 삭제"""
        region_normalized = region_display_name.replace(" ", "-")
        resource_group_name = f"{prefix}-{region_normalized}-rg"
        
        deleted_vms = []
        skipped_vms = []
        failed_vms = []
        
        try:
            # 리소스 그룹 내 모든 VM 조회
            vms = compute_client.virtual_machines.list(resource_group_name)
            
            async for vm in vms:
                vm_name = vm.name
                try:
                    # VM 삭제 (비동기)
                    await compute_client.virtual_machines.begin_delete(
                        resource_group_name,
                        vm_name
                    )
                    deleted_vms.append(vm_name)
                except Exception as e:
                    error_str = str(e)
                    if "NotFound" in error_str or "ResourceNotFound" in error_str:
                        skipped_vms.append(vm_name)
                    else:
                        failed_vms.append((vm_name, error_str[:100]))
            
            return {
                "region": region_display_name,
                "deleted": deleted_vms,
                "skipped": skipped_vms,
                "failed": failed_vms
            }
            
        except Exception as e:
            error_str = str(e)
            # 리소스 그룹이 없으면 무시
            if "NotFound" in error_str or "ResourceGroupNotFound" in error_str:
                return {
                    "region": region_display_name,
                    "deleted": [],
                    "skipped": [],
                    "failed": [],
                    "rg_not_found": True
                }
            return {
                "region": region_display_name,
                "deleted": [],
                "skipped": [],
                "failed": [(region_display_name, error_str[:100])]
            }
    
    # 모든 리전에 대해 VM 삭제 태스크 준비
    tasks = []
    for region in azure_test_regions:
        tasks.append(delete_vm_in_region(region))
    
    # 진행률 추적
    start_time = time.time()
    
    print(f"\n📡 {len(tasks)}개 리전에서 VM 삭제 중...")
    
    results = []
    completed = 0
    
    # asyncio.as_completed로 완료되는 대로 처리
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        completed += 1
        
        # 진행률 표시
        progress = (completed / len(tasks)) * 100
        region_name = result["region"]
        deleted_count = len(result["deleted"])
        
        if result.get("rg_not_found"):
            print(f"   [{completed}/{len(tasks)}] {region_name}: 리소스 그룹 없음")
        elif deleted_count > 0:
            print(f"   [{completed}/{len(tasks)}] {region_name}: {deleted_count}개 VM 삭제")
        else:
            print(f"   [{completed}/{len(tasks)}] {region_name}: VM 없음")
    
    # 결과 집계
    total_deleted = sum(len(r["deleted"]) for r in results)
    total_skipped = sum(len(r["skipped"]) for r in results)
    total_failed = sum(len(r["failed"]) for r in results)
    elapsed = time.time() - start_time
    
    print(f"\n✅ VM 삭제 완료!")
    print(f"   삭제: {total_deleted}개")
    if total_skipped > 0:
        print(f"   이미 없음: {total_skipped}개")
    if total_failed > 0:
        print(f"   실패: {total_failed}개")
        for r in results:
            for vm_name, error in r["failed"][:3]:
                print(f"     - {vm_name}: {error}")
    print(f"   소요 시간: {elapsed:.1f}초")
    
    # 클라이언트 정리
    await compute_client.close()
    await credential.close()
    
    return total_deleted + total_skipped, total_failed


async def delete_nic_pool_async(
    subscription_id,
    tenant_id,
    client_id,
    client_secret,
    prefix,
    azure_test_regions,
    azure_nic_pool_size
):
    """
    Python asyncio로 NIC 풀 병렬 삭제
    
    Args:
        subscription_id: Azure 구독 ID
        tenant_id: Azure Tenant ID
        client_id: Azure Client ID (Service Principal)
        client_secret: Azure Client Secret
        prefix: 리소스 prefix
        azure_test_regions: Azure 테스트 리전 리스트 (예: ["US West 2", "US East"])
        azure_nic_pool_size: 각 리전별 NIC 풀 크기
    
    Returns:
        tuple: (success_count, failed_count)
    """
    
    total_nics = len(azure_test_regions) * azure_nic_pool_size
    print(f"\n⚡ NIC 풀 비동기 삭제 시작")
    print(f"   총 {len(azure_test_regions)} 리전 × {azure_nic_pool_size}개 = {total_nics}개 NIC")
    
    # Azure 클라이언트 초기화
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    
    network_client = NetworkManagementClient(credential, subscription_id)
    
    async def delete_single_nic(region_display_name, nic_index):
        """단일 NIC 삭제"""
        region_normalized = region_display_name.replace(" ", "-")
        resource_group_name = f"{prefix}-{region_normalized}-rg"
        nic_name = f"{prefix}-{region_normalized}-nic-{nic_index}"
        
        try:
            # 비동기 NIC 삭제
            await network_client.network_interfaces.begin_delete(
                resource_group_name,
                nic_name
            )
            return {"success": True, "nic_name": nic_name}
        except Exception as e:
            # NIC가 없거나 이미 삭제된 경우 성공으로 간주
            error_str = str(e)
            if "NotFound" in error_str or "ResourceNotFound" in error_str:
                return {"success": True, "nic_name": nic_name, "skipped": True}
            return {"success": False, "nic_name": nic_name, "error": error_str}
    
    # 모든 NIC 삭제 태스크 준비
    tasks = []
    for region in azure_test_regions:
        for i in range(azure_nic_pool_size):
            tasks.append(delete_single_nic(region, i))
    
    # 진행률 추적
    start_time = time.time()
    
    print(f"\n📡 {len(tasks)}개 NIC 삭제 요청 발송 중...")
    
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
    skipped_count = sum(1 for r in results if r.get("skipped", False))
    failed_count = len(results) - success_count
    elapsed = time.time() - start_time
    
    print(f"\n✅ NIC 풀 삭제 완료!")
    print(f"   성공: {success_count}개 (이미 없음: {skipped_count}개)")
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
    print("Azure Spot VM Tester 인프라 삭제")
    print("=" * 60)
    
    # AWS 설정
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = f"{prefix}-spot-availability-tester-log"
    spot_log_stream_name = f"{variables.log_stream_name}-spot"
    terminate_log_stream_name = f"{variables.log_stream_name}-terminate"
    pending_log_stream_name = f"{variables.log_stream_name}-pending"
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

    # 리전 목록 읽기
    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines() if line.strip()]

    print(f"\n📍 삭제 대상 리전: {', '.join(regions)}")
    if azure_test_regions:
        print(f"   Azure 리전: {', '.join(azure_test_regions)}")
    
    tf_project_dir = "./IaC"
    os.chdir(tf_project_dir)

    # 0단계: 모든 VM 강제 삭제 (NIC가 사용 중이면 삭제 불가하므로 VM 먼저 삭제)
    if azure_test_regions:
        print("\n" + "=" * 60)
        print("0단계: 리소스 그룹 내 모든 VM 강제 삭제")
        print("=" * 60)
        
        success, failed = asyncio.run(delete_all_vms_async(
            azure_subscription_id,
            azure_tenant_id,
            azure_client_id,
            azure_client_secret,
            prefix,
            azure_test_regions
        ))
        
        if failed > 0:
            print(f"\n⚠️  경고: {failed}개 VM 삭제 실패")
            print(f"   계속 진행합니다...")
        
        print(f"\n⏳ VM 삭제 완료 대기 중... (10초)")
        time.sleep(10)

    # 1단계: NIC 풀 고속 삭제 (Terraform destroy 전에 삭제하여 속도 향상)
    if azure_test_regions and azure_nic_pool_size > 0:
        print("\n" + "=" * 60)
        print("1단계: NIC 풀 고속 삭제 (Python asyncio)")
        print("=" * 60)
        
        success, failed = asyncio.run(delete_nic_pool_async(
            azure_subscription_id,
            azure_tenant_id,
            azure_client_id,
            azure_client_secret,
            prefix,
            azure_test_regions,
            azure_nic_pool_size
        ))
        
        if failed > 0:
            print(f"\n⚠️  경고: {failed}개 NIC 삭제 실패")
            print(f"   Terraform destroy가 나머지를 처리합니다.")
        
        print(f"\n⏳ NIC 삭제 완료 대기 중... (10초)")
        time.sleep(10)

    # 2단계: spot-availability-tester 모듈 먼저 삭제 (VM 생성을 멈춤)
    print("\n" + "=" * 60)
    print("2단계: Lambda 및 테스터 삭제 중...")
    print("=" * 60)
    
    for region in regions:
        print(f"\n📦 리전: {region}")
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session.client('logs')
        
        run_command(["terraform", "workspace", "select", "-or-create", f"{region}"])
        
        # Azure 변수를 포함한 terraform destroy
        azure_test_regions_str = '["' + '","'.join(azure_test_regions) + '"]' if azure_test_regions else '[]'
        
        run_command([
            "terraform", "destroy",
            "--parallelism=150",
            "--target=module.spot-availability-tester",
            "--auto-approve",
            "--var", f"region={region}",
            "--var", f"prefix={prefix}",
            "--var", f"awscli_profile={awscli_profile}",
            "--var", f"log_group_name={log_group_name}",
            "--var", f"spot_log_stream_name={spot_log_stream_name}",
            "--var", f"terminate_log_stream_name={terminate_log_stream_name}",
            "--var", f"pending_log_stream_name={pending_log_stream_name}",
            "--var", f"lambda_rate={spawn_rate}",
            "--var", f"use_ec2={use_ec2}",
            "--var", f"describe_rate={describe_rate}",
            "--var", f"azure_subscription_id={azure_subscription_id}",
            "--var", f"azure_tenant_id={azure_tenant_id}",
            "--var", f"azure_client_id={azure_client_id}",
            "--var", f"azure_client_secret={azure_client_secret}",
            "--var", f"azure_resource_group={azure_resource_group}",
            "--var", f"azure_test_regions={azure_test_regions_str}",
            "--var", f"azure_nic_pool_size_runtime={azure_nic_pool_size}"
        ])

    print("\n⏳ Lambda 삭제 대기 중... (10초)")
    time.sleep(10)
    print("✅ Lambda 삭제 완료!")

    # 3단계: 나머지 모든 리소스 삭제 (AWS 인프라 + Azure 인프라)
    print("\n" + "=" * 60)
    print("3단계: 모든 인프라 삭제 중 (AWS + Azure)...")
    print("=" * 60)
    
    for region in regions:
        print(f"\n📦 리전: {region}")
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = boto3_session.client('logs')
        
        run_command(["terraform", "workspace", "select", "-or-create", f"{region}"])
        
        azure_test_regions_str = '["' + '","'.join(azure_test_regions) + '"]' if azure_test_regions else '[]'
        
        # 모든 리소스 삭제 (AWS + Azure)
        run_command([
            "terraform", "destroy",
            "--parallelism=150",
            "--auto-approve",
            "--var", f"region={region}",
            "--var", f"prefix={prefix}",
            "--var", f"awscli_profile={awscli_profile}",
            "--var", f"log_group_name={log_group_name}",
            "--var", f"spot_log_stream_name={spot_log_stream_name}",
            "--var", f"terminate_log_stream_name={terminate_log_stream_name}",
            "--var", f"pending_log_stream_name={pending_log_stream_name}",
            "--var", f"lambda_rate={spawn_rate}",
            "--var", f"use_ec2={use_ec2}",
            "--var", f"describe_rate={describe_rate}",
            "--var", f"azure_subscription_id={azure_subscription_id}",
            "--var", f"azure_tenant_id={azure_tenant_id}",
            "--var", f"azure_client_id={azure_client_id}",
            "--var", f"azure_client_secret={azure_client_secret}",
            "--var", f"azure_resource_group={azure_resource_group}",
            "--var", f"azure_test_regions={azure_test_regions_str}",
            "--var", f"azure_nic_pool_size_runtime={azure_nic_pool_size}"
        ])
        
        # Workspace 정리
        run_command(["terraform", "workspace", "select", "default"])
        run_command(["terraform", "workspace", "delete", f"{region}"])
        
        # CloudWatch Log Groups 삭제
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-spot-availability-tester", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-orphan-disk", logs_client)
        delete_cloudwatch_log_group(f"/aws/lambda/{prefix}-terminate-failed-vms", logs_client)
        # delete_cloudwatch_log_group(log_group_name, logs_client)
    
    print("\n" + "=" * 60)
    print("✅ 모든 리소스 삭제 완료!")
    print("=" * 60)
    print("\n삭제된 리소스:")
    print("  - AWS Lambda Functions")
    print("  - AWS EC2 Instances (use_ec2=true인 경우)")
    print("  - AWS VPC, Subnets, Security Groups")
    print("  - AWS CloudWatch Log Groups")
    if azure_test_regions:
        print("  - Azure Resource Groups")
        print("  - Azure Virtual Networks")
        print("  - Azure Network Interfaces (NIC 풀)")
    print()


if __name__ == "__main__":
    delete_check = input("⚠️  모든 리소스를 삭제하시겠습니까? (y/n): ")
    if delete_check != "y":
        print("❌ 삭제 취소!")
        os._exit(0)
    main()
    print("\n✅ 삭제 완료!")
