import boto3
import random
import pickle
import numpy as np
import pandas as pd
from tqdm import tqdm
from io import StringIO

# boto3 setting
session = boto3.session.Session(profile_name='default')
s3_client = session.client('s3')
s3_resource = session.resource('s3')

BUCKET_SPS = 'sps-data'
BUCKET_SPOTINFO = 'spotinfo-data'

# get most recent sps, spotinfo data
top_n = 5

pagenator = s3_client.get_paginator('list_objects').paginate(Bucket=BUCKET_SPS, Prefix='data/')
pages = [page for page in pagenator]
contents = [content['Contents'] for content in pages]
flat_contents = [content for sublist in contents for content in sublist]
sps_objects = [(x['Key'], x['LastModified']) for x in flat_contents if 'pkl' in x['Key']]

sps_list = []
for sps_filename, sps_datetime in tqdm(sps_objects[-top_n:]):
    sps_queries = pickle.loads(s3_resource.Bucket(BUCKET_SPS).Object(sps_filename).get()['Body'].read())
    for query in sps_queries:
        instance_type = query[1]
        scores = query[3]
        for score in scores:
            sps_list.append([instance_type, score['Region'], score['AvailabilityZoneId'], score['Score'], sps_datetime])
            
sps_df = pd.DataFrame(sps_list, columns=['InstanceType', 'Region', 'AvailabilityZoneId', 'Score', 'TimeStamp'])
sps_df = sps_df.sort_values(by=['TimeStamp', 'InstanceType', 'Region', 'AvailabilityZoneId'], ignore_index=True)

pickle.dump(sps_df, open('./sps_df.pkl', 'wb'))

session = boto3.session.Session(profile_name='default')
s3_client = session.client('s3')
s3_resource = session.resource('s3')


pagenator = s3_client.get_paginator('list_objects').paginate(Bucket=BUCKET_SPOTINFO)
pages = [page for page in pagenator]
contents = [content['Contents'] for content in pages]
flat_contents = [content for sublist in contents for content in sublist]
spotinfo_objects = [(x['Key'], x['LastModified']) for x in flat_contents if 'txt' in x['Key']]

spotinfo_df_list = []
for spotinfo_filename, spotinfo_datetime in tqdm(spotinfo_objects[-top_n:]):
    spotinfo_object = s3_resource.Object(bucket_name=BUCKET_SPOTINFO, key=spotinfo_filename)
    spotinfo_response = spotinfo_object.get()
    
    spotinfo_df = pd.read_csv(StringIO(spotinfo_response['Body'].read().decode('utf-8')), skiprows=1)
    spotinfo_df = spotinfo_df[['Region', 'Instance Info', 'Frequency of interruption', 'USD/Hour']]
    spotinfo_df = spotinfo_df.rename(columns={'Instance Info': 'InstanceType',
                                              'Frequency of interruption': 'Frequency',
                                              'USD/Hour': 'Price'})
    spotinfo_df = spotinfo_df[['InstanceType', 'Region', 'Frequency', 'Price']]
    spotinfo_df['TimeStamp'] = spotinfo_datetime
    spotinfo_df = spotinfo_df.sort_values(by=['InstanceType', 'Region'], ignore_index=True)
    spotinfo_df_list.append(spotinfo_df)
    
spotinfo_df = pd.concat(spotinfo_df_list)
pickle.dump(spotinfo_df, open('./spotinfo_df.pkl', 'wb'))

# load and filter dataset
sps = pickle.load(open('./sps_df.pkl', 'rb'))
spotinfo = pickle.load(open('./spotinfo_df.pkl', 'rb'))

spotinfo = spotinfo[spotinfo['TimeStamp'] == spotinfo['TimeStamp'].iloc[-1]]
sps = sps[sps['TimeStamp'] == sps['TimeStamp'].iloc[-1]]

frequency_map = {'<5%': 5, '5-10%': 4, '10-15%': 3, '15-20%': 2, '>20%': 1}
spotinfo = spotinfo.replace({'Frequency': frequency_map})

# join sps and spotinfo
join_df = sps.merge(spotinfo,
                    how='inner',
                    on = ['InstanceType', 'Region'],
                    suffixes=('_sps', '_spotinfo'))

instance_types = join_df['InstanceType']
instance_classes = instance_types.str.extract('([a-zA-Z]+)', expand=True)
instance_families = instance_types.str.extract('([a-zA-Z0-9]+).', expand=True)
join_df['InstanceClass'] = instance_classes
join_df['InstanceFamily'] = instance_families
join_df = join_df[['InstanceClass', 'InstanceFamily', 'InstanceType', 'Region', 'AvailabilityZoneId', 'Score', 'Frequency', 'Price']]

cheap_workload = join_df[join_df['Price'] <= 1]
expensive_workload = join_df[join_df['Price'] > 1]

msk = np.random.rand(len(cheap_workload)) < 0.5
cheap_workload_1 = cheap_workload[msk]
cheap_workload_2 = cheap_workload[~msk]

workload_list_1 = []
cheap_workload_min_1 = cheap_workload_1.groupby(by=['InstanceFamily', 'Region']).min()
for idx, row in cheap_workload_min_1.iterrows():
    workload_info = f"{row['InstanceType']} {idx[1]} {row['AvailabilityZoneId']}"
    workload_list_1.append(workload_info)

workload_list_2 = []
cheap_workload_min_2 = cheap_workload_2.groupby(by=['InstanceFamily', 'Region']).min()
for idx, row in cheap_workload_min_2.iterrows():
    workload_info = f"{row['InstanceType']} {idx[1]} {row['AvailabilityZoneId']}"
    workload_list_2.append(workload_info)

    
with open(f'./data/workloads_{len(cheap_workload_min_1)}_1.txt', 'w') as file:
    file.write('\n'.join(workload_list_1))
    file.close()
    
with open(f'./data/workloads_{len(cheap_workload_min_2)}_2.txt', 'w') as file:
    file.write('\n'.join(workload_list_2))
    file.close()
