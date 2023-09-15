while IFS=" " read instance region az_id
do
    python3 spot-dingdongditch.py --instance_type=$instance --region=$region --az_id=$az_id &
done < ../data/workloads_10.txt