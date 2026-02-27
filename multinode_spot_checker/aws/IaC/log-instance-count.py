import boto3
import os
from collections import defaultdict
import time
import json
from datetime import datetime, timezone, timedelta

ec2_client = boto3.client('ec2')
logs_client = boto3.client('logs')

LOG_GROUP_NAME = os.environ['LOG_GROUP_NAME']
LOG_STREAM_NAME_COUNT = os.environ['LOG_STREAM_NAME_COUNT']
LOG_STREAM_NAME_PLACEMENT_FAILED = os.environ['LOG_STREAM_NAME_PLACEMENT_FAILED']
RECENT_WINDOW_MINUTES = int(os.environ.get('RECENT_WINDOW_MINUTES', '10'))

# placement 실패로 판단할 상태 코드 목록
PLACEMENT_FAILURE_CODES = {
    'capacity-not-available',
    'spot-capacity-not-available',
    'placement-group-constraint-not-fulfilled',
    'constraint-not-fulfillable',
    'price-too-low',
    'not-scheduled-yet',
    'launch-group-constraint',
    'az-group-constraint',
    'placement-group-constraint',
    'bad-parameters',
}


def put_log(log_stream_name, data):
    log_event = {
        'timestamp': int(time.time() * 1000),
        'message': json.dumps(data)
    }
    logs_client.put_log_events(
        logGroupName=LOG_GROUP_NAME,
        logStreamName=log_stream_name,
        logEvents=[log_event]
    )


def lambda_handler(event, context):
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    recent_cutoff = now_utc - timedelta(minutes=RECENT_WINDOW_MINUTES)

    # ── 1. active/open 요청 집계 → instance_count 스트림 ─────────────
    count_dict = defaultdict(int)
    paginator = ec2_client.get_paginator('describe_spot_instance_requests')

    for page in paginator.paginate(
        Filters=[
            {'Name': 'state', 'Values': ['active', 'open']},
            {'Name': 'type', 'Values': ['persistent']}
        ]
    ):
        for req in page.get('SpotInstanceRequests', []):
            instance_type = req['LaunchSpecification']['InstanceType']
            az = req.get('LaunchedAvailabilityZone') or \
                 req['LaunchSpecification']['Placement']['AvailabilityZone']
            count_dict[(instance_type, az)] += 1

    for (instance_type, az), count in count_dict.items():
        put_log(LOG_STREAM_NAME_COUNT, {
            "EventType": "InstanceCount",
            "Timestamp": timestamp_str,
            "InstanceType": instance_type,
            "AZ": az,
            "Count": count
        })

    # ── 2. placement 실패 수집 → placement_failed 스트림 ─────────────
    # UpdateTime 기반 최근 N분 이내 항목만 기록 (중복 방지)
    for page in paginator.paginate(
        Filters=[
            {'Name': 'state', 'Values': ['closed', 'failed']},
            {'Name': 'type', 'Values': ['persistent']}
        ]
    ):
        for req in page.get('SpotInstanceRequests', []):
            status = req.get('Status', {})
            code = status.get('Code', '')

            if code not in PLACEMENT_FAILURE_CODES:
                continue

            update_time = status.get('UpdateTime')
            if update_time is None or update_time < recent_cutoff:
                continue

            instance_type = req['LaunchSpecification']['InstanceType']
            az = req.get('LaunchedAvailabilityZone') or \
                 req['LaunchSpecification']['Placement']['AvailabilityZone']

            put_log(LOG_STREAM_NAME_PLACEMENT_FAILED, {
                "EventType": "PlacementFailed",
                "Timestamp": update_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "SpotRequestId": req['SpotInstanceRequestId'],
                "InstanceType": instance_type,
                "AZ": az,
                "FailureCode": code,
                "FailureMessage": status.get('Message', ''),
                "RequestState": req['State']
            })

    return {
        'statusCode': 200,
        'body': f'Logged counts for {len(count_dict)} (type, AZ) pairs'
    }
