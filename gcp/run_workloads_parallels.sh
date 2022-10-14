#!/bin/bash
while IFS=" " read zone instance
do
    GOOGLE_APPLICATION_CREDENTIALS=spot-checker-27158a2ef6bc.json python3 spot-health-checker.py --instance_type=$instance --zone=$zone --time_hours=24 --time_minutes=0 &
done < workload.txt