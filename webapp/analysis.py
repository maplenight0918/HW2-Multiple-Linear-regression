"""自訂 CSV／第二題的可重現回歸流程；測試集不參與選模。"""
import math
import platform
import warnings
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_regression, RFE, SelectFromModel
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import KFold, train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import skew
from threadpoolctl import threadpool_limits

SEED = 42

def clean(value):
    """輸出嚴格 JSON，不容許 NaN／Infinity。"""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value

def score(y, prediction, p=None):
    mse = mean_squared_error(y, prediction)
    r2 = r2_score(y, prediction)
    return dict(mae=mean_absolute_error(y, prediction), mse=mse, rmse=np.sqrt(mse), r2=r2,
                adjusted_r2=1-(1-r2)*(len(y)-1)/(len(y)-p-1) if p is not None and len(y)>p+1 else None)

def split_indices(n):
    development, test = train_test_split(np.arange(n), test_size=.2, random_state=SEED)
    train, calibration = train_test_split(development, test_size=max(19, int(round(n*.2))), random_state=SEED)
    return train, calibration, test

def preprocessing(X):
    numeric = list(X.select_dtypes(include='number').columns)
    categorical = [c for c in X if c not in numeric]
    return ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
                          ('scaler', StandardScaler())]), numeric),
        ('cat', Pipeline([('imputer', SimpleImputer(strategy='most_frequent', keep_empty_features=True)),
                          ('encoder', OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False))]), categorical)
    ], verbose_feature_names_out=False)

def pipeline(preprocessor, selector='passthrough', model=None):
    # Target 也於每個訓練 fold 標準化，讓 alpha 不依金額／機率單位改變。
    regressor = Pipeline([('preprocessor', clone(preprocessor)), ('selector', selector),
                          ('model', LinearRegression() if model is None else model)])
    return TransformedTargetRegressor(regressor=regressor, transformer=StandardScaler())

