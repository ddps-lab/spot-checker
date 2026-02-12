"""
Azure Spot VM Availability Tester Lambda Function (EC2 모드)

EC2에서 tester.go/tester.sh가 Lambda Function URL로 HTTP POST 요청을 보내면 실행됩니다.
Azure Spot VM의 가용성을 테스트하고 결과를 CloudWatch Logs에 기록합니다.
"""

import os
import time
import json
import boto3
import random
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute.models import (
    VirtualMachine, HardwareProfile, StorageProfile, OSDisk, ManagedDiskParameters,
    OSProfile, NetworkProfile, NetworkInterfaceReference,
    ImageReference, BillingProfile, LinuxConfiguration,
    DiskCreateOptionTypes, CachingTypes, DiskDeleteOptionTypes, StorageAccountTypes,
    SecurityProfile, UefiSettings, SecurityTypes
)
from azure.core.exceptions import AzureError

# ============================================
# AWS CloudWatch Logs 설정
# ============================================
logs_client = boto3.client('logs')
lambda_client = boto3.client('lambda')

LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
PREFIX = os.environ['PREFIX']

# ============================================
# Azure 인증 정보 (Lambda 환경변수)
# ============================================
AZURE_SUBSCRIPTION_ID = os.environ['AZURE_SUBSCRIPTION_ID']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_NIC_POOL_SIZE = int(os.environ.get('AZURE_NIC_POOL_SIZE', '50'))

# ============================================
# Azure Region 매핑 (CSV Region → Azure API)
# ============================================
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
    "AP Southeast": "southeastasia",
    "AP East": "eastasia",
    "CN North": "chinanorth",
    "CN North 2": "chinanorth2",
    "CN North 3": "chinanorth3",
    "CN East": "chinaeast",
    "CN East 2": "chinaeast2",
    "CN East 3": "chinaeast3",
    "SG Central": "singaporecentral",
    "ID Central": "indonesiacentral",
    "HK East": "hongkongeast",
    "TW North": "taiwannorth",
    "NZ North": "newzealandnorth",
}

# ============================================
# Azure 에러 코드
# ============================================
AZURE_FAILED_CODES = [
    "SkuNotAvailable",
    "AllocationFailed",
    "OverconstrainedAllocationRequest",
    "ZonalAllocationFailed",
    "OperationNotAllowed",
    "QuotaExceeded",
    "RestrictedSkuNotAvailable",
]

# ============================================
# Azure 클라이언트 초기화 (전역 변수로 재사용)
# ============================================
azure_credential = None
compute_client = None
network_client = None


def get_azure_clients():
    """Azure 클라이언트 초기화 (Lambda warm start에서 재사용)"""
    global azure_credential, compute_client, network_client
    
    if azure_credential is None:
        azure_credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
    
    if compute_client is None:
        compute_client = ComputeManagementClient(
            azure_credential,
            AZURE_SUBSCRIPTION_ID
        )
    
    if network_client is None:
        network_client = NetworkManagementClient(
            azure_credential,
            AZURE_SUBSCRIPTION_ID
        )
    
    return compute_client, network_client


def create_log_event(result):
    """CloudWatch Logs에 결과 기록"""
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': result
    }
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=LOG_STREAM_NAME,
            logEvents=[log_event]
        )
    except Exception as e:
        print(f"CloudWatch Logs 기록 실패: {e}")


def normalize_region_name(region):
    """azure.csv의 Region 이름을 Azure API region으로 변환"""
    if region in AZURE_REGION_MAP:
        return AZURE_REGION_MAP[region]
    
    # 직접 매칭되지 않으면 소문자로 변환하여 시도
    normalized = region.lower().replace(" ", "")
    return normalized


def is_arm_vm(instance_type):
    """
    VM 타입이 ARM 기반인지 확인
    
    Args:
        instance_type: Azure VM 크기 (예: Standard_D2ps_v5, Standard_E2pds_v5)
    
    Returns:
        bool: ARM 기반이면 True, x86이면 False
    """
    instance_lower = instance_type.lower()
    # Azure ARM VM은 이름에 'p'가 포함됨 (예: D2ps_v5, E2pds_v5, B2pts_v2)
    return 'p' in instance_lower


