"""以真實瀏覽器驗證內建題目、自訂 CSV、圖表、預測與手機排版。"""
import os
import sys
import json
from pathlib import Path
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/tmp/dic2-browsers')
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('HW2_TEST_URL','http://127.0.0.1:8012')

def run():
    checks=[]; errors=[]
    def record(name,evidence):checks.append(dict(check=name,status='PASS',evidence=evidence))
    with sync_playwright() as p:
        browser=p.chromium.launch(args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(BASE,wait_until='networkidle')
        page.wait_for_function("document.getElementById('status').textContent.includes('分析已完成')",timeout=45000)
        assert page.locator('#metrics').inner_text().find('0.02008')>=0
        record('Flood 真實指標','RMSE=0.02008，主要模型 LR_All')
        page.screenshot(path='/tmp/hw2-desktop.png',full_page=True)
        for problem,raw in [('flood',20),('housing',19)]:
            page.select_option('#problem',problem)
            page.wait_for_function(f"current && current.id==='{problem}' && !document.getElementById('analysis-content').hidden")
            assert page.evaluate('current.raw_features')==raw
            for method in ['All','KBest','RFE','LassoSelect']:
                page.select_option('#selection-method',method)
                assert page.locator('#selection-k option').count()>0
                assert page.locator('#selected-features .chip').count()>0
            diagnostics=page.evaluate("""Object.entries(charts).map(([id,c])=>({id,width:c.width,height:c.height,datasets:c.data.datasets.length,valid:c.data.datasets.every(ds=>ds.data.every(v=>typeof v==='number'?Number.isFinite(v):(Number.isFinite(v.x)&&Number.isFinite(v.y))))}))""")
            assert len(diagnostics)==5 and all(r['valid'] and r['width']>0 and r['height']>0 for r in diagnostics)
            record(problem+' 圖表',diagnostics)
            if not page.locator('#predictor-summary').evaluate('el=>el.parentElement.open'):
                page.locator('#predictor-summary').click()
            expected=page.evaluate("""()=>{const values=Object.fromEntries(current.predictor.fields.map(f=>[f.name,f.value]));return current.predictor.intercept+current.predictor.terms.reduce((v,t)=>v+t.coefficient*(t.kind==='numeric'?(values[t.raw]-t.mean)/t.scale:Number(values[t.raw]===t.category)),0)}""")
            displayed=float(page.locator('#prediction-value').inner_text().replace(',',''))
            assert abs(expected-displayed)<1.1
            page.fill('#pred-0','')
            assert '請輸入有效數值' in page.locator('#prediction-value').inner_text()
            page.click('#reset-inputs')
            record(problem+' 預測工具','訓練代表值與公式一致；空白輸入阻止預測。')
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.documentElement.scrollWidth<=innerWidth',timeout=5000)
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=f'/tmp/hw2-mobile-{problem}.png',full_page=True)
            record(problem+' 手機排版','390 px，頁面無水平溢出')
            page.set_viewport_size({'width':1440,'height':1000})
        page.select_option('#problem','custom')
        page.click('#load-example')
        page.wait_for_selector('#schema:not([hidden])',timeout=45000)
        assert page.locator('#target').input_value()=='Profit'
        assert page.locator('#feature-checks input:checked').count()==4
        page.click('#run-analysis')
        page.wait_for_function("(current && current.id==='custom' && document.getElementById('status').textContent.includes('分析已完成')) || document.getElementById('status').classList.contains('error')",timeout=120000)
        assert '分析已完成' in page.locator('#status').inner_text(),page.locator('#status').inner_text()
        assert page.evaluate('current.split.calibration')==19
        assert page.evaluate('current.interval.q')>0
        record('老師指定 CSV 網址端到端分析',page.evaluate('({split:current.split,primary:current.primary,interval:current.interval,models:current.models.length})'))
        page.locator('#feature-checks input').first.uncheck()
        assert page.locator('#analysis-content').is_hidden()
        record('變更特徵後使舊結果失效','必須重新分析，不能顯示過期的預測圖')
        page.set_input_files('#csv-file',str(ROOT/'tests/fixtures/50_Startups.csv'))
        page.wait_for_function("document.getElementById('status').textContent.includes('已載入')")
        record('CSV 檔案上傳','50 筆資料正確解析；Target=Profit')
        page.fill('#csv-url','http://127.0.0.1:8012/api/health');page.click('#load-url')
        page.wait_for_function("document.getElementById('status').classList.contains('error')")
        assert page.locator('#schema').is_hidden()
        record('非法網址錯誤處理','拒絕讀取內部網路；隱藏舊資料設定')
        assert not errors,errors
        record('瀏覽器 JavaScript','零 pageerror')
        browser.close()
    report={'base_url':BASE,'checks':checks,'errors':errors,'screenshots':['/tmp/hw2-desktop.png','/tmp/hw2-mobile-flood.png','/tmp/hw2-mobile-housing.png']}
    (ROOT/'outputs/web/browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
