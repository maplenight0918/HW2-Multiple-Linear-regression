# 研究來源與查核紀錄

查閱日期：2026-10-19。下列為來源支持的理論／公開說明，本專案分數只來自 outputs/tables；不轉用他人排行榜分數。網頁經瀏覽工具查核，動態 Kaggle 頁面的部分內容須透過搜尋索引與公開 API 交叉核對。各來源抓取狀態另見 source_checks.json。

## S01 — Regression with a Flood Prediction Dataset
- URL：https://www.kaggle.com/competitions/playground-series-s4e5
- 作者／組織：Walter Reade、Ashley Chow／Kaggle
- 日期：2024；查閱時頁面顯示競賽已結束，並有 Late Submission 入口。
- 主題：競賽背景、資料生成與評估。
- 發現：官方採 R²；提交欄位為 id、FloodProbability。Playground 使用合成資料以提供練習基準。
- 與 HW2 關係：支持連續目標與評估設計；不能推論已驗證真實災害預警能力。

## S02 — playground_series 公開資料集鏡像
- URL：https://www.kaggle.com/datasets/johnwicknice/playground-series
- API：https://www.kaggle.com/api/v1/datasets/view/johnwicknice/playground-series
- 作者／組織：wang tong（johnwicknice）／Kaggle
- 日期：2024-05-18；version 1。
- 主題：合法公開取得 CSV。
- 發現：API 標示 Apache 2.0，壓縮檔含 S4E5 train、test、sample_submission。保存原始 API 回覆與 SHA-256。
- 與 HW2 關係：官方 competition API 未登入回傳 401，改由此公開 Kaggle 鏡像下載。欄位、筆數、ID 與預期競賽結構相符；未能直接與需登入的官方 CSV 雜湊逐位元比對。
- 使用限制：鏡像上傳者標示的授權不自動取代競賽原始條款；只用於本次學術作業並保留來源。官方 rules 頁動態內容未完整可讀，正式提交或再發布前應由帳號持有人確認原始條款，不宣稱商用權已獲驗證。

## S03 — Feature selection
- URL：https://scikit-learn.org/stable/modules/feature_selection.html
- 作者／組織：scikit-learn developers
- 日期：持續更新，頁面未提供單一發表日。
- 主題：單變量選擇、RFE、模型係數選擇。
- 發現：單變量評分與遞迴剔除採不同訊息；L1 係數可用於稀疏選擇。
- 與 HW2 關係：設計 KBest、RFE 與 Lasso 篩選實驗；不能預設刪減必然改善泛化。

## S04 — Linear Models
- URL：https://scikit-learn.org/stable/modules/linear_model.html
- 作者／組織：scikit-learn developers
- 日期：持續更新，未列單一發表日。
- 主題：OLS、Ridge、Lasso。
- 發現：OLS 最小化殘差平方和；Ridge 使用 L2 懲罰，Lasso 使用 L1 懲罰且可產生零係數。
- 與 HW2 關係：正則化的偏差／變異取捨與尺度處理。

## S05 — Common pitfalls and recommended practices
- URL：https://scikit-learn.org/stable/common_pitfalls.html
- 作者／組織：scikit-learn developers
- 日期：持續更新，未列單一發表日。
- 主題：前處理一致性與資料洩漏。
- 發現：前處理只在訓練部分 fit；Pipeline 有助將前處理與模型一起進行交叉驗證。
- 與 HW2 關係：所有訓練／測試／校準資料邊界及實作驗證。

## S06 — A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification
- URL：https://arxiv.org/abs/2107.07511
- 作者：Anastasios N. Angelopoulos、Stephen Bates
- 日期：2021（arXiv 初版；來源頁含修訂日期）。
- 主題：Conformal prediction。
- 發現：在交換性等條件下，校準分數的適當分位數可建立有限樣本邊際涵蓋保證；不等同每一子群的條件涵蓋保證。
- 與 HW2 關係：以獨立校準集建立個別預測區間，避開把任意固定百分比誤當統計區間。

## S07 — het_breuschpagan
- URL：https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_breuschpagan.html
- 作者／組織：statsmodels developers
- 日期：持續更新，未列單一發表日。
- 主題：殘差異質變異檢定。
- 發現：可使用輔助回歸檢驗誤差變異是否與解釋變數有關。
- 與 HW2 關係：結合殘差圖、效果量與 HC3 推論，避免僅以 p-value 判定。

## S08 — S4E5 competition solution discussion
- URL：https://www.kaggle.com/competitions/playground-series-s4e5/discussion/500453
- 作者／組織：Kaggle 參賽者；可見內容連結 jamesking76 的 AutoML 解法，作者身分不額外推定。
- 日期：2024；精確發表日未確認。
- 主題：列內總和、標準差與集成方法。
- 發現：參賽者分享由輸入特徵計算列內總和、標準差等特徵，協助樹模型學習整體訊號。
- 與 HW2 關係：本專案實作 HGB + sum/std 作為比較；不引用其未複現分數。本專案全部輸入仍只有 20 個原始特徵，衍生後為 22 欄。

## S09 — Awesome AutoGluon: Competition Solutions
- URL：https://github.com/autogluon/autogluon/blob/master/AWESOME.md
- 作者／組織：AutoGluon maintainers
- 日期：持續更新；S4E5 條目標示 2024-05-31。
- 主題：公開競賽集成解法。
- 發現：維護者列出 S4E5 使用 AutoGluon 的成功案例，顯示集成與特徵工程值得研究。
- 與 HW2 關係：作理論與文獻比較；本作業未重現 AutoGluon，也不聲稱達到該名次。

