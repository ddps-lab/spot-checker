#!/usr/bin/env python3
"""
Test script to verify az_name_mapped and ami_id_mapped values
"""

import pickle
import variables
from pprint import pprint

# Load mapping data
region_ami = pickle.load(open('./ami_az_data/region_ami_dict.pkl', 'rb'))
az_map_dict = pickle.load(open('./ami_az_data/az_map_dict.pkl', 'rb'))
pprint("region_ami")
pprint(region_ami)

# Parse configuration
instance_type = variables.instance_type
instance_family = instance_type.split('.')[0]

# ARM64 family list
arm64_family = [
    'a1', 't4g', 'c6g', 'c6gd', 'c6gn', 'c7g', 'c7gd', 'c7gn',
    'im4gn', 'is4gen', 'm6g', 'm6gd', 'm7g', 'm7gd', 'm8g',
    'r6g', 'r6gd', 'r7g', 'r7gd', 'r8g', 'x2gd'
]

instance_arch = 'arm' if (instance_family in arm64_family) else 'x86'
regions = variables.region if isinstance(variables.region, list) else [variables.region]
az_ids = variables.az_id if isinstance(variables.az_id, list) else [variables.az_id]

print("=" * 100)
print("AZ & AMI Mapping Test")
print("=" * 100)
print(f"\nConfiguration:")
print(f"  Instance Type: {instance_type}")
print(f"  Instance Family: {instance_family}")
print(f"  Instance Architecture: {instance_arch}")
print(f"  Regions: {regions}")
print(f"  AZ IDs: {az_ids}")

if len(regions) != len(az_ids):
    print(f"\n✗ ERROR: Number of regions ({len(regions)}) != number of az_ids ({len(az_ids)})")
    exit(1)

print(f"\n{'Region':<20} {'AZ-ID':<10} {'AZ-Name':<20} {'AMI-ID':<25} {'OS Type':<20}")
print("-" * 100)

for region, az_id in zip(regions, az_ids):
    try:
        # Get AZ name
        az_name = az_map_dict[(region, az_id)]

        # Get AMI ID and info
        ami_id, ami_info = region_ami[instance_arch][region]

        # Extract OS type from Description or Name
        description = ami_info.get('Description', '')
        name = ami_info.get('Name', '')

        # Determine OS type
        if 'Amazon Linux 2' in description or 'amzn2' in name:
            os_type = 'Amazon Linux 2'
        elif 'Ubuntu' in description or 'ubuntu' in name:
            os_type = 'Ubuntu'
        elif 'RHEL' in description or 'rhel' in name:
            os_type = 'RHEL'
        elif 'CentOS' in description or 'centos' in name:
            os_type = 'CentOS'
        else:
            os_type = 'Unknown'

        print(f"{region:<20} {az_id:<10} {az_name:<20} {ami_id:<25} {os_type:<20}")

    except KeyError as e:
        print(f"{region:<20} {az_id:<10} ✗ ERROR: {str(e)}")
    except Exception as e:
        print(f"{region:<20} {az_id:<10} ✗ ERROR: {str(e)}")

print("\n" + "=" * 100)
print("Test completed!")
print("=" * 100)

# Detailed view
print("\n📋 Detailed Information:\n")
for region, az_id in zip(regions, az_ids):
    try:
        az_name = az_map_dict[(region, az_id)]
        ami_id, ami_info = region_ami[instance_arch][region]

        print(f"[{region}]")
        print(f"  AZ-ID: {az_id}")
        print(f"  AZ-Name: {az_name}")
        print(f"  AMI-ID: {ami_id}")
        print(f"  Description: {ami_info.get('Description', 'N/A')}")
        print(f"  Name: {ami_info.get('Name', 'N/A')}")
        print(f"  Architecture: {ami_info.get('Architecture', 'N/A')}")
        print()

    except Exception as e:
        print(f"[{region}] ✗ ERROR: {str(e)}\n")
