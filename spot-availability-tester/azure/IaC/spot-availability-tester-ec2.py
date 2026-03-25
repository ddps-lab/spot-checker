"""
Azure Spot VM Availability Tester Lambda Function (EC2 모드)

EC2에서 tester.go/tester.sh가 Lambda Function URL로 HTTP POST 요청을 보내면 실행됩니다.
Azure Spot VM의 가용성을 테스트하고 결과를 CloudWatch Logs에 기록합니다.
"""

import os
import re
import time
import json
import boto3
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute.models import (
    VirtualMachine,
    HardwareProfile,
    StorageProfile,
    OSDisk,
    ManagedDiskParameters,
    OSProfile,
    NetworkProfile,
    NetworkInterfaceReference,
    ImageReference,
    BillingProfile,
    LinuxConfiguration,
    DiskCreateOptionTypes,
    CachingTypes,
    DiskDeleteOptionTypes,
    StorageAccountTypes,
    SecurityProfile,
    UefiSettings,
    SecurityTypes,
)
from azure.core.exceptions import AzureError

# ============================================
# AWS CloudWatch Logs 설정
# ============================================
logs_client = boto3.client("logs")
lambda_client = boto3.client("lambda")

LOG_GROUP_NAME = os.environ["LOG_GROUP_NAME"]
LOG_STREAM_NAME = os.environ["LOG_STREAM_NAME"]
PREFIX = os.environ["PREFIX"]

# ============================================
# Azure 인증 정보 (Lambda 환경변수)
# ============================================
AZURE_SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
AZURE_TENANT_ID = os.environ["AZURE_TENANT_ID"]
AZURE_CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
AZURE_CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
AZURE_NIC_POOL_SIZE = int(os.environ.get("AZURE_NIC_POOL_SIZE", "50"))

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
            client_secret=AZURE_CLIENT_SECRET,
        )

    if compute_client is None:
        compute_client = ComputeManagementClient(
            azure_credential, AZURE_SUBSCRIPTION_ID
        )

    if network_client is None:
        network_client = NetworkManagementClient(
            azure_credential, AZURE_SUBSCRIPTION_ID
        )

    return compute_client, network_client


def create_log_event(result):
    """CloudWatch Logs에 결과 기록"""
    log_event = {"timestamp": int(time.time() * 1000), "message": result}
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=LOG_STREAM_NAME,
            logEvents=[log_event],
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
    return "p" in instance_lower


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
    if "_v5" in vm_size_lower or "_v6" in vm_size_lower:
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
    return "_DC" in vm_size_upper


def get_image_reference(instance_type, hyper_v_gen=""):
    """
    VM 타입에 맞는 이미지 레퍼런스 반환

    판별 우선순위:
      1. hyper_v_gen 파라미터 (azure.csv의 SKU API 결과) — 가장 정확
      2. 정규식 fallback (hyper_v_gen 없을 때)

    Args:
        instance_type: Azure VM 크기
        hyper_v_gen: "V1", "V2", "V1,V2" 또는 "" (SKU API 결과)
    """
    # 1. ARM 계열 (이름에 'p' 포함) — 항상 Gen2 ARM 이미지
    if is_arm_vm(instance_type):
        return ImageReference(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-jammy",
            sku="22_04-lts-arm64",
            version="latest",
        )

    # 2. hyper_v_gen이 있으면 그걸로 판별 (SKU API 기반, 정확)
    if hyper_v_gen:
        if hyper_v_gen == "V1":
            # Gen1 전용
            return ImageReference(
                publisher="Canonical",
                offer="0001-com-ubuntu-server-jammy",
                sku="22_04-lts",
                version="latest",
            )
        else:
            # V2 또는 V1,V2 → Gen2 이미지 사용
            return ImageReference(
                publisher="Canonical",
                offer="0001-com-ubuntu-server-jammy",
                sku="22_04-lts-gen2",
                version="latest",
            )

    # 3. Fallback: 정규식 판별 (hyper_v_gen 없을 때)
    instance_lower = instance_type.lower().replace("standard_", "")
    if '_v' not in instance_lower or re.match(r'^a\d+m?_v2$', instance_lower):
        return ImageReference(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-jammy",
            sku="22_04-lts",
            version="latest",
        )

    return ImageReference(
        publisher="Canonical",
        offer="0001-com-ubuntu-server-jammy",
        sku="22_04-lts-gen2",
        version="latest",
    )



