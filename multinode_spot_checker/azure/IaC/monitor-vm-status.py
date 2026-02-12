"""
Azure VM 상태 모니터링 Lambda

매 1분마다 실행:
- PREFIX로 시작하는 모든 Resource Group 내 VM 상태 체크
- ProvisioningState 로그를 CloudWatch Logs에 기록
- experiment_end_time Tag를 확인하여 만료된 VM 및 NIC 자동 삭제
"""
import boto3
import os
import time
import json
from datetime import datetime, timezone
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient

# CloudWatch Logs
LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
logs_client = boto3.client('logs')

# Azure 인증
credential = ClientSecretCredential(
    tenant_id=os.environ['AZURE_TENANT_ID'],
    client_id=os.environ['AZURE_CLIENT_ID'],
    client_secret=os.environ['AZURE_CLIENT_SECRET']
)
compute_client = ComputeManagementClient(
    credential, 
    os.environ['AZURE_SUBSCRIPTION_ID']
)
network_client = NetworkManagementClient(
    credential,
    os.environ['AZURE_SUBSCRIPTION_ID']
)
resource_client = ResourceManagementClient(
    credential,
    os.environ['AZURE_SUBSCRIPTION_ID']
)

PREFIX = os.environ['PREFIX']


def create_log_event(message):
    """CloudWatch Logs 기록"""
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': message
    }
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=LOG_STREAM_NAME,
            logEvents=[log_event]
        )
    except Exception as e:
        print(f"Log write failed: {e}")


def delete_vm_with_nics(rg_name, vm_name, vm):
    """
    VM과 연결된 모든 NIC를 삭제 (force delete 적용)
    
    Args:
        rg_name: Resource Group 이름
        vm_name: VM 이름
        vm: VM 객체
    
    Returns:
        int: 삭제된 NIC 개수
    """
    deleted_nics = 0
    
    try:
        # VM 먼저 force delete (연결된 리소스도 함께 처리)
        print(f"  Force deleting VM: {vm_name}")
        compute_client.virtual_machines.begin_delete(rg_name, vm_name, force_deletion=True)
        
        # VM에 연결된 NIC 목록 가져오기
        if vm.network_profile and vm.network_profile.network_interfaces:
            for nic_ref in vm.network_profile.network_interfaces:
                try:
                    # NIC ID에서 NIC 이름 추출
                    # 형식: /subscriptions/.../resourceGroups/RG_NAME/providers/Microsoft.Network/networkInterfaces/NIC_NAME
                    nic_id = nic_ref.id
                    nic_name = nic_id.split('/')[-1]
                    
                    print(f"  Deleting NIC: {nic_name}")
                    # NIC 삭제 (VM 삭제 후이므로 연결 해제됨)
                    network_client.network_interfaces.begin_delete(rg_name, nic_name)
                    deleted_nics += 1
                    
                except Exception as e:
                    # NIC가 이미 삭제되었거나 VM 삭제로 인해 자동 삭제된 경우 무시
                    if "NotFound" not in str(e) and "ResourceNotFound" not in str(e):
                        print(f"  Failed to delete NIC {nic_name}: {e}")
                    else:
                        deleted_nics += 1  # VM 삭제로 인해 자동 삭제된 것으로 간주
        
    except Exception as e:
        print(f"  Error deleting VM and NICs: {e}")
    
    return deleted_nics


