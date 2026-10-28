"""補齊每個候選方法在完整訓練部分選中的特徵；不接觸測試或校準資料。"""
import numpy as np
from sklearn.base import clone
from .modeling import selected_features
from .common import TABLES

def complete_selection_table(choices, fitted_models, X_train, y_train, cv_results, comparison):
    result=cv_results.merge(comparison[['model','rmse','r2']],on='model',how='left')
    records={}
    for name,prototype in choices.items():
        model=fitted_models.get(name)
        if model is None:
            model=clone(prototype).fit(X_train,y_train)
        names=selected_features(model,list(X_train.columns))
        records[name]={'selected_features':';'.join(names),'number_selected':len(names),
            'model_input_features':len(names)+(2 if name=='HGB_Summary' else 0),
            'method':'SelectKBest' if 'KBest' in name else 'RFE' if 'RFE' in name else 'LassoCV' if 'LassoSelect' in name else 'All',
            'test_role':'鎖定後診斷' if name in fitted_models else '未評估；不可使用測試選模'}
    for field in next(iter(records.values())):
        result[field]=result.model.map(lambda name:records[name][field])
    result.to_csv(TABLES/'feature_selection_results.csv',index=False)
    return result

if __name__=='__main__':
    import pandas as pd
    from .common import ROOT,RAW,CONFIG
    from .modeling import candidates
    df=pd.read_csv(RAW/'train.csv');splits=np.load(ROOT/'data/processed/splits.npz')
    features=[c for c in df if c not in ['id',CONFIG['target']]]
    # 此獨立入口只補齊選用名稱；保留既有鎖定後測試結果，不重新評分。
    results=complete_selection_table(candidates(),{},df.iloc[splits['train']][features],df.iloc[splits['train']][CONFIG['target']],
        pd.read_csv(TABLES/'cv_results.csv'),pd.read_csv(TABLES/'model_comparison.csv'))
    results['test_role']=np.where(results.rmse.notna(),'鎖定後診斷','未評估；不可使用測試選模')
    results.to_csv(TABLES/'feature_selection_results.csv',index=False)
