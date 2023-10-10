import os
from datetime import datetime
import boto3
import json
import csv
import variables
import time
import shutil
import subprocess
import random
import string
import pandas as pd

def random_string(length=4):
    characters = string.ascii_letters + string.digits  # 대소문자 알파벳과 숫자 포함
    return ''.join(random.choice(characters) for i in range(length))

def empty_s3_bucket(bucket_name, s3_resource):
    bucket = s3_resource.Bucket(bucket_name)
    
    for obj in bucket.objects.all():
        obj.delete()

def export_logs_to_s3(boto3_session, log_group_name, start_time, end_time, destination_bucket, bucket_prefix, region):
    client = boto3_session.client('logs')

    # Start the export task
    response = client.create_export_task(
        logGroupName=log_group_name,
        fromTime=start_time,
        to=end_time,
        destination=destination_bucket,
        destinationPrefix=bucket_prefix
    )
    
    task_id = response['taskId']
    while True:
        response = client.describe_export_tasks(taskId=task_id)
        status = response['exportTasks'][0]['status']['code']

        if status in ['COMPLETED', 'FAILED']:
            print(f"Region {region} log CloudWatch Logs to S3 Export task {status.lower()}!")
            break
        else:
            time.sleep(2)

    return response

def datetime_to_utc_milliseconds(datetime_str):
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    utc_timestamp = int(dt.timestamp())  # Convert datetime to UTC timestamp in seconds
    return utc_timestamp * 1000  # Convert to milliseconds

def spot_log_parse_log_data_to_csv(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["InstanceType", "AZ", "Timestamp", "Code", "RawCode", "CreateTime", "RequestCreateTime", "StatusUpdateTime"])  # 헤더

        for line in lines:
            log_timestamp, log_data = line.split(' ', 1)
            log_json = json.loads(log_data.strip())
            writer.writerow([log_json['InstanceType'], log_json['AZ'], log_json['Timestamp'], log_json['Code'], log_json['RawCode'], log_json['RequestCreateTime'], log_json['StatusUpdateTime']])

def terminate_log_parse_log_data_to_csv(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["LaunchTime", "TerminateTime", "BillingTime", "InstanceId", "InstanceState", "InstanceType", "AvailabilityZone"])  # 헤더

        for line in lines:
            log_timestamp, log_data = line.split(' ', 1)
            log_json = json.loads(log_data.strip())
            writer.writerow([log_json['LaunchTime'], log_json['TerminateTime'], log_json['BillingTime'], log_json['InstanceId'], log_json['InstanceState'], log_json['InstanceType'], log_json['AvailabilityZone']])

def pending_log_parse_log_data_to_csv(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "InstanceId", "InstanceState", "Region"])  # 헤더

        for line in lines:
            log_timestamp, log_data = line.split(' ', 1)
            log_json = json.loads(log_data.strip())
            writer.writerow([log_json['Timestamp'], log_json['InstanceId'], log_json['InstanceState'], log_json['Region']])

#수정 필요
def download_result(s3_client, bucket_name, log_stream_name, log_type, region, result_folder_path):
    # 버킷에서 객체 목록 조회
    objects = s3_client.list_objects_v2(Bucket=bucket_name)
    
    log_paths = []

    for obj in objects.get('Contents', []):
        if log_stream_name in obj['Key']:
            log_paths.append(obj['Key'])
    
    if not os.path.exists(f'/tmp/spot-availability-test/{region}/{log_type}'):
        os.makedirs(f'/tmp/spot-availability-test/{region}/{log_type}')
    
    if not os.path.exists(f'./result_data/{result_folder_path}/{region}/{log_type}'):
        os.makedirs(f'./result_data/{result_folder_path}/{region}/{log_type}')

    gz_file_names = [path.split("/")[-1] for path in log_paths]
    file_names = [name.replace(".gz", "") for name in gz_file_names]

    for log_path, gz_file_name, file_name in zip(log_paths, gz_file_names, file_names):
        download_path = os.path.join(f'/tmp/spot-availability-test/{region}/{log_type}/{gz_file_name}')
        s3_client.download_file(bucket_name, log_path, download_path)
        subprocess.run(f"cd /tmp/spot-availability-test/{region}/{log_type} && gunzip {gz_file_name}", shell=True, text=True)
        if log_type == "spot":
            spot_log_parse_log_data_to_csv(f"/tmp/spot-availability-test/{region}/{log_type}/{file_name}", f"./result_data/{result_folder_path}/{region}/{log_type}/{file_name}.csv")
        elif log_type == "terminate":
            terminate_log_parse_log_data_to_csv(f"/tmp/spot-availability-test/{region}/{log_type}/{file_name}", f"./result_data/{result_folder_path}/{region}/{log_type}/{file_name}.csv")
        else:
            pending_log_parse_log_data_to_csv(f"/tmp/spot-availability-test/{region}/{log_type}/{file_name}", f"./result_data/{result_folder_path}/{region}/{log_type}/{file_name}.csv")
    
    df_list = [pd.read_csv(f"./result_data/{result_folder_path}/{region}/{log_type}/{file}.csv") for file in file_names]
    if not df_list:
        return 0
    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df.to_csv(f'./result_data/{result_folder_path}/{region}/{log_type}/result.csv', index=False)

    for file_name in file_names:
        if os.path.exists(f"./result_data/{result_folder_path}/{region}/{log_type}/{file_name}.csv"):
            os.remove(f"./result_data/{result_folder_path}/{region}/{log_type}/{file_name}.csv")

    print(f"Region {region} {log_type} log export complete!")

