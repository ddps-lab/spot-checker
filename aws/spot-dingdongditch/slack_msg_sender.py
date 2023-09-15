import requests


def send_slack_message(instance_type, az_name, time, msg):
    url = ''
    msg = f"""
    {instance_type}, {az_name}, {time} : {msg}
    """
    slack_data = {
        "text": msg
    }

    requests.post(url, json=slack_data)

