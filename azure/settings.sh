#!/bin/bash

sudo apt-get update
sudo apt-get install curl python3-pip -y

pip3 install azure-identity azure-mgmt-compute azure-mgmt-resource azure-mgmt-network

curl -L https://aka.ms/InstallAzureCli | bash
