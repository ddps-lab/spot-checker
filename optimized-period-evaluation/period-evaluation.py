import pickle
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

simulation_data = pd.read_csv("simulation_data.csv")
simulation_data = simulation_data.dropna()
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
print("Data Count:", simulation_data.groupby('Period').count()['Cost'][1])
print(entire_data[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']].reset_index(drop=True))

# SPS로 클러스터링

for value in sorted(simulation_data['SPS'].unique()):
    sps = simulation_data[(simulation_data['SPS'] == value)].reset_index(drop=True)
    sps = sps.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
    sps['MissingRate'] = (sps['MissingInterruptedCount'] + sps['MissingFulfilledCount']) / sps['LogCount']

    mm_cost = MinMaxScaler()
    mm_mr = MinMaxScaler()

    norm_cost = mm_cost.fit_transform(sps['Cost'].values.reshape(-1, 1))
    norm_mr = mm_mr.fit_transform(sps['MissingRate'].values.reshape(-1, 1))

    plt.title(f"Optimal Period for SPS {value} Data")
    plt.plot(sps['Period'], norm_cost + norm_mr)
    plt.xlabel("Period")
    plt.ylabel("Objective Function Value")
    plt.savefig(f"fig/sps{value}_data.png")
    plt.close()

    print(f"SPS{value} Data)")
    print(sps[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']].reset_index(drop=True))

# IF로 클러스터링

for value in sorted(simulation_data['IF'].unique()):
    IF = simulation_data[(simulation_data['IF'] == value)].reset_index(drop=True)
    IF = IF.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
    IF['MissingRate'] = (IF['MissingInterruptedCount'] + IF['MissingFulfilledCount']) / IF['LogCount']

    mm_cost = MinMaxScaler()
    mm_mr = MinMaxScaler()

    norm_cost = mm_cost.fit_transform(IF['Cost'].values.reshape(-1, 1))
    norm_mr = mm_mr.fit_transform(IF['MissingRate'].values.reshape(-1, 1))

    plt.title(f"Optimal Period for IF {value} Data")
    plt.plot(IF['Period'], norm_cost + norm_mr)
    plt.xlabel("Period")
    plt.ylabel("Objective Function Value")
    plt.savefig(f"fig/if{value}_data.png")
    plt.close()

    print(f"IF{value} Data)")
    print(IF[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']].reset_index(drop=True))

# SPS_STD로 클러스터링

for value in sorted(simulation_data['label_STD'].unique()):
    std = simulation_data[(simulation_data['label_STD'] == value)].reset_index(drop=True)
    std = std.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
    std['MissingRate'] = (std['MissingInterruptedCount'] + std['MissingFulfilledCount']) / std['LogCount']

    mm_cost = MinMaxScaler()
    mm_mr = MinMaxScaler()

    norm_cost = mm_cost.fit_transform(std['Cost'].values.reshape(-1, 1))
    norm_mr = mm_mr.fit_transform(std['MissingRate'].values.reshape(-1, 1))

    plt.title(f"Optimal Period for std {value} Data")
    plt.plot(std['Period'], norm_cost + norm_mr)
    plt.xlabel("Period")
    plt.ylabel("Objective Function Value")
    plt.savefig(f"fig/std{value}_data.png")
    plt.close()

    print(f"STD{value} Data)")
    print(std[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']].reset_index(drop=True))

# SPS와 IF로 클러스터링

for sps_value in sorted(simulation_data['SPS'].unique()):
    for if_value in sorted(simulation_data['IF'].unique()):
        spsif = simulation_data[((simulation_data['SPS'] == sps_value) & (simulation_data['IF'] == if_value))].reset_index(drop=True)
        spsif = spsif.groupby('Period').sum().reset_index()[['Period', 'Cost', 'MissingInterruptedCount', 'MissingFulfilledCount', 'LogCount']]
        spsif['MissingRate'] = (spsif['MissingInterruptedCount'] + spsif['MissingFulfilledCount']) / spsif['LogCount']

        mm_cost = MinMaxScaler()
        mm_mr = MinMaxScaler()

        norm_cost = mm_cost.fit_transform(spsif['Cost'].values.reshape(-1, 1))
        norm_mr = mm_mr.fit_transform(spsif['MissingRate'].values.reshape(-1, 1))

        plt.title(f"Optimal Period for SPS {sps_value} and IF {if_value} Data")
        plt.plot(spsif['Period'], norm_cost + norm_mr)
        plt.xlabel("Period")
        plt.ylabel("Objective Function Value")
        plt.savefig(f"fig/sps{sps_value}_if{if_value}_data.png")
        plt.close()

        print(f"SPS{sps_value} and IF{if_value} Data)")
        print(spsif[(norm_cost + norm_mr == min(norm_cost + norm_mr))][['Period', 'Cost', 'MissingRate']].reset_index(drop=True))
