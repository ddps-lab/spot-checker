from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
import os
from uuid import uuid4

credential = AzureCliCredential()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

resource_client = ResourceManagementClient(credential, subscription_id)
network_client = NetworkManagementClient(credential, subscription_id)
compute_client = ComputeManagementClient(credential, subscription_id)


def create_group(group_name: str, location: str):
    resource_client.resource_groups.create_or_update(
        group_name, {"location": location})


def delete_group(group_name: str):
    poller = resource_client.resource_groups.begin_delete(group_name)
    poller.result()


def get_instance(group_name: str, name: str):
    vm_result = compute_client.virtual_machines.get(group_name, name)
    return vm_result


def create_spot_instance(group_name: str, location: str, vm_size: str, name: str = uuid4().replace("-", "")):
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
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest"
            }
        },
        "hardware_profile": {
            "vm_size": vm_size  # "Standard_B1ls"
        },
        "os_profile": {
            "computer_name": name,
            "admin_username": "azureadmin",
            "admin_password": uuid4()
        },
        "network_profile": {
            "network_interfaces": [{
                "id": nic_result.id
            }]
        },
        "priority": "Spot"
    })
    vm_result = poller.result()
    # vm_result["provisioning_state"]

    return vm_result


# group_name = uuid4()
# location = "westus2"
# vm_size = "Standard_B1ls"
# create_group(group_name, location)
# try:
#     create_spot_instance(group_name, location, vm_size)
# except:
#     pass
# finally:
#     delete_group(group_name)
