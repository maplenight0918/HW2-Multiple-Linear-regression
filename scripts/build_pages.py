"""產生 GitHub Pages 成品；只匯出分析本文，不公開對話、模型或原始 CSV。"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def export_assets():
    import fitz
    dest=ROOT/'web/downloads';dest.mkdir(exist_ok=True,parents=True)
    meta=json.loads((ROOT/'outputs/logs/report_appendix.json').read_text())
    with fitz.open(ROOT/'report/report.pdf') as src, fitz.open() as out:
        out.insert_pdf(src,from_page=0,to_page=meta['core_pages']-1)
        out.set_metadata({'title':'HW2 多元線性回歸分析本文','author':json.loads((ROOT/'config.json').read_text())['student_id']})
        out.save(dest/'report_analysis.pdf',garbage=4,deflate=True)
    student=json.loads((ROOT/'config.json').read_text())['student_id']
    shutil.copy2(ROOT/'notebooks'/f'{student}_hw2.ipynb',dest/f'{student}_hw2.ipynb')
    shutil.copy2(ROOT/'research/sources.md',dest/'sources.md')
    shutil.copy2(ROOT/'outputs/tables/model_comparison.csv',dest/'model_comparison.csv')
    target=ROOT/'web/figures';target.mkdir(exist_ok=True)
    for path in (ROOT/'outputs/figures').glob('*.png'):shutil.copy2(path,target/path.name)

def build():
    config=json.loads((ROOT/'deployment.json').read_text())
    if os.getenv('API_BASE_URL'):config['apiBase']=os.environ['API_BASE_URL'].rstrip('/')
    config['hostedStatic']=True
    dest=ROOT/'dist'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(ROOT/'web',dest)
    student=json.loads((ROOT/'config.json').read_text())['student_id']
    index=dest/'index.html'
    index.write_text(index.read_text().replace('7114056093',student))
    (dest/'config.js').write_text('// 公開設定，不含憑證。\nwindow.HW2_CONFIG = '+json.dumps(config,ensure_ascii=False)+';\n')
    (dest/'.nojekyll').touch()
    for name in ['flood','housing','research']:
        data=json.loads((dest/'data'/f'{name}.json').read_text())
        if name!='research':
            assert data['predictions'] and data['models'] and data['interval']['q']>0
    assert not list(dest.rglob('*conversation*')) and not list(dest.rglob('*.joblib'))
    files={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
    (ROOT/'outputs/web/pages_manifest.json').write_text(json.dumps(files,indent=2))
    print(f'Pages 建置完成：{len(files)} 個檔案，{sum(p.stat().st_size for p in dest.rglob("*") if p.is_file()):,} bytes')
    print('自訂 API：'+(config['apiBase'] or '尚未設定；本機 FastAPI 可完整執行，自訂服務部署後設定 API_BASE_URL。'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-assets',action='store_true');args=parser.parse_args()
    if args.refresh_assets:export_assets()
    build()
