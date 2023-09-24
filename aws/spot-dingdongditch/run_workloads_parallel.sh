while IFS=" " read instance region az_id ding_dong_period
do
    python3 spot-dingdongditch.py --instance_type=$instance --region=$region --az_id=$az_id --ding_dong_period=$ding_dong_period &
done < ./workloads_10.txt