def requires_gen2(vm_size):
    """
    VM 크기가 Gen2 Hypervisor를 요구하는지 확인
    
    Args:
        vm_size: Azure VM 크기 (예: Standard_D8pls_v6, Standard_D2s_v3)
    
    Returns:
        bool: Gen2가 필수이면 True, Gen1도 가능하면 False
    """
    vm_size_lower = vm_size.lower()
    # v5, v6 세대 VM은 Gen2 필수
    if '_v5' in vm_size_lower or '_v6' in vm_size_lower:
        return True
    return False


def is_confidential_vm(vm_size):
    """
    VM 크기가 Confidential VM (DC 시리즈)인지 확인
    
    Args:
        vm_size: Azure VM 크기 (예: Standard_DC2as_v5, Standard_DC1s_v3)
    
    Returns:
        bool: Confidential VM이면 True
    """
    vm_size_upper = vm_size.upper()
    # Standard_DC로 시작하거나 _DC가 포함된 VM 크기는 Confidential VM
    # 예: Standard_DC2as_v5, Standard_DC1s_v3, Standard_DC2ads_v6
    return '_DC' in vm_size_upper


def get_image_reference(instance_type):
    """
    VM 타입에 맞는 이미지 레퍼런스 반환 (ARM vs x86, Confidential VM 지원)
    
    Args:
        instance_type: Azure VM 크기
    
    Returns:
        ImageReference: ARM 또는 x86 Ubuntu 22.04 LTS 이미지 (Gen2 지원, CVM 지원)
    """
    is_confidential = is_confidential_vm(instance_type)
    
    if is_arm_vm(instance_type):
        if is_confidential:
            # ARM64 Confidential VM Ubuntu 22.04 LTS CVM 이미지
            return ImageReference(
                publisher='Canonical',
                offer='0001-com-ubuntu-server-jammy',
                sku='22_04-lts-cvm-arm64',
                version='latest'
            )
        else:
            # ARM64 Ubuntu 22.04 LTS (사용 가능한 이미지)
            return ImageReference(
                publisher='Canonical',
                offer='0001-com-ubuntu-server-jammy',
                sku='22_04-lts-arm64',
                version='latest'
            )
    else:
        if is_confidential:
            # x86_64 Confidential VM Ubuntu 22.04 LTS CVM 이미지
            return ImageReference(
                publisher='Canonical',
                offer='0001-com-ubuntu-server-jammy',
                sku='22_04-lts-cvm',
                version='latest'
            )
        else:
            # x86_64 Ubuntu 22.04 LTS Gen2
            return ImageReference(
                publisher='Canonical',
                offer='0001-com-ubuntu-server-jammy',
                sku='22_04-lts-gen2',
                version='latest'
            )


def get_available_nic(network_client, resource_group_name, region_display_name, max_pool_size=50):
    """
    미리 생성된 NIC 풀에서 사용 가능한 (VM에 attach되지 않은) NIC를 찾습니다.
    최적화: 랜덤 인덱스로 직접 접근하여 빠르게 찾기
    
    Args:
        network_client: Azure NetworkManagementClient
        resource_group_name: Resource Group 이름
        region_display_name: CSV의 Region 값 (예: "US West 2")
        max_pool_size: NIC 풀 크기 (기본 50)
    
    Returns:
        NIC ID 문자열, 없으면 None
    """
    indices = list(range(max_pool_size))
    random.shuffle(indices)
    
    # 리소스 이름에는 공백이 허용되지 않으므로 하이픈으로 변환
    region_normalized = region_display_name.replace(" ", "-")
    
    try:
        for idx in indices:
            nic_name = f"{PREFIX}-{region_normalized}-nic-{idx}"
            
            try:
                nic = network_client.network_interfaces.get(resource_group_name, nic_name)
                
                if nic.virtual_machine is None:
                    return nic.id
                    
            except Exception:
                continue
        
        print(f"No available NIC in pool for region {region_display_name}")
        return None
        
    except Exception as e:
        print(f"NIC lookup error: {e}")
        return None


