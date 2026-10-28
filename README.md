# HW2｜迴歸研究室

學號：7114056093。以 **Flood Prediction 與 King County Housing** 兩個 Kaggle 題目展示多元線性回歸、特徵選擇、模型評估、95% 預測區間與 CRISP-DM 六階段。

## 新版作業對照

主要繳交為 **GitHub repository 與可瀏覽的網站**；PDF 報告、對話與資訊圖表為補充附件。分析仍包含多元線性回歸、必要的特徵選擇與評估、含 95% 預測區間的預測圖，以及 CRISP-DM 六階段。NotebookLM 超過 100 字摘要與「GPT 輔助內容」已保留於網站與報告。

| 新版要求 | 本專案對應 |
|---|---|
| Kaggle 原始特徵 >13；題目搜尋 14～39 | Flood 20 欄、King County 19 欄；均不含 ID、Target，也符合較早 10～20 欄限制 |
| 下拉視窗呈現兩種 problem（加分項） | 網站「選擇問題」可切換 Flood 與 King County |
| 任意 Dataset 輸入（加分項） | 支援公開 CSV URL 與上傳、選 Target／特徵；需 FastAPI 分析服務，依容量與資料型別驗證 |
| 模型與統計結果 | LinearRegression 主模型、KBest／RFE／Lasso 篩選、CV、MAE／MSE／RMSE／R²、預測區間 |
| GitHub＋web 主繳交 | 原始碼 repository、GitHub Actions Pages 工作流程與網站 |
| 選用附件 | 已執行 Notebook、分析 PDF、完整私人對話與本地 ZIP |
| Kaggle 名次（若有） | 未正式提交；呈現真實本地測試指標，不虛構排名 |

兩項加分功能是否計分由老師判定；自訂 CSV 不要求符合內建 Kaggle 題目的原始特徵數，才能支援老師的 50 Startups 範例。

## 網站

GitHub repository：`maplenight0918/HW2-Multiple-Linear-regression`。Pages 工作流程成功後，網站網址為 `https://maplenight0918.github.io/HW2-Multiple-Linear-regression/`。是否上線以 repository 的 Actions／Pages 實際部署狀態為準。

- 下拉切換兩個回歸問題。
- 自訂 CSV 網址與檔案上傳，可選 Target 及輸入特徵。
- All、SelectKBest、RFE、Lasso-based 選擇及 LinearRegression、Ridge、Lasso 比較。
- 真實值與預測、殘差、係數、模型比較及 95% 個別預測區間互動圖表。
- 新樣本即時預測、CRISP-DM、NotebookLM 摘要與 GPT 輔助內容。
- 隨網站提供繁體中文字型，桌面與手機均可使用。

## 題目與實際結果

| 題目 | 原始樣本 | 原始輸入 | Target | LinearRegression 測試 RMSE | 測試 R² | 區間涵蓋率 |
|---|---:|---:|---|---:|---:|---:|
| [Flood](https://www.kaggle.com/competitions/playground-series-s4e5) | 1,117,957 | 20 | FloodProbability | 0.020080 | 0.844878 | 94.9667% |
| [King County](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction) | 21,613 | 19 | price | USD 153,909.11 | 0.828156 | 94.9860% |

Flood 是合成 benchmark，不宣稱可預警真實洪災。主研究以訓練內 80,000 筆五折 CV 選模，完整訓練 715,492 筆、校準 178,873 筆、測試 223,592 筆。全部 20 特徵的 LinearRegression 優於刪至 15 特徵的版本；LassoCV 保留全部 20 欄。HGB 為進階比較，測試 RMSE 0.018559、R² 0.867484，不取代主要線性模型。沒有 Kaggle 官方排名。

房價資料保留每屋最早一筆交易，分析 21,436 間住宅。19 原始輸入中 date 轉天數、zipcode 類別編碼，全模型產生 87 個編碼特徵；原始欄數與編碼欄數不同。以 12,861 筆訓練內五折 CV 選模，4,287 筆獨立校準、4,288 筆測試。完整矩陣含精確共線性，係數不宜當成因果解釋。

## 安裝與執行

建議 Python 3.11。網站依賴與完整研究依賴分開，單純執行網站不需安裝 PDF／Notebook 工具。

```bash
python -m pip install -r requirements-web.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

開啟 http://127.0.0.1:8000 。完整部署方式見 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md)。GitHub Pages 讀取預先計算的 JSON；自訂 CSV 需要 FastAPI，Render 設定已提供。未配置後端時頁面會明確提示。

## CRISP-DM

1. **Business Understanding**：建立可解釋的連續目標預測，區分 benchmark 與真實部署。
2. **Data Understanding**：資料型別、缺失／重複檢查，分布、Pearson、離群值及共線性分析。
3. **Data Preparation**：互斥訓練、校準與測試；Pipeline 在每個訓練折 fit。
4. **Modeling**：LinearRegression 主模型、特徵選擇與正則化比較，以訓練 CV 決定模型。
5. **Evaluation**：MAE、MSE、RMSE、R²，殘差、假設與獨立校準的 split conformal。
6. **Deployment**：已訓練轉換的即時預測、自訂 CSV 背景分析、輸入錯誤提示與可重現程式。

## 預測區間

有限樣本校準分位數 `ceil((n_cal+1)*0.95)`；絕不使用測試集決定半寬。Flood 平均寬度 0.08011631。房價平均寬度 USD 544,497.47，764 筆測試下界低於零，保留原始界限。邊際涵蓋不保證每一子群，也不保證資料漂移後有效。

自訂 CSV 50～5,000 列、最多 5 MB；至少保留 19 筆校準。老師的 50 Startups 範例會分成 21／19／10。小校準集的 95% 區間可能很寬。自訂與房價的 Lasso 篩選是固定 alpha=0.01，與 Flood 的 LassoCV 明確區分。

## 目錄與重現

- `web/`：繁體中文前端、實際 JSON 成果、互動圖表、公開分析本文與 Notebook。
- `webapp/`：FastAPI、CSV 載入、訓練內交叉驗證、特徵選擇及 conformal。
- `src/`、`notebooks/7114056093_hw2.ipynb`：完整主題分析。
- `outputs/tables/`、`outputs/web/`：模型指標、區間、第二題稽核與瀏覽器驗證。
- `research/`：來源、NotebookLM 提示詞與經使用者確認文件整理的摘要。
- `report/web_validation.md`：網站測試證據及遠端部署狀態。

```bash
# 不需科學運算依賴的靜態檢查與建置
python scripts/check_web_artifacts.py
python scripts/build_pages.py
# 完整研究重現（需要下載原始 Kaggle 資料）
python -m pip install -r requirements.txt
python scripts/setup_assets.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m src.run_experiment
python scripts/build_web_data.py
```

所有切分固定 seed=42。版本列於 requirements 與 outputs/tables/environment.json。原始大型 CSV 與 joblib 不公開提交，重跑可重建。

## 研究、對話與授權

NotebookLM 摘要超過 100 字，來源對應見 research/sources.md。GPT 協助資料研究、程式、統計、圖表、測試與網站；私人原始對話及完整對話附錄保留在本地作業繳交包。公開 PDF 為分析本文，不含私人逐字對話。報告亦包含第二題、網站操作與新版繳交方式；對話僅涵蓋附件標示的匯出截止時間。

[分析報告](web/downloads/report_analysis.pdf) · [主程式](notebooks/7114056093_hw2.ipynb) · [來源](research/sources.md) · [第三方授權](NOTICE.md)
