import os
import time
import math
import pickle
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timedelta

# 가격 데이터 읽어옴
price_2022 = pd.read_csv(f"/tf/kyunghwan/ieee_journal/data/rawdata/aws/2022/07/12/04-20-00.csv.gz", compression='gzip')

file_list = []

for (path, dir, files) in os.walk(f"/tf/kmkim/aws_csvFiles_2022/"):
    for filename in files:
        ext = os.path.splitext(filename)[-1]
        if ext == '.csv':
            file_list.append("%s%s" % (path, filename))


# 순서대로 비교할 수 있게 정렬
file_list.sort()

# spot-checker 데이터 전처리
df_list = []

for filename in tqdm(file_list):
    df = pd.read_csv(filename)
    # Timestamp를 str에서 timestamp로 type 변경
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    # Fulfilled와 Interrupted 제외하고 requesting...으로 log 변경
    df['Code'] = df['Code'].apply(lambda x: 'requesting...' if (x != 'fulfilled' and x != 'capacity-not-available') else x)
    instanceType = filename.split("/")[-1].split("_")[0]
    region = filename.split("/")[-1].split("_")[1]
    az = filename.split("/")[-1].split("_")[2].split(".")[0]
    instance_info = (instanceType, region, az)
    price_info = price_2022[((price_2022['InstanceType'] == instanceType) & (price_2022['Region'] == region) & (price_2022['AZ'] == az))]
    spotPrice = float(price_info['SpotPrice'])
    testMinutes = math.ceil((df['Timestamp'][len(df['Timestamp'])-1] - df['Timestamp'][0]).total_seconds() / 60)
    df_list.append((df, instance_info, spotPrice, testMinutes, df['Timestamp'][len(df['Timestamp'])-1]))

pickle.dump(df_list, open("df_list.pkl", "wb"))    

# DataFrame을 만들기 위한 데이터 기록
simulation = {
    "InstanceType": [],
    "Region": [],
    "AZ": [],
    "Period": [],
    "Cost": [],
    "InterruptedCount": [],
    "FulfilledCount": [],
    "MissingInterruptedCount": [],
    "MissingFulfilledCount": [],
    "MissingRate": [],
    "MissingFulfilledRate": [],
    "MissingInterruptedRate": [],
}

# 병렬처리를 위한 파라미터
# p_term과 p_order를 달리하여 여러 파일에서 실행 가능
p_term = 1440
p_order = 1

print(f"{p_term*(p_order-1)+1} ~ {p_term*p_order}")

for p in tqdm(range(p_term*(p_order-1)+1, p_term*p_order+1)):
    for df, instance_info, spotPrice, testMinutes, testEndTime in df_list:
        checkpoint = {
            'checkpointTime': df['Timestamp'][0],
            'checkpointCode': df['Code'][0],
            'fulfilledCount': 0,
            'interruptedCount': 0,
            'missingFulfilled': 0,
            'missingInterrupted': 0
        }
        for idx, value in df['Code'].items():
            # 이전 요청과 현재 요청 사이에 발생한 Log들 중, 이전 요청의 결과와 다른 Log의 개수를 카운팅
            if df['Timestamp'][idx] < checkpoint['checkpointTime']:
                if df['Code'][idx] != 'requesting...':
                    if checkpoint['checkpointCode'] == 'fulfilled' and df['Code'][idx] == 'capacity-not-available':
                        checkpoint['missingInterrupted'] += 1
                    elif checkpoint['checkpointCode'] == 'capacity-not-available' and df['Code'][idx] == 'fulfilled':
                        checkpoint['missingFulfilled'] += 1
            # fulfilled or interrupted 응답 시 설정된 주기가 지난 후 재요청
            elif df['Code'][idx] == 'fulfilled':
                checkpoint['fulfilledCount'] += 1
                checkpoint['checkpointCode'] = 'fulfilled'
                checkpoint['checkpointTime'] = df['Timestamp'][idx] + timedelta(minutes=p)
            elif df['Code'][idx] == 'capacity-not-available':
                checkpoint['interruptedCount'] += 1
                checkpoint['checkpointCode'] = 'capacity-not-available'
                checkpoint['checkpointTime'] = df['Timestamp'][idx] + timedelta(minutes=p)
                
        simulation['InstanceType'].append(instance_info[0])
        simulation['Region'].append(instance_info[1])
        simulation['AZ'].append(instance_info[2])
        simulation['Period'].append(p)
        simulation['Cost'].append(checkpoint['fulfilledCount'] / 60 * spotPrice)
        simulation['InterruptedCount'].append(checkpoint['interruptedCount'])
        simulation['FulfilledCount'].append(checkpoint['fulfilledCount'])
        simulation['MissingInterruptedCount'].append(checkpoint['missingInterrupted'])
        simulation['MissingFulfilledCount'].append(checkpoint['missingFulfilled'])
        simulation['MissingRate'].append((checkpoint['missingFulfilled']+checkpoint['missingInterrupted'])/len(df))
        simulation['MissingFulfilledRate'].append(checkpoint['missingFulfilled']/len(df))
        simulation['MissingInterruptedRate'].append(checkpoint['missingInterrupted']/len(df))

simulation_df = pd.DataFrame(simulation)
simulation_df.to_csv(f"simulation_df_{p_order}.csv", index=False)

simulation_df