def test_azure_spot_vm(instance_type, region, availability_zone, ddd_request_time, row_index):
    """
    Azure Spot VM 생성 테스트 (EC2 모드)
    
    Args:
        instance_type: Azure VM 크기 (예: Standard_D2s_v3)
        region: Azure 리전 (azure.csv의 Region 컬럼 값)
        availability_zone: 가용존 (1, 2, 3 또는 Single)
        ddd_request_time: EC2에서 요청한 시간 (Unix timestamp)
        row_index: CSV 행 번호 (0부터 시작)
    
    Returns:
        dict: 테스트 결과 (AWS EC2 형식과 호환)
    """
    request_create_time = time.time()
    azure_region = normalize_region_name(region)
    # microsecond 단위 + row_index로 고유한 VM 이름 생성
    timestamp = int(time.time() * 1000000)  # microsecond
    vm_name = f"spot-test-{timestamp}-{row_index}"
    
    try:
        compute, network = get_azure_clients()
        region_normalized = region.replace(" ", "-")
        resource_group_name = f"{PREFIX}-{region_normalized}-rg"
        
        print(f"[DEBUG] Attempting to test VM in region: {region}")
        print(f"[DEBUG] Azure location: {azure_region}")
        print(f"[DEBUG] Resource Group: {resource_group_name}")
        print(f"[DEBUG] Instance Type: {instance_type}, AZ: {availability_zone}")
        
        # 아키텍처 감지 및 로깅
        is_arm = is_arm_vm(instance_type)
        arch_type = "ARM64" if is_arm else "x86_64"
        print(f"[DEBUG ARCH] Detected architecture: {arch_type} for {instance_type}")
        
        # 모듈로 연산으로 NIC 인덱스 결정: row_index % NIC_POOL_SIZE
        # 홀수 분에는 기본 인덱스 사용, 짝수 분에는 +NIC_POOL_SIZE//2 사용하여 NIC 충돌 완화
        current_minute = time.localtime().tm_min
        is_odd_minute = (current_minute % 2) == 1
        
        base_nic_index = row_index % AZURE_NIC_POOL_SIZE
        if is_odd_minute:
            # 홀수 분: 기본 인덱스 사용 (nic-0 ~ nic-24)
            nic_index = base_nic_index
        else:
            # 짝수 분: 기본 인덱스 + NIC_POOL_SIZE//2 사용 (nic-25 ~ nic-49)
            nic_index = (base_nic_index%(AZURE_NIC_POOL_SIZE//2)) + (AZURE_NIC_POOL_SIZE // 2)
        
        nic_name = f"{PREFIX}-{region_normalized}-nic-{nic_index}"
        
        print(f"[DEBUG NIC] minute={current_minute} ({'odd' if is_odd_minute else 'even'}), row_index={row_index}, pool_size={AZURE_NIC_POOL_SIZE}, base_index={base_nic_index}, nic_index={nic_index}, nic_name={nic_name}")
        
        # NIC 조회
        try:
            nic = network.network_interfaces.get(resource_group_name, nic_name)
            nic_id = nic.id
        except Exception as e:
            print(f"Failed to get NIC {nic_name}: {e}")
            status_update_time = time.time()
            return {
                "InstanceType": instance_type,
                "Region": region,
                "AZ": availability_zone,
                "Code": "fail",
                "RawCode": "NICNotFound",
                "PowerState": None,
                "ProvisioningState": None,
                "SpotInfo": {},
                "RequestCreateTime": request_create_time,
                "StatusUpdateTime": status_update_time,
                "Timestamp": time.time(),
                "DDDRequestTime": ddd_request_time,
                "Error": f"NIC {nic_name} not found: {str(e)}",
                "LoopIndex": 0
            }
        
        # 아키텍처에 맞는 Ubuntu 22.04 LTS 이미지 선택
        image_reference = get_image_reference(instance_type)
        
        # v5, v6 VM 크기는 Gen2 필수
        needs_gen2 = requires_gen2(instance_type)
        
        # DC 시리즈는 Confidential VM이므로 securityProfile 필요
        is_confidential = is_confidential_vm(instance_type)
        
        # ManagedDiskParameters 생성 (Confidential VM인 경우 securityProfile 추가)
        managed_disk_kwargs = {
            'storage_account_type': StorageAccountTypes.STANDARD_LRS  # 가장 저렴한 HDD
        }
        
        # DC 시리즈 (Confidential VM)는 디스크 securityProfile 필수
        # VMDiskSecurityProfile 모델이 없을 수 있으므로 딕셔너리로 직접 설정
        if is_confidential:
            try:
                from azure.mgmt.compute.models import VMDiskSecurityProfile
                managed_disk_kwargs['security_profile'] = VMDiskSecurityProfile(
                    security_encryption_type='VMGuestStateOnly'
                )
            except ImportError:
                # 모델이 없으면 딕셔너리로 직접 설정
                managed_disk_kwargs['security_profile'] = {
                    'security_encryption_type': 'VMGuestStateOnly'
                }
        
        # StorageProfile 생성 (Gen2 필요 시 설정)
        storage_profile_kwargs = {
            'image_reference': image_reference,
            'os_disk': OSDisk(
                create_option=DiskCreateOptionTypes.FROM_IMAGE,
                caching=CachingTypes.NONE,  # 캐싱 불필요 (테스트용)
                delete_option=DiskDeleteOptionTypes.DELETE,  # VM 삭제 시 디스크도 삭제
                disk_size_gb=30,  # 최소 크기 (Ubuntu 이미지 최소 요구사항)
                managed_disk=ManagedDiskParameters(**managed_disk_kwargs)
            )
        }
        
        # v5, v6는 Gen2 필수이므로 명시적으로 설정
        if needs_gen2:
            storage_profile_kwargs['hyper_v_generation'] = 'V2'
        
        storage_profile = StorageProfile(**storage_profile_kwargs)
        
        # Spot VM 설정 (미리 생성된 NIC 사용)
        vm_parameters = VirtualMachine(
            location=azure_region,
            hardware_profile=HardwareProfile(
                vm_size=instance_type
            ),
            storage_profile=storage_profile,
            os_profile=OSProfile(
                computer_name=vm_name,
                admin_username='azureuser',
                admin_password='TempPass123!@#',  # 테스트용 (즉시 삭제됨)
                linux_configuration=LinuxConfiguration(
                    disable_password_authentication=False
                )
            ),
            network_profile=NetworkProfile(
                network_interfaces=[
                    NetworkInterfaceReference(
                        id=nic_id,
                        primary=True
                    )
                ]
            ),
            # Spot VM 설정
            priority='Spot',
            eviction_policy='Delete',
            billing_profile=BillingProfile(
                max_price=-1  # -1 = 최대 spot 가격까지 허용
            )
        )
        
        # DC 시리즈 (Confidential VM)는 securityProfile 필수
        if is_confidential:
            # SecurityTypes enum이 없을 수 있으므로 문자열 사용
            try:
                security_type_value = SecurityTypes.CONFIDENTIAL_VM
            except AttributeError:
                # enum이 없으면 문자열 직접 사용
                security_type_value = 'ConfidentialVM'
            
            vm_parameters.security_profile = SecurityProfile(
                security_type=security_type_value,
                uefi_settings=UefiSettings(
                    secure_boot_enabled=True,
                    v_tpm_enabled=True
                )
            )
        
        if availability_zone and availability_zone != 'Single':
            vm_parameters.zones = [str(availability_zone)]
        
        async_vm_creation = compute.virtual_machines.begin_create_or_update(
            resource_group_name,
            vm_name,
            vm_parameters
        )
        
        status = "success"
        raw_code = "pending-fulfillment"
        vm_id = None
        power_state = None
        provisioning_state = None
        spot_info = {}
        
        # VM 상태 조회 루프 (최대 9번, 각 루프 시작 전 0.1초 sleep)
        max_loops = 20
        loop_delay = 0.1
        final_loop_index = max_loops  # 루프 종료 인덱스 추적 (기본값: 최대 루프 수)
        
        time.sleep(loop_delay)
        for loop_idx in range(max_loops):
            try:
                instance_view = compute.virtual_machines.instance_view(resource_group_name, vm_name)
                
                # PowerState 및 ProvisioningState 추출
                power_state = None
                provisioning_state = None
                for status_obj in instance_view.statuses:
                    if status_obj.code.startswith('PowerState/'):
                        power_state = status_obj.code.split('/')[-1]
                    elif status_obj.code.startswith('ProvisioningState/'):
                        provisioning_state = status_obj.code.split('/')[-1]
                
                print(f"[DEBUG] Loop {loop_idx + 1}/{max_loops} - PowerState: {power_state}, ProvisioningState: {provisioning_state}")
                
                # ProvisioningState가 "OverconstrainedZonalAllocationRequest"이거나 PowerState가 "stopped"이면 break
                if provisioning_state == "OverconstrainedZonalAllocationRequest" or power_state == "stopped":
                    print(f"[DEBUG] 조건 충족으로 루프 종료 - ProvisioningState: {provisioning_state}, PowerState: {power_state}")
                    final_loop_index = loop_idx + 1  # 1-based 인덱스
                    break
                
                # 마지막 루프인 경우 인덱스 저장
                if loop_idx == max_loops - 1:
                    final_loop_index = loop_idx + 1  # 1-based 인덱스
                    
            except AzureError as e:
                # VM이 아직 생성되지 않았거나 조회 실패
                error_code = getattr(e.error, 'code', 'Unknown') if hasattr(e, 'error') else 'Unknown'
                if error_code not in ['ResourceNotFound', 'NotFound']:
                    print(f"[WARN] VM 상태 조회 실패 (루프 {loop_idx + 1}): {error_code}")
                
                # 마지막 루프인 경우 인덱스 저장
                if loop_idx >= max_loops - 1:
                    final_loop_index = loop_idx + 1  # 1-based 인덱스
                    break
            except Exception as e:
                print(f"[WARN] VM 상태 조회 중 예외 (루프 {loop_idx + 1}): {str(e)[:100]}")
                
                # 마지막 루프인 경우 인덱스 저장
                if loop_idx >= max_loops - 1:
                    final_loop_index = loop_idx + 1  # 1-based 인덱스
                    break
        
        # 최종 VM 상태 조회 및 정보 수집
        try:
            instance_view = compute.virtual_machines.instance_view(resource_group_name, vm_name)
            
            # PowerState 및 ProvisioningState 재확인 (최종)
            for status_obj in instance_view.statuses:
                if status_obj.code.startswith('PowerState/'):
                    power_state = status_obj.code.split('/')[-1]
                elif status_obj.code.startswith('ProvisioningState/'):
                    provisioning_state = status_obj.code.split('/')[-1]
            
            # VM ID 수집
            try:
                vm_resource = compute.virtual_machines.get(resource_group_name, vm_name)
                vm_id = vm_resource.id
            except Exception as e:
                print(f"[WARN] VM ID 조회 실패: {str(e)[:100]}")
            
            # Spot VM 정보 수집
            try:
                vm_resource = compute.virtual_machines.get(resource_group_name, vm_name)
                if vm_resource.priority == 'Spot':
                    spot_info = {
                        "priority": "Spot",
                        "eviction_policy": getattr(vm_resource, 'eviction_policy', None),
                        "billing_profile": getattr(vm_resource.billing_profile, 'max_price', None) if vm_resource.billing_profile else None
                    }
            except Exception as e:
                print(f"[WARN] Spot 정보 조회 실패: {str(e)[:100]}")
            
            print(f"[DEBUG] 최종 VM 상태 - PowerState: {power_state}, ProvisioningState: {provisioning_state}")
            
        except AzureError as e:
            # VM 상태 조회 실패
            error_code = getattr(e.error, 'code', 'Unknown') if hasattr(e, 'error') else 'Unknown'
            if error_code not in ['ResourceNotFound', 'NotFound']:
                print(f"[WARN] 최종 VM 상태 조회 실패: {error_code}")
        except Exception as e:
            print(f"[WARN] 최종 VM 상태 조회 중 예외: {str(e)[:100]}")
        
        status_update_time = time.time()
        
        # terminate-pending-instances Lambda 호출
        # resource_group_name에서 region 추출하여 해당 region의 Lambda 함수 호출
        # resource_group_name 형식: "{PREFIX}-{region-normalized}-rg"
        # 예: "prefix-US-West-2-rg" -> region: "US-West-2"
        try:
            # resource_group_name에서 region 부분 추출
            # "{PREFIX}-" 제거하고 "-rg" 제거
            rg_name_without_prefix = resource_group_name.replace(f"{PREFIX}-", "", 1)
            region_from_rg = rg_name_without_prefix.replace("-rg", "")
            
            # region을 하이픈에서 공백으로 변환 (Lambda 함수 이름 형식에 맞춤)
            # 예: "US-West-2" -> "US West 2"
            region_display_name = region_from_rg.replace("-", " ")
            
            # Lambda 함수 이름 생성 (현재는 하나만 있지만, 향후 region별 배포 대비)
            # 현재는 단일 Lambda 함수만 있으므로 기본 이름 사용
            terminate_lambda_name = f"{PREFIX}-terminate-failed-vms"
            
            lambda_client.invoke(
                FunctionName=terminate_lambda_name,
                InvocationType='Event',  # 비동기 호출
                Payload=json.dumps({
                    "vm_name": vm_name,
                    "resource_group_name": resource_group_name
                })
            )
            print(f"[DEBUG] Called terminate Lambda: {terminate_lambda_name} for VM: {vm_name} in {resource_group_name} (region: {region_display_name})")
        except Exception as e:
            # Lambda 호출 실패는 로그만 남기고 계속 진행
            print(f"[WARN] terminate Lambda 호출 실패: {str(e)[:100]}")
        
        code = "success" if status == "success" else "fail"
        
        result = {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": code,
            "RawCode": raw_code,
            "PowerState": power_state,
            "ProvisioningState": provisioning_state,
            "SpotInfo": spot_info,
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": status_update_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
            "LoopIndex": final_loop_index
        }
        
        return result
        
    except AzureError as e:
        # Azure SDK의 에러 객체에서 코드 추출
        if hasattr(e, 'error') and hasattr(e.error, 'code'):
            error_code = e.error.code
        else:
            error_code = 'AzureError'
        
        error_message = str(e)
        status_update_time = time.time()
        
        print(f"[ERROR] Azure API Error: {error_code}")
        print(f"[ERROR] Message: {error_message}")
        
        return {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": "fail",
            "RawCode": error_code,
            "PowerState": None,
            "ProvisioningState": None,
            "SpotInfo": {},
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": status_update_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
            "Error": error_message,
            "LoopIndex": 0
        }
        
    except Exception as e:
        status_update_time = time.time()
        
        return {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": "fail",
            "RawCode": "UnknownError",
            "PowerState": None,
            "ProvisioningState": None,
            "SpotInfo": {},
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": status_update_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
            "Error": str(e),
            "LoopIndex": 0
        }


def lambda_handler(event, context):
    """
    Lambda Handler (EC2 모드)
    
    tester.go에서 보낸 HTTP POST 요청을 처리합니다.
    event['body']에서 JSON을 파싱하여 Azure Spot VM 테스트를 실행합니다.
    
    Expected JSON format from tester.go:
    {
        "inputs": {
            "instance_type": "Standard_E64-16ds_v4",
            "region": "US West 2",
            "availability_zone": "1",
            "ddd_request_time": 1234567890,
            "row_index": 0
        }
    }
    """
    try:
        json_body = json.loads(event['body'])['inputs']

        instance_type = json_body['instance_type']
        region = json_body['region']
        availability_zone = json_body['availability_zone']
        ddd_request_time = json_body.get('ddd_request_time', 0)
        row_index = json_body.get('row_index', 0)
        
        print(f"[DEBUG LAMBDA] Received: row_index={row_index}, type={instance_type}, region={region}")
        
        result = test_azure_spot_vm(
            instance_type=instance_type,
            region=region,
            availability_zone=availability_zone,
            ddd_request_time=ddd_request_time,
            row_index=row_index
        )
        
        create_log_event(json.dumps(result))
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "finish", "result": result})
        }
        
    except Exception as e:
        error_result = {
            "Timestamp": time.time(),
            "Code": "fail",
            "RawCode": "LambdaHandlerError",
            "Error": str(e),
            "LoopIndex": 0
        }
        create_log_event(json.dumps(error_result))
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