def merge_csv_files(log_type, regions, result_folder_path):
    df_list = []
    
    for region in regions:
        file_path = f"./result_data/{result_folder_path}/{region}/{log_type}/result.csv"
        
        if os.path.exists(file_path):
            df_list.append(pd.read_csv(file_path))
    
    combined_df = pd.concat(df_list, ignore_index=True)
    combined_df.to_csv(f'./result_data/{result_folder_path}/{log_type}_result.csv', index=False)

def main():
    awscli_profile = variables.awscli_profile
    prefix = variables.prefix
    log_group_name = f"{prefix}-spot-availability-tester-log"
    spot_log_stream_name = f"{variables.log_stream_name}-spot"
    terminate_log_stream_name = f"{variables.log_stream_name}-terminate"
    pending_log_stream_name = f"{variables.log_stream_name}-pending"

    # start_time = input("Enter the log start time ex)2020-10-10 10:10 : ")
    # end_time = input("Enter the log end time ex)2020-10-10 10:10 : ")
    # milliseconds_start_time = datetime_to_utc_milliseconds(start_time)
    # milliseconds_end_time = datetime_to_utc_milliseconds(end_time)
    milliseconds_start_time = datetime_to_utc_milliseconds("2023-10-01 00:00")
    milliseconds_end_time = datetime_to_utc_milliseconds("2023-11-01 00:00")

    with open('regions.txt', 'r', encoding='utf-8') as file:
        regions = [line.strip() for line in file.readlines()]

    if os.path.exists('/tmp/spot-availability-test') and os.path.isdir('/tmp/spot-availability-test'):
        shutil.rmtree('/tmp/spot-availability-test')

    global result_folder_path
    while True:
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y-%m-%d")
        result_folder_path = f"{formatted_date}-{random_string()}"
        if not os.path.exists(f'./result_data/{result_folder_path}'):
            os.makedirs(f'./result_data/{result_folder_path}')
            break

    for region in regions:
        boto3_session = boto3.Session(profile_name=awscli_profile, region_name=region)
        s3_resource = boto3_session.resource('s3')
        s3_client = boto3_session.client('s3')
        empty_s3_bucket(f"{prefix}-spot-availability-tester-log-{region}", s3_resource)
        export_logs_to_s3(boto3_session, log_group_name, milliseconds_start_time, milliseconds_end_time, f"{prefix}-spot-availability-tester-log-{region}", "spot-availability-test", region)
        download_result(s3_client, f"{prefix}-spot-availability-tester-log-{region}", spot_log_stream_name, "spot", region, result_folder_path)
        download_result(s3_client, f"{prefix}-spot-availability-tester-log-{region}", terminate_log_stream_name, "terminate", region, result_folder_path)
        download_result(s3_client, f"{prefix}-spot-availability-tester-log-{region}", pending_log_stream_name, "pending", region, result_folder_path)

    merge_csv_files("spot", regions, result_folder_path)
    merge_csv_files("terminate", regions, result_folder_path)
    merge_csv_files("pending", regions, result_folder_path)

if __name__ == "__main__":
    main()
