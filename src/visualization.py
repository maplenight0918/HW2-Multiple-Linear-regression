"""一致的繁體中文圖表；所有探索圖只使用訓練資料。"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy import stats
from .common import ROOT, FIGURES, TABLES

BLUE='#176B87'
TEAL='#26A69A'
ORANGE='#E38B3A'
DARK='#183B4E'

def setup():
    font=ROOT/'assets/NotoSansCJKtc-Regular.otf'
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':DARK,
        'axes.titleweight':'bold','axes.titlesize':13,'axes.labelsize':10,'font.size':10,
        'figure.facecolor':'white','axes.facecolor':'#F6F9FB','axes.grid':True,'grid.alpha':0.2,
        'axes.unicode_minus':False,'savefig.dpi':170})

def save(fig,name):
    fig.tight_layout(pad=1.6)
    fig.savefig(FIGURES/(name+'.png'),bbox_inches='tight')
    plt.close(fig)

def eda(X,y):
    setup()
    codes={f:f'F{i+1:02d}' for i,f in enumerate(X.columns)}
    pd.DataFrame({'code':list(codes.values()),'feature':list(codes)}).to_csv(TABLES/'feature_dictionary.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4))
    ax.hist(y,bins=60,color=BLUE,alpha=.9)
    ax.axvline(y.mean(),color=ORANGE,label=f'平均值 {y.mean():.3f}')
    ax.set(title='目標值集中於中段：FloodProbability 分布',xlabel='FloodProbability（0～1 目標尺度）',ylabel='樣本數');ax.legend()
    save(fig,'01_target_distribution')
    fig,axes=plt.subplots(4,5,figsize=(13,10))
    for ax,f in zip(axes.flat,X):
        ax.hist(X[f],bins=np.arange(X[f].min()-.5,X[f].max()+1.5),color=TEAL)
        ax.set(title=codes[f],xlabel='因子評分（無物理單位）',ylabel='樣本數')
    fig.suptitle('20 個原始特徵的分布｜代碼對照見欄位表',fontsize=16)
    save(fig,'02_feature_distributions')
    corr=X.assign(Target=y).corr()
    corr.to_csv(TABLES/'pearson_correlation.csv')
    fig,ax=plt.subplots(figsize=(10,9))
    im=ax.imshow(corr,cmap='RdBu_r',vmin=-1,vmax=1)
    labels=list(codes.values())+['Target']
    ax.set_xticks(range(21),labels,rotation=90);ax.set_yticks(range(21),labels)
    ax.set(title='Pearson 相關矩陣｜訓練子樣本',xlabel='特徵代碼／目標',ylabel='特徵代碼／目標')
    ax.grid(False);fig.colorbar(im,ax=ax,label='Pearson r（−1～1）',shrink=.7)
    save(fig,'03_correlation_heatmap')
    top=corr.Target.drop('Target').abs().nlargest(6).index
    plot=X.assign(Target=y).sample(min(2500,len(X)),random_state=42)
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for ax,f in zip(axes.flat,top):
        ax.scatter(plot[f],plot.Target,s=8,alpha=.16,color=BLUE)
        means=X.assign(Target=y).groupby(f).Target.mean()
        ax.plot(means.index,means.values,color=ORANGE,label='條件平均')
        ax.set(title=f'{codes[f]} | r={corr.loc[f,"Target"]:.3f}',xlabel='因子評分',ylabel='FloodProbability');ax.legend(fontsize=8)
    save(fig,'04_feature_target')
    fig,ax=plt.subplots(figsize=(12,4.5))
    ax.boxplot([X[c] for c in X],tick_labels=list(codes.values()),showfliers=False,patch_artist=True,
               boxprops=dict(facecolor='#B6DADD'),medianprops=dict(color=BLUE))
    ax.set(title='特徵箱形圖｜顯示中間分布，離群比例另列於表格',xlabel='原始特徵代碼',ylabel='因子評分（無物理單位）')
    save(fig,'05_boxplots')
    out=[]
    for f in X:
        q1,q3=X[f].quantile([.25,.75]);iqr=q3-q1
        out.append(dict(feature=f,lower=q1-1.5*iqr,upper=q3+1.5*iqr,
                        outlier_fraction=((X[f]<q1-1.5*iqr)|(X[f]>q3+1.5*iqr)).mean()))
    pd.DataFrame(out).to_csv(TABLES/'outlier_analysis.csv',index=False)

def evaluation_figures(y,pred,coef,cv,comparison,q,residuals):
    setup()
    rng=np.random.default_rng(42)
    ix=rng.choice(len(y),min(7000,len(y)),replace=False)
    y,pred=np.asarray(y),np.asarray(pred)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    hb=axes[0].hexbin(y,pred,gridsize=55,cmap='Blues',mincnt=1,bins='log')
    lim=[min(y.min(),pred.min()),max(y.max(),pred.max())]
    axes[0].plot(lim,lim,color=ORANGE,ls='--',label='理想預測')
    axes[0].set(title='真實值與預測值',xlabel='真實 FloodProbability',ylabel='預測 FloodProbability');axes[0].legend()
    fig.colorbar(hb,ax=axes[0],label='每格樣本數（對數色階）')
    axes[1].scatter(pred[ix],y[ix]-pred[ix],s=6,alpha=.2,color=BLUE)
    axes[1].axhline(0,color=ORANGE,ls='--')
    bins=pd.qcut(pred,10,duplicates='drop')
    grouped=pd.DataFrame({'pred':pred,'res':y-pred,'bin':bins}).groupby('bin',observed=True).mean()
    axes[1].plot(grouped.pred,grouped.res,'o-',color=ORANGE,label='十分位平均殘差')
    axes[1].set(title='殘差與預測值',xlabel='預測 FloodProbability',ylabel='真實值 − 預測值');axes[1].legend()
    save(fig,'06_predictions_residuals')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    axes[0].hist(y-pred,bins=80,density=True,color=TEAL,alpha=.85)
    axes[0].set(title='獨立測試集殘差分布',xlabel='殘差（目標尺度）',ylabel='機率密度')
    stats.probplot(residuals,dist='norm',plot=axes[1])
    axes[1].lines[0].set_label('訓練殘差分位數')
    axes[1].lines[1].set_label('常態參考擬合線')
    axes[1].legend(loc='upper left',fontsize=8)
    axes[1].set(title='訓練殘差 Q–Q 圖',xlabel='標準常態理論分位數',ylabel='殘差排序值')
    save(fig,'07_residual_distribution_qq')
    c=coef.sort_values('standardized_coefficient')
    fig,ax=plt.subplots(figsize=(10,7))
    ax.barh(c.feature,c.standardized_coefficient,color=BLUE)
    ax.set(title='標準化係數｜每增加一個訓練標準差的目標變化',xlabel='係數（FloodProbability 單位／1 SD）',ylabel='選用特徵')
    save(fig,'08_coefficients')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for prefix,label,color,marker,style in [('LR_KBest','SelectKBest',BLUE,'o','-'),('LR_RFE','RFE',ORANGE,'s','--')]:
        subset=cv[cv.model.str.startswith(prefix)].sort_values('mean_selected_features')
        axes[0].errorbar(subset.mean_selected_features,subset.cv_rmse,yerr=subset.cv_sd,marker=marker,linestyle=style,markersize=7,markerfacecolor='none',capsize=3,label=label,color=color)
    base=cv[cv.model=='LR_All'].iloc[0]
    axes[0].axhline(base.cv_rmse,color=TEAL,ls='--',label='全部 20 特徵')
    axes[0].set_xticks([5,10,15])
    axes[0].set(title='減少特徵的預測代價',xlabel='選用特徵數',ylabel='五折 CV RMSE（越低越好）');axes[0].legend()
    c=comparison.sort_values('rmse',ascending=False)
    axes[1].barh(c.model,c.rmse,color=[TEAL if x=='LR_All' else BLUE for x in c.model])
    axes[1].set(title='鎖定模型後的測試診斷比較',xlabel='測試 RMSE（越低越好）',ylabel='模型')
    save(fig,'09_model_comparison')
    # 先以固定亂數抽樣，再按預測值排序；真實值和上下界同步排序。
    sample=rng.choice(len(y),200,replace=False)
    order=sample[np.argsort(pred[sample])]
    fig,ax=plt.subplots(figsize=(11,5))
    ax.fill_between(range(len(order)),pred[order]-q,pred[order]+q,color=TEAL,alpha=.25,label='95% 個別預測區間')
    ax.plot(pred[order],color=BLUE,lw=2,label='點預測')
    ax.scatter(range(len(order)),y[order],s=14,color=ORANGE,alpha=.8,label='真實值')
    ax.set(title='Split conformal prediction｜區間由獨立校準集估計',xlabel='測試樣本序位（依預測值排序，抽樣 200 筆）',ylabel='FloodProbability（0～1 目標尺度）');ax.legend()
    save(fig,'10_prediction_intervals')
