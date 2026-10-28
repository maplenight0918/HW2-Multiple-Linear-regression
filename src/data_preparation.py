"""下載、資料稽核與互斥資料切分；不在全資料估計前處理參數。"""
import hashlib
import io
import zipfile
import requests
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from .common import ROOT, RAW, CONFIG, TABLES, save_json

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def download_data():
    if all((RAW / x).exists() for x in ['train.csv', 'test.csv', 'sample_submission.csv']):
        return
    response = requests.get(CONFIG['mirror_download'], timeout=180)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            if name.split('/')[-1] in ['train.csv', 'test.csv', 'sample_submission.csv']:
                RAW.mkdir(parents=True, exist_ok=True)
                (RAW / name.split('/')[-1]).write_bytes(archive.read(name))

def validate_frame(df, features=None, labeled=True):
    target, idcol = CONFIG['target'], CONFIG['id_column']
    if labeled and target not in df:
        raise ValueError('缺少 Target 欄位')
    if features is None:
        features = [c for c in df if c not in [target, idcol]]
    if not 14 <= len(features) <= 20 or target in features or idcol in features:
        raise ValueError('原始輸入特徵數或欄位不合規')
    if not all(pd.api.types.is_numeric_dtype(df[c]) for c in features):
        raise ValueError('模型僅接受數值特徵')
    numeric = df[features + ([target] if labeled else [])]
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError('資料包含無限值')
    if labeled and (df[target].isna().any() or not df[target].between(0, 1).all()):
        raise ValueError('目標值缺失或超出 0～1')
    if not df[idcol].is_unique:
        raise ValueError('ID 不唯一')
    return features

def load_and_audit():
    download_data()
    df = pd.read_csv(RAW / 'train.csv')
    official = pd.read_csv(RAW / 'test.csv')
    features = validate_frame(df)
    validate_frame(official, features, labeled=False)
    assert set(df.id).isdisjoint(set(official.id))
    assert list(official.columns) == ['id'] + features
    audit = dict(shape=list(df.shape), official_test_shape=list(official.shape), features=features,
                 feature_count=len(features), target=CONFIG['target'], dtypes=df.dtypes.astype(str).to_dict(),
                 missing=df.isna().sum().to_dict(), official_missing=official.isna().sum().to_dict(),
                 duplicate_rows=int(df.duplicated().sum()),
                 duplicate_without_id=int(df.drop(columns='id').duplicated().sum()),
                 duplicate_features=int(df[features].duplicated().sum()),
                 categorical_features=[], infinite_values=int(np.isinf(df.to_numpy()).sum()),
                 negative_feature_values=int((df[features] < 0).sum().sum()),
                 feature_min=int(df[features].min().min()), feature_max=int(df[features].max().max()),
                 target_min=float(df.FloodProbability.min()), target_max=float(df.FloodProbability.max()),
                 hashes={p.name: sha256(p) for p in RAW.glob('*.csv')}, dataset_version=CONFIG['dataset_version'])
    save_json(TABLES / 'dataset_audit.json', audit)
    df.describe().T.to_csv(TABLES / 'descriptive_statistics.csv')
    return df, official, features, audit

def split_indices(df):
    development, test = train_test_split(np.arange(len(df)), test_size=CONFIG['test_size'], random_state=CONFIG['seed'])
    train, calibration = train_test_split(development, test_size=CONFIG['calibration_fraction_of_development'], random_state=CONFIG['seed'])
    cv = np.random.default_rng(CONFIG['seed']).choice(train, min(CONFIG['cv_sample_size'], len(train)), replace=False)
    np.savez_compressed(ROOT / 'data/processed/splits.npz', train=train, calibration=calibration, test=test, cv=cv)
    save_json(TABLES / 'split_summary.json', {k:len(v) for k,v in dict(train=train,calibration=calibration,test=test,cv=cv).items()})
    return train, calibration, test, cv
