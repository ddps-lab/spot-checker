import boto3
import joblib
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta


aws_access_key_id = 'YOUR_AWS_ACCESS_KEY_ID'
aws_secret_access_key = 'YOUR_AWS_SECRET_ACCESS_KEY'
region_name = 'YOUR_REGION_NAME'
bucket_name = ''

s3_client = boto3.client('s3',
                         aws_access_key_id=aws_access_key_id,
                         aws_secret_access_key=aws_secret_access_key,
                         region_name=region_name)


def get_previous_3d():
    current_time = datetime.utcnow()

    floored_minutes = (current_time.minute // 10) * 10
    current_time_floored = current_time.replace(minute=floored_minutes, second=0, microsecond=0)

    time_list_floored = [(current_time_floored - timedelta(minutes=10 * i)).strftime('%Y/%m/%d/%H-%M-%S') for i in range(144)].sort()

    return time_list_floored


def download_rawdata(list_3d):
    date = list_3d[0]

    response = s3_client.get_object(Bucket=bucket_name, Key=f'rawdata/aws/{date}.csv.gz')
    gzip_file = response['Body'].read()
    df = pd.read_csv(BytesIO(gzip_file), compression='gzip')

    df = df[['InstanceType', 'Region', 'AZ', 'SPS']]
    df.rename(columns={'SPS': 0})
    df.dropna(inplace=True)
    df = df[(df['SPS']!=-1)]


    for i in range(1, len(list_3d)):
        date = list_3d[i]

        response = s3_client.get_object(Bucket=bucket_name, Key=f'rawdata/aws/{date}.csv.gz')
        gzip_file = response['Body'].read()
        data = pd.read_csv(BytesIO(gzip_file), compression='gzip')

        data = data[['InstanceType', 'Region', 'AZ', 'SPS']]
        data.rename(columns={'SPS': 0})
        data.dropna(inplace=True)
        data = data[(data['SPS'] != -1)]

        df = pd.merge(df, data, on=['InstanceType', 'Region', 'AZ'])

    return df

def predict_sps(sps_3d):
    xgb = joblib.load("./lr/lr.joblib")
    X = sps_3d.iloc[:, 3:].values
    instance_az = sps_3d.iloc[:, :3]

    predict = xgb.predict(X)

    predicted_sps = pd.DataFrame(predict+1)
    predicted_df = pd.merge(instance_az, predicted_sps, left_index=True, right_index=True)

    predicted_df['SPS_Mean'] = predicted_df.iloc[:,3:].mean(axis=1)
    predicted_df['SPS_STD'] = predicted_df.iloc[:,3:].std(axis=1)
    sps_mean_std = predicted_df[['InstanceType', 'Region', 'AZ', 'SPS_Mean', 'SPS_STD']]

    return sps_mean_std
def make_workload(sps_mean_std):
    conditions = [
        (sps_mean_std['SPS_Mean'] == 3.0),
        (sps_mean_std['SPS_Mean'] < 3.0) & (sps_mean_std['SPS_Mean'] >= 2.5),
        (sps_mean_std['SPS_Mean'] < 2.5) & (sps_mean_std['SPS_Mean'] >= 2.0),
        (sps_mean_std['SPS_Mean'] < 2.0) & (sps_mean_std['SPS_Mean'] >= 1.5),
        (sps_mean_std['SPS_Mean'] < 1.5) & (sps_mean_std['SPS_Mean'] > 1.0),
        (sps_mean_std['SPS_Mean'] == 1.0)
    ]
    choices = [5, 4, 3, 2, 1, 0]

    sps_mean_std['SPS_Mean'] = np.select(conditions, choices)

    conditions = [
        (sps_mean_std['SPS_STD'] >= 0.75),
        (sps_mean_std['SPS_STD'] < 0.75) & (sps_mean_std['SPS_STD'] >= 0.5),
        (sps_mean_std['SPS_STD'] < 0.5) & (sps_mean_std['SPS_STD'] >= 0.25),
        (sps_mean_std['SPS_STD'] < 0.25) & (sps_mean_std['SPS_STD'] > 0.0),
        (sps_mean_std['SPS_STD'] == 0.0)
    ]
    choices = [4, 3, 2, 1, 0]

    sps_mean_std['SPS_STD'] = np.select(conditions, choices)

    sps_mean_std.to_csv('predicted_sps_mean_std.csv', index=False)

    sps_mean_std['SPS_STD'].replace({4:10, 3:15, 2:20, 1:25, 0:30}, inplace=True)

    sps_mean_std[['InstanceType', 'Region', 'AZ', 'SPS_STD']].to_csv('workloads.txt', sep=' ', index=False, header=False)


if __name__ == "__main__":
    list_3d = get_previous_3d()
    sps_3d = download_rawdata(list_3d)
    sps_mean_std = predict_sps(sps_3d)
    make_workload(sps_mean_std)

