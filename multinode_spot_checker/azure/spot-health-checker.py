from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient

import variables
from uuid import uuid4
import datetime
import base64
import subprocess
import json
import boto3
import time
from threading import Thread

azurecli_user_id = variables.azurecli_user_id
credential = AzureCliCredential()

resource_client = ResourceManagementClient(credential, azurecli_user_id)
network_client = NetworkManagementClient(credential, azurecli_user_id)
compute_client = ComputeManagementClient(credential, azurecli_user_id)

prefix = variables.prefix
log_group_name = f"{prefix}-spot-checker-multinode-log"
log_stream_name_status_change = f"{variables.log_stream_name_change_status}"
log_stream_name_init_time = f"{variables.log_stream_name_init_time}"
region = variables.region
aws_access_key_id = variables.aws_access_key_id
aws_secret_access_key = variables.aws_secret_access_key

custom_data = """#!/bin/bash
current_time=$(date +%s)
current_time_ms=$((current_time * 1000))
sudo apt-get update && sudo apt-get install -y -qq jq
response=$(curl -s -H Metadata:true --noproxy "*" "http://169.254.169.254/metadata/instance/compute/?api-version=2021-02-01" | python3 -m json.tool)
vm_id=$(echo $response | jq -r '.vmId')
vm_name=$(echo $response | jq -r '.name')
vm_size=$(echo $response | jq -r '.vmSize')
location=$(echo $response | jq -r '.location')
echo $vm_id $vm_size $location
log_event=$(cat <<EOF
[
    {
        "timestamp": ${current_time_ms},
        "message": "{\\"timestamp\\": \\"${current_time_ms}\\", \\"vm_id\\": \\"${vm_id}\\", \\"vm_name\\": \\"${vm_name}\\", \\"vm_size\\": \\"${vm_size}\\", \\"location\\": \\"${location}\\"}"
    }
]
EOF
)
echo $log_event

sudo apt-get install -y -qq awscli
aws configure set aws_access_key_id %s
aws configure set aws_secret_access_key %s
aws configure set region %s

aws logs put-log-events --log-group-name %s --log-stream-name %s --log-events "$log_event" --region %s
""" % ("%s", aws_access_key_id, aws_secret_access_key, region, log_group_name, log_stream_name_init_time, region)
customdata_encoded = base64.b64encode(custom_data.encode('utf-8')).decode('utf-8')

def create_group(group_name, location):
    resource_client.resource_groups.create_or_update(
        group_name, {"location": location})


def delete_group(group_name):
    resource_client.resource_groups.begin_delete(group_name)


def get_status(group_name, name):
    vm_result = compute_client.virtual_machines.instance_view(group_name, name)
    if len(vm_result.statuses) < 2:
        return "Unknown"
    return vm_result.statuses[1].display_status


def create_spot_instance(group_name, location, vm_size, name):
    poller = network_client.virtual_networks.begin_create_or_update(group_name, f"VNET-{name}", {
        "location": location,
        "address_space": {
            "address_prefixes": ["10.0.0.0/16"]
        }
    })
    vnet_result = poller.result()

    poller = network_client.subnets.begin_create_or_update(group_name, f"VNET-{name}", f"SUBNET-{name}", {
        "address_prefix": "10.0.0.0/24"
    })
    subnet_result = poller.result()

    poller = network_client.public_ip_addresses.begin_create_or_update(group_name, f"IP-{name}", {
        "location": location,
        "sku": {
            "name": "Standard"
        },
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPV4"
    })
    ip_address_result = poller.result()

    poller = network_client.network_interfaces.begin_create_or_update(group_name, f"NIC-{name}", {
        "location": location,
        "ip_configurations": [{
            "name": f"IPCONFIG-{name}",
            "subnet": {
                "id": subnet_result.id
            },
            "public_ip_address": {
                "id": ip_address_result.id
            }
        }]
    })
    nic_result = poller.result()

    poller = compute_client.virtual_machines.begin_create_or_update(group_name, name, {
        "location": location,
        "storage_profile": {
            "image_reference": {
                "publisher": "Canonical",
                "offer": "0001-com-ubuntu-server-focal",
                "sku": "20_04-lts-arm64" if "p" in vm_size else "20_04-lts-gen2",
                "version": "latest"
            }
        },
        "hardware_profile": {
            "vm_size": vm_size
        },
        "os_profile": {
            "computer_name": name,
            "admin_username": "azureadmin",
            "admin_password": uuid4(),
            "custom_data": customdata_encoded
        },
        "network_profile": {
            "network_interfaces": [{
                "id": nic_result.id
            }]
        },
        "diagnosticsProfile": {
            "bootDiagnostics": {
                "enabled": "true"
            }
        },
        "priority": "Spot",
    })


def auto_shutdown(group_name, name, stop_time):
    command = [
    'az', 'vm', 'auto-shutdown', '-g', group_name,
    '-n', name, '--time', f"{stop_time}"
    ]  
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def azure_vm_list(resource_group_name, launch_time):
    command = [
        'az', 'vm', 'list', '-g', resource_group_name,
        '--query', '[].{vm_id: vmId, vm_size: hardwareProfile.vmSize, time_created: timeCreated}',
        '--output', 'json'
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout

    vms_info = json.loads(output)
    for item in vms_info:
        item['request_time'] = f"{launch_time}"

    logs_client = boto3.client('logs')

    for item in vms_info:
        item = json.dumps(item)
        log_event = {
            'timestamp': int(time.time() * 1000),
            'message': item
        }
        logs_client.put_log_events(logGroupName=log_group_name, logStreamName=log_stream_name_status_change, logEvents=[log_event])


def spot_request(vm_size, location, resource_group_name, instance_name, minutes):
    try:
        launch_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(f"""\nInstance Type: {vm_size}\nInstance Zone: {location}\nGroup Name: {resource_group_name}\nInstance Name: {instance_name}\nLuanch Time: {launch_time}\n""")
        create_spot_instance(resource_group_name, location, vm_size, instance_name)

        stop_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(minutes))
        stop_time = stop_time.strftime("%H%M")
        auto_shutdown(resource_group_name, instance_name, stop_time)
    except:
        print("ERROR OUCCURED")
        raise


def main():
    resource_group_name = f"{prefix}-multinode-spot-checker1"
    location = variables.location
    vm_size = variables.vm_size
    vm_count = variables.vm_count
    minutes = variables.time_minutes
    
    create_group(resource_group_name, location)

    threads = []

    launch_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for i in range(vm_count):
        instance_name = f"{prefix}-vm-{i}"
        th = Thread(target=spot_request, args=(vm_size, location, resource_group_name, instance_name, minutes))
        th.start()
        threads.append(th)

    for th in threads:
        th.join()
    
    print("VM Allocated")
    # vm_list가 바로 조회되지 않아서 3분간 대기 후 로깅
    time.sleep(180)
    azure_vm_list(resource_group_name, launch_time)
    print("Logging azure vm list")

if __name__ == "__main__":
    main()