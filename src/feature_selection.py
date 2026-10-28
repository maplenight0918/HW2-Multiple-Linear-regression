"""特徵選擇：只接受訓練部分，LassoCV 於相同評分尺度的原始特徵運作。"""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LassoCV
from sklearn.model_selection import KFold
from sklearn.utils.validation import check_array, check_is_fitted

class LassoCVSelector(TransformerMixin, BaseEstimator):
    """先做 LassoCV 再標準化，避免內層 CV 共用已估計的 scaler。"""
    def __init__(self, seed=42):
        self.seed = seed

    def fit(self, X, y):
        values = check_array(X)
        self.n_features_in_ = values.shape[1]
        self.estimator_ = LassoCV(alphas=np.logspace(-5, -2, 12),
            cv=KFold(3, shuffle=True, random_state=self.seed), max_iter=10000, n_jobs=1)
        self.estimator_.fit(values, y)
        self.support_ = np.abs(self.estimator_.coef_) > 1e-10
        if not self.support_.any():
            raise ValueError('LassoCV 沒有保留特徵；請檢查訓練資料與候選 alpha')
        return self

    def transform(self, X):
        check_is_fitted(self, 'support_')
        # 部署時缺失值交給後續 imputer；訓練資料須先通過完整性稽核。
        return np.asarray(X, dtype=float)[:, self.support_]

    def get_support(self):
        check_is_fitted(self, 'support_')
        return self.support_

class AddRowSummary(TransformerMixin, BaseEstimator):
    """僅由當筆 X 建立總和與標準差；不使用 Target 或其他樣本。"""
    def fit(self, X, y=None):
        self.n_features_in_ = np.asarray(X).shape[1]
        return self

    def transform(self, X):
        values = np.asarray(X)
        return np.column_stack([values, values.sum(axis=1), values.std(axis=1)])
