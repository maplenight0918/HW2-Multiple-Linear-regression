"""驗證網站與原成果一致、輸入處理、資料切分及實際新模型。"""
import io
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import joblib
from fastapi.testclient import TestClient
from webapp.analysis import analyze, split_indices, preprocessing
from webapp.app import app, ingest, public_address
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def startups():
    return pd.read_csv(ROOT/'tests/fixtures/50_Startups.csv')

@pytest.fixture(scope='module')
def analyzed(startups):
    return analyze(startups,'Profit')

def browser_equivalent(predictor, row):
    value=predictor['intercept']
    for term in predictor['terms']:
        raw=row[term['raw']]
        if pd.isna(raw):raw=term['fill']
        transformed=(raw-term['mean'])/term['scale'] if term['kind']=='numeric' else float(raw==term['category'])
        value+=term['coefficient']*transformed
    return value

def test_flood_web_matches_saved_experiment():
    d=json.loads((ROOT/'web/data/flood.json').read_text())
    comp=pd.read_csv(ROOT/'outputs/tables/model_comparison.csv').set_index('model')
    for row in d['models']:
        for metric in ['mae','mse','rmse','r2','cv_rmse']:
            assert row[metric]==pytest.approx(comp.loc[row['model'],metric],rel=1e-12)
    bundle=joblib.load(ROOT/'outputs/models/primary_bundle.joblib')
    samples=pd.read_csv(ROOT/'data/processed/new_samples.csv')[bundle['features']]
    assert np.allclose([browser_equivalent(d['predictor'],row) for _,row in samples.iterrows()],bundle['pipeline'].predict(samples),atol=1e-12)
    assert d['interval']['q']==bundle['conformal_q']

def test_housing_real_source_and_prediction_parity():
    d=json.loads((ROOT/'web/data/housing.json').read_text())
    audit=json.loads((ROOT/'outputs/web/housing_audit.json').read_text())
    assert audit['original_shape']==[21613,21]
    assert d['raw_features']==19 and 'price' not in d['features'] and 'id' not in d['features']
    raw=pd.read_csv(ROOT/'data/raw/king-county/kc_house_data.csv').sort_values('date',kind='stable').drop_duplicates('id')
    raw['date']=(pd.to_datetime(raw.date,format='%Y%m%dT%H%M%S')-pd.Timestamp('1970-01-01')).dt.days
    raw['zipcode']=raw.zipcode.astype(str)
    X=raw[d['features']].sample(20,random_state=42)
    model=joblib.load(ROOT/'outputs/models/housing_pipeline.joblib')
    assert np.allclose([browser_equivalent(d['predictor'],row) for _,row in X.iterrows()],model.predict(X),rtol=1e-10,atol=1e-5)
    splits=json.loads((ROOT/'outputs/web/housing_splits.json').read_text())
    assert not set(splits['train']) & set(splits['test'])
    ids=raw.id.to_numpy()
    assert not set(ids[splits['train']])&set(ids[splits['test']])

def test_small_data_conformal_and_cv(analyzed,startups):
    d,model=analyzed
    assert d['split']=={'train':21,'calibration':19,'test':10}
    assert all(len(row['folds'])==5 for row in d['models'])
    assert any(row['model'].startswith('LR_KBest') and row['features']<5 for row in d['models'])
    assert any(row['model'].startswith('LR_RFE') for row in d['models'])
    assert d['primary']==min((r for r in d['models'] if r['model'].startswith('LR_')),key=lambda r:r['cv_rmse'])['model']
    ca=d['_splits']['calibration'];test=d['_splits']['test']
    y=startups.Profit
    errors=np.abs(y.iloc[ca]-model.predict(startups.iloc[ca][d['features']]))
    assert d['interval']['q']==pytest.approx(errors.max())
    pred=model.predict(startups.iloc[test][d['features']]);actual=y.iloc[test].to_numpy()
    assert d['interval']['coverage']==np.mean(np.abs(actual-pred)<=errors.max())
    assert all(v['lower']<=v['prediction']<=v['upper'] for v in d['predictions'])
    assert np.allclose([browser_equivalent(d['predictor'],row) for _,row in startups.iterrows()],model.predict(startups[d['features']]),atol=1e-5)

