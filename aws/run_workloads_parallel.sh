while IFS=" " read instance region az_id instance_count
do
    echo $instance : $region : $az_id : $instance_count;
    python3 spot-health-checker.py --instance_type=$instance --region=$region --az_id=$az_id --instance_count=$instance_count&
done < ./data/workloads_10.txt