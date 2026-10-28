"""建立可從頭執行的繁體中文實驗 Notebook。"""
import json
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'config.json').read_text())
nb=nbf.v4.new_notebook()
nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
nb.cells=[
nbf.v4.new_markdown_cell('# HW2｜FloodProbability 多元線性回歸\n以 CRISP-DM 完成資料稽核、訓練內特徵選擇、模型比較與獨立校準的 95% 預測區間。\n\n原始資料來自 Kaggle S4E5 的公開鏡像，屬合成 benchmark；不是經驗證的真實洪災預警模型。'),
nbf.v4.new_markdown_cell('## 執行與資料邊界\n固定 seed=42。先保留 20% 測試集，再將剩餘資料的 20% 作為校準集。僅從真正訓練部分抽取 80,000 筆執行五折 CV；選定模型後在完整訓練部分擬合。下列儲存格會實際重新執行完整實驗，約數分鐘，並更新 outputs/。'),
nbf.v4.new_code_cell("from pathlib import Path\nimport os, sys, json\nROOT = Path.cwd()\nif not (ROOT / 'config.json').exists():\n    ROOT = ROOT.parent\nos.chdir(ROOT)\nsys.path.insert(0, str(ROOT))\nfor variable in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:\n    os.environ[variable] = '1'\nprint('專案根目錄：', ROOT)"),
nbf.v4.new_code_cell("from src.run_experiment import run\nresults = run()\ndisplay(results[['model', 'features', 'cv_rmse', 'mae', 'rmse', 'r2']])"),
nbf.v4.new_markdown_cell('## 資料理解與特徵選擇\nKBest 使用 f_regression；RFE 以 LinearRegression 遞迴刪除；LassoCV 在原始相同評分尺度進行三折內層選擇，再接 imputer、scaler 與 OLS。其他模型在每個 CV fold 內完整擬合 Pipeline。校準與測試資料皆不參與選擇。'),
nbf.v4.new_code_cell("import pandas as pd\ndisplay(pd.read_csv('outputs/tables/cv_results.csv'))\ndisplay(pd.read_csv('outputs/tables/lasso_selection.csv'))\nprint(Path('outputs/tables/selection_lock.json').read_text())"),
nbf.v4.new_code_cell("from IPython.display import display, Image\nfor name in ['01_target_distribution', '03_correlation_heatmap', '09_model_comparison']:\n    display(Image(filename=f'outputs/figures/{name}.png', width=850))"),
nbf.v4.new_markdown_cell('## 評估與不確定性\n下表多個測試分數僅為模型鎖定後的診斷；不能依測試分數改選主模型。Conformal 區間的校準誤差取第 ceil((n+1)×0.95) 個排序值。其保證為交換性條件下的邊際涵蓋，不代表每個風險區段均達 95%。'),
nbf.v4.new_code_cell("print(Path('outputs/tables/prediction_interval.json').read_text())\nprint(Path('outputs/tables/assumptions.json').read_text())\ndisplay(pd.read_csv('outputs/tables/conditional_diagnostics.csv'))\nfor name in ['06_predictions_residuals', '07_residual_distribution_qq', '10_prediction_intervals']:\n    display(Image(filename=f'outputs/figures/{name}.png', width=850))"),
nbf.v4.new_markdown_cell('## Deployment\n使用儲存的完整 Pipeline 與校準分位數預測。額外的 id 欄位會被忽略；缺少必要欄位或非法型別會回報錯誤。模型不裁切點預測或區間。Kaggle 提交模型另以全部標籤資料重訓，不能沿用此校準區間。'),
nbf.v4.new_code_cell("from src.prediction import predict_new_data\npredictions = predict_new_data('data/processed/new_samples.csv')\ndisplay(predictions)\nassert predictions.notna().all().all()\nassert (predictions.lower_95 <= predictions.prediction).all()\nassert (predictions.prediction <= predictions.upper_95).all()"),
nbf.v4.new_markdown_cell('## 新版繳交與研究附件\n主要繳交為 GitHub 與網站：https://github.com/maplenight0918/HW2-Multiple-Linear-regression 。Pages 目標為 https://maplenight0918.github.io/HW2-Multiple-Linear-regression/ ，上線狀態見 report/web_validation.md。本 Notebook 實際執行 Flood 主要研究；第二個 King County 題目與自訂 CSV 分析見 webapp/、scripts/build_web_data.py 與 WEB_DEPLOYMENT.md。\n\nPDF、對話與資訊圖表依新版規定作為補充附件。NotebookLM 真實研究摘要超過 100 字；GPT 輔助內容與來源見報告及網站。完整私人對話保留於本地附件，範圍以匯出截止時間為準。學號由 config.json 統一設定。Kaggle 未正式提交，沒有官方排名。\n\n重建報告：`python scripts/build_report.py`；同步公開下載檔：`python scripts/build_pages.py --refresh-assets`；驗收打包：`python scripts/validate_and_package.py`。')]
nb.cells[0].source += f"\n\n學號：{config['student_id']}（由 config.json 設定）。"
path=ROOT/'notebooks'/f"{config['student_id']}_hw2.ipynb"
nbf.write(nb,path)
print(path)
