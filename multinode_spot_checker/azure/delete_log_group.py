"""
CloudWatch Log Group 삭제 스크립트
"""
import boto3
import sys
import variables


def main():
    awscli_profile = variables.awscli_profile
    region = variables.region
    log_group_name = variables.log_group_name
    
    print(f"Deleting CloudWatch Log Group...")
    print(f"  Profile: {awscli_profile}")
    print(f"  Region: {region}")
    print(f"  Log Group: {log_group_name}")
    
    response = input(f"\n⚠️  Are you sure you want to delete '{log_group_name}'? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    try:
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')
        
        # Log Group 삭제
        logs_client.delete_log_group(logGroupName=log_group_name)
        print(f"✅ Log Group deleted: {log_group_name}")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Log Group not found: {log_group_name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

