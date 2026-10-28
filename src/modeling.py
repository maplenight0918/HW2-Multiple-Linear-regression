"""在訓練資料內比較模型，鎖定選擇後才允許測試集評估。"""
import time
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_validate
from .feature_selection import LassoCVSelector, AddRowSummary
from .common import CONFIG, TABLES, save_json

def candidates():
    def pipe(selector='passthrough', model=None):
        return Pipeline([('imputer',SimpleImputer(strategy='median')),('scaler',StandardScaler()),
                         ('selector',selector),('model',LinearRegression() if model is None else model)])
    choices = {'LR_All':pipe()}
    for k in [5,10,15]:
        choices[f'LR_KBest_{k}'] = pipe(SelectKBest(f_regression,k=k))
        choices[f'LR_RFE_{k}'] = pipe(RFE(LinearRegression(),n_features_to_select=k,step=5))
    choices['LR_LassoSelect'] = Pipeline([('selector',LassoCVSelector()),('imputer',SimpleImputer(strategy='median')),
        ('scaler',StandardScaler()),('model',LinearRegression())])
    for alpha in [0.1,10,1000]:
        choices[f'Ridge_{alpha:g}'] = pipe(model=Ridge(alpha=alpha))
    for alpha in [1e-5,1e-4,1e-3]:
        choices[f'Lasso_{alpha:g}'] = pipe(model=Lasso(alpha=alpha,max_iter=10000))
    choices['HGB_Summary'] = Pipeline([('imputer',SimpleImputer(strategy='median')),('summary',AddRowSummary()),
        ('model',HistGradientBoostingRegressor(max_iter=140,max_leaf_nodes=15,learning_rate=0.08,l2_regularization=10,
                 early_stopping=False,random_state=42))])
    return choices

def selected_features(model, features):
    selector = model.named_steps.get('selector','passthrough')
    if isinstance(selector,str):
        return list(features)
    return list(np.asarray(features)[selector.get_support()])

def compare_cv(X,y):
    splitter = KFold(CONFIG['cv_folds'],shuffle=True,random_state=CONFIG['seed'])
    choices, rows, fold_rows = candidates(), [], []
    for name,pipeline in choices.items():
        start = time.time()
        result = cross_validate(pipeline,X,y,cv=splitter,scoring='neg_root_mean_squared_error',return_estimator=True,n_jobs=1)
        scores = -result['test_score']
        selected = [selected_features(est,list(X.columns)) for est in result['estimator']]
        for i,(score,feat) in enumerate(zip(scores,selected)):
            fold_rows.append(dict(model=name,fold=i+1,rmse=score,features=';'.join(feat),count=len(feat)))
        rows.append(dict(model=name,cv_rmse=scores.mean(),cv_sd=scores.std(ddof=1),cv_n=len(X),
                         mean_selected_features=np.mean([len(s) for s in selected]),seconds=time.time()-start))
        print(name, f'CV RMSE={scores.mean():.6f}',flush=True)
    results = pd.DataFrame(rows)
    results.to_csv(TABLES/'cv_results.csv',index=False)
    pd.DataFrame(fold_rows).to_csv(TABLES/'cv_folds.csv',index=False)
    winner = lambda prefix: results[results.model.str.startswith(prefix)].sort_values('cv_rmse').iloc[0].model
    primary = winner('LR_')
    frozen = list(dict.fromkeys(['LR_All',winner('LR_KBest'),winner('LR_RFE'),'LR_LassoSelect',winner('Ridge'),winner('Lasso_'),'HGB_Summary']))
    lock = dict(primary=primary,overall_cv_winner=results.sort_values('cv_rmse').iloc[0].model,
                diagnostic_models=frozen,selection_rule='僅依訓練子樣本五折 CV RMSE；主要模型限制為 LinearRegression。',
                locked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),test_accessed=False,
                parameters={name:repr(choices[name]) for name in frozen})
    save_json(TABLES/'selection_lock.json',lock)
    return choices,results,lock
