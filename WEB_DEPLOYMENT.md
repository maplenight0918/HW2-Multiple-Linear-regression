# 網站執行與發布

本專案依新版作業，以 GitHub＋網站作為主要展示。兩個內建題目直接讀取實際計算的結果；自訂 CSV 由 FastAPI 執行 Python 分析。原有 Notebook、完整 PDF 與對話附件保留在本地繳交包。

已上線：[HW2 迴歸研究室](https://maplenight0918.github.io/HW2-Multiple-Linear-regression/)。原始碼：[GitHub repository](https://github.com/maplenight0918/HW2-Multiple-Linear-regression)。25 個公開檔案與建置 SHA-256 一致，線上兩題、圖表、新樣本預測與手機排版已驗證。自訂 CSV 遠端重新訓練仍需配置下述 FastAPI 服務。

## 本機完整執行

建議 Python 3.11：

```bash
python -m pip install -r requirements-web.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

開啟 http://127.0.0.1:8000 。此模式可使用兩個題目、CSV 網址、上傳與實際訓練，不需雲端帳號。不要直接雙擊 index.html，瀏覽器對本機檔案的 fetch 有限制。

## GitHub 公開版本

指定 repository：`maplenight0918/HW2-Multiple-Linear-regression`。

**本地研究專案的 Git 歷史含原始對話附件，請使用公開匯出版本，不要直接推送本地研究專案的完整歷史。** 公開匯出採白名單，包含網站、程式、Notebook、分析本文、來源與聚合成果，不含原始對話、完整對話 PDF、原始大型 CSV、joblib 模型或憑證。

```bash
python scripts/export_public_repo.py --output /tmp/HW2-Multiple-Linear-regression
cd /tmp/HW2-Multiple-Linear-regression
python scripts/check_web_artifacts.py
python scripts/build_pages.py
```

上述 repository 已發布，以下為後續更新方式。安裝 GitHub CLI 並於自己的終端機完成 `gh auth login --scopes workflow` 後，在**完整本地研究專案**執行：

```bash
python scripts/publish_github.py
```

此腳本會先檢查登入、驗證公開成果、白名單匯出到暫存資料夾，再 clone 指定 repository；保留遠端歷史、不使用 force push。推送 main 後設定 Pages 為 GitHub Actions，記錄實際回應至 `outputs/web/github_deployment.json`。第一次啟用 Pages 需要帳號具有 repository 管理與 Pages 設定權限。腳本不寫入或輸出 token，也不把本地私人 Git 歷史帶上遠端。

若已在公開匯出資料夾，可手動使用 Git 推送該乾淨版本，並至 repository 的 **Settings → Pages → Build and deployment → Source** 選擇 **GitHub Actions**。在 **Actions → 驗證並部署 HW2 網站 → Run workflow** 啟動部署。網站網址為：

https://maplenight0918.github.io/HW2-Multiple-Linear-regression/

GitHub Pages 不執行 Python。兩個內建題目、圖表、研究與已訓練公式的單筆預測可直接使用；只有「自訂 CSV 重新訓練」需下節後端。Pages 上線不能單獨證明自訂 CSV 遠端服務可用。

## 自訂 CSV 的 Render 服務

1. 登入 Render，從上述 repository 建立 Blueprint，使用根目錄 `render.yaml`。
2. 確認部署成功，開啟實際服務網址的 `/api/health`，應回傳 `service: hw2-regression`。
3. 在 GitHub **Settings → Secrets and variables → Actions → Variables** 建立公開變數 `API_BASE_URL`，值填 Render 實際網址，不加 `/api`。
4. 重新執行 Pages workflow。內建題目不需 Render；自訂分析使用該網址。也可在網站「分析服務連線」輸入服務網址，設定只留在瀏覽器。

Render 的實際方案可用性與價格以帳號當下顯示為準；本專案提供 free 設定，不替使用者購買方案。未設定後端時，頁面會明確提示未連線，不會假裝已執行自訂分析。

## 自訂資料的行為

- CSV 使用 UTF-8、逗號分隔、唯一且非空的欄名；上限 5 MB、50～5,000 列、2～40 欄。
- Target 必須是至少三種值的數值欄；排除 ID／index／`*_id`。
- 支援數值缺失補中位數、類別缺失補眾數、未知類別以全零編碼處理。高基數文字需先整理。
- 一般採 60% 訓練／20% 校準／20% 測試。小資料至少保留 19 筆校準，因此老師的 50 Startups 範例分成 21／19／10。
- 五折 CV 在 Pipeline 內擬合前處理與篩選；數值輸入與 Target 均在各訓練折標準化。
- All、KBest、RFE、Lasso 篩選後以 LinearRegression 擬合，另比較 Ridge 與 Lasso。自訂題的 Lasso 篩選為 alpha=0.01，不冒稱 LassoCV。
- 主模型只依訓練 CV 選定；所有 Test 數值皆為鎖定後診斷。特徵選擇操作區不會改變已鎖定的主模型。
- 絕對校準殘差的第 `ceil((n_cal+1)*0.95)` 個排序值作為半寬。50 筆範例只有 19 筆校準，使用最大校準殘差，區間可能很寬。
- 上下界不截斷；區間假設為交換性，並不保證每一地區或價格帶涵蓋 95%。
- 資料與工作結果暫存伺服器記憶體，不落地；資料 30 分鐘後過期或重啟即消失，最多保留 10 組、一次執行一份分析。

## 重新計算與建置

```bash
# 若需要重建 Flood 原始成果，先依 README 安裝完整研究依賴，再執行：
python -m src.run_experiment
# 匯出 Flood 並重新下載／分析第二題：
python scripts/build_web_data.py
# 僅匯出既有 Flood，不重訓第二題：
python scripts/build_web_data.py --flood-only
# 純靜態建置，不需訓練套件：
python scripts/check_web_artifacts.py
python scripts/build_pages.py
```

`python scripts/build_pages.py --refresh-assets` 僅用於完整本地研究專案，會從原報告擷取分析本文、同步圖表與 Notebook。公開 repository 已包含下載檔案，直接執行不帶參數的建置即可。

## 驗證

完整本地研究環境：

```bash
python -m pytest -q --junitxml=outputs/logs/pytest.xml
python scripts/check_web_artifacts.py
python scripts/build_pages.py
python scripts/check_pages_browser.py
node --check web/app.js
# 另開終端機啟動網站後，使用已安裝的 Playwright Chromium：
HW2_TEST_URL=http://127.0.0.1:8000 python scripts/check_web_browser.py
```

Playwright 是瀏覽器 QA 的選用依賴，安裝 `playwright==1.60.0` 並執行 `python -m playwright install chromium`。若瀏覽器安裝於自訂位置，設定 `PLAYWRIGHT_BROWSERS_PATH`；不需要將它加入 Render 生產依賴。

測試證據在 `outputs/logs/web_pytest.xml`、`outputs/web/browser_validation.json` 與 `report/web_validation.md`。GitHub Pages 已完成遠端驗證，證據見 outputs/web/pages_browser_validation.json；Render 自訂 CSV 服務尚未部署。

官方部署文件：[GitHub Pages 自訂工作流程](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[Render FastAPI](https://render.com/docs/deploy-fastapi)。部署設定於 2026-10-28 查核。

線上驗證：先於乾淨公開 repository 執行 `python scripts/build_pages.py`，再於完整研究專案執行 `python scripts/check_live_pages.py --expected-root public_repository/dist`。工具會比對所有公開資產雜湊，並操作兩題、篩選、預測、手機排版及未連後端提示。
