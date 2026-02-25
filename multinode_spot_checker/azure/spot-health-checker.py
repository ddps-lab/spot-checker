"""
Azure Spot VM 생성 스크립트 (로컬에서 실행)

variables.py의 vm_specs를 파싱하여 Azure Spot VM을 생성합니다.
- Evict 시 자동 재시작 (Deallocate 정책)
- Tag에 실험 종료 시간 기록
- Location별로 Resource Group, VNet, Subnet 자동 생성
"""
import time
import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
import variables

# Azure 인증
credential = ClientSecretCredential(
    tenant_id=variables.azure_tenant_id,
    client_id=variables.azure_client_id,
    client_secret=variables.azure_client_secret
)

compute_client = ComputeManagementClient(credential, variables.azure_subscription_id)
network_client = NetworkManagementClient(credential, variables.azure_subscription_id)
resource_client = ResourceManagementClient(credential, variables.azure_subscription_id)

# Azure 지역 목록 캐싱 (API 호출 최소화)
_azure_locations_cache = None

# 실험 종료 시간 계산
end_time = datetime.datetime.now(pytz.UTC) + datetime.timedelta(
    hours=variables.time_hours,
    minutes=variables.time_minutes + variables.wait_minutes
)
end_time_str = end_time.isoformat()


def parse_vm_specs(specs_list):
    """
    리스트 형식 파싱
    형식: "Tier,InstanceType,Location,Zone,Count"
    예시: "Standard,E2_v4,US West 3,2,10" -> 10개 생성
    
    Args:
        specs_list: VM 스펙 문자열 리스트
    
    Returns:
        list: VM 정보 딕셔너리 리스트
    """
    vms = []
    vm_index = 0
    
    for spec_line in specs_list:
        line = spec_line.strip()
        if not line:
            continue
            
        parts = [p.strip() for p in line.split(',')]
        
        # 형식 검증
        if len(parts) == 5:
            tier, instance_type, location, zone, count = parts
            try:
                count = int(count)
            except ValueError:
                print(f"⚠️  Warning: Invalid count '{count}' in spec: {line}")
                print(f"   Skipping this spec.")
                continue
        elif len(parts) == 4:
            # 하위 호환성: Count 없으면 1개로 간주
            tier, instance_type, location, zone = parts
            count = 1
            print(f"⚠️  Warning: No count specified in spec: {line}")
            print(f"   Using default count: 1")
        else:
            print(f"⚠️  Warning: Invalid spec format: {line}")
            print(f"   Expected: Tier,InstanceType,Location,Zone,Count")
            continue
        
        # Count만큼 VM 생성
        for i in range(count):
            vms.append({
                'index': vm_index,
                'vm_size': f"{tier}_{instance_type}",  # Standard_E2_v4
                'location': location,
                'zone': zone,
                'spec_line': spec_line  # 디버깅용
            })
            vm_index += 1
    
    return vms


def is_arm64_vm_size(vm_size):
    """
    VM 사이즈가 ARM64 아키텍처인지 확인
    
    Azure ARM64 VM은 사이즈 이름에 소문자 'p'가 포함됨
    (예: D2ps_v5, B2pts_v2, E2pls_v5 등)
    
    Args:
        vm_size: Azure VM 사이즈 (예: Standard_D2ps_v5, Standard_B2pts_v2)
    
    Returns:
        bool: ARM64 VM이면 True, x64 VM이면 False
    """
    return 'p' in vm_size.lower()


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
    # v2, v3, v4는 Gen1도 지원하지만 Gen2도 가능
    if '_v5' in vm_size_lower or '_v6' in vm_size_lower:
        return True
    # 기본적으로 Gen2를 사용 (대부분의 최신 VM 크기 지원)
    # 특정 오래된 VM 크기는 Gen1으로 fallback 가능
    return False


def get_vm_image_reference(vm_size):
    """
    VM 사이즈에 맞는 이미지 레퍼런스 반환
    
    Args:
        vm_size: Azure VM 사이즈
    
    Returns:
        dict: image_reference 딕셔너리
    """
    if is_arm64_vm_size(vm_size):
        # ARM64 이미지 (Ubuntu 22.04 ARM64)
        return {
            'publisher': 'Canonical',
            'offer': '0001-com-ubuntu-server-jammy',
            'sku': '22_04-lts-arm64',
            'version': 'latest'
        }
    else:
        # x64 이미지 (Ubuntu 22.04 x64)
        return {
            'publisher': 'Canonical',
            'offer': '0001-com-ubuntu-server-jammy',
            'sku': '22_04-lts-gen2',
            'version': 'latest'
        }


