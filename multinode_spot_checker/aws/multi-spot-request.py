import boto3
import pickle
import time
import datetime
import pytz
import os
# import json

### Spot Checker Mapping Data
region_ami = pickle.load(open('./ami_az_data/region_ami_dict.pkl', 'rb'))  # {x86/arm: {region: (ami-id, ami-info), ...}}
az_map_dict = pickle.load(open('./ami_az_data/az_map_dict.pkl', 'rb'))  # {(region, az-id): az-name, ...}
arm64_family = ['a1', 't4g', 'c6g', 'c6gd', 'c6gn', 'c7gd', 'c7gn', 'im4gn', 'is4gen', 'm6g', 'm6gd', 'm7g', 'm7gd', 'r6g', 'r6gd', 'r7g', 'r7gd', 'x2gd']

def dummy_algorithm(region, instance_family, needed_core, sps):
    region = region
    instance_family = instance_family
    needed_core = needed_core
    sps = sps

    print("\n##### WORK SOMETHING #####")
    dummy_data = {
        'results': [
                {'instance_type': 'p3.2xlarge',
                'az_id': 'usw2-az3',
                'count': '23'},
                {'instance_type': 'p3.16xlarge',
                'az_id': 'usw2-az3',
                'count': '5'}
            ],
        'expectPrice': '$59.2005' 
        }
    # dummy_json = json.dumps(dummy_data, ensure_ascii=False, indent=4)
    # response = json.loads(dummy_json)
    return dummy_data

def spot_instance_request(instance_family, instance_type, az_id, count, time_minute):
    az_name = az_map_dict[(region, az_id)]

    instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'
    ami_id = region_ami[instance_arch][region][0]

    launch_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
    launch_time = launch_time.astimezone(pytz.UTC)
    stop_time = datetime.datetime.now() + datetime.timedelta(hours=0, minutes=(time_minutes + 1))
    stop_time = stop_time.astimezone(pytz.UTC)

    ### Spot Launch Specifications
    launch_spec = {
        'ImageId': ami_id,
        'InstanceType': instance_type,
        'Placement': {'AvailabilityZone': az_name},
        'IamInstanceProfile': {
                'Arn': 'arn:aws:iam::741926482963:instance-profile/EC2toEC2_CW' # IAM ARN for CloudWatch access
            },
    }
    print(f"""\n##### SPOT INSTANCE REQUEST ######\n""")
    print(f"""Instance Type: {instance_type}\nInstance Arhictecture: {instance_arch}\nRegion: {region}\nAZ-ID: {az_id}\nAZ-Name:{az_name}\nAMI ID: {ami_id}\nCount: {count}\nTime Minutes: {time_minute}""")

    ### session & client
    session = boto3.session.Session(profile_name='default')
    ec2 = session.client('ec2', region_name=region)

    # create_request_response = ec2.request_spot_instances(
    #     InstanceCount=count,
    #     LaunchSpecification=launch_spec,
    #     ValidFrom=launch_time,
    #     ValidUntil=stop_time,
    #     Type='persistent'  # not 'one-time', persistent request
    # )
    siri_list = []
    # for rq in create_request_response['SpotInstanceRequests']:
    #     siri_list.append(rq['SpotInstanceRequestId'])

    time.sleep(1)
    print(f"""\n##### SPOT REQUEST DONE #####""")
    return siri_list

if __name__ == "__main__":
    region = input("Region. (ex: us-east-1) = ")
    instance_family = input("Instance Family. (ex: p3) = ")
    needed_core = input("Needed Core. (ex: 1000) = ")
    sps = input("SPS. (1 | 2 | 3) = ")
    time_minutes = int(input("Needed Time. (ex: 10) = "))

    print(f"""\nRegion: {region}\nInstance Family: {instance_family}\nNeeded Core: {needed_core}\nSPS: {sps}\nTime Minutes: {time_minutes}""")    
    
    checking = input("\nPlease check your input.\nIf right, press 'y' : ")
    if checking != "y":
        print("Interrupted!")
        os._exit(0)

    recommand_result = dummy_algorithm(region, instance_family, needed_core, sps)

    for item in recommand_result['results']:
        instance_type = item['instance_type']
        az_id = item['az_id']
        count = item['count']
        print(f"""\n##### Selected Instance #####""")
        print(f"""\nInstance Type: {instance_type}\nAZ: {az_id}\nInstance Count: {count}""")
        spot_instance_request(instance_family, instance_type, az_id, count, time_minutes)