"""評估指標與有限樣本 split conformal prediction。"""
import math
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def metrics(y,pred,p=None):
    n=len(y)
    mse=mean_squared_error(y,pred)
    r2=r2_score(y,pred)
    return dict(mae=mean_absolute_error(y,pred),mse=mse,rmse=np.sqrt(mse),r2=r2,
                adjusted_r2=(1-(1-r2)*(n-1)/(n-p-1)) if p is not None and n>p+1 else None)

def conformal_quantile(y_cal,pred_cal,coverage=0.95):
    errors=np.abs(np.asarray(y_cal)-np.asarray(pred_cal))
    k=math.ceil((len(errors)+1)*coverage)
    if k>len(errors):
        raise ValueError('校準資料不足以估計指定 coverage 的有限區間')
    return float(np.partition(errors,k-1)[k-1]),k

def interval_metrics(y,pred,q):
    y,pred=np.asarray(y),np.asarray(pred)
    lower,upper=pred-q,pred+q
    return dict(coverage=float(np.mean((y>=lower)&(y<=upper))),average_width=float(np.mean(upper-lower)),
        prediction_out_of_bounds=int(np.sum((pred<0)|(pred>1))),lower_out_of_bounds=int(np.sum(lower<0)),
        upper_out_of_bounds=int(np.sum(upper>1)))
