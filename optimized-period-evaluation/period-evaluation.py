import pickle
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

simulation_data = pd.read_csv("simulation_data.csv")
price_df = pd.read_csv("price_data.csv")

# Objective Function의 최솟값을 최적의 Global P로 계산 (MinMax Scaler 정규화)
mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

entire_data = simulation_data.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
entire_data['MissingRate'] = (entire_data['MissingInterruptedCount'] + entire_data['MissingFulfilledCount']) / entire_data['LogCount']

norm_cost = mm_cost.fit_transform(entire_data['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(entire_data['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for Entire Data")
plt.plot(entire_data['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/entire_data.png")
plt.close()

print("Entire Data)")
print(entire_data[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS가 1인 경우

sps1 = simulation_data[(simulation_data['SPS'] == 1)].reset_index(drop=True)
sps1 = sps1.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
sps1['MissingRate'] = (sps1['MissingInterruptedCount'] + sps1['MissingFulfilledCount']) / sps1['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(sps1['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(sps1['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for SPS 1 Data")
plt.plot(sps1['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/sps1_data.png")
plt.close()

print("SPS1 Data)")
print(sps1[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS가 2인 경우

sps2 = simulation_data[(simulation_data['SPS'] == 2)].reset_index(drop=True)
sps2 = sps2.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
sps2['MissingRate'] = (sps2['MissingInterruptedCount'] + sps2['MissingFulfilledCount']) / sps2['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(sps2['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(sps2['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for SPS 2 Data")
plt.plot(sps2['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/sps2_data.png")
plt.close()

print("SPS2 Data)")
print(sps2[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS가 3인 경우

sps3 = simulation_data[(simulation_data['SPS'] == 3)].reset_index(drop=True)
sps3 = sps3.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
sps3['MissingRate'] = (sps3['MissingInterruptedCount'] + sps3['MissingFulfilledCount']) / sps3['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(sps3['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(sps3['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for SPS 3 Data")
plt.plot(sps3['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/sps3_data.png")
plt.close()

print("SPS3 Data)")
print(sps3[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# IF가 1.0인 경우

IF10 = simulation_data[(simulation_data['IF'] == 1.0)].reset_index(drop=True)
IF10 = IF10.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
IF10['MissingRate'] = (IF10['MissingInterruptedCount'] + IF10['MissingFulfilledCount']) / IF10['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(IF10['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(IF10['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for IF 1.0 Data")
plt.plot(IF10['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/if10_data.png")
plt.close()

print("IF1.0 Data)")
print(IF10[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# IF가 1.5인 경우

IF15 = simulation_data[(simulation_data['IF'] == 1.5)].reset_index(drop=True)
IF15 = IF15.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
IF15['MissingRate'] = (IF15['MissingInterruptedCount'] + IF15['MissingFulfilledCount']) / IF15['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(IF15['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(IF15['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for IF 1.5 Data")
plt.plot(IF15['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/if15_data.png")
plt.close()

print("IF1.5 Data)")
print(IF15[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# IF가 2.0인 경우

IF20 = simulation_data[(simulation_data['IF'] == 2.0)].reset_index(drop=True)
IF20 = IF20.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
IF20['MissingRate'] = (IF20['MissingInterruptedCount'] + IF20['MissingFulfilledCount']) / IF20['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(IF20['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(IF20['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for IF 2.0 Data")
plt.plot(IF20['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/if20_data.png")
plt.close()

print("IF2.0 Data)")
print(IF20[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# IF가 2.5인 경우

IF25 = simulation_data[(simulation_data['IF'] == 2.5)].reset_index(drop=True)
IF25 = IF25.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
IF25['MissingRate'] = (IF25['MissingInterruptedCount'] + IF25['MissingFulfilledCount']) / IF25['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(IF25['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(IF25['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for IF 2.5 Data")
plt.plot(IF25['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/if25_data.png")
plt.close()

print("IF2.5 Data)")
print(IF25[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# IF가 3.0인 경우

IF30 = simulation_data[(simulation_data['IF'] == 3.0)].reset_index(drop=True)
IF30 = IF30.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
IF30['MissingRate'] = (IF30['MissingInterruptedCount'] + IF30['MissingFulfilledCount']) / IF30['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(IF30['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(IF30['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for IF 3.0 Data")
plt.plot(IF30['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/if30_data.png")
plt.close()

print("IF3.0 Data)")
print(IF30[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS_STD가 0인 경우

std0 = simulation_data[(simulation_data['label_STD'] == 0.0)].reset_index(drop=True)
std0 = std0.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
std0['MissingRate'] = (std0['MissingInterruptedCount'] + std0['MissingFulfilledCount']) / std0['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(std0['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(std0['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for STD Label 0 Data")
plt.plot(std0['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/std0_data.png")
plt.close()

print("STD 0 Data)")
print(std0[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS_STD가 1인 경우

std1 = simulation_data[(simulation_data['label_STD'] == 1.0)].reset_index(drop=True)
std1 = std1.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
std1['MissingRate'] = (std1['MissingInterruptedCount'] + std1['MissingFulfilledCount']) / std1['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(std1['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(std1['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for STD Label 0 Data")
plt.plot(std1['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/std1_data.png")
plt.close()

print("STD 1 Data)")
print(std1[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS_STD가 2인 경우

std2 = simulation_data[(simulation_data['label_STD'] == 2.0)].reset_index(drop=True)
std2 = std2.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
std2['MissingRate'] = (std2['MissingInterruptedCount'] + std2['MissingFulfilledCount']) / std2['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(std2['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(std2['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for STD Label 0 Data")
plt.plot(std2['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/std2_data.png")
plt.close()

print("STD 2 Data)")
print(std2[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS_STD가 3인 경우

std3 = simulation_data[(simulation_data['label_STD'] == 3.0)].reset_index(drop=True)
std3 = std3.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
std3['MissingRate'] = (std3['MissingInterruptedCount'] + std3['MissingFulfilledCount']) / std3['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(std3['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(std3['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for STD Label 0 Data")
plt.plot(std3['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/std3_data.png")
plt.close()

print("STD 3 Data)")
print(std3[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])

# SPS_STD가 4인 경우

std4 = simulation_data[(simulation_data['label_STD'] == 4.0)].reset_index(drop=True)
std4 = std4.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
std4['MissingRate'] = (std4['MissingInterruptedCount'] + std4['MissingFulfilledCount']) / std4['LogCount']

mm_cost = MinMaxScaler()
mm_mr = MinMaxScaler()

norm_cost = mm_cost.fit_transform(std4['Cost'].values.reshape(-1, 1))
norm_mr = mm_mr.fit_transform(std4['MissingRate'].values.reshape(-1, 1))

plt.title("Optimal Period for STD Label 0 Data")
plt.plot(std4['Period'], norm_cost + norm_mr)
plt.xlabel("Period")
plt.ylabel("Objective Function Value")
plt.savefig("fig/std4_data.png")
plt.close()

print("STD 4 Data)")
print(std4[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']])