def test_azure_spot_vm(
    instance_type, region, availability_zone, ddd_request_time, row_index,
    hyper_v_gen=""
):
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

        # 모듈로 연산으로 NIC 인덱스 결정: 3등분 로테이션 (180초 NIC 예약 대응)
        # ddd_request_time(배치 공통 타임스탬프)을 180초 버킷으로 나눠 슬롯 결정
        # 같은 배치 내 모든 VM이 동일 슬롯 보장, 호출 타이밍 drift에 강건
        slot = (int(ddd_request_time) // 180) % 3  # 0, 1, 2

        slot_size = AZURE_NIC_POOL_SIZE // 3  # 90 // 3 = 30
        base_nic_index = row_index % slot_size
        nic_index = base_nic_index + (slot * slot_size)

        nic_name = f"{PREFIX}-{region_normalized}-nic-{nic_index}"

        print(
            f"[DEBUG NIC] slot={slot}, row_index={row_index}, pool_size={AZURE_NIC_POOL_SIZE}, slot_size={slot_size}, nic_index={nic_index}, nic_name={nic_name}"
        )

        # NIC 조회
        try:
            nic = network.network_interfaces.get(resource_group_name, nic_name)
            nic_id = nic.id
        except Exception as e:
            print(f"Failed to get NIC {nic_name}: {e}")
            reject_time = time.time()
            return {
                "InstanceType": instance_type,
                "Region": region,
                "AZ": availability_zone,
                "Code": "fail",
                "RawCode": "NICNotFound",
                "ResponseTime": round(reject_time - request_create_time, 3),
                "RequestCreateTime": request_create_time,
                "StatusUpdateTime": reject_time,
                "Timestamp": time.time(),
                "DDDRequestTime": ddd_request_time,
                "Error": f"NIC {nic_name} not found: {str(e)[:200]}",
            }

        # 아키텍처에 맞는 Ubuntu 22.04 LTS 이미지 선택
        image_reference = get_image_reference(instance_type, hyper_v_gen)

        # Gen2 필요 여부: hyper_v_gen 있으면 그걸로 판별, 없으면 정규식 fallback
        if hyper_v_gen:
            needs_gen2 = "V2" in hyper_v_gen and hyper_v_gen != "V1"
        else:
            needs_gen2 = requires_gen2(instance_type)

        # DC 시리즈는 Confidential VM이므로 securityProfile 필요
        is_confidential = is_confidential_vm(instance_type)

        # ManagedDiskParameters 생성 (Confidential VM인 경우 securityProfile 추가)
        managed_disk_kwargs = {
            "storage_account_type": StorageAccountTypes.STANDARD_LRS  # 가장 저렴한 HDD
        }

        # DC 시리즈 (Confidential VM)는 디스크 securityProfile 필수
        # VMDiskSecurityProfile 모델이 없을 수 있으므로 딕셔너리로 직접 설정
        if is_confidential:
            try:
                from azure.mgmt.compute.models import VMDiskSecurityProfile

                managed_disk_kwargs["security_profile"] = VMDiskSecurityProfile(
                    security_encryption_type="VMGuestStateOnly"
                )
            except ImportError:
                # 모델이 없으면 딕셔너리로 직접 설정
                managed_disk_kwargs["security_profile"] = {
                    "security_encryption_type": "VMGuestStateOnly"
                }

        # StorageProfile 생성 (Gen2 필요 시 설정)
        storage_profile_kwargs = {
            "image_reference": image_reference,
            "os_disk": OSDisk(
                create_option=DiskCreateOptionTypes.FROM_IMAGE,
                caching=CachingTypes.NONE,  # 캐싱 불필요 (테스트용)
                delete_option=DiskDeleteOptionTypes.DELETE,  # VM 삭제 시 디스크도 삭제
                disk_size_gb=30,  # 최소 크기 (Ubuntu 이미지 최소 요구사항)
                managed_disk=ManagedDiskParameters(**managed_disk_kwargs),
            ),
        }

        # v5, v6는 Gen2 필수이므로 명시적으로 설정
        if needs_gen2:
            storage_profile_kwargs["hyper_v_generation"] = "V2"

        storage_profile = StorageProfile(**storage_profile_kwargs)

        # Spot VM 설정 (미리 생성된 NIC 사용)
        vm_parameters = VirtualMachine(
            location=azure_region,
            hardware_profile=HardwareProfile(vm_size=instance_type),
            storage_profile=storage_profile,
            os_profile=OSProfile(
                computer_name=vm_name,
                admin_username="azureuser",
                admin_password="TempPass123!@#",  # 테스트용 (즉시 삭제됨)
                linux_configuration=LinuxConfiguration(
                    disable_password_authentication=False
                ),
            ),
            network_profile=NetworkProfile(
                network_interfaces=[NetworkInterfaceReference(id=nic_id, primary=True)]
            ),
            # Spot VM 설정
            priority="Spot",
            eviction_policy="Delete",
            billing_profile=BillingProfile(
                max_price=-1  # -1 = 최대 spot 가격까지 허용
            ),
        )

        # DC 시리즈 (Confidential VM)는 securityProfile 필수
        if is_confidential:
            # SecurityTypes enum이 없을 수 있으므로 문자열 사용
            try:
                security_type_value = SecurityTypes.CONFIDENTIAL_VM
            except AttributeError:
                # enum이 없으면 문자열 직접 사용
                security_type_value = "ConfidentialVM"

            vm_parameters.security_profile = SecurityProfile(
                security_type=security_type_value,
                uefi_settings=UefiSettings(
                    secure_boot_enabled=True, v_tpm_enabled=True
                ),
            )

        if availability_zone and availability_zone != "Single":
            vm_parameters.zones = [str(availability_zone)]

        # ============================================
        # VM 생성 요청 (Poller-wait 방식)
        # begin_create_or_update() → poller.result() 대기:
        #   - 프로비저닝 성공 (Succeeded) → success
        #   - 프로비저닝 실패 (OverconstrainedZonalAllocationRequest 등) → fail
        # 완료 즉시 VM 삭제 호출
        # ============================================
        poller = compute.virtual_machines.begin_create_or_update(
            resource_group_name, vm_name, vm_parameters
        )

        accept_time = time.time()
        print(
            f"[DEBUG] VM create accepted in {accept_time - request_create_time:.2f}s, waiting for poller..."
        )

        # Poller 완료 대기 (성공 시 VM 객체 반환, 실패 시 예외)
        vm_result = poller.result(timeout=120)
        provision_time = time.time()
        response_time = provision_time - request_create_time
        provisioning_state = vm_result.provisioning_state

        print(
            f"[DEBUG] Provisioning completed in {response_time:.2f}s, state={provisioning_state}"
        )

        # ============================================
        # VM Describe (instance_view) — 상세 상태 수집
        # Poller 결과는 provisioning 결과만 제공하므로,
        # describe로 PowerState, EvictionInfo 등 런타임 상태 확인
        # ============================================
        describe_info = {}
        try:
            vm_detail = compute.virtual_machines.get(
                resource_group_name, vm_name, expand="instanceView"
            )
            describe_time = time.time()

            # PowerState 추출 (예: "running", "deallocated")
            power_state = None
            all_status_codes = []
            if vm_detail.instance_view and vm_detail.instance_view.statuses:
                for status in vm_detail.instance_view.statuses:
                    all_status_codes.append(status.code)
                    if status.code.startswith("PowerState/"):
                        power_state = status.code.split("/", 1)[1]

            describe_info = {
                "PowerState": power_state,
                "DescribeProvisioningState": vm_detail.provisioning_state,
                "AllStatusCodes": all_status_codes,
                "DescribeResponseTime": round(describe_time - provision_time, 3),
            }

            # EvictionInfo 확인 (Spot eviction 여부)
            if hasattr(vm_detail, "scheduled_events_profile"):
                describe_info["ScheduledEventsProfile"] = str(vm_detail.scheduled_events_profile)[:200] if vm_detail.scheduled_events_profile else None

            print(
                f"[DEBUG] Describe completed: PowerState={power_state}, "
                f"StatusCodes={all_status_codes}, took {describe_time - provision_time:.2f}s"
            )
        except Exception as e:
            print(f"[WARN] VM describe failed: {str(e)[:200]}")
            describe_info = {"DescribeError": str(e)[:200]}

        # 즉시 VM 삭제 (동기 — NIC 해제 보장)
        try:
            delete_poller = compute.virtual_machines.begin_delete(
                resource_group_name, vm_name, force_deletion=True
            )
            delete_poller.result(timeout=60)
            print(
                f"[DEBUG] VM deleted (sync): {vm_name} in {resource_group_name}"
            )
        except Exception as e:
            print(f"[WARN] VM 동기 삭제 실패: {str(e)[:100]}")
            # Fallback: terminate Lambda 비동기 호출
            try:
                terminate_lambda_name = f"{PREFIX}-terminate-failed-vms"
                lambda_client.invoke(
                    FunctionName=terminate_lambda_name,
                    InvocationType="Event",
                    Payload=json.dumps(
                        {"vm_name": vm_name, "resource_group_name": resource_group_name}
                    ),
                )
            except:
                pass

        status_update_time = time.time()

        result = {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": "success",
            "RawCode": provisioning_state,
            "ResponseTime": round(response_time, 3),
            "PollerStatus": provisioning_state,
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": status_update_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
        }
        # Describe 결과 병합
        result.update(describe_info)

        return result

    except AzureError as e:
        # Azure가 요청을 거부 (Spot 용량 부족, 쿼터 초과 등)
        if hasattr(e, "error") and hasattr(e.error, "code"):
            error_code = e.error.code
        else:
            error_code = "AzureError"

        error_message = str(e)
        reject_time = time.time()
        response_time = reject_time - request_create_time

        print(f"[ERROR] Azure rejected in {response_time:.2f}s: {error_code}")

        # 실패 시에도 VM이 부분 생성되었을 수 있으므로 describe 시도
        describe_info = {}
        try:
            vm_detail = compute.virtual_machines.get(
                resource_group_name, vm_name, expand="instanceView"
            )
            power_state = None
            all_status_codes = []
            if vm_detail.instance_view and vm_detail.instance_view.statuses:
                for status in vm_detail.instance_view.statuses:
                    all_status_codes.append(status.code)
                    if status.code.startswith("PowerState/"):
                        power_state = status.code.split("/", 1)[1]
            describe_info = {
                "PowerState": power_state,
                "DescribeProvisioningState": vm_detail.provisioning_state,
                "AllStatusCodes": all_status_codes,
            }
            print(f"[DEBUG] Failed VM describe: PowerState={power_state}, StatusCodes={all_status_codes}")

            # 부분 생성된 VM 삭제
            try:
                delete_poller = compute.virtual_machines.begin_delete(
                    resource_group_name, vm_name, force_deletion=True
                )
                delete_poller.result(timeout=60)
            except:
                pass
        except Exception as desc_e:
            # VM이 아예 생성되지 않은 경우 (정상)
            print(f"[DEBUG] Failed VM describe skipped (VM not created): {str(desc_e)[:100]}")

        result = {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": "fail",
            "RawCode": error_code,
            "ResponseTime": round(response_time, 3),
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": reject_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
            "Error": error_message[:500],
        }
        result.update(describe_info)

        return result

    except Exception as e:
        reject_time = time.time()
        response_time = reject_time - request_create_time

        return {
            "InstanceType": instance_type,
            "Region": region,
            "AZ": availability_zone,
            "Code": "fail",
            "RawCode": "UnknownError",
            "ResponseTime": round(response_time, 3),
            "RequestCreateTime": request_create_time,
            "StatusUpdateTime": reject_time,
            "Timestamp": time.time(),
            "DDDRequestTime": ddd_request_time,
            "Error": str(e)[:500],
        }


def lambda_handler(event, context):
    """
    Lambda Handler

    EC2 모드: tester.go → HTTP POST → Function URL → event['body'] 파싱
    서버리스 모드: Dispatcher Lambda → Lambda Invoke → event 직접 접근
    """
    try:
        if "body" in event:
            json_body = json.loads(event["body"])["inputs"]
        else:
            json_body = event

        instance_type = json_body["instance_type"]
        region = json_body["region"]
        availability_zone = json_body["availability_zone"]
        ddd_request_time = json_body.get("ddd_request_time", 0)
        row_index = json_body.get("row_index", 0)
        hyper_v_gen = json_body.get("hyper_v_gen", "")

        print(
            f"[DEBUG LAMBDA] Received: row_index={row_index}, type={instance_type}, region={region}"
        )

        result = test_azure_spot_vm(
            instance_type=instance_type,
            region=region,
            availability_zone=availability_zone,
            ddd_request_time=ddd_request_time,
            row_index=row_index,
            hyper_v_gen=hyper_v_gen,
        )

        create_log_event(json.dumps(result))

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "finish", "result": result}),
        }

    except Exception as e:
        error_result = {
            "Timestamp": time.time(),
            "Code": "fail",
            "RawCode": "LambdaHandlerError",
            "Error": str(e)[:500],
        }
        create_log_event(json.dumps(error_result))

        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