def test_preprocessing_fitted_only_on_training(analyzed,startups):
    d,model=analyzed
    train=d['_splits']['train'];cal=d['_splits']['calibration'];test=d['_splits']['test']
    assert not set(train)&set(cal) and not set(cal)&set(test) and not set(train)&set(test)
    num=model.regressor_['preprocessor'].named_transformers_['num']
    assert np.allclose(num['imputer'].statistics_,startups.iloc[train].select_dtypes('number').drop(columns='Profit').median())
    assert np.allclose(num['scaler'].mean_,startups.iloc[train].select_dtypes('number').drop(columns='Profit').mean())
    assert int(model.transformer_.n_samples_seen_)==len(train)
    assert [name for name,_ in model.regressor_.steps]==['preprocessor','selector','model']

def test_preprocessor_does_not_learn_validation_values():
    train=pd.DataFrame({'numeric':[1.,3.,np.nan],'category':['a','b','a']})
    prep=preprocessing(train).fit(train)
    before=prep.named_transformers_['num']['imputer'].statistics_.copy()
    with pytest.warns(UserWarning):
        result=prep.transform(pd.DataFrame({'numeric':[1000.],'category':['never-seen']}))
    assert np.array_equal(before,prep.named_transformers_['num']['imputer'].statistics_)
    assert result.shape==(1,2) and result[0,1]==0

@pytest.mark.parametrize('url',['http://127.0.0.1/data','http://localhost/data','http://169.254.169.254/latest','http://[::1]/','file:///etc/passwd','https://user:pass@example.com/a','http://example.com:1234/a'])
def test_private_or_invalid_urls_rejected(url):
    with pytest.raises(ValueError):public_address(url)

def test_csv_validation_and_api():
    client=TestClient(app)
    assert client.get('/api/health').json()['service']=='hw2-regression'
    raw=(ROOT/'tests/fixtures/50_Startups.csv').read_bytes()
    result=client.post('/api/upload',files={'file':('test.csv',raw,'text/csv')})
    assert result.status_code==200 and result.json()['rows']==50
    assert client.post('/api/upload',files={'file':('large.csv',b'x'*5000001)}).status_code==400
    assert client.post('/api/analyze',json={'dataset':'missing','target':'Profit','features':['State']}).status_code==404
    assert client.get('/api/jobs/missing').status_code==404
    for raw in [b'a,a\n1,2\n',b'a,b\n1,2\n',b'\xff\xfe']:
        with pytest.raises(ValueError):ingest(raw,'test')

def test_target_and_id_cannot_enter_features(startups):
    with pytest.raises(ValueError):analyze(startups,'Profit',['Profit','State'])
    data=startups.assign(id=np.arange(len(startups)))
    with pytest.raises(ValueError):analyze(data,'Profit',['id','State'])
    with pytest.raises(ValueError):analyze(startups,'State')

def test_public_site_contains_analysis_no_private_transcripts():
    import fitz
    with fitz.open(ROOT/'web/downloads/report_analysis.pdf') as d:
        assert len(d)>=28
        text=''.join(page.get_text() for page in d)
        assert 'King County' in text and 'GitHub' in text
        assert 'HW2-Multiple-Linear-regression' in text
        assert 'NotebookLM' in text and 'GPT' in text and '0.844878' in text
    for p in (ROOT/'web').rglob('*'):
        assert not any(word in p.name for word in ['raw_session','conversation','visible_messages'])

def test_reproducible_small_data(analyzed,startups):
    second,_=analyze(startups,'Profit')
    first=analyzed[0]
    assert first==second
