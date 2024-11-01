import warnings
warnings.filterwarnings('ignore')

# 기본 라이브러리 및 설정
import pandas as pd
import numpy as np
import ast
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Input, Dropout
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2

df = pd.read_csv('dataset/processed_dataset.csv')

# 텍스트 데이터를 리스트로 변환
def safe_literal_eval(val):
    try:
        if pd.isnull(val) or val in ['Null', 'None', 'null', 'NaN']:  # 다양한 Null 형태를 체크
            return []  # Null일 경우 빈 리스트로 처리
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []

df['classified_class_encoded'] = df['classified_class_encoded'].apply(lambda x: safe_literal_eval(x) if isinstance(x, str) else x)
df['descendant_classes_encoded'] = df['descendant_classes_encoded'].apply(lambda x: safe_literal_eval(x) if isinstance(x, str) else x)

# PCA를 사용하여 descendant_classes_encoded의 차원 축소
def pca(data, n_components=4):
    vectors = np.stack(data['descendant_classes_encoded'].values)
    pca = PCA(n_components=n_components)
    reduced_vectors = pca.fit_transform(vectors)
    return reduced_vectors

# descendant_classes_encoded 피처를 제거하고 차원 축소된 벡터를 결합
def combined_data(data, reduced_vectors):
    features = data.drop(columns=['descendant_classes_encoded', 'classified_class_encoded']).values
    classified_vectors = np.stack(data['classified_class_encoded'].values)
    combined_data = np.concatenate([features, reduced_vectors, classified_vectors], axis=1)
    return combined_data

# 긍정 데이터와 부정 데이터 분리
positive_data = df[df['dataset_type'] == 1]
negative_data = df[df['dataset_type'] == 0]

# 긍정 데이터에서 8:1:1 비율로 나누기
train_data, temp_data = train_test_split(positive_data, test_size=0.2, random_state=42)
val_data, positive_test_data = train_test_split(temp_data, test_size=0.5, random_state=42)

test_data = pd.concat([positive_test_data, negative_data])

# 'dataset_type' 열 삭제
train_data = train_data.drop(columns=['dataset_type'])
val_data = val_data.drop(columns=['dataset_type'])
test_data = test_data.drop(columns=['dataset_type'])

# 데이터 섞기
train_data = shuffle(train_data, random_state=42)
val_data = shuffle(val_data, random_state=42)
test_data = shuffle(test_data, random_state=42)

# 차원 축소를 수행하여 임베딩된 벡터로 변환
train_reduced = pca(train_data)
val_reduced = pca(val_data)
test_reduced = pca(test_data)

# 데이터를 모델의 입력 형식으로 준비
train_combined = combined_data(train_data, train_reduced)
val_combined = combined_data(val_data, val_reduced)
test_combined = combined_data(test_data, test_reduced)

# 데이터 저장
positive_test_data.to_csv('dataset/positive_test_data.csv', index=False)
negative_data.to_csv('dataset/negative_test_data.csv', index=False)

# 결과 출력
print(f"학습 데이터 수: {len(train_combined)}")
print(f"검증 데이터 수: {len(val_combined)}")
print(f"테스트 데이터 수 (긍정): {len(positive_test_data)}")
print(f"테스트 데이터 수 (부정): {len(negative_data)}")

# Autoencoder 모델 정의
CODE_DIM = 4
INPUT_SHAPE = train_combined.shape[1]  

input_layer = Input(shape=(INPUT_SHAPE,))
x = Dense(32, activation='relu', kernel_regularizer=l2(0.001))(input_layer)
x = Dropout(0.3)(x)
x = Dense(16, activation='relu')(x)
x = Dense(8, activation='relu')(x)
code = Dense(CODE_DIM, activation='relu')(x)  
x = Dense(8, activation='relu')(code)
x = Dense(16, activation='relu')(x)
x = Dense(32, activation='relu')(x)
output_layer = Dense(INPUT_SHAPE, activation='relu')(x) 

# 모델 정의 (Autoencoder)
autoencoder = Model(input_layer, output_layer, name='autoencoder')

# 콜백 정의 (체크포인트와 조기 종료)
model_name = "dataset/unsupervised_autoencoder.keras"
checkpoint = ModelCheckpoint(model_name,
                             monitor="val_loss",
                             mode="min",
                             save_best_only=True,
                             save_weights_only=False,
                             verbose=1)
earlystopping = EarlyStopping(monitor='val_loss',
                              min_delta=0.001, 
                              patience=5, 
                              verbose=1,
                              restore_best_weights=True)

callbacks = [checkpoint, earlystopping]

# 모델 컴파일
autoencoder.compile(optimizer=Adam(learning_rate=0.0003), loss='mse')

# 모델 학습
history = autoencoder.fit(train_combined, train_combined,
                          epochs=100, batch_size=64,
                          validation_data=(val_combined, val_combined),
                          callbacks=callbacks, shuffle=True)

