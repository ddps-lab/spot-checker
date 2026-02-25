import pytz
import time
import boto3
import pickle
import datetime
import base64
import csv
import glob
import os
import variables

### Spot Checker Mapping Data
region_ami = pickle.load(
    open("./ami_az_data/region_ami_dict.pkl", "rb")
)  # {x86/arm: {region: (ami-id, ami-info), ...}}
az_map_dict = pickle.load(
    open("./ami_az_data/az_map_dict.pkl", "rb")
)  # {(region, az-id): az-name, ...}
arm64_family = [
    "a1",
    "t4g",
    "c6g",
    "c6gd",
    "c6gn",
    "c7g",
    "c8g",
    "c7gd",
    "c7gn",
    "i4g",
    "im4gn",
    "is4gen",
    "m6g",
    "m6gd",
    "m7g",
    "m7gd",
    "m8g",
    "r6g",
    "r6gd",
    "r7g",
    "r7gd",
    "r8g",
    "x2gd",
    "i8g",
]

### Spot Checker Arguments Parsing
prefix = variables.prefix
wait_minutes = variables.wait_minutes
time_minutes = variables.time_minutes
time_hours = variables.time_hours


def load_targets_from_csv_dir(test_data_dir):
    """test_data_dir 내 *.csv 파일들을 동적으로 스캔하여
    (instance_type, region, az_name) 리스트를 반환한다.
    region은 파일명에서 추출하고, CSV 내 중복 행은 제거한다.
    """
    targets = []
    csv_files = sorted(glob.glob(os.path.join(test_data_dir, "*.csv")))

    if not csv_files:
        print(f"No CSV files found in {test_data_dir}")
        return targets

    for csv_file in csv_files:
        region = os.path.splitext(os.path.basename(csv_file))[0]
        seen = set()

        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                instance_type = row["InstanceType"]
                az = row["AZ"]
                key = (instance_type, az)
                if key not in seen:
                    seen.add(key)
                    targets.append((instance_type, region, az))

    print(
        f"Loaded {len(targets)} unique targets from {len(csv_files)} CSV files: {[os.path.basename(f) for f in csv_files]}"
    )
    return targets


### Start Spot Checker
def start_spot_checker(target_count, ec2, launch_spec, launch_time, stop_time):
    for i in range(0, target_count):
        create_request_response = ec2.request_spot_instances(
            InstanceCount=1,
            LaunchSpecification=launch_spec,
            #     SpotPrice=spot_price, # default value for on-demand price
            ValidFrom=launch_time,
            ValidUntil=stop_time,
            Type="persistent",  # not 'one-time', persistent request
        )
        time.sleep(0.1)

    return create_request_response


if __name__ == "__main__":
    instance_count = variables.instance_count
    test_data_dir = variables.test_data_dir
    targets = load_targets_from_csv_dir(test_data_dir)

    if not targets:
        print("No targets to process. Exiting.")
        exit(0)

    print(f"Instance count per target: {instance_count}")

    for instance_type, region, az_name in targets:
        ### session & client
        session = boto3.session.Session(profile_name=variables.awscli_profile)
        ec2 = session.client("ec2", region_name=region)

        instance_family = instance_type.split(".")[0]
        instance_arch = "arm" if (instance_family in arm64_family) else "x86"

        log_group_name = f"{prefix}-spot-checker-multinode-log"
        log_stream_name = f"{variables.log_stream_name_init_time}"
        ami_id = region_ami[instance_arch][region][0]
        launch_time = datetime.datetime.now() + datetime.timedelta(minutes=wait_minutes)
        launch_time = launch_time.astimezone(pytz.UTC)
        stop_time = datetime.datetime.now() + datetime.timedelta(
            hours=time_hours, minutes=(time_minutes + wait_minutes)
        )
        stop_time = stop_time.astimezone(pytz.UTC)

        ### Spot Launch Specifications
        launch_spec = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "Placement": {"AvailabilityZone": az_name},
            "IamInstanceProfile": {
                "Arn": "arn:aws:iam::741926482963:instance-profile/EC2toEC2_CW"  # IAM ARN for CloudWatch access
            },
        }

        launch_info = [
            instance_type,
            instance_family,
            instance_arch,
            region,
            az_name,
            az_name,
            ami_id,
        ]
        print(f"""Instance Type: {instance_type}\nInstance Family: {instance_family}\nInstance Arhictecture: {instance_arch}
        Region: {region}\nAZ-Name:{az_name}\nAMI ID: {ami_id}\n""")

        spot_data_dict = {}
        spot_data_dict["launch_spec"] = launch_spec
        spot_data_dict["launch_info"] = launch_info
        spot_data_dict["start_time"] = launch_time
        spot_data_dict["end_time"] = stop_time
        start_spot_checker(instance_count, ec2, launch_spec, launch_time, stop_time)

        time.sleep(2)
