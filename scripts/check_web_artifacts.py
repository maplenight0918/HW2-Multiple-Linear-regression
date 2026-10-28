"""不需訓練套件的公開網站資料一致性檢查，供 GitHub Actions 執行。"""
import csv
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def check():
    for name in ['flood','housing']:
        d=json.loads((ROOT/'web/data'/f'{name}.json').read_text())
        assert 14<=d['raw_features']<=20
        assert d['target'] not in d['features'] and 'id' not in d['features']
        assert sum(d['split'][k] for k in ['train','calibration','test'])==d['analysis_samples']
        assert d['provenance']['test_used_for_selection'] is False
        primary=next(r for r in d['models'] if r['model']==d['primary'])
        assert primary['model'].startswith('LR_')
        assert all(math.isfinite(r[k]) for r in d['models'] for k in ['mae','mse','rmse','r2','cv_rmse'])
        assert all(r['lower']<=r['prediction']<=r['upper'] for r in d['predictions'])
        assert abs(d['interval']['average_width']-2*d['interval']['q'])<1e-8
        assert len(d['predictor']['terms'])==primary['features']
        assert len(d['coefficients'])==primary['features']
        assert d['interval']['calibration_n']==d['split']['calibration']
    flood=json.loads((ROOT/'web/data/flood.json').read_text())
    rows=list(csv.DictReader((ROOT/'outputs/tables/model_comparison.csv').open()))
    assert len(rows)==len(flood['models'])
    for row,saved in zip(rows,flood['models']):
        assert row['model']==saved['model']
        for metric in ['mae','mse','rmse','r2','cv_rmse']:assert abs(float(row[metric])-saved[metric])<1e-12
    research=json.loads((ROOT/'web/data/research.json').read_text())
    assert len(research['summary'])>100
    for path in ['downloads/report_analysis.pdf',f"downloads/{research['student_id']}_hw2.ipynb",'downloads/sources.md','downloads/model_comparison.csv','vendor/chart.umd.min.js']:
        assert (ROOT/'web'/path).stat().st_size>100
    for path in (ROOT/'web').rglob('*'):
        assert not any(term in path.name.lower() for term in ['raw_session','conversation','visible_messages'])
    print('PASS：兩題結構、Flood 數值一致、預測區間、研究摘要與公開檔案界線。')

if __name__=='__main__':check()
