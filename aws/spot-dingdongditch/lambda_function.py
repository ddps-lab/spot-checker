import boto3
import time
import pickle
import datetime
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

bucket_name = ''
region_ami_dict_key = 'data/region_ami_dict.pkl'
workloads_txt_key = 'data/workloads.txt'
az_map_dict_key = 'data/az_map_dict.pkl'

s3 = boto3.resource('s3', aws_access_key_id='', aws_secret_access_key='')
session = boto3.session.Session()
ec2 = session.client('ec2',  aws_access_key_id='', aws_secret_access_key='')

launch_time = datetime.datetime.now()
status_lock = threading.Lock()

spot_data_list = []


def update_status_code(code, instance_type, az_name):
    with status_lock:
        spot_data_list.append([instance_type, az_name, code, launch_time])


def read_pickle_from_s3(key):
    """Reads a pickled object from S3"""
    obj = s3.Object(bucket_name, key)
    body = obj.get()['Body'].read()
    data = pickle.loads(body)
    return data


def read_file_from_s3(file_key):
    obj = s3.Object(bucket_name, file_key)
    file_content = obj.get()['Body'].read().decode('utf-8')
    return file_content


def upload_file_to_s3():
    df = pd.DataFrame(spot_data_list, columns=['InstanceType', 'AZ', 'status', 'time'])
    df.to_csv('/tmp/spot_data.csv', index=False)
    bucket = s3.Bucket(bucket_name)
    bucket.upload_file('/tmp/spot_data.csv', f'rawdata/{launch_time}.csv')


def create_spot_instance(workload, region_ami, az_map_dict):
    instance_type, region, az_id = workload.split()
    az_name = az_map_dict[(region, az_id)]
    instance_family = instance_type.split('.')[0]
    arm64_family = ['a1', 't4g', 'c7g', 'c7gn', 'c6g', 'c6gd', 'c6gn', 'im4gn', 'is4gen', 'm7g', 'm6g', 'm6gd', 'r7g', 'r6g', 'r6gd', 'x2gd']
    instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'
    ami_id = region_ami[instance_arch][region][0]
    launch_spec = {
        'ImageId': ami_id,
        'InstanceType': instance_type,
        'Placement': {'AvailabilityZone': az_name}
    }
    print(launch_spec)
    create_request_response = ec2.request_spot_instances(
        InstanceCount=1,
        LaunchSpecification=launch_spec,
        Type='one-time'
    )
    request_id = create_request_response['SpotInstanceRequests'][0]['SpotInstanceRequestId']

    while True:
        time.sleep(1)
        spot_request = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])['SpotInstanceRequests'][0]
        code = spot_request['Status']['Code']
        if code == 'fulfilled' or code == 'capacity-not-available':
            update_status_code(code, instance_type, az_name)
            break

    if code == 'fulfilled':
        spot_instance_id = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])['SpotInstanceRequests'][0]['InstanceId']
        ec2.terminate_instances(InstanceIds=[spot_instance_id])

    response = ec2.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id])
    print(response['CancelledSpotInstanceRequests'][0]['State'])


def lambda_handler(event, context):
    az_map_dict = read_pickle_from_s3(az_map_dict_key)
    region_ami = read_pickle_from_s3(region_ami_dict_key)
    workloads = read_file_from_s3(bucket_name, workloads_txt_key)

    workload = workloads.split('\n')
    workload.pop(-1)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = []
        for w in workload:
            futures.append(executor.submit(create_spot_instance, w, region_ami, az_map_dict))

        for f in futures:
            f.result()

    upload_file_to_s3()