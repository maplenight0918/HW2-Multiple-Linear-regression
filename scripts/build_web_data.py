"""匯出真實 Flood 成果，並從固定 Kaggle 版本執行第二個題目的分析。"""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='1'
import sys
import json
import hashlib
import io
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from webapp.analysis import analyze,clean
OUT=ROOT/'web/data'; OUT.mkdir(exist_ok=True,parents=True)
T=ROOT/'outputs/tables'

def write(name,value):
    (OUT/name).write_text(json.dumps(clean(value),ensure_ascii=False,allow_nan=False,separators=(',',':')))

def flood():
    read=lambda name:json.loads((T/name).read_text())
    audit=read('dataset_audit.json'); bundle=joblib.load(ROOT/'outputs/models/primary_bundle.joblib')
    pipeline=bundle['pipeline']; fs=pd.read_csv(T/'feature_selection_results.csv'); comp=pd.read_csv(T/'model_comparison.csv')
    models=comp.to_dict('records')
    for row in models: row['selected_features']=row['selected_features'].split(';')
    selection=fs.to_dict('records')
    for row in selection:
        row['selected_features']=row['selected_features'].split(';');row['features']=row['number_selected']
    preds=pd.read_csv(T/'test_predictions.csv').sample(400,random_state=42).rename(columns={'lower_95':'lower','upper_95':'upper'})
    coef=pd.read_csv(T/'coefficients.csv')
    terms=[]; fields=[]
    scaler=pipeline['scaler']; imputer=pipeline['imputer']
    for i,name in enumerate(bundle['features']):
        terms.append(dict(name=name,raw=name,kind='numeric',mean=scaler.mean_[i],scale=scaler.scale_[i],fill=imputer.statistics_[i],coefficient=pipeline['model'].coef_[i]))
        fields.append(dict(name=name,kind='numeric',value=imputer.statistics_[i],minimum=bundle['train_min'][name],maximum=bundle['train_max'][name]))
    interval=read('prediction_interval.json'); interval['below_zero']=interval['lower_out_of_bounds'];interval['above_one']=interval['upper_out_of_bounds']
    result=dict(id='flood',title='洪災機率預測',short='Flood Prediction',target='FloodProbability',unit='機率尺度 0–1',
        subtitle='20 個環境評分，能解釋多少預測差異？',source_url='https://www.kaggle.com/competitions/playground-series-s4e5',
        samples=audit['shape'][0],analysis_samples=audit['shape'][0],raw_features=20,features=audit['features'],
        split=read('split_summary.json'),cv_n=80000,primary=read('selection_lock.json')['primary'],models=models,selection=selection,
        interval=interval,predictions=preds.to_dict('records'),
        coefficients=[dict(feature=r.feature,coefficient=r.standardized_coefficient) for r in coef.itertuples()],
        predictor=dict(intercept=float(pipeline['model'].intercept_),fields=fields,terms=terms),
        assumptions=read('assumptions.json'),audit=dict(missing=sum(audit.get('missing',{}).values()),duplicate_rows=audit.get('duplicate_rows',0)),
        notes=['這是 Kaggle 合成 benchmark；不能直接用於現實洪災預警。',
            '20 個原始特徵均保留是特徵選擇實驗的結果：刪除到 15 欄會使預測誤差增加。',
            '在訓練部分固定抽取 80,000 筆做五折 CV，再用 715,492 筆訓練資料擬合。校準與測試獨立保留。',
            '模型比較表為選模鎖定後診斷，未使用測試集調參。主模型仍為 LinearRegression，HGB 僅為進階比較。',
            '95% split conformal 為邊際涵蓋；分組最低涵蓋約 84.59%，不保證每一子群。區間未裁切。',
            '官方 test.csv 無標籤，與本站本地測試集不同；未取得 Kaggle 官方排名。'],
        provenance=dict(dataset_version='johnwicknice/playground-series v1', source_tables=['model_comparison.csv','feature_selection_results.csv','prediction_interval.json'],test_used_for_selection=False))
    write('flood.json',result)
    print('Flood 成果匯出完成',flush=True)

def housing():
    path=ROOT/'data/raw/king-county/kc_house_data.csv'
    url='https://www.kaggle.com/api/v1/datasets/download/harlfoxem/housesalesprediction?datasetVersionNumber=1'
    if not path.exists():
        r=requests.get(url,timeout=90);r.raise_for_status()
        raw=zipfile.ZipFile(io.BytesIO(r.content)).read('kc_house_data.csv')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    original=pd.read_csv(path)
    # 同一房屋可能重複交易；只保留首筆，避免相同住宅跨資料切分。
    d=original.sort_values('date',kind='stable').drop_duplicates('id',keep='first').copy()
    d['date']=(pd.to_datetime(d['date'],format='%Y%m%dT%H%M%S')-pd.Timestamp('1970-01-01')).dt.days
    d['zipcode']=d['zipcode'].astype(str)
    result,model=analyze(d,'price',[c for c in d if c not in ('id','price')],offline=True)
    splits=result.pop('_splits')
    result.update(id='housing',title='King County 房價預測',short='King County Housing',
        subtitle='房屋條件與地點，如何共同影響成交價格？',unit='美元 USD',
        source_url='https://www.kaggle.com/datasets/harlfoxem/housesalesprediction', samples=len(original))
    result['notes'].insert(0,'原始 21,613 筆交易；每個房屋 ID 僅保留最早一筆，共 21,436 間，避免同屋跨集合。19 個原始輸入含日期；日期轉為自 1970-01-01 起天數，郵遞區號採類別編碼。')
    result['notes'].append('sqft_living = sqft_above + sqft_basement 造成完整模型共線性；係數不宜解讀為因果。日期為交易當日資訊，非未來價格預測。')
    result['provenance'].update(dataset_version='harlfoxem/housesalesprediction v1',download=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),license='CC0: Public Domain（Kaggle API）')
    write('housing.json',result)
    folder=ROOT/'outputs/web';folder.mkdir(exist_ok=True)
    (folder/'housing_splits.json').write_text(json.dumps(splits))
    pd.DataFrame(result['models']).to_csv(folder/'housing_models.csv',index=False)
    joblib.dump(model,ROOT/'outputs/models/housing_pipeline.joblib')
    (folder/'housing_audit.json').write_text(json.dumps(dict(original_shape=list(original.shape),analysis_rows=len(d),features=result['features'],missing=int(original.isna().sum().sum()),duplicate_id=int(original.id.duplicated().sum()),provenance=result['provenance']),ensure_ascii=False,indent=2))
    print('房價分析完成',result['primary'],result['interval'],flush=True)

def research():
    summary=(ROOT/'research/notebooklm_summary.md').read_text().split('<!-- SUMMARY_START -->')[1].split('<!-- SUMMARY_END -->')[0].strip()
    write('research.json',dict(student_id=json.loads((ROOT/'config.json').read_text())['student_id'],summary=summary,
        sources=[dict(title='Kaggle Flood Prediction',url='https://www.kaggle.com/competitions/playground-series-s4e5'),
                 dict(title='Kaggle King County Housing',url='https://www.kaggle.com/datasets/harlfoxem/housesalesprediction'),
                 dict(title='scikit-learn：避免資料洩漏',url='https://scikit-learn.org/stable/common_pitfalls.html'),
                 dict(title='scikit-learn：特徵選擇',url='https://scikit-learn.org/stable/modules/feature_selection.html'),
                 dict(title='Conformal Prediction 入門論文',url='https://arxiv.org/abs/2107.07511')]))

if __name__=='__main__':
    flood();research()
    if '--flood-only' not in sys.argv:housing()
