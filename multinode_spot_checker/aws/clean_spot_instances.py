import boto3
import variables

def main():
    regions = variables.region if isinstance(variables.region, list) else [variables.region]

    print("=" * 60)
    print("SPOT INSTANCE CLEANER (Multi-Region)")
    print(f"Targeting EC2 Instances with Tag: Environment={variables.prefix}-spot-test")
    print("=" * 60)

    for r in regions:
        print(f"\n[Scanning Region: {r}]")
        try:
            session = boto3.Session(profile_name=variables.awscli_profile, region_name=r)
            ec2_client = session.client('ec2')

            # 1. 태그된 Spot 인스턴스 검색
            response = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Environment',
                        'Values': [f'{variables.prefix}-spot-test']
                    },
                    {
                        'Name': 'instance-lifecycle',
                        'Values': ['spot']
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running', 'stopped', 'pending']
                    }
                ]
            )

            instance_ids_to_terminate = []
            spot_request_ids_to_cancel = []

            # Extract all instance IDs and Spot Request IDs from reservations
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_ids_to_terminate.append(instance['InstanceId'])

                    # Get SpotInstanceRequestId if available
                    spot_request_id = instance.get('SpotInstanceRequestId')
                    if spot_request_id:
                        spot_request_ids_to_cancel.append(spot_request_id)

            # 2. Spot Instance Request 취소 (ValidUntil이 길게 남아있을 수 있음)
            if spot_request_ids_to_cancel:
                print(f"  > Cancelling {len(spot_request_ids_to_cancel)} Spot Request(s)...")
                try:
                    ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids_to_cancel)
                    for rid in spot_request_ids_to_cancel:
                        print(f"    - Cancelled Request: {rid}")
                except Exception as e:
                    print(f"    [WARNING] Warning cancelling requests: {e}")

            # 3. EC2 인스턴스 종료
            if instance_ids_to_terminate:
                print(f"  > Terminating {len(instance_ids_to_terminate)} Spot Instance(s)...")
                ec2_client.terminate_instances(InstanceIds=instance_ids_to_terminate)
                for iid in instance_ids_to_terminate:
                    print(f"    - Terminated: {iid}")
            else:
                print("  > No matching Spot Instances found.")

        except Exception as e:
            print(f"ERROR in region {r}: {e}")

    print("\n" + "=" * 60)
    print("Cleanup Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    confirm = input("This will TERMINATE all tagged Spot instances! Proceed? (y/n): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("Cleanup aborted.")
