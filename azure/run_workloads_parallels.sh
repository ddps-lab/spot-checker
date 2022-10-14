#!/bin/bash
while IFS=" " read zone instance
do
    AZURE_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000 python3 spot-health-checker.py --instance_type=$instance --zone=$zone --time_hours=24 --time_minutes=0 &
done < workload.txt