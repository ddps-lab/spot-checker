"""
CloudWatch Logs를 S3로 Export 후 CSV 변환 스크립트
"""
import boto3
import json
import os
import csv
import time
import shutil
import subprocess
import random
import string
import pandas as pd
import variables
from datetime import datetime


def random_string(length=4):
    """랜덤 문자열 생성 (폴더명용)"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def datetime_to_utc_milliseconds(datetime_str):
    """datetime 문자열을 UTC milliseconds로 변환"""
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    utc_timestamp = int(dt.timestamp())
    return utc_timestamp * 1000


def empty_s3_bucket(bucket_name, s3_resource):
    """S3 버킷 비우기"""
    bucket = s3_resource.Bucket(bucket_name)
    
    deleted_count = 0
    for obj in bucket.objects.all():
        obj.delete()
        deleted_count += 1
    
    if deleted_count > 0:
        print(f"  Cleared {deleted_count} objects from S3 bucket")


def export_logs_to_s3(boto3_session, log_group_name, start_time, end_time, destination_bucket, bucket_prefix):
    """CloudWatch Logs를 S3로 Export"""
    client = boto3_session.client('logs')

    print(f"Starting CloudWatch Logs export to S3...")
    print(f"  Time range: {datetime.fromtimestamp(start_time/1000)} - {datetime.fromtimestamp(end_time/1000)}")
    
    # Export task 시작
    response = client.create_export_task(
        logGroupName=log_group_name,
        fromTime=start_time,
        to=end_time,
        destination=destination_bucket,
        destinationPrefix=bucket_prefix
    )
    
    task_id = response['taskId']
    print(f"  Export task ID: {task_id}")
    
    # Export 완료 대기
    while True:
        response = client.describe_export_tasks(taskId=task_id)
        status = response['exportTasks'][0]['status']['code']

        if status == 'COMPLETED':
            print(f"  ✅ Export completed!")
            break
        elif status == 'FAILED':
            print(f"  ❌ Export failed!")
            raise Exception("Export task failed")
        else:
            print(f"  Status: {status}... waiting")
            time.sleep(5)

    return response


def parse_log_data_to_csv(input_file, output_file):
    """JSON 로그를 CSV로 변환"""
    with open(input_file, 'r') as f:
        lines = f.readlines()

    if not lines:
        return

    # 첫 번째 JSON으로 헤더 결정
    first_log = None
    for line in lines:
        try:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                log_data = json.loads(parts[1].strip())
                first_log = log_data
                break
        except:
            continue
    
    if not first_log:
        return

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=first_log.keys())
        writer.writeheader()

        for line in lines:
            try:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    log_data = json.loads(parts[1].strip())
                    writer.writerow(log_data)
            except Exception as e:
                continue


def download_and_process_logs(s3_client, bucket_name, log_stream_name, result_folder_path):
    """S3에서 로그 다운로드 및 처리"""
    # S3 객체 목록 조회
    objects = s3_client.list_objects_v2(Bucket=bucket_name)
    
    log_paths = []
    for obj in objects.get('Contents', []):
        if log_stream_name in obj['Key']:
            log_paths.append(obj['Key'])
    
    if not log_paths:
        print("  ⚠️  No log files found in S3")
        return 0
    
    print(f"  Found {len(log_paths)} log files in S3")
    
    # 임시 디렉토리 생성
    tmp_dir = '/tmp/azure-spot-checker-logs'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    
    result_dir = f'./result_data/{result_folder_path}'
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    gz_file_names = [path.split("/")[-1] for path in log_paths]
    file_names = [name.replace(".gz", "") for name in gz_file_names]

    csv_files = []
    
    # 각 로그 파일 처리
    for log_path, gz_file_name, file_name in zip(log_paths, gz_file_names, file_names):
        download_path = os.path.join(tmp_dir, gz_file_name)
        
        # S3에서 다운로드
        s3_client.download_file(bucket_name, log_path, download_path)
        
        # gunzip 압축 해제
        subprocess.run(f"cd {tmp_dir} && gunzip -f {gz_file_name}", shell=True, text=True)
        
        # CSV로 변환
        csv_file = f"{result_dir}/{file_name}.csv"
        parse_log_data_to_csv(f"{tmp_dir}/{file_name}", csv_file)
        
        if os.path.exists(csv_file):
            csv_files.append(csv_file)
    
    # CSV 파일 병합
    if csv_files:
        print(f"  Merging {len(csv_files)} CSV files...")
        df_list = [pd.read_csv(f) for f in csv_files]
        combined_df = pd.concat(df_list, ignore_index=True)
        
        # TimestampUnix 기준 정렬
        if 'TimestampUnix' in combined_df.columns:
            combined_df = combined_df.sort_values('TimestampUnix')
        elif 'Timestamp' in combined_df.columns:
            combined_df = combined_df.sort_values('Timestamp')
        
        # 최종 CSV 저장
        final_csv = f"{result_dir}/vm_status.csv"
        combined_df.to_csv(final_csv, index=False)
        
        # 개별 CSV 파일 삭제
        for csv_file in csv_files:
            os.remove(csv_file)
        
        print(f"  ✅ Final CSV saved: {final_csv}")
        print(f"  Total records: {len(combined_df)}")
        
        return len(combined_df)
    
    return 0


def main():
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    region = variables.region
    log_group_name = variables.log_group_name
    log_stream_name = variables.log_stream_name
    
    print(f"\n{'='*70}")
    print(f"Azure Spot VM Logs Export (via S3)")
    print(f"{'='*70}")
    print(f"Log Group: {log_group_name}")
    print(f"Log Stream: {log_stream_name}")
    print(f"{'='*70}\n")
    
    # 시간 범위 입력
    start_time_str = input("Enter the log start time (YYYY-MM-DD HH:MM): ")
    end_time_str = input("Enter the log end time (YYYY-MM-DD HH:MM): ")
    
    start_time = datetime_to_utc_milliseconds(start_time_str)
    end_time = datetime_to_utc_milliseconds(end_time_str)
    
    # 결과 폴더 생성
    current_date = datetime.now().strftime("%Y-%m-%d")
    result_folder_path = f"{current_date}-{random_string()}"
    
    # S3 버킷 이름
    bucket_name = f"{prefix}-logs-export"
    bucket_prefix = "vm-logs"
    
    print(f"\nResult folder: {result_folder_path}")
    print(f"S3 bucket: {bucket_name}\n")
    
    # 임시 디렉토리 정리
    if os.path.exists('/tmp/azure-spot-checker-logs'):
        shutil.rmtree('/tmp/azure-spot-checker-logs')
    
    try:
        # boto3 세션
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        s3_resource = boto3_session.resource('s3')
        s3_client = boto3_session.client('s3')
        
        # S3 버킷 확인 (Terraform으로 생성됨)
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ S3 bucket exists: {bucket_name}")
        except:
            print(f"❌ S3 bucket not found: {bucket_name}")
            print(f"   Please run 'python3 create_tester.py' first to create infrastructure")
            return
        
        # S3 버킷 비우기 (이전 export 결과 삭제)
        empty_s3_bucket(bucket_name, s3_resource)
        
        # CloudWatch Logs를 S3로 Export
        export_logs_to_s3(
            boto3_session,
            log_group_name,
            start_time,
            end_time,
            bucket_name,
            bucket_prefix
        )
        
        # S3에서 다운로드 및 CSV 변환
        total_records = download_and_process_logs(
            s3_client,
            bucket_name,
            log_stream_name,
            result_folder_path
        )
        
        print(f"\n{'='*70}")
        print(f"✅ Export completed successfully!")
        print(f"{'='*70}")
        print(f"Total records: {total_records}")
        print(f"Output: ./result_data/{result_folder_path}/vm_status.csv")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