def normalize_location(location):
    """
    Location Display Name을 Azure API 형식으로 변환
    
    Examples:
        "US East" → "eastus"
        "KR Central" → "koreacentral"
        "eastus" → "eastus" (이미 API 형식)
    
    지원하는 형식:
        약어 형식 (azure_list.csv와 동일): "US East", "KR Central", "AP Southeast"
        API 이름: "eastus", "koreacentral", "southeastasia"
    """
    # Display Name → API Name 매핑 (spot-availability-tester 기준)
    location_mapping = {
        # Americas - US
        "us east": "eastus",
        "us east 2": "eastus2",
        "us west": "westus",
        "us west 2": "westus2",
        "us west 3": "westus3",
        "us central": "centralus",
        "us north central": "northcentralus",
        "us south central": "southcentralus",
        "us west central": "westcentralus",
        
        # Americas - Other
        "ca central": "canadacentral",
        "ca east": "canadaeast",
        "br south": "brazilsouth",
        "cl central": "chilecentral",
        "mx central": "mexicocentral",
        
        # Europe
        "eu north": "northeurope",
        "eu west": "westeurope",
        "uk south": "uksouth",
        "uk west": "ukwest",
        "fr central": "francecentral",
        "fr south": "francesouth",
        "de west central": "germanywestcentral",
        "ch north": "switzerlandnorth",
        "ch west": "switzerlandwest",
        "no east": "norwayeast",
        "no west": "norwaywest",
        "se central": "swedencentral",
        "pl central": "polandcentral",
        "it north": "italynorth",
        "es central": "spaincentral",
        "at east": "austriaeast",
        "gr central": "greececentral",
        "be central": "belgiumcentral",
        
        # Middle East & Africa
        "il central": "israelcentral",
        "qa central": "qatarcentral",
        "ae central": "uaecentral",
        "ae north": "uaenorth",
        "za north": "southafricanorth",
        "za west": "southafricawest",
        
        # Asia Pacific - India & Japan & Korea
        "in central": "centralindia",
        "in south": "southindia",
        "in west": "westindia",
        "ja east": "japaneast",
        "ja west": "japanwest",
        "kr central": "koreacentral",
        "kr south": "koreasouth",
        
        # Asia Pacific - Australia & Southeast Asia
        "au east": "australiaeast",
        "au southeast": "australiasoutheast",
        "au central": "australiacentral",
        "au central 2": "australiacentral2",
        "ap southeast": "southeastasia",
        "ap east": "eastasia",
        
        # Asia Pacific - Other
        "cn north": "chinanorth",
        "cn north 2": "chinanorth2",
        "cn north 3": "chinanorth3",
        "cn east": "chinaeast",
        "cn east 2": "chinaeast2",
        "cn east 3": "chinaeast3",
        "id central": "indonesiacentral",
        "my west": "malaysiawest",
        "nz north": "newzealandnorth",
    }
    
    # 입력을 소문자로 변환하여 매핑 확인
    location_lower = location.lower().strip()
    
    if location_lower in location_mapping:
        return location_mapping[location_lower]
    
    # 매핑이 없으면 이미 API 형식일 수 있으므로 공백만 제거
    normalized = location.replace(" ", "").lower()
    
    # API 형식인지 검증 (공백 없고 소문자)
    if normalized == location.lower() and " " not in location:
        return normalized
    
    # 그래도 안 되면 경고와 함께 반환
    print(f"⚠️  Warning: Location '{location}' not found in mapping.")
    print(f"   Normalized to: '{normalized}'")
    print(f"   Supported format: 'US East', 'KR Central' or API name 'eastus'")
    return normalized


