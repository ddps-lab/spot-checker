import requests


def send_slack_message(instance_type, az_name, time, msg):
    url = ''
    message = f"""
    {instance_type}, {az_name}, {time} : {msg}
    """
    slack_data = {
        "text": message
    }

    requests.post(url, json=slack_data)