def lambda_handler(event, context):
    """
    메인 핸들러
    
    1. PREFIX로 시작하는 모든 Resource Group 찾기
    2. 각 Resource Group의 VM 상태 체크
    3. ProvisioningState 로그만 기록 (공통 timestamp 사용)
    4. experiment_end_time이 지난 VM 및 NIC 삭제
    """
    # 공통 timestamp (년월일시분) - 한 Lambda 실행의 모든 로그가 같은 시간 공유
    current_time = time.time()
    current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
    # 초를 0으로 만들어 분 단위까지만 사용
    common_timestamp = current_dt.replace(second=0, microsecond=0).timestamp()
    common_timestamp_str = datetime.fromtimestamp(common_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:00')
    
    total_vms = 0
    running_vms = 0
    deallocated_vms = 0
    deleted_vms = 0
    deleted_nics = 0
    deleted_rgs = 0
    restarted_vms = 0
    error_vms = 0
    logged_vms = 0  # ProvisioningState 로그 기록된 VM 수
    
    print(f"Lambda execution timestamp: {common_timestamp_str}")
    
    try:
        # PREFIX로 시작하는 모든 리소스 그룹 찾기
        resource_groups = [
            rg for rg in resource_client.resource_groups.list()
            if rg.name.startswith(PREFIX)
        ]
        
        print(f"Found {len(resource_groups)} resource groups with prefix '{PREFIX}'")
        
        for rg in resource_groups:
            rg_name = rg.name
            print(f"Checking Resource Group: {rg_name}")
            
            try:
                # 리소스 그룹의 모든 VM 조회
                vms = list(compute_client.virtual_machines.list(rg_name))
                
                for vm in vms:
                    total_vms += 1
                    
                    try:
                        # Instance View로 상세 상태 조회
                        instance_view = compute_client.virtual_machines.instance_view(
                            rg_name, vm.name
                        )
                        
                        # PowerState 추출
                        power_state = "unknown"
                        provisioning_state = "unknown"
                        
                        for status in instance_view.statuses:
                            if status.code.startswith('PowerState/'):
                                power_state = status.code.split('/')[-1]
                            elif status.code.startswith('ProvisioningState/'):
                                provisioning_state = status.code.split('/')[-1]
                        
                        # 상태 카운트
                        if power_state == "running":
                            running_vms += 1
                        elif power_state in ["deallocated", "stopped"]:
                            deallocated_vms += 1
                        
                        # ProvisioningState가 있는 경우에만 로그 기록
                        if provisioning_state != "unknown":
                            log_data = {
                                "Timestamp": common_timestamp_str,  # 공통 timestamp 사용
                                "TimestampUnix": common_timestamp,
                                "ResourceGroup": rg_name,
                                "VMName": vm.name,
                                "VMSize": vm.hardware_profile.vm_size if vm.hardware_profile else "unknown",
                                "Location": vm.location,
                                "Zone": vm.zones[0] if vm.zones else "none",
                                "Priority": vm.priority if hasattr(vm, 'priority') else "unknown",
                                "PowerState": power_state,
                                "ProvisioningState": provisioning_state
                            }
                            
                            create_log_event(json.dumps(log_data))
                            logged_vms += 1
                        
                        # 실험 종료 시간 체크
                        end_time = None
                        if vm.tags and 'experiment_end_time' in vm.tags:
                            try:
                                # Python 3.7+ 내장 함수 사용 (dateutil 불필요)
                                end_time_str = vm.tags['experiment_end_time']
                                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                                
                                # 실험 종료 시간이 지났으면 삭제
                                if current_dt > end_time:
                                    print(f"Deleting expired VM: {vm.name}")
                                    
                                    # VM과 연결된 NIC 삭제
                                    nics_deleted = delete_vm_with_nics(rg_name, vm.name, vm)
                                    deleted_nics += nics_deleted
                                    deleted_vms += 1
                                    
                                    # 삭제 로그 (Summary와 함께 기록)
                                    print(f"  Deleted VM: {vm.name}, NICs: {nics_deleted}")
                                    continue  # 삭제된 VM은 재시작 시도 안 함
                            except Exception as e:
                                print(f"Error parsing/deleting VM {vm.name}: {e}")
                        
                        # Deallocated 상태인 Spot VM 자동 재시작 시도
                        # (실험 종료 시간 전이고, Spot VM이고, Deallocated 상태인 경우)
                        is_spot = hasattr(vm, 'priority') and vm.priority == 'Spot'
                        if is_spot and power_state == "deallocated":
                            # 실험 종료 시간이 지나지 않았는지 확인
                            if end_time is None or current_dt <= end_time:
                                try:
                                    print(f"Attempting to restart deallocated Spot VM: {vm.name}")
                                    compute_client.virtual_machines.begin_start(rg_name, vm.name)
                                    restarted_vms += 1
                                    print(f"  Restart initiated for VM: {vm.name}")
                                except Exception as e:
                                    # 재시작 실패 (아직 capacity 없을 수 있음)
                                    print(f"  Failed to restart VM {vm.name}: {e}")
                                    # 에러는 무시 (capacity 부족일 수 있으므로)
                    
                    except Exception as e:
                        print(f"Error processing VM {vm.name}: {e}")
                        error_vms += 1
                
                # 리소스 그룹의 모든 VM이 삭제되었는지 확인
                # remaining_vms = list(compute_client.virtual_machines.list(rg_name))
                # if len(remaining_vms) == 0:
                #     # VM이 없으면 리소스 그룹도 삭제
                #     try:
                #         print(f"Resource group {rg_name} is empty, deleting...")
                #         resource_client.resource_groups.begin_delete(rg_name)
                #         deleted_rgs += 1
                #         print(f"  Deleted Resource Group: {rg_name}")
                #     except Exception as e:
                #         print(f"  Failed to delete Resource Group {rg_name}: {e}")
            
            except Exception as e:
                print(f"Error processing resource group {rg_name}: {e}")
        
        # 콘솔 출력만 (CloudWatch Logs에는 기록 안 함)
        print(f"Summary: Total={total_vms}, Logged={logged_vms}, Running={running_vms}, Deallocated={deallocated_vms}, Restarted={restarted_vms}, DeletedVMs={deleted_vms}, DeletedNICs={deleted_nics}, DeletedRGs={deleted_rgs}, Errors={error_vms}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                "TotalVMs": total_vms,
                "LoggedVMs": logged_vms,
                "Running": running_vms,
                "Deallocated": deallocated_vms,
                "Restarted": restarted_vms,
                "DeletedVMs": deleted_vms,
                "DeletedNICs": deleted_nics,
                "DeletedRGs": deleted_rgs,
                "Errors": error_vms
            })
        }
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        
        return {
            'statusCode': 500,
            'body': error_msg
        }