def ensure_resource_group(location):
    """리소스 그룹 확인/생성"""
    location_normalized = normalize_location(location)
    rg_name = f"{variables.prefix}-{location_normalized}-rg"
    
    try:
        resource_client.resource_groups.get(rg_name)
        print(f"✓ Resource Group exists: {rg_name}")
    except Exception:
        print(f"Creating Resource Group: {rg_name}")
        
        # 리소스 그룹 생성 (비동기 작업이 가능한 경우)
        try:
            # begin_create_or_update가 있는 경우 (비동기)
            poller = resource_client.resource_groups.begin_create_or_update(
                rg_name,
                {'location': location_normalized}
            )
            # 완료 대기 (최대 5분)
            poller.result(timeout=300)
            print(f"✓ Resource Group created: {rg_name}")
        except AttributeError:
            # begin_create_or_update가 없는 경우 (동기 방식)
            resource_client.resource_groups.create_or_update(
                rg_name,
                {'location': location_normalized}
            )
            # 폴링으로 실제 생성 확인
            max_retries = 30
            for i in range(max_retries):
                try:
                    rg = resource_client.resource_groups.get(rg_name)
                    if rg:
                        print(f"✓ Resource Group confirmed: {rg_name}")
                        break
                except Exception:
                    if i < max_retries - 1:
                        time.sleep(2)
                    else:
                        print(f"✗ Resource Group creation timeout after {max_retries * 2} seconds")
                        raise
        except Exception as e:
            # 다른 예외 발생 시 폴링으로 확인
            print(f"⚠️  Resource Group creation may still be in progress: {e}")
            max_retries = 30
            for i in range(max_retries):
                try:
                    rg = resource_client.resource_groups.get(rg_name)
                    if rg:
                        print(f"✓ Resource Group confirmed: {rg_name}")
                        break
                except Exception:
                    if i < max_retries - 1:
                        time.sleep(2)
                    else:
                        print(f"✗ Resource Group creation timeout after {max_retries * 2} seconds")
                        raise
    
    return rg_name


def create_vnet_if_not_exists(rg_name, location):
    """VNet/Subnet 확인/생성"""
    vnet_name = f"{variables.prefix}-vnet"
    subnet_name = f"{variables.prefix}-subnet"
    
    try:
        vnet = network_client.virtual_networks.get(rg_name, vnet_name)
        print(f"✓ VNet exists: {vnet_name}")
        return vnet_name, subnet_name
    except Exception:
        print(f"Creating VNet: {vnet_name}")
        vnet_params = {
            'location': normalize_location(location),
            'address_space': {'address_prefixes': ['10.0.0.0/16']},
            'subnets': [{
                'name': subnet_name,
                'address_prefix': '10.0.0.0/24'
            }]
        }
        
        # VNet 생성 시 재시도 로직 추가
        max_retries = 3
        for attempt in range(max_retries):
            try:
                poller = network_client.virtual_networks.begin_create_or_update(
                    rg_name, vnet_name, vnet_params
                )
                # .result() 사용 (더 안정적)
                poller.result(timeout=300)  # 5분 타임아웃
                print(f"✓ VNet created: {vnet_name}")
                return vnet_name, subnet_name
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2초, 4초, 6초
                    print(f"⚠️  VNet creation attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Failed to create VNet after {max_retries} attempts: {e}")
                    raise


def create_spot_vm(vm_info, rg_name, subnet_id):
    """
    Spot VM 생성 (Deallocate 정책)
    
    핵심:
    - eviction_policy: "Deallocate" (삭제 안 됨)
    - Azure가 Capacity 복구 시 자동으로 재시작
    """
    vm_name = f"{variables.prefix}-vm-{vm_info['index']:03d}"
    nic_name = f"{vm_name}-nic"
    
    # VM 아키텍처 감지
    is_arm64 = is_arm64_vm_size(vm_info['vm_size'])
    arch_str = "ARM64" if is_arm64 else "x64"
    
    print(f"Creating VM: {vm_name} ({vm_info['vm_size']}, Zone {vm_info['zone']}, {arch_str})")
    
    try:
        # NIC 생성
        nic_params = {
            'location': normalize_location(vm_info['location']),
            'ip_configurations': [{
                'name': f'{nic_name}-ipconfig',
                'subnet': {'id': subnet_id}
            }]
        }
        
        nic = network_client.network_interfaces.begin_create_or_update(
            rg_name, nic_name, nic_params
        ).result()
        
        # VM 크기에 따라 Gen1/Gen2 결정
        # v5, v6는 Gen2 필수, 나머지는 기본값 사용 (Azure가 자동 선택)
        needs_gen2 = requires_gen2(vm_info['vm_size'])
        
        # Spot VM 생성
        storage_profile_params = {
            'image_reference': get_vm_image_reference(vm_info['vm_size']),
            'os_disk': {
                'create_option': 'FromImage',
                'managed_disk': {
                    'storage_account_type': 'Standard_LRS'
                },
                'delete_option': 'Delete'  # VM 삭제 시 디스크도 삭제
            }
        }
        
        # v5, v6는 Gen2 필수이므로 명시적으로 설정
        if needs_gen2:
            storage_profile_params['hyper_v_generation'] = 'V2'
        
        vm_params = {
            'location': normalize_location(vm_info['location']),
            'zones': [vm_info['zone']],  # Availability Zone
            
            # ★★★ 핵심: Deallocate 정책 (자동 재시작) ★★★
            'priority': 'Spot',
            'eviction_policy': 'Deallocate',  # Delete 아님!
            'billing_profile': {
                'max_price': -1  # On-demand 가격까지 허용
            },
            
            'hardware_profile': {
                'vm_size': vm_info['vm_size']
            },
            'storage_profile': storage_profile_params,
            'os_profile': {
                'computer_name': vm_name[:15],  # 15자 제한
                'admin_username': 'azureuser',
                'admin_password': 'SpotTest123!@#',
            },
            'network_profile': {
                'network_interfaces': [{
                    'id': nic.id,
                    'properties': {
                        'delete_option': 'Delete'  # VM 삭제 시 NIC도 삭제
                    }
                }]
            },
            
            # 시간 기반 삭제를 위한 Tag
            'tags': {
                'experiment': variables.prefix,
                'experiment_end_time': end_time_str,
                'vm_size': vm_info['vm_size'],
                'zone': vm_info['zone']
            }
        }
        
        # 비동기 생성 (기다리지 않음)
        compute_client.virtual_machines.begin_create_or_update(
            rg_name, vm_name, vm_params
        )
        # sleep 제거: 병렬 처리로 대체
        
    except Exception as e:
        print(f"✗ Failed to create {vm_name}: {e}")


