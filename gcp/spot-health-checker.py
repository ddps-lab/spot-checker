import argparse
from typing import Any, Dict, List
from google.cloud import compute_v1 as compute
from google.api_core.extended_operation import ExtendedOperation
import os
import json
from uuid import uuid4
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import sys
import requests

SLACK_URL = ""


# print to slack webhook
def print(msg):
    sys.stdout.write(f"{msg}\n")
    requests.post(SLACK_URL, json={"text": f"{msg}"})


PRINT_LOG = True
SAVE_LOG_INTERVAL_SEC = 60 * 60

IMAGE_PROJECT_NAME = "ubuntu-os-cloud"
IMAGE_NAME = "ubuntu-2204-lts"

with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], "r", encoding="utf-8") as f:
    PROJECT_NAME = json.loads(f.read())["project_id"]


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


def get_image(project: str, family: str, arch: str) -> str:
    """
    Returns the image link that is part of an image family

    :param project: Project ID for this request.
    :param family: Name of the image family to get.
    :param arch: Architecture of a CPU. Must follow this format:
        "(x86|arm)"
    """
    return compute.ImagesClient().get_from_family(
        project=project, family=(
            family + ("-arm64" if arch == "arm" else "")
        )
    ).self_link


def get_disk(source_image: str, disk_type: str, disk_size: int = 10, boot: bool = True, auto_delete: bool = True) -> compute.AttachedDisk:
    """
    Returns an AttachedDisk object

    :param source_image: Source image URL to use.
    :param disk_type: Disk type to use. Must follow this format:
        "zones/{zone}/diskTypes/pd-(standard|ssd|balanced|extreme)"
    :param disk_size: Disk size to use. (GB)
    :param boot: Whether the disk is bootable.
    :param auto_delete: Whether to delete a disk when deleting a VM.
    """
    return compute.AttachedDisk(
        initialize_params=compute.AttachedDiskInitializeParams(
            source_image=source_image,
            disk_type=disk_type,
            disk_size_gb=disk_size
        ),
        boot=boot,
        auto_delete=auto_delete
    )


def get_instance(project: str, zone: str, name: str) -> compute.Instance:
    """
    Returns instance

    :param project: Project ID for this request.
    :param zone: Zone of instance.
    :param name: Name of instance.
    """
    return compute.InstancesClient().get(project=project, zone=zone, instance=name)


def wait_for_operation(operation: ExtendedOperation, timeout: int = 300) -> Any:
    """
    Wait ExtendedOperation and return result

    :param operation: An ExtendedOperation to wait.
    :param timeout: Seconds to wait for the operation. If None, wait indefinitely.
    """
    result = operation.result(timeout=timeout)

    if operation.error_code:
        raise operation.exception() or RuntimeError(operation.error_message)

    return result


def create_spot_instance(project: str, zone: str, name: str, disks: List[compute.AttachedDisk], machine_type: str) -> None:
    """
    Create spot instance

    :param project: Project ID for this request.
    :param zone: Zone to create spot instance.
    :param name: Name of spot instance
    :param disks: List of AttachedDisk
    :param machine_type: Machine type to create
    """
    instance_resource = compute.Instance(
        network_interfaces=[
            compute.NetworkInterface(
                name="global/networks/default",
                access_configs=[
                    compute.AccessConfig(
                        type_="ONE_TO_ONE_NAT",
                        name="External NAT",
                        network_tier="PREMIUM"
                    )
                ]
            )
        ],
        name=name,
        disks=disks,
        machine_type=machine_type,
        scheduling=compute.Scheduling(
            provisioning_model="SPOT",
            instance_termination_action="STOP"
        )
    )
    operation = compute.InstancesClient().insert(
        compute.InsertInstanceRequest(
            zone=zone,
            project=project,
            instance_resource=instance_resource
        )
    )
    wait_for_operation(operation)


def start_instance(project: str, zone: str, name: str) -> None:
    """
    Start instance

    :param project: Project ID for this request.
    :param zone: Zone of instance to start
    :param name: Name of instance to start
    """
    operation = compute.InstancesClient().start(
        project=project, zone=zone, instance=name)
    wait_for_operation(operation)


def delete_instance(project: str, zone: str, name: str) -> None:
    """
    Delete instance

    :param project: Project ID for this request.
    :param zone: Zone of instance to delete
    :param name: Name of instance to delete
    """
    operation = compute.InstancesClient().delete(
        project=project, zone=zone, instance=name
    )
    wait_for_operation(operation)


parser = argparse.ArgumentParser(description="Spot Checker For GCP")
parser.add_argument("--instance_name", type=str,
                    default="instance-" + str(uuid4()).replace("-", ""))
parser.add_argument("--instance_type", type=str, default="n1-standard-1")
parser.add_argument("--instance_disk_type", type=str, default="pd-standard")
parser.add_argument("--zone", type=str, default="us-east1-b")
parser.add_argument("--time_hours", type=int, default="0")
parser.add_argument("--time_minutes", type=int, default="5")
args = parser.parse_args()
# zone, instance_type, /* wait_minutes */, time_minutes, time_hours

launch_time = datetime.utcnow()

instance_name = args.instance_name
instance_type = args.instance_type
instance_disk_type = args.instance_disk_type
instance_arch = "arm" if instance_type.lower().startswith("t2a") else "x86"
instance_zone = args.zone
instance_region = "-".join(instance_zone.split("-")[:-1])

logger = Logger(instance_type, instance_zone, instance_name, launch_time)

hours = args.time_hours
minutes = args.time_minutes

print(f"""Instance Name: {instance_name}\nInstance Type: {instance_type}\nInstance DiskType: {instance_disk_type}\nInstance Arch: {instance_arch}\nInstance Region: {instance_region}\nInstance Zone: {instance_zone}""")

logger.print_log("Creating instance...")
try:
    create_spot_instance(PROJECT_NAME, instance_zone, instance_name, [get_disk(get_image(
        IMAGE_PROJECT_NAME, IMAGE_NAME, instance_arch), f"zones/{instance_zone}/diskTypes/{instance_disk_type}")], f"zones/{instance_zone}/machineTypes/{instance_type}")
except Exception as e:
    print(f"{instance_name} {instance_type} {instance_region} {instance_zone} {e}")
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
            spot_instance = get_instance(
                PROJECT_NAME, instance_zone, instance_name)

            # status can be PROVISIONING, STAGING, RUNNING, STOPPING, REPAIRING, TERMINATED, SUSPENDING, SUSPENDED
            # https://cloud.google.com/compute/docs/instances/instance-life-cycle
            status = spot_instance.status

            logger.append({"time": datetime.utcnow(), "status": status})

            if status != status_old:
                logger.print_log(f"Status Changed - {status}")
                status_old = status

            if status == "TERMINATED":
                logger.print_log("Instance stopped. Restarting...")
                try:
                    start_instance(PROJECT_NAME, instance_zone, instance_name)
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
    delete_instance(PROJECT_NAME, instance_zone, instance_name)
    logger.print_log("Delete successful")
except:
    logger.print_error("Delete failed")
