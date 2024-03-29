import json
import pandas as pd
import variables
import os

prefix = variables.prefix
log_stream_name_chage_status = variables.log_stream_name_chage_status
log_stream_name_init_time = variables.log_stream_name_init_time

'''
디렉터리 구조

log - [sps1, sps2, sps3] - [{instance_type}_{region}_{az}_{instance_count}_{...}, ...] - [{...}_init_time.csv, ...]
'''

os.chdir('./log')
listdir = os.listdir()
if ".DS_Store" in listdir:
    listdir.remove(".DS_Store")

for dir in listdir:
    os.chdir(f"./{dir}")
    log_dir = os.listdir()
    if ".DS_Store" in log_dir:
        log_dir.remove(".DS_Store")
    for json_dir in log_dir:
        index = json_dir.find(prefix)
        change_status_json = f"./{json_dir}/{json_dir[:index]}{log_stream_name_chage_status}"
        init_time_json = f"./{json_dir}/{json_dir[:index]}{log_stream_name_init_time}"
        for file_path in [change_status_json, init_time_json]:
            with open(f"{file_path}.json", 'r') as json_file:
                json_data = json.load(json_file)

            csv_records = []

            for item in json_data:
                message_dict = json.loads(item['message'])
                record = {
                    "timestamp": item['timestamp'],
                    "ingestionTime": item['ingestionTime'],
                    **message_dict
                }
                csv_records.append(record)

            df = pd.DataFrame(csv_records)

            # save CSV file
            csv_file_path = f'./{file_path}.csv'
            df.to_csv(csv_file_path, index=False)

    os.chdir("..")