def candidates(X, p):
    prep = preprocessing(X)
    result = {'LR_All': pipeline(prep)}
    for k in sorted(set(([max(1, p//2)] if p<=5 else [])+[5, 10, 15])):
        if k < p:
            result[f'LR_KBest_{k}'] = pipeline(prep, SelectKBest(f_regression, k=k))
            result[f'LR_RFE_{k}'] = pipeline(prep, RFE(LinearRegression(), n_features_to_select=k, step=.25))
    # 此處為固定 alpha 的 Lasso 篩選；不冒稱與主題的 LassoCV 相同。
    result['LR_LassoSelect'] = pipeline(prep, SelectFromModel(Lasso(alpha=.01, max_iter=20000), threshold=1e-8))
    for alpha in [.01, .1, 1.]:
        result[f'Ridge_{alpha:g}'] = pipeline(prep, model=Ridge(alpha=alpha))
        result[f'Lasso_{alpha:g}'] = pipeline(prep, model=Lasso(alpha=alpha, max_iter=20000))
    return result

def fitted_details(estimator, Xtrain):
    reg = estimator.regressor_
    prep, selector, model = reg['preprocessor'], reg['selector'], reg['model']
    names = np.array(prep.get_feature_names_out())
    mask = np.ones(len(names), bool) if isinstance(selector, str) else selector.get_support()
    numeric, categorical = prep.transformers_[0][2], prep.transformers_[1][2]
    specs, fields = [], []
    if numeric:
        num = prep.named_transformers_['num']
        for i, c in enumerate(numeric):
            specs.append(dict(name=c, raw=c, kind='numeric', mean=num['scaler'].mean_[i], scale=num['scaler'].scale_[i], fill=num['imputer'].statistics_[i]))
            fields.append(dict(name=c, kind='numeric', value=num['imputer'].statistics_[i], minimum=Xtrain[c].min(), maximum=Xtrain[c].max()))
    if categorical:
        cat = prep.named_transformers_['cat']
        for i, c in enumerate(categorical):
            levels = cat['encoder'].categories_[i].tolist()
            fields.append(dict(name=c, kind='category', value=cat['imputer'].statistics_[i], categories=levels))
            for category in levels[1:]:
                specs.append(dict(name=f'{c}_{category}', raw=c, kind='category', category=category, fill=cat['imputer'].statistics_[i]))
    yscale = estimator.transformer_.scale_[0]
    selected_specs = [s for s, keep in zip(specs, mask) if keep]
    for spec, coef in zip(selected_specs, model.coef_):
        spec['coefficient'] = coef * yscale
    active_raw = {s['raw'] for s in selected_specs}
    predictor = dict(intercept=model.intercept_*yscale+estimator.transformer_.mean_[0],
                     fields=[f for f in fields if f['name'] in active_raw], terms=selected_specs)
    coefficients = [dict(feature=s['name'], coefficient=s['coefficient']) for s in selected_specs]
    return names[mask].tolist(), coefficients, predictor

def analyze(frame, target, features=None, offline=False):
    """保留 60/20/20，訓練內五折 CV；至少 19 筆校準才能估計有限 95% 區間；小資料調整比例。"""
    with threadpool_limits(limits=1):
        return _analyze(frame, target, features, offline)

def _analyze(frame, target, features, offline):
    if target not in frame or not pd.api.types.is_numeric_dtype(frame[target]):
        raise ValueError('Target 必須是存在的連續數值欄位。')
    features = features or [c for c in frame if c != target and c.lower() not in ('id', 'index') and not c.lower().endswith('_id')]
    if not features or target in features or len(set(features)) != len(features) or any(c not in frame for c in features):
        raise ValueError('請選擇有效且不重複的輸入欄位，不能包含 Target。')
    if any(c.lower() in ('id', 'index') or c.lower().endswith('_id') for c in features):
        raise ValueError('ID／索引欄位不可作為預測特徵。')
    d = frame[features+[target]].replace([np.inf, -np.inf], np.nan).dropna(subset=[target]).drop_duplicates()
    if len(d)<50 or (not offline and len(d)>5000):
        raise ValueError('有效且不重複資料需 50～5,000 列，才能保留足夠校準資料建立 95% 區間。')
    if d[target].nunique()<3:
        raise ValueError('請選擇至少有三種數值的連續回歸目標。')
    X,y = d[features].copy(), d[target].astype(float)
    for c in X.select_dtypes(exclude='number'):
        X[c] = X[c].map(lambda v: str(v) if pd.notna(v) else np.nan)
        if X[c].nunique()>100:
            raise ValueError(f'類別欄位 {c} 超過 100 種取值；請排除 ID／文字或先轉換日期。')
    tr, ca, te = split_indices(len(d))
    Xtr, ytr = X.iloc[tr], y.iloc[tr]
    cv = KFold(5, shuffle=True, random_state=SEED)
    # 僅訓練折的類別數影響 k 可用範圍；校準與測試均不參與。
    min_p = min(preprocessing(Xtr).fit_transform(Xtr.iloc[a]).shape[1] for a,_ in cv.split(Xtr))
    if min_p>160:
        raise ValueError('編碼後超過 160 個特徵；請減少高基數類別欄位。')
    models = candidates(Xtr, min_p)
    cvrows, messages = [], []
    for name, est in models.items():
        try:
            with warnings.catch_warnings(record=True) as caught:
                values = -cross_val_score(est, Xtr, ytr, cv=cv, scoring='neg_root_mean_squared_error', error_score='raise')
            cvrows.append(dict(model=name, cv_rmse=values.mean(), cv_sd=values.std(ddof=1), folds=values.tolist()))
            if any('converge' in str(w.message).lower() for w in caught):
                messages.append(f'{name} 出現收斂警告，請審慎解讀。')
        except ValueError as exc:
            messages.append(f'{name} 無法評估：{str(exc)[:180]}')
    linear = [r for r in cvrows if r['model'].startswith('LR_')]
    if not linear:
        raise ValueError('資料無法建立線性模型；請檢查全缺失或常數欄位。')
    primary = min(linear, key=lambda r:r['cv_rmse'])['model']
    # 到這裡才鎖定主模型，之後測試資料只作診斷；不再調參。
    selected_rows, fitted = [], {}
    for row in cvrows:
        name = row['model']
        est = clone(models[name]).fit(Xtr, ytr)
        fitted[name] = est
        names, coefficients, predictor = fitted_details(est, Xtr)
        pred = est.predict(X.iloc[te])
        row.update(score(y.iloc[te], pred))
        row.update(selected_features=names, features=len(names))
        selected_rows.append(row)
    est = fitted[primary]
    names, coefficients, predictor = fitted_details(est, Xtr)
    cal_errors = np.abs(y.iloc[ca].to_numpy()-est.predict(X.iloc[ca]))
    rank = math.ceil((len(ca)+1)*.95)
    q = float(np.partition(cal_errors, rank-1)[rank-1])
    pred = est.predict(X.iloc[te]); actual = y.iloc[te].to_numpy()
    sample = np.random.default_rng(SEED).choice(len(te), min(400,len(te)), replace=False)
    predictions = [dict(actual=actual[i], prediction=pred[i], lower=pred[i]-q, upper=pred[i]+q) for i in sample]
    residual = actual-pred
    # 以已選模型的訓練設計矩陣作探索性診斷；不把非時間資料的 DW 視為獨立性證明。
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson, jarque_bera
    reg=est.regressor_; design=reg['preprocessor'].transform(Xtr)
    if not isinstance(reg['selector'],str): design=reg['selector'].transform(design)
    design=sm.add_constant(design,has_constant='add'); train_res=ytr-est.predict(Xtr)
    bp=het_breuschpagan(train_res,design); jb=jarque_bera(train_res)
    result=dict(target=target, unit='Target 原始單位', samples=len(frame), analysis_samples=len(d), raw_features=len(features),
        features=features, seed=SEED, split=dict(train=len(tr), calibration=len(ca), test=len(te)), cv_n=len(tr),
        primary=primary, models=selected_rows, selection=selected_rows, coefficients=coefficients, predictor=predictor,
        predictions=predictions, interval=dict(q=q, nominal_coverage=.95, coverage=np.mean(np.abs(residual)<=q), average_width=2*q,
            calibration_n=len(ca), quantile_rank=rank, below_zero=int(np.sum(pred-q<0)), above_one=None),
        assumptions=dict(breusch_pagan_p=bp[1], durbin_watson=durbin_watson(train_res), jarque_bera_p=jb[1],
            residual_skew=skew(train_res), design_rank=np.linalg.matrix_rank(design), design_columns=design.shape[1]),
        notes=['通常為 60% 訓練／20% 校準／20% 測試；小資料優先保留至少 19 筆校準，實際筆數見卡片。seed=42，所有轉換只在各訓練折 fit。',
               '五折 CV 決定主要 LinearRegression；表內 Test 指標為鎖定後診斷，不能用來反覆選模。',
               'Lasso 篩選使用固定 alpha=0.01；與 Flood 的 LassoCV 不同。k 為編碼後特徵數。',
               'Split conformal 提供交換性假設下的邊際涵蓋保證，不保證個別區域／價格帶的涵蓋。未截斷負值區間。',
               '隨機切分結果不代表未來時間、其他地區或分布改變後的表現。']+messages,
        audit=dict(missing=int(frame[features+[target]].isna().sum().sum()), duplicate_rows=int(frame[features+[target]].duplicated().sum()),
                   dropped_rows=len(frame)-len(d), dtypes={c:str(frame[c].dtype) for c in features+[target]}),
        provenance=dict(python=platform.python_version(), selection_rule='訓練內五折 CV RMSE，主模型限定 LinearRegression', test_used_for_selection=False))
    # 測試用及離線稽核用索引，不放到公開頁面。
    result['_splits'] = dict(train=tr.tolist(), calibration=ca.tolist(), test=te.tolist())
    return clean(result), est
