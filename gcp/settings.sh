#!/bin/bash
GCP_CLI_VER="402.0.0"
ARCH=$(uname -m)

sudo apt-get update
sudo apt-get install curl tar python3-pip -y

pip3 install google-cloud-compute # pytz google-api-python-client

if [[ $ARCH =~ (arm|aarch) ]]
then
    echo "ARM Detected"
    ARCH="arm"
else
    echo "X86_64 Detected"
    ARCH="x86_64"
fi

FILENAME="google-cloud-cli-$GCP_CLI_VER-linux-$ARCH.tar.gz"

curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/$FILENAME

tar -xf $FILENAME
chmod +x ./google-cloud-sdk/install.sh
./google-cloud-sdk/install.sh
