# HW2 網站驗收

本輪新增兩題互動網站與自訂 CSV 分析。原有研究結果沿用已驗證版本；第二題為實際下載並訓練。

| 項目 | 狀態 | 證據 |
|---|---|---|
| 兩個符合原始特徵數條件的 Kaggle 題目 | PASS | Flood 20 欄；King County 19 欄；web/data 與 housing_audit.json |
| LinearRegression、特徵選擇、訓練內 CV | PASS | tests/test_web.py 與兩題 models／selection 真實輸出 |
| 95% Prediction Interval | PASS | 獨立校準分位數；測試涵蓋與寬度核對；未截斷 |
| 原有作業＋網站整合測試 | PASS | outputs/logs/pytest.xml：44 passed，0 failures/errors |
| 網頁與 Python 預測一致 | PASS | Flood 範例與房價 20 筆樣本，實際比較保存 Pipeline 與前端公式 |
| NotebookLM、GPT 輔助與 CRISP-DM | PASS | 網頁完整六階段、真實研究摘要；私人原始對話留在本地作業包 |
| 中文字型與圖表視覺 | PASS | 內嵌 Noto Sans CJK TC；實際檢視桌面圖表、區間與手機畫面，無缺字／重疊 |
| GitHub Pages 建置 | PASS | scripts/check_web_artifacts.py、scripts/build_pages.py；僅公開分析本文 |
| GitHub Pages 子路徑與後端未配置狀態 | PASS | outputs/web/static_validation.json；實際瀏覽器載入兩題，錯誤提示明確 |
| GitHub repository | PASS | GitHub API 於 2026-10-28 回傳 200；使用者已建立指定公開 repository |
| 原始碼 push | PENDING | outputs/web/github_deployment.json；尚未取得可用帳號認證 |
| 公開 Pages 網址驗證 | PENDING | 需 repository 登入與第一次部署成功後檢查 |
| Render 遠端 API | PENDING | 本機完整 API 已驗證；雲端帳號與 API_BASE_URL 尚未設定 |
| Flood 真實指標 | PASS | outputs/web/browser_validation.json |
| flood 圖表 | PASS | outputs/web/browser_validation.json |
| flood 預測工具 | PASS | outputs/web/browser_validation.json |
| flood 手機排版 | PASS | outputs/web/browser_validation.json |
| housing 圖表 | PASS | outputs/web/browser_validation.json |
| housing 預測工具 | PASS | outputs/web/browser_validation.json |
| housing 手機排版 | PASS | outputs/web/browser_validation.json |
| 老師指定 CSV 網址端到端分析 | PASS | outputs/web/browser_validation.json |
| 變更特徵後使舊結果失效 | PASS | outputs/web/browser_validation.json |
| CSV 檔案上傳 | PASS | outputs/web/browser_validation.json |
| 非法網址錯誤處理 | PASS | outputs/web/browser_validation.json |
| 瀏覽器 JavaScript | PASS | outputs/web/browser_validation.json |

## 視覺檢閱

桌面 1440 px、手機 390 px。固定種子的抽樣點、同步排序預測區間、坐標單位、模型圖例及係數標籤均檢查。係數長名稱以省略號顯示，滑鼠提示保留完整名稱。手機完整表格使用區塊內水平捲動，不使整個頁面溢出。

網站預覽：outputs/web/website_preview.png。截圖只是畫面證據；數值正確性另由 Python 與瀏覽器測試驗證。

## 繳交界線

完整報告已補入新版要求、房價題目、網站架構及自訂 CSV 分析；私人對話附錄保留原始匯出內容與截止時間。本地完整 ZIP 與公開 GitHub ZIP 分開，公開包不含私人逐字對話或原 Git 歷史。

主要繳交為 GitHub 與 web；PDF、逐字對話與資訊圖表為選用附件。遠端部署完成與本機可執行性分別列示；自訂 CSV 遠端訓練需另行連接 API。

部署目標：https://maplenight0918.github.io/HW2-Multiple-Linear-regression/ 。設定與恢復發布方式見 WEB_DEPLOYMENT.md。

公開 ZIP 已實際解壓、核對全部 SHA-256，從乾淨目錄重新建置並執行 50 Startups CSV 訓練；證據見 outputs/web/public_export_validation.json。
