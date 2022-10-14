while IFS=" " read instance region az_id
do 
    echo $instance : $region : $az_id;
    python3 spot-health-checker.py --instance_type=$instance --region=$region --az_id=$az_id &
done < ./data/workloads_10.txt