def main():
    print(f"\n{'='*70}")
    print(f"Azure Spot VM Multinode Checker")
    print(f"{'='*70}")
    print(f"Prefix: {variables.prefix}")
    print(f"Experiment will end at: {end_time_str}")
    print(f"{'='*70}\n")
    
    # VM 스펙 파싱
    vm_list = parse_vm_specs(variables.vm_specs)
    
    if len(vm_list) == 0:
        print("❌ No valid VM specs found. Please check variables.py")
        return
    
    print(f"Total VMs to create: {len(vm_list)}")
    
    # 스펙별 개수 요약
    spec_summary = {}
    for spec in variables.vm_specs:
        parts = spec.strip().split(',')
        if len(parts) >= 5:
            key = ','.join(parts[:4])  # Tier,Type,Location,Zone
            count = int(parts[4])
            spec_summary[key] = spec_summary.get(key, 0) + count
    
    print("\nVM Specs Summary:")
    for spec, count in spec_summary.items():
        print(f"  - {spec}: {count} VMs")
    print()
    
    
    # Location별 그룹핑
    location_groups = {}
    for vm in vm_list:
        loc = vm['location']
        if loc not in location_groups:
            location_groups[loc] = []
        location_groups[loc].append(vm)
    
    # Location별로 리소스 생성
    for location, vms in location_groups.items():
        print(f"\n{'='*70}")
        print(f"Processing Location: {location} ({len(vms)} VMs)")
        print(f"{'='*70}")
        
        # 리소스 그룹 생성
        rg_name = ensure_resource_group(location)
        
        # VNet/Subnet 생성
        vnet_name, subnet_name = create_vnet_if_not_exists(rg_name, location)
        
        subnet_id = (
            f"/subscriptions/{variables.azure_subscription_id}"
            f"/resourceGroups/{rg_name}"
            f"/providers/Microsoft.Network/virtualNetworks/{vnet_name}"
            f"/subnets/{subnet_name}"
        )
        
        # VM 생성 (병렬 처리)
        # max_workers: 동시에 생성할 VM 개수 (너무 크면 API rate limit에 걸릴 수 있음)
        max_workers = getattr(variables, 'max_parallel_vms', 20)
        
        print(f"Creating {len(vms)} VMs in parallel (max {max_workers} concurrent)...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 VM 생성 작업 제출
            future_to_vm = {
                executor.submit(create_spot_vm, vm, rg_name, subnet_id): vm 
                for vm in vms
            }
            
            # 완료된 작업 추적
            completed = 0
            failed = 0
            for future in as_completed(future_to_vm):
                vm = future_to_vm[future]
                try:
                    future.result()  # 예외 확인
                    completed += 1
                    if completed % 10 == 0:
                        print(f"  Progress: {completed}/{len(vms)} VMs creation started...")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ Failed to start VM creation for {vm.get('vm_size', 'unknown')}: {e}")
        
        elapsed_time = time.time() - start_time
        print(f"✓ Completed: {completed} succeeded, {failed} failed in {elapsed_time:.2f} seconds")
    
    print(f"\n{'='*70}")
    print(f"✅ All {len(vm_list)} VMs creation started!")
    print(f"{'='*70}")
    print(f"\nNote: VMs are being created asynchronously.")
    print(f"Use Azure Portal or CLI to monitor progress:")
    print(f"  az vm list --query \"[].{{Name:name, State:provisioningState}}\" -o table\n")


if __name__ == "__main__":
    main()

