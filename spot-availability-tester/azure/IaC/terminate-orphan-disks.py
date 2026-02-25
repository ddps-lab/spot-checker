"""
Azure Disk 자동 정리 Lambda
테스트 환경의 모든 디스크를 주기적으로 삭제
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
    Resource Group의 모든 디스크 삭제
    테스트 환경이므로 모든 disk를 정리
    """
    disks_to_delete = []
    disk_logs = []
    
    # Resource Group 이름 생성
    region_normalized = AZURE_REGION.replace(" ", "-")
    resource_group_name = f"{PREFIX}-{region_normalized}-rg"
    
    print(f"Checking disks in Resource Group: {resource_group_name}")
    
    try:
        # Resource Group의 모든 Managed Disk 조회
        disks = compute_client.disks.list_by_resource_group(resource_group_name)
        
        for disk in disks:
            disk_name = disk.name
            disks_to_delete.append(disk_name)
            
            # 로그 데이터 생성
            log_data = {
                "Timestamp": time.time(),
                "ResourceGroup": resource_group_name,
                "DiskName": disk_name,
                "DiskId": disk.id,
                "Location": disk.location,
                "DiskSizeGB": disk.disk_size_gb if hasattr(disk, 'disk_size_gb') else 'Unknown',
                "DiskState": disk.disk_state if hasattr(disk, 'disk_state') else 'Unknown',
                "ManagedBy": disk.managed_by if disk.managed_by else "None (Orphan)",
                "Reason": "Disk cleanup in test environment"
            }
            disk_logs.append(log_data)
            
            print(f"Marking for deletion: {disk_name}")
        
        # Disk 삭제 실행
        deleted_count = 0
        for disk_name in disks_to_delete:
            try:
                # Disk 삭제 (비동기)
                compute_client.disks.begin_delete(
                    resource_group_name,
                    disk_name
                )
                print(f"Delete operation started for: {disk_name}")
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {disk_name}: {e}")
        
        # 로그 기록
        for log in disk_logs:
            create_log_event(json.dumps(log))
        
        result_message = f"Disk cleanup completed. Deleted {deleted_count} disks out of {len(disks_to_delete)} found."
        print(result_message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': result_message,
                'deleted_disks': disks_to_delete,
                'deleted_count': deleted_count
            })
        }
        
    except Exception as e:
        error_message = f"Error during disk cleanup: {str(e)}"
        print(error_message)
        create_log_event(json.dumps({
            "Timestamp": time.time(),
            "Error": error_message
        }))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }

