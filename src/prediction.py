"""載入可重現 Pipeline，驗證新輸入並回傳點預測與個別預測區間。"""
import warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .common import ROOT

def predict_new_data(input_data, model_path=None):
    path=Path(model_path) if model_path else ROOT/'outputs/models/primary_bundle.joblib'
    if not path.is_file():
        raise FileNotFoundError('找不到模型，請先執行 python -m src.run_experiment')
    bundle=joblib.load(path)
    if isinstance(input_data,(str,Path)):
        df=pd.read_csv(input_data)
    elif isinstance(input_data,dict):
        df=pd.DataFrame([input_data])
    else:
        df=pd.DataFrame(input_data).copy()
    required=bundle['features']
    missing=set(required)-set(df.columns)
    if missing:
        raise ValueError('缺少必要欄位：'+', '.join(sorted(missing)))
    if len(df)==0 or df.columns.duplicated().any():
        raise ValueError('輸入不可空白或有重複欄名')
    if not all(pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) for c in required):
        raise ValueError('所有輸入特徵必須為數值型別，不接受文字或布林值')
    X=df[required]
    if np.isinf(X.to_numpy(dtype=float)).any():
        raise ValueError('輸入不可包含無限值')
    if X.isna().any().any():
        warnings.warn('缺失值將以訓練中位數補值；資料分布改變可能影響區間涵蓋率')
    if ((X<bundle['train_min'])|(X>bundle['train_max'])).any().any():
        warnings.warn('輸入超過訓練範圍，可能發生外推；區間保證依賴交換性')
    pred=bundle['pipeline'].predict(X)
    if not np.isfinite(pred).all():
        raise ValueError('模型輸出非有限值')
    q=bundle['conformal_q']
    return pd.DataFrame({'prediction':pred,'lower_95':pred-q,'upper_95':pred+q},index=df.index)
