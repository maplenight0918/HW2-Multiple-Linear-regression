# NotebookLM 真實研究提示詞

請先匯入 sources.md 的來源 S01、S03～S09 的實際網址／原始文件，必要時將原始網頁列印為 PDF 後匯入。來源清單本身不能代替原始文件。再上傳 report/report.pdf，其中已有本專案的模型比較與區間結果；可另補充 model_comparison.csv 與 cv_results.csv。

來源完成匯入後，將以下「你是統計學…」開始的內容貼到 NotebookLM 的聊天輸入框執行，不是僅把提示詞上傳為來源。

你是統計學與機器學習研究助理。請以繁體中文研究 Kaggle Playground S4E5 FloodProbability 回歸。請逐項回答：

1. 比較常見 Linear Regression 解法，以及資料生成方式如何限制真實洪災推論。
2. 說明 All Features、SelectKBest(f_regression)、RFE 與 LassoCV 特徵選擇的優缺點；區分篩選、包裝與嵌入法。
3. 比較 Linear Regression、Ridge、Lasso 與梯度提升／AutoGluon；不可將他人的排行榜分數當成本專案結果。
4. 說明訓練內交叉驗證、獨立測試集、MAE、RMSE、R² 及資料洩漏。
5. 比較 OLS 平均值信賴區間、個別預測區間與 split conformal prediction。交代交換性、邊際涵蓋與條件涵蓋差別。
6. 以來源支持每項重要論點，列出原文來源標題及引用定位。沒有證據的內容標示「無法確認」。
7. 對照本專案實測表格，指出特徵刪減與正則化是否改善預測；不可捏造實驗。
8. 產生至少 100 字（建議 300～500 字）的繁體中文整合摘要，另附方法優缺點表與引用。
9. 指出合成資料、極端值、資料分布改變、有限超參數搜尋與未參加 Kaggle 提交的限制。

請將 NotebookLM 回覆原文、來源編號、執行日期及 notebook 連結匯出保留。使用者核對後，將摘要插入 notebooklm_summary.md 並在 manual_status.json 填寫真實資訊，最後重建 PDF 與 ZIP。

## 操作參考

Google 官方說明：先加入來源，再透過聊天依選取的來源提問，並檢查引用。
https://support.google.com/gemininotebook/answer/16215270?co=GENIE.Platform%3DDesktop&hl=en

請保留輸出原文與來源；提供給本專案時可附 NotebookLM 回覆／研究匯出 PDF、摘要、操作日期及 notebook 連結。