## S10 — Lasso model selection: AIC-BIC / cross-validation
- URL：https://scikit-learn.org/stable/auto_examples/linear_model/plot_lasso_model_selection.html
- 作者／組織：scikit-learn developers
- 日期：持續更新，未列單一發表日。
- 主題：以驗證誤差呈現正則化選擇。
- 發現：可視覺化 alpha 與誤差的取捨。
- 與 HW2 關係：參考清楚的座標、曲線與誤差呈現原則；本專案圖形完全使用本次實測數據自行繪製，沒有複製他人結果圖片。


## S11 — Linear Models（實驗版本核對）
- URL：https://scikit-learn.org/1.6/modules/linear_model.html
- 作者／組織：scikit-learn developers
- 日期：版本 1.6.1 文件；查閱 2026-10-20。
- 主題：核對使用者研究整理的 OLS、Ridge、Lasso、分位數與求解器適用範圍。
- 發現：平方損失、L2、L1 與不同任務的 solver 需區別。
- 與 HW2 關係：後補技術核對；不宣稱是原 NotebookLM 當時匯入的來源。

## S12 — Feature selection（實驗版本核對）
- URL：https://scikit-learn.org/1.6/modules/feature_selection.html
- 作者／組織：scikit-learn developers
- 日期：版本 1.6.1 文件；查閱 2026-10-20。
- 主題：KBest、RFE 與模型選擇。
- 發現：各選擇器依不同規則篩選，需驗證泛化效能。
- 與 HW2 關係：核對新增研究摘要，非原生 NotebookLM 引用證據。

## S13 — Common pitfalls（實驗版本核對）
- URL：https://scikit-learn.org/1.6/common_pitfalls.html
- 作者／組織：scikit-learn developers
- 日期：版本 1.6.1 文件；查閱 2026-10-20。
- 主題：Pipeline、防洩漏與隨機性。
- 發現：前處理及選擇應只於訓練資料擬合；隨機種子的語意需區分。
- 與 HW2 關係：核對研究文件中的流程與重現性敘述。

## S14 — scikit-learn 線性模型估計器與求解器技術選型指南
- 作者／組織：使用者提供，使用者說明為 NotebookLM 研究整理。
- 日期：2026-10-20 收件；實際研究日期未提供。
- 主題：研究摘要原始附件；13 頁。
- 本地檔案：research/notebooklm_chat.pdf。
- 發現：包含線性模型、特徵選擇、分位數及 Pipeline；未保留原生來源引用標記；使用者已明確確認當時匯入 S01–S10 的 URL。
- 與 HW2 關係：第 17 節依本附件整理，技術另核對 S11–S13；不是本專案實驗結果。

## S15 — HW2 對話內容整理與實作提示詞存檔
- 作者／組織：使用者提供之 ChatGPT 整理稿。
- 日期：文件標示製作日期 2026-10-20。
- 主題：作業需求、特徵數限制、研究與實作提示詞；4 頁。
- 本地檔案：research/chatgpt_session.pdf。
- 發現：首頁及末頁自述並非完整逐字對話。
- 與 HW2 關係：收錄為輔助證據；原始 GPT／Codex 對話已另由新上傳原檔及本輪 session 匯出合併，見 report/gpt_conversation.pdf。


## S16 — 第二題：House Sales in King County, USA

- URL：https://www.kaggle.com/datasets/harlfoxem/housesalesprediction
- 作者／組織：harlfoxem / Kaggle
- 日期：version 1，2016-08-25（Kaggle API metadata）
- 主題：房屋成交價多元回歸；19 個原始輸入特徵。
- 發現：原資料 21,613 筆、21 欄；排除 id 與 price 得 19 欄。首筆住宅去重後分析 21,436 筆；zipcode 編碼與日期轉換均明確記錄。
- 與 HW2 關係：網站下拉選單的第二個完整回歸題目，作為不同尺度、類別輸入及共線性的比較。
- 使用限制：Kaggle API 標示 CC0: Public Domain，保存於 research/king_county_metadata.json。實際分析結果屬本專案，非引用他人分數。
- 研究／下載日期：2026-10-27 UTC。


## S17 — Using custom workflows with GitHub Pages
- URL：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- 作者／組織：GitHub Docs。
- 日期：未提供固定出版日期；查核 2026-10-28。
- 主題：GitHub Actions 靜態網站建置與 Pages 發布。
- 發現：需啟用自訂工作流程；建置上傳 Pages artifact，部署 job 設定 pages:write、id-token:write 與 github-pages environment。
- 與 HW2 關係：新版主要繳交 GitHub＋web 的實際發布設定依據。

## S18 — Deploy a FastAPI App
- URL：https://render.com/docs/deploy-fastapi
- 作者／組織：Render。
- 日期：未提供固定出版日期；查核 2026-10-28。
- 主題：FastAPI Web Service 部署。
- 發現：以 requirements 安裝 Python 依賴，使用 Uvicorn 啟動服務並監聽平台提供的 PORT。
- 與 HW2 關係：自訂 CSV 的 Python 訓練服務部署參考；此來源不表示本專案已完成 Render 上線。
