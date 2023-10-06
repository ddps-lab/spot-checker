import pandas as pd
import pickle

region = "us-east-1"

az_map_dict = pickle.load(open('./dataset/az_map_dict.pkl', 'rb'))

low_data = pd.read_csv(f'./dataset/{region}/sps_low.csv')
medium_data = pd.read_csv(f'./dataset/{region}/sps_medium.csv')
high_data = pd.read_csv(f'./dataset/{region}/sps_high.csv')

def az_id_to_actual_name(az_id, region):
    az_name = az_map_dict[(region, az_id)]
    return az_name

def extract_and_transform_actual_name(df):
    df['AZ'] = df.apply(lambda row: az_id_to_actual_name(row['AZ'], row['Region']), axis=1)
    return df[['InstanceType','AZ']]

# Extract and transform data from each file using the updated function
transformed_low_actual = extract_and_transform_actual_name(low_data)
transformed_medium_actual = extract_and_transform_actual_name(medium_data)
transformed_high_actual = extract_and_transform_actual_name(high_data)

# Concatenate the transformed dataframes
combined_transformed_actual_data = pd.concat([transformed_high_actual.head(10), transformed_low_actual.head(10), transformed_medium_actual.head(10)], ignore_index=True)
# combined_transformed_actual_data = pd.concat([transformed_high_actual, transformed_low_actual, transformed_medium_actual], ignore_index=True)

combined_transformed_actual_output_path = f"./test_data/{region}.csv"
combined_transformed_actual_data.to_csv(combined_transformed_actual_output_path, index=False)