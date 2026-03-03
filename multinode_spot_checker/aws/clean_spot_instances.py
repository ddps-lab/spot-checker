import boto3
import variables

def main():
    regions = variables.region if isinstance(variables.region, list) else [variables.region]
    
    print("=" * 60)
    print("SPOT INSTANCE CLEANER (Multi-Region)")
    print("Targeting Spot Requests with Tag: Project=spot-checker-multinode")
    print("=" * 60)

    for r in regions:
        print(f"\n[Scanning Region: {r}]")
        try:
            session = boto3.Session(profile_name=variables.awscli_profile, region_name=r)
            ec2_client = session.client('ec2')
            
            # 1. 활성화된 스팟 요청 검색 (태그 기반 필터링)
            response = ec2_client.describe_spot_instance_requests(
                Filters=[
                    {
                        'Name': 'tag:Environment',
                        'Values': [f'{variables.prefix}-spot-test']
                    },
                    {
                        'Name': 'state',
                        'Values': ['open', 'active', 'failed']
                    }
                ]
            )
            
            spot_requests = response.get('SpotInstanceRequests', [])
            
            req_ids_to_cancel = []
            instance_ids_to_terminate = []
            
            for req in spot_requests:
                req_id = req['SpotInstanceRequestId']
                req_ids_to_cancel.append(req_id)
                
                # 이미 인스턴스가 켜져 있다면 (InstanceId가 존재한다면) 해지 리스트에 추가
                instance_id = req.get('InstanceId')
                if instance_id:
                    instance_ids_to_terminate.append(instance_id)

            # 2. 스팟 요청 취소 (Cancel Requests)
            if req_ids_to_cancel:
                print(f"  > Cancelling {len(req_ids_to_cancel)} Spot Requests...")
                ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=req_ids_to_cancel)
                for rid in req_ids_to_cancel:
                    print(f"    - Canceled: {rid}")
            else:
                print("  > No matching Spot Requests found.")

            # 3. 켜져 있는 EC2 인스턴스 강제 종료 (Terminate Instances)
            if instance_ids_to_terminate:
                print(f"  > Terminating {len(instance_ids_to_terminate)} running Instances...")
                ec2_client.terminate_instances(InstanceIds=instance_ids_to_terminate)
                for iid in instance_ids_to_terminate:
                    print(f"    - Terminated: {iid}")
            else:
                print("  > No running Instances to terminate.")
                
        except Exception as e:
            print(f"ERROR in region {r}: {e}")

    print("\n" + "=" * 60)
    print("Cleanup Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    confirm = input("This will CANCEL Spot Requests and TERMINATE running instances! Proceed? (y/n): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("Cleanup aborted.")
