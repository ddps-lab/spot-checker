import boto3
import random
import pickle
import numpy as np
import pandas as pd
from tqdm import tqdm
from io import StringIO

# boto3 setting
start_date = "2022-07-11"
end_date = "2022-07-12"
profile_name = "default"
region_name = "us-west-2"

timestream_data = {"SpotPrice" : [], "Savings" : [], "SPS" : [], "AZ" : [], "Region" : [], "InstanceType" : [], "IF" : [], "time" : []}

def run_query(query_string):
    try:
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        query_client = session.client('timestream-query')
        paginator = query_client.get_paginator('query')
        page_iterator = paginator.paginate(QueryString=query_string)
        for page in page_iterator:
            _parse_query_result(page)
    except Exception as err:
        print("Exception while running query:", err)

def _parse_query_result(query_result):
    query_status = query_result["QueryStatus"]

    column_info = query_result['ColumnInfo']
    for row in query_result['Rows']:
        _parse_row(column_info, row)

def _parse_row(column_info, row):
    data = row['Data']
    row_output = []
    for j in range(len(data)):
        info = column_info[j]
        datum = data[j]
        row_output.append(_parse_datum(info, datum))

    return "{%s}" % str(row_output)

def _parse_datum(info, datum):
    if datum.get('NullValue', False):
        return "%s=NULL" % info['Name'],

    column_type = info['Type']

    # If the column is of TimeSeries Type
    if 'TimeSeriesMeasureValueColumnInfo' in column_type:
        return _parse_time_series(info, datum)

    # If the column is of Array Type
    elif 'ArrayColumnInfo' in column_type:
        array_values = datum['ArrayValue']
        return "%s=%s" % (info['Name'], _parse_array(info['Type']['ArrayColumnInfo'], array_values))

    # If the column is of Row Type
    elif 'RowColumnInfo' in column_type:
        row_column_info = info['Type']['RowColumnInfo']
        row_values = datum['RowValue']
        return _parse_row(row_column_info, row_values)

    # If the column is of Scalar Type
    else:
        global timestream_data
        if info['Name'] == "time":
            timestream_data[info['Name']].append(datum['ScalarValue'].split('.')[0]+"+00:00")
        elif info['Name'] != "measure_name" and info['Name'] != "measure_value::double":
            timestream_data[info['Name']].append(datum['ScalarValue'])
        return _parse_column_name(info) + datum['ScalarValue']

def _parse_time_series(info, datum):
    time_series_output = []
    for data_point in datum['TimeSeriesValue']:
        time_series_output.append("{time=%s, value=%s}"
                                    % (data_point['Time'],
                                        _parse_datum(info['Type']['TimeSeriesMeasureValueColumnInfo'],
                                                        data_point['Value'])))
    return "[%s]" % str(time_series_output)

def _parse_array(array_column_info, array_values):
    array_output = []
    for datum in array_values:
        array_output.append(_parse_datum(array_column_info, datum))

    return "[%s]" % str(array_output)

def run_query_with_multiple_pages(limit):
    query_with_limit = SELECT_ALL + " LIMIT " + str(limit)
    print("Starting query with multiple pages : " + query_with_limit)
    run_query(query_with_limit)

def cancel_query():
    print("Starting query: " + SELECT_ALL)
    result = client.query(QueryString=SELECT_ALL)
    print("Cancelling query: " + SELECT_ALL)
    try:
        client.cancel_query(QueryId=result['QueryId'])
        print("Query has been successfully cancelled")
    except Exception as err:
        print("Cancelling query failed:", err)

def _parse_column_name(info):
    if 'Name' in info:
        return info['Name'] + "="
    else:
        return ""

def get_timestream(start_date, end_date):
    print(f"Start query ({start_date}~{end_date})")
    query_string = f"""SELECT * FROM "spotrank-timestream"."spot-table" WHERE time between from_iso8601_date('{start_date}') and from_iso8601_date('{end_date}') ORDER BY time"""
    run_query(query_string)
    print(start_date + "~" + end_date + " is end")
    timestream_df = pd.DataFrame(timestream_data)
    timestream_df.drop_duplicates(inplace=True)
    return timestream_df

join_df = get_timestream(start_date, end_date)
join_df = join_df[join_df['time'] == max(join_df['time'].unique())]

frequency_map = {'<5%': 5, '5-10%': 4, '10-15%': 3, '15-20%': 2, '>20%': 1}
join_df = join_df.replace({'IF': frequency_map})
instance_types = join_df['InstanceType']
instance_classes = instance_types.str.extract('([a-zA-Z]+)', expand=True)
instance_families = instance_types.str.extract('([a-zA-Z0-9]+).', expand=True)
join_df['InstanceClass'] = instance_classes
join_df['InstanceFamily'] = instance_families
join_df['SpotPrice'] = join_df['SpotPrice'].astype(float)
join_df = join_df[['InstanceClass', 'InstanceFamily', 'InstanceType', 'Region', 'AZ', 'SPS', 'IF', 'SpotPrice']]

cheap_workload = join_df[join_df['SpotPrice'] <= 1]
expensive_workload = join_df[join_df['SpotPrice'] > 1]

cheap_workload_min = cheap_workload.sort_values(by=['SpotPrice']).groupby(by=['InstanceFamily', 'Region']).first()
msk = np.random.rand(len(cheap_workload_min)) < 0.3
cheap_workload_min_1 = cheap_workload_min[msk]
cheap_workload_min_2 = cheap_workload_min[~msk]

workload_list_1 = []
for idx, row in cheap_workload_min_1.iterrows():
    workload_info = f"{row['InstanceType']} {idx[1]} {row['AZ']}"
    workload_list_1.append(workload_info)

workload_list_2 = []
for idx, row in cheap_workload_min_2.iterrows():
    workload_info = f"{row['InstanceType']} {idx[1]} {row['AZ']}"
    workload_list_2.append(workload_info)
    
with open(f'./data/workloads_{len(cheap_workload_min_1)}_1.txt', 'w') as file:
    file.write('\n'.join(workload_list_1))
    file.close()
    
with open(f'./data/workloads_{len(cheap_workload_min_2)}_2.txt', 'w') as file:
    file.write('\n'.join(workload_list_2))
    file.close()
