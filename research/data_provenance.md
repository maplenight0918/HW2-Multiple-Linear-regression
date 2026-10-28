# 資料來源、生成方式與授權界線

本專案使用公開 Kaggle 資料集鏡像 johnwicknice/playground-series version 1，原始競賽為 playground-series-s4e5。下載失敗與替代路徑：競賽 API 回傳 401 Unauthenticated，公開 datasets API 成功回傳 ZIP。原始資料完全未自行生成或改寫。

Kaggle Playground 官方說明此系列為合成資料；本資料不是可驗證的現場洪水觀測。原始競賽 data 動態頁未能完整讀取，因此不把其他同名競賽的文字當成原始生成程序的確證。資料生成模型的架構、種子與完整生成碼未知；只可確認其合成 benchmark 性質，不宣稱知道真實物理單位。

kaggle_metadata.json 保存鏡像 version 1、更新時間與 Apache 2.0 標記。此為鏡像上傳者提供的中繼資料，未能驗證其對原始競賽資料的再授權範圍。原始競賽 rules：https://www.kaggle.com/competitions/playground-series-s4e5/rules 。正式提交及外部再散布前，須檢閱原始條款。ZIP 不內嵌原始大 CSV，提供固定版本下載程式與 SHA-256，以兼顧重現、檔案大小與來源管理。

原始 CSV 位於 data/raw/playground-series-s4e5/；雜湊見 outputs/tables/dataset_audit.json。資料欄位／筆數與公開競賽說明吻合，但未取得官方檔案的獨立雜湊，因此不能聲稱已完成位元級官方一致性驗證。

官方測試集沒有 Target，無法計算其 MAE、R² 或涵蓋率。本研究主要使用自行保留的測試集進行模型評估，未取得 Kaggle 官方排名。官方評分為 R²，與本地 R² 定義一致；本地模型選擇使用 RMSE，在同一驗證樣本上與 R² 單調對應，但跨折平均排名不保證完全一致。

查閱時原始競賽已結束，頁面仍顯示 Late Submission。可用已產生的 submission.csv 嘗試帳號內晚交功能，實際提交權限須以登入介面為準，本專案沒有送出任何提交。
