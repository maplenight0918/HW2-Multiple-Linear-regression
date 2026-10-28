"""檢查真正上線的 Pages；將遠端檔案、瀏覽器與後端狀態分開記錄。"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/tmp/dic2-browsers')
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-root', type=Path, default=ROOT/'public_repository/dist')
    args = parser.parse_args()
    deployment = json.loads((ROOT/'deployment.json').read_text())
    base = deployment['siteUrl'].rstrip('/')+'/'
    checks, errors, failed_responses = [], [], []
    files = {}
    for path in sorted(args.expected_root.rglob('*')):
        if not path.is_file() or path.name == '.nojekyll':
            continue
        name = path.relative_to(args.expected_root).as_posix()
        with urlopen(base+name, timeout=40) as response:
            assert response.status == 200, name
            remote = response.read()
        digest = hashlib.sha256(remote).hexdigest()
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest(), '遠端版本不同：'+name
        files[name] = digest
    assert len(files) >= 20
    checks.append({'check':'遠端靜態檔案','status':'PASS','evidence':f'{len(files)} 個檔案 HTTP 200 且 SHA-256 與本版建置一致'})
    with sync_playwright() as p:
        # 此執行環境的 Chromium 以 HTTP/1.1 連線驗證，避免 HTTP/2 協定逾時。
        browser = p.chromium.launch(args=['--no-sandbox','--disable-quic','--disable-http2'])
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failed_responses.append({'url':response.url,'status':response.status}) if response.status >= 400 else None)
        page.goto(base, wait_until='networkidle', timeout=60000)
        page.wait_for_function("current && current.id==='flood'")
        assert page.locator('#github').get_attribute('href') == deployment['repository']
        assert page.evaluate('HW2_CONFIG.hostedStatic') is True
        assert page.evaluate("document.fonts.check('16px HW2CJK')")
        for problem,count in [('flood',20),('housing',19)]:
            page.select_option('#problem', problem)
            page.wait_for_function(f"current && current.id==='{problem}' && !document.getElementById('analysis-content').hidden")
            local = json.loads((ROOT/'web/data'/f'{problem}.json').read_text())
            assert page.evaluate('current.primary') == local['primary']
            assert page.evaluate('current.raw_features') == count
            assert page.evaluate('current.interval.q') == local['interval']['q']
            charts = page.evaluate("""Object.entries(charts).map(([id,c])=>({id,width:c.width,height:c.height,valid:c.data.datasets.every(d=>d.data.every(v=>typeof v==='number'?Number.isFinite(v):(Number.isFinite(v.x)&&Number.isFinite(v.y))))}))""")
            assert len(charts)==5 and all(c['valid'] and c['width']>0 and c['height']>0 for c in charts)
            for method in ['All','KBest','RFE','LassoSelect']:
                page.select_option('#selection-method', method)
                assert page.locator('#selected-features .chip').count()>0
            if not page.locator('#predictor-summary').evaluate('el=>el.parentElement.open'):
                page.locator('#predictor-summary').click()
            expected = page.evaluate("""()=>{const values=Object.fromEntries(current.predictor.fields.map(f=>[f.name,f.value]));return current.predictor.intercept+current.predictor.terms.reduce((v,t)=>v+t.coefficient*(t.kind==='numeric'?(values[t.raw]-t.mean)/t.scale:Number(values[t.raw]===t.category)),0)}""")
            actual = float(page.locator('#prediction-value').inner_text().replace(',',''))
            assert abs(expected-actual)<1.1
            page.fill('#pred-0','')
            assert '請輸入有效數值' in page.locator('#prediction-value').inner_text()
            page.click('#reset-inputs')
            page.select_option('#selection-method','All')
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            page.wait_for_function('scrollY===0')
            page.screenshot(path=f'/tmp/hw2-live-{problem}-desktop.png',full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            page.wait_for_function('scrollY===0')
            page.screenshot(path=f'/tmp/hw2-live-{problem}-mobile.png',full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            checks.append({'check':problem+' 線上互動','status':'PASS','evidence':{'raw_features':count,'charts':charts,'selection_methods':4,'predictor_formula':True,'empty_input_rejected':True,'mobile_no_overflow':True}})
        page.select_option('#problem','custom')
        page.click('#load-example')
        page.wait_for_function("document.getElementById('status').classList.contains('error')")
        message = page.locator('#status').inner_text()
        assert '服務' in message or 'API' in message
        checks.append({'check':'未配置自訂 CSV 後端時的提示','status':'PASS','evidence':message})
        assert not errors and not failed_responses, (errors, failed_responses)
        browser.close()
    evidence = {'checked_at':datetime.now(timezone.utc).isoformat(),'site_url':base,'status':'PASS',
                'checks':checks,'pageerrors':errors,'failed_responses':failed_responses,'remote_sha256':files,
                'browser_transport':'Chromium HTTPS／HTTP/1.1（此環境停用 QUIC 與 HTTP/2）',
                'custom_csv_remote_training':'PENDING：API_BASE_URL 尚未設定；不將本機訓練成功當作遠端服務已上線。'}
    (ROOT/'outputs/web/pages_browser_validation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','site_url':base,'verified_files':len(files),'browser_checks':len(checks),'pageerrors':errors},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
