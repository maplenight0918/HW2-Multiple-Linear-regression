"""完整實驗入口；測試集只能在 selection_lock 寫出之後使用。"""
import os
for variable in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[variable]='1'
import sys
import json
import platform
import importlib.metadata as metadata
import time
import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson,jarque_bera
from sklearn.base import clone
from .common import ROOT,CONFIG,TABLES,save_json
from .data_preparation import load_and_audit,split_indices
from .modeling import compare_cv,selected_features
from .evaluation import metrics,conformal_quantile,interval_metrics
from .visualization import eda,evaluation_figures

def run():
    # 公開 repository 不保存原始資料或模型目錄；首次執行須自行建立。
    for relative in ['data/processed','outputs/models','outputs/figures','outputs/tables','outputs/logs']:
        (ROOT/relative).mkdir(parents=True,exist_ok=True)
    started=time.time()
    df,official,features,audit=load_and_audit()
    train,calibration,test,cv_indices=split_indices(df)
    X,y=df[features],df[CONFIG['target']]
    Xcv,ycv=X.iloc[cv_indices],y.iloc[cv_indices]
    print('資料稽核完成：',df.shape,'CV 子樣本：',len(Xcv),flush=True)
    eda(Xcv,ycv)
    choices,cv_results,lock=compare_cv(Xcv,ycv)
    rows,models=[],{}
    for name in lock['diagnostic_models']:
        pipeline=clone(choices[name]).fit(X.iloc[train],y.iloc[train])
        models[name]=pipeline
        names=selected_features(pipeline,features)
        # 正則化模型和非線性模型不把名目特徵數誤當成有效自由度。
        p=len(names) if name.startswith('LR_') else None
        pred=pipeline.predict(X.iloc[test])
        row=dict(model=name,selection=('All' if name=='LR_All' else name),features=len(names),
                 selected_features=';'.join(names),train_n=len(train),test_n=len(test),
                 cv_rmse=float(cv_results.set_index('model').loc[name,'cv_rmse']),**metrics(y.iloc[test],pred,p))
        rows.append(row)
        print('測試診斷：',name,row['rmse'],flush=True)
    comparison=pd.DataFrame(rows)
    comparison.to_csv(TABLES/'model_comparison.csv',index=False)
    feature_results=cv_results.merge(comparison[['model','selected_features','features','rmse','r2']],on='model',how='left')
    feature_results.to_csv(TABLES/'feature_selection_results.csv',index=False)
    from .finalize_feature_selection import complete_selection_table
    complete_selection_table(choices,models,X.iloc[train],y.iloc[train],cv_results,comparison)
    primary=models[lock['primary']]
    selected=selected_features(primary,features)
    pred=primary.predict(X.iloc[test])
    q,k=conformal_quantile(y.iloc[calibration],primary.predict(X.iloc[calibration]),CONFIG['nominal_coverage'])
    intervals=dict(method='Split conformal, absolute residual, finite-sample quantile',nominal_coverage=.95,
        q=q,quantile_rank=k,calibration_n=len(calibration),test_n=len(test),**interval_metrics(y.iloc[test],pred,q))
    save_json(TABLES/'prediction_interval.json',intervals)
    predictions=pd.DataFrame({'id':df.id.iloc[test].to_numpy(),'actual':y.iloc[test].to_numpy(),
        'prediction':pred,'lower_95':pred-q,'upper_95':pred+q})
    predictions.to_csv(TABLES/'test_predictions.csv',index=False)
    predictions.assign(absolute_error=np.abs(predictions.actual-predictions.prediction)).nlargest(15,'absolute_error').to_csv(TABLES/'failure_cases.csv',index=False)
    bins=pd.qcut(predictions.prediction,10,duplicates='drop')
    diagnostic=[]
    for label,sub in predictions.groupby(bins,observed=True):
        diagnostic.append(dict(prediction_bin=str(label),n=len(sub),**metrics(sub.actual,sub.prediction),
                               **interval_metrics(sub.actual,sub.prediction,q)))
    pd.DataFrame(diagnostic).to_csv(TABLES/'conditional_diagnostics.csv',index=False)
    bundle=dict(pipeline=primary,features=features,selected_features=selected,conformal_q=q,
                train_min=X.iloc[train].min(),train_max=X.iloc[train].max(),config=CONFIG)
    joblib.dump(bundle,ROOT/'outputs/models/primary_bundle.joblib')
    scaler=primary.named_steps['scaler']
    coefs=primary.named_steps['model'].coef_
    if primary.steps[0][0]=='selector':
        scales,means=scaler.scale_,scaler.mean_
    else:
        mask=[f in selected for f in features]
        scales,means=scaler.scale_[mask],scaler.mean_[mask]
    raw=coefs/scales
    intercept=float(primary.named_steps['model'].intercept_-np.dot(raw,means))
    coef=pd.DataFrame({'feature':selected,'standardized_coefficient':coefs,'raw_coefficient':raw})
    coef.to_csv(TABLES/'coefficients.csv',index=False)
    save_json(TABLES/'linear_equation.json',dict(intercept=intercept,standardized_intercept=float(primary.named_steps['model'].intercept_),features=selected))
    # 診斷在訓練子樣本進行，HC3 區間為條件於已選模型的探索性推論。
    design=sm.add_constant(Xcv[selected].astype(float))
    ols=sm.OLS(ycv,design).fit()
    robust=ols.get_robustcov_results(cov_type='HC3')
    ci=robust.conf_int()
    pd.DataFrame({'term':design.columns,'coefficient':robust.params,'hc3_se':robust.bse,
                  'lower_95':ci[:,0],'upper_95':ci[:,1],'p_value':robust.pvalues}).to_csv(TABLES/'ols_hc3_inference.csv',index=False)
    bp=het_breuschpagan(ols.resid,design)
    jb=jarque_bera(ols.resid)
    corr=Xcv.corr().to_numpy()
    vif=np.diag(np.linalg.inv(corr))
    pd.DataFrame({'feature':features,'VIF':vif}).to_csv(TABLES/'vif.csv',index=False)
    assumptions=dict(diagnostic_n=len(Xcv),breusch_pagan_lm=bp[0],breusch_pagan_p=bp[1],
        breusch_pagan_f_p=bp[3],durbin_watson=durbin_watson(ols.resid),jarque_bera=jb[0],
        jarque_bera_p=jb[1],residual_skew=jb[2],residual_kurtosis=jb[3],max_vif=vif.max(),
        max_absolute_feature_correlation=float(np.abs(corr-np.eye(len(features))).max()),
        rank=int(np.linalg.matrix_rank(design)),condition_number=float(ols.condition_number))
    save_json(TABLES/'assumptions.json',assumptions)
    selector=models['LR_LassoSelect'].named_steps['selector']
    pd.DataFrame({'feature':features,'lasso_cv_coefficient':selector.estimator_.coef_,
                  'retained':selector.get_support()}).to_csv(TABLES/'lasso_selection.csv',index=False)
    save_json(TABLES/'lasso_cv.json',dict(alpha=selector.estimator_.alpha_,retained=int(selector.get_support().sum()),
        alpha_grid=selector.estimator_.alphas_,inner_folds=3,scale='原始評分尺度；selector 先於 imputer 與 scaler'))
    evaluation_figures(y.iloc[test],pred,coef,cv_results,comparison,q,ols.resid)
    # Kaggle 提交專用模型可用全部有標籤資料重訓；不再宣稱獨立測試分數或套用舊區間。
    submission_model=clone(choices[lock['primary']]).fit(X,y)
    submission=pd.DataFrame({'id':official.id,'FloodProbability':submission_model.predict(official[features])})
    sample=pd.read_csv(ROOT/'data/raw/playground-series-s4e5/sample_submission.csv')
    assert list(submission.columns)==list(sample.columns) and np.array_equal(submission.id,sample.id)
    assert np.isfinite(submission.FloodProbability).all()
    submission.to_csv(ROOT/'outputs/submission.csv',index=False)
    joblib.dump(submission_model,ROOT/'outputs/models/submission_pipeline.joblib')
    official.head(5).to_csv(ROOT/'data/processed/new_samples.csv',index=False)
    from .prediction import predict_new_data
    predict_new_data(official.head(5)).to_csv(TABLES/'deployment_example.csv',index=False)
    versions={p:metadata.version(p) for p in ['numpy','pandas','scikit-learn','scipy','statsmodels','matplotlib','joblib','PyMuPDF','nbformat','nbclient','pytest','requests']}
    save_json(TABLES/'environment.json',dict(python=sys.version,platform=platform.platform(),packages=versions,config=CONFIG,seconds=time.time()-started,
        model_parameters={k:repr(v) for k,v in models.items()},submission_out_of_bounds=int((~submission.FloodProbability.between(0,1)).sum())))
    print('完整實驗完成，耗時秒數：',round(time.time()-started,1),flush=True)
    return comparison

if __name__=='__main__':
    run()
