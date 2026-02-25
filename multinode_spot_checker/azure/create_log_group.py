"""
CloudWatch Log Group 생성 스크립트
AWS의 CloudWatch Logs에 로그 그룹을 생성합니다.
"""
import boto3
import sys
import variables


def main():
    awscli_profile = variables.awscli_profile
    region = variables.region
    log_group_name = variables.log_group_name
    
    print(f"Creating CloudWatch Log Group...")
    print(f"  Profile: {awscli_profile}")
    print(f"  Region: {region}")
    print(f"  Log Group: {log_group_name}")
    
    try:
        session = boto3.Session(profile_name=awscli_profile, region_name=region)
        logs_client = session.client('logs')
        
        # Log Group 생성
        logs_client.create_log_group(logGroupName=log_group_name)
        print(f"✅ Log Group created: {log_group_name}")
        
        # Log Stream 생성
        log_stream_name = variables.log_stream_name
        logs_client.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        print(f"✅ Log Stream created: {log_stream_name}")
        
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"⚠️  Log Group already exists: {log_group_name}")
        
        # Log Stream만 추가 시도
        try:
            logs_client.create_log_stream(
                logGroupName=log_group_name,
                logStreamName=log_stream_name
            )
            print(f"✅ Log Stream created: {log_stream_name}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            print(f"⚠️  Log Stream already exists: {log_stream_name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

