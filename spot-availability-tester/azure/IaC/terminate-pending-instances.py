"""
Azure VM 정리 Lambda
spot-test-로 시작하는 모든 VM을 즉시 삭제
1분마다 실행되어 테스트 실패/누락된 VM 정리
"""
import boto3
import os
import time
import json
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient

# AWS CloudWatch Logs (결과 기록용)
LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME = os.environ['LOG_STREAM_NAME']
logs_client = boto3.client('logs')

# Azure 인증 및 리소스 설정
PREFIX = os.environ['PREFIX']
AZURE_SUBSCRIPTION_ID = os.environ['AZURE_SUBSCRIPTION_ID']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_REGION = os.environ['AZURE_REGION']  # Display name (e.g. "US West 3")

# Azure 클라이언트 초기화
credential = ClientSecretCredential(
    tenant_id=AZURE_TENANT_ID,
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET
)
compute_client = ComputeManagementClient(credential, AZURE_SUBSCRIPTION_ID)


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


def lambda_handler(event, context):
    """
    VM 삭제 Lambda
    
    호출 방식:
    1. 직접 호출 (tester에서): event에 vm_name, resource_group_name 전달 → 해당 VM만 삭제
    2. EventBridge 스케줄: event가 비어있거나 다른 형식 → spot-test-로 시작하는 모든 VM 스캔 및 삭제
    """
    vms_to_delete = []
    
    # event가 문자열인 경우 파싱 (Lambda invoke의 Payload가 문자열로 전달될 수 있음)
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except (json.JSONDecodeError, TypeError):
            print(f"[WARN] Failed to parse event as JSON: {event[:100]}")
            event = {}
    
    # event에서 직접 호출 여부 확인
    vm_name = event.get('vm_name')
    resource_group_name = event.get('resource_group_name')
    
    # 직접 호출인 경우 (tester에서 호출)
    if vm_name and resource_group_name:
        print(f"[DIRECT CALL] Deleting specific VM: {vm_name} in {resource_group_name}")
        vms_to_delete = [vm_name]
        # resource_group_name을 직접 사용 (AZURE_REGION 환경변수 무시)
    else:
        # EventBridge 스케줄 호출인 경우 (기존 동작)
        print(f"[SCHEDULED CALL] Scanning for all spot-test- VMs")
        region_normalized = AZURE_REGION.replace(" ", "-")
        resource_group_name = f"{PREFIX}-{region_normalized}-rg"
        
        print(f"Scanning Resource Group: {resource_group_name}")
        
        try:
            # Resource Group의 모든 VM 조회
            vms = compute_client.virtual_machines.list(resource_group_name)
            
            for vm in vms:
                vm_name_found = vm.name
                
                # spot-test-로 시작하는 VM만 삭제 대상
                if vm_name_found.startswith('spot-test-'):
                    vms_to_delete.append(vm_name_found)
                    print(f"Found test VM: {vm_name_found}")
        except Exception as e:
            error_message = f"Error scanning VMs: {str(e)}"
            print(error_message)
            create_log_event(json.dumps({
                "Timestamp": time.time(),
                "Error": error_message
            }))
            
            return {
                'statusCode': 500,
                'body': json.dumps({'error': error_message})
            }
    
    # VM 삭제 실행
    deleted_count = 0
    failed_count = 0
    
    for vm_name_to_delete in vms_to_delete:
        try:
            # VM 삭제 (비동기, force_deletion=True로 강제 삭제)
            compute_client.virtual_machines.begin_delete(
                resource_group_name,
                vm_name_to_delete,
                force_deletion=True
            )
            print(f"Force deleting: {vm_name_to_delete}")
            deleted_count += 1
            
            # 로그 기록
            log_data = {
                "Timestamp": time.time(),
                "ResourceGroup": resource_group_name,
                "VMName": vm_name_to_delete,
                "Action": "Deleted",
                "CallType": "direct" if (vm_name and resource_group_name) else "scheduled"
            }
            create_log_event(json.dumps(log_data))
            
        except Exception as e:
            error_msg = str(e)
            # NotFound 에러는 무시 (이미 삭제됨)
            if "NotFound" not in error_msg and "ResourceNotFound" not in error_msg:
                print(f"Failed to delete {vm_name_to_delete}: {error_msg[:100]}")
                failed_count += 1
    
    result_message = f"VM cleanup completed. Deleted: {deleted_count}, Failed: {failed_count}"
    print(result_message)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': result_message,
            'deleted_vms': vms_to_delete,
            'deleted_count': deleted_count,
            'failed_count': failed_count
        })
    }