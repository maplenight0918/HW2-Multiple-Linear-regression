"""以真實瀏覽器驗證 Pages 專案子路徑；不把本機測試當成遠端發布。"""
import functools
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/tmp/dic2-browsers')
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]


def main():
    deployment = json.loads((ROOT/'deployment.json').read_text())
    project = deployment['repository'].rstrip('/').split('/')[-1]
    temporary = tempfile.TemporaryDirectory(prefix='hw2-pages-check-')
    (Path(temporary.name)/project).symlink_to(ROOT/'dist', target_is_directory=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=temporary.name))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/{project}/'
    errors, checks = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--no-sandbox'])
            page = browser.new_page(viewport={'width':1440, 'height':1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(base, wait_until='networkidle')
            page.wait_for_function("current && current.id==='flood'")
            assert page.locator('#github').get_attribute('href') == deployment['repository']
            assert page.evaluate("document.fonts.check('16px HW2CJK')")
            for problem, count in [('flood',20), ('housing',19)]:
                page.select_option('#problem', problem)
                page.wait_for_function(f"current && current.id==='{problem}'")
                assert page.evaluate('current.raw_features') == count
                assert page.evaluate('Object.keys(charts).length') == 5
                assert page.evaluate('Object.values(charts).every(c=>c.width>0 && c.height>0)')
                checks.append(problem+'：正確欄數與五組互動圖表')
                page.set_viewport_size({'width':390, 'height':844})
                page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
                page.set_viewport_size({'width':1440, 'height':1000})
            for relative in ['style.css', 'app.js', 'vendor/NotoSansCJKtc-Regular.woff',
                             'downloads/report_analysis.pdf', 'downloads/sources.md']:
                with urlopen(base+relative, timeout=15) as response:
                    assert response.status == 200 and len(response.read()) > 100
            checks.extend(['指定 repository 連結正確','中文字型及下載檔可由子路徑載入','兩題手機版無頁面水平溢出'])
            page.select_option('#problem','custom')
            page.click('#load-example')
            page.wait_for_function("document.getElementById('status').classList.contains('error')")
            text = page.locator('#status').inner_text()
            assert 'API' in text or '服務' in text
            checks.append('未連接後端時明確提示，沒有假分析結果')
            page.select_option('#problem','flood')
            page.wait_for_function("current && current.id==='flood'")
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path='/tmp/hw2-pages-desktop.png',full_page=True)
            # 係數圖六位小數提示與原始資料相符，避免近似值看似完全相同。
            labels = page.evaluate("""()=>{const c=charts['coefficient-chart']; return c.data.datasets[0].data.slice(0,3).map(x=>c.options.plugins.tooltip.callbacks.label({parsed:{x}}));}""")
            assert len(set(labels)) == 3, labels
            checks.append('Flood 前三項係數提示顯示不同的六位小數')
            assert not errors, errors
            browser.close()
        proof={'status':'PASS','checked_at':datetime.now(timezone.utc).isoformat(),
               'scope':'本機模擬 GitHub Pages 專案子路徑，並非遠端上線證據',
               'subpath':base,'checks':checks,'pageerrors':errors}
        (ROOT/'outputs/web/static_validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(proof,ensure_ascii=False,indent=2))
    finally:
        server.shutdown();server.server_close();temporary.cleanup()


if __name__=='__main__':main()
