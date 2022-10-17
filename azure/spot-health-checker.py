from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
import argparse
from typing import Any, Dict, List
import os
from uuid import uuid4
from datetime import datetime, timedelta
import time
from pathlib import Path

PRINT_LOG = True
SAVE_LOG_INTERVAL_SEC = 60 * 60

credential = AzureCliCredential()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

resource_client = ResourceManagementClient(credential, subscription_id)
network_client = NetworkManagementClient(credential, subscription_id)
compute_client = ComputeManagementClient(credential, subscription_id)


class Logger:
    def __init__(self, instance_type: str, instance_zone: str, instance_name: str, launch_time: datetime, path: str = "./logs"):
        """
        Logger

        :param instance_type: Instance type of log to save
        :param instance_zone: Instance zone of log to save
        :param instance_name: Instance name of log to save
        :param launch_time: Start time of health checker
        :param created_time: Creation time of instance
        :param path: Path to save logs (default: "./logs")
        """
        self.logs: List[Dict] = []
        self.keys: List[str] = []
        Path(path).mkdir(exist_ok=True)
        self.file_path = os.path.join(
            path, f"{instance_type}_{instance_zone}_{launch_time}.csv")
        self.instance_type = instance_type
        self.instance_zone = instance_zone
        self.instance_name = instance_name

        self.logging = True

    def set_logging(self, logging: bool) -> None:
        self.logging = logging

    def print_log(self, message: str) -> None:
        """
        Print log message when logging is enabled.

        :param message: message to print
        """
        if self.logging:
            print(
                f"[!] {self.instance_type}/{self.instance_zone}/{self.instance_name}: {message}")

    def print_error(self, message: str) -> None:
        """
        Print error message

        :param message: message to print
        """
        print(
            f"[-] {self.instance_type}/{self.instance_zone}/{self.instance_name}: {message}")

    def append(self, val: Any) -> None:
        """
        Append log

        :param val: Value to append
        """
        self.logs.append(val)

    def save_log(self) -> None:
        """
        Save log
        """
        self.print_log("Saving logs...")
        try:
            if not self.logs:
                return
            if not self.keys:  # init log dict keys and csv file
                self.keys = list(self.logs[0].keys())
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(",".join(self.keys))

            content = []
            for i in self.logs:
                tmp = []
                for j in self.keys:
                    tmp.append(str(i[j]))
                content.append(",".join(tmp))

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(content))

            self.logs = []
            self.print_log("Save log successful")
        except Exception as e:
            self.print_error("Save log failed")
            print(e)


def create_group(group_name: str, location: str):
    resource_client.resource_groups.create_or_update(
        group_name, {"location": location})


def delete_group(group_name: str):
    poller = resource_client.resource_groups.begin_delete(group_name)
    poller.result()


def get_status(group_name: str, name: str):
    vm_result = compute_client.virtual_machines.instance_view(group_name, name)
    if len(vm_result.statuses) < 2:
        return "Unknown"
    return vm_result.statuses[1].display_status


def create_spot_instance(group_name: str, location: str, vm_size: str, name: str):
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

    return vm_result


def start_instance(group_name: str, name: str):
    poller = compute_client.virtual_machines.begin_start(group_name, name)
    poller.result()


parser = argparse.ArgumentParser(description="Spot Checker For Azure")
parser.add_argument("--instance_name", type=str,
                    default=str(uuid4()))
parser.add_argument("--instance_type", type=str, default="Standard_DS1_v2")
parser.add_argument("--zone", type=str, default="westus2")
parser.add_argument("--time_hours", type=int, default="0")
parser.add_argument("--time_minutes", type=int, default="5")
args = parser.parse_args()


launch_time = datetime.utcnow()

instance_name = args.instance_name
instance_type = args.instance_type
instance_zone = args.zone

logger = Logger(instance_type, instance_zone, instance_name, launch_time)

hours = args.time_hours
minutes = args.time_minutes

group_name = f"{instance_zone}_{instance_type}_{instance_name}"

print(
    f"""Instance Name: {instance_name}\nInstance Type: {instance_type}\nInstance Zone: {instance_zone}\nGroup Name: {group_name}""")

create_group(group_name, instance_zone)

logger.print_log("Creating instance...")
try:
    create_spot_instance(group_name, instance_zone,
                         instance_type, instance_name)
except:
    logger.print_error("Creating instance failed")
    logger.print_log("Deleting group...")
    delete_group(group_name)
    raise

created_time = datetime.utcnow()
logger.append({"time": created_time, "status": "CREATED"})
logger.print_log("Create successful")


stop_time = datetime.utcnow() + timedelta(hours=hours, minutes=minutes)
status_old = None
next_log_time = datetime.utcnow() + timedelta(seconds=5)
next_save_time = datetime.utcnow() + timedelta(seconds=SAVE_LOG_INTERVAL_SEC)

try:
    while True:
        if datetime.utcnow() > stop_time:
            logger.print_log("Done")
            break
        if datetime.utcnow() >= next_save_time:
            logger.save_log()
            next_save_time += timedelta(seconds=SAVE_LOG_INTERVAL_SEC)
        try:
            status = get_status(group_name, instance_name)

            logger.append({"time": datetime.utcnow(), "status": status})

            if status != status_old:
                logger.print_log(f"Status Changed - {status}")
                status_old = status

            if status == "VM deallocated":
                logger.print_log("Instance stopped. Restarting...")
                try:
                    start_instance(group_name, instance_name)
                    logger.print_log("Restart successful")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.print_error("Restart failed")
                    print(e)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.print_error("Unknown Error")
            print(e)

        if datetime.utcnow() >= next_log_time:
            next_log_time = datetime.utcnow() + timedelta(seconds=5)
        else:
            time.sleep((next_log_time - datetime.utcnow()).total_seconds())
            next_log_time += timedelta(seconds=5)

except KeyboardInterrupt:
    logger.print_error("KeyboardInterrupt raised. Shutting down gracefully...")

logger.save_log()

try:
    logger.print_log("Deleting instance...")
    delete_group(group_name)
    logger.print_log("Delete successful")
except:
    logger.print_error("Delete failed")
