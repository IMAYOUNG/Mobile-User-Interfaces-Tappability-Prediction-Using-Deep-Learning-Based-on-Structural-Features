# 기본 라이브러리
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import ast
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.utils import shuffle

# 데이터 불러오기 및 결합
df = pd.read_csv('dataset/positive_original_data.csv')
ndf = pd.read_csv('dataset/negative_original_data.csv')

df['dataset_type'] = 1
ndf['dataset_type'] = 0
df = pd.concat([df, ndf], ignore_index=True)

df = df[["dataset_type", "bounds", "classified_class", 
         "siblings_cnt", "Hierarchy_Depth", "Nesting_Level", 
         "top_spacing", "bottom_spacing", "left_spacing", "right_spacing", 
         "total_components", "descendant_count", 'descendant_classes']]

# 문자열을 리스트로 안전하게 변환
def safe_literal_eval(val):
    if pd.isnull(val) or val in ['Null', 'None', 'null', 'NaN']:
        return []
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []

df['descendant_classes'] = df['descendant_classes'].apply(lambda x: safe_literal_eval(x) if isinstance(x, str) else x)
# 데이터프레임의 모든 고유 클래스 유형 리스트를 생성
unique_descendant_classes = set([cls for sublist in df['descendant_classes'] for cls in sublist])

# 각 행의 형제 요소의 반복성을 반영하여 빈도수를 계산하는 함수
def encode_descendant_classes(descendant_list):
    counts = {cls: 0 for cls in unique_descendant_classes}  # 모든 고유 클래스 유형에 대해 초기화
    if descendant_list:  # 형제가 존재하는 경우에만 계산
        for descendant_class in descendant_list:
            if descendant_class in counts:
                counts[descendant_class] += 1
    return [counts[cls] for cls in unique_descendant_classes]  # 고유 클래스 순서대로 빈도를 반환

# 형제 요소의 빈도를 반영한 결과를 새로운 열에 추가
df['descendant_classes_encoded'] = df['descendant_classes'].apply(encode_descendant_classes)

# 빈도수를 스케일링하는 함수
def scale_encoded_classes(encoded_list, total_count):
    return [count / total_count if total_count > 0 else 0 for count in encoded_list]

df['descendant_classes_encoded'] = df.apply(
    lambda row: scale_encoded_classes(row['descendant_classes_encoded'], row['descendant_count']), axis=1
)

# 'classified_class'가 'Other'이고 'data_type'이 0인 행 제거
df = df[~((df['classified_class'] == 'Other') & (df['dataset_type'] == 1))]

# classified_class 원핫 인코딩 함수
def encode_class(classified_class):
    # 기본적으로 모든 값을 0으로 설정하고, 해당 클래스에 1을 설정
    encoded = [0, 0, 0]  # 순서대로 'Image', 'TextButton', 'other'
    if classified_class == 'Image':
        encoded[0] = 1
    elif classified_class == 'TextButton':
        encoded[1] = 1
    elif classified_class == 'Other':
        encoded[2] = 1
    return encoded
    
# df에 적용
df['classified_class_encoded'] = df['classified_class'].apply(encode_class)
df['classified_class_encoded'] = df['classified_class_encoded'].apply(lambda x: safe_literal_eval(x) if isinstance(x, str) else x)

# 기존 데이터프레임(df)과 분리된 피처들을 결합
df = pd.concat([df.reset_index(drop=True)], axis=1)

# bounds가 문자열로 저장된 경우 리스트로 변환
df['bounds'] = df['bounds'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

# bounds 데이터를 'left', 'top', 'right', 'bottom'으로 분리
df[['bounds_left', 'bounds_top', 'bounds_right', 'bounds_bottom']] = pd.DataFrame(df['bounds'].tolist(), index=df.index)

df['Width'] = (df['bounds_right'] - df['bounds_left'])  # Width : right - left
df['Height'] = (df['bounds_bottom'] - df['bounds_top'])  # Height : bottom - top

df['center_X'] = ((df['Width'] / 2) + df['bounds_left']) / 1440
df['center_Y'] = ((df['Height'] / 2) + df['bounds_top']) / 2560

df['Width'] = df['Width'] / 1440
df['Height'] = df['Height'] / 2560

df["Spacing"] = (df["bottom_spacing"] - df["top_spacing"]) * (df["right_spacing"] - df["left_spacing"]) / (1440 * 2560)
df['Size'] = (df['Width'] * df['Height']) / (1440 * 2560)

df.drop(columns=['classified_class', 'descendant_classes'], inplace=True)
df.drop(columns=['left_spacing', 'top_spacing', 'right_spacing', 'bottom_spacing'], inplace=True)
df.drop(columns=['bounds', 'bounds_left', 'bounds_top', 'bounds_right', 'bounds_bottom'], inplace=True)
df.drop(columns=['Width', 'Height'], inplace=True)
df.drop(columns=['total_components'], inplace=True)

# MinMaxScaler를 적용할 피처만 따로 선택
minmax_feats = ['siblings_cnt', 'Hierarchy_Depth', 'Nesting_Level', 'descendant_count']

# MinMaxScaler 적용
scaler = MinMaxScaler()
df[minmax_feats] = scaler.fit_transform(df[minmax_feats])

# 로그 변환 전에 값에 1을 더해 음수값 방지
df['Size'] = np.log(df['Size'] + 1)

file_path = 'dataset/processed_dataset.csv'
df.to_csv(file_path, index=False)
print("Dataset successfully saved to:", file_path)
