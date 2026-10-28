"""在已登入 GitHub CLI 的環境發布乾淨公開版本，保留遠端歷史。"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=ROOT, capture=False):
    # 強制非互動，未登入時立即回報，不把憑證寫入 URL 或檔案。
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': ''}
    result = subprocess.run(args, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if result.returncode:
        raise RuntimeError('命令未完成：' + ' '.join(args[:3]) + '；請檢查登入與 repository 權限。')
    return result.stdout.strip() if capture else ''


def api(path, method='GET', fields=None):
    args = ['gh', 'api', path, '--method', method]
    for key, value in (fields or {}).items():
        args += ['-f', key + '=' + str(value)]
    output = run(args, capture=True)
    return json.loads(output) if output else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-seconds', type=int, default=600)
    args = parser.parse_args()
    deployment = json.loads((ROOT / 'deployment.json').read_text())
    repository = deployment['repository'].removesuffix('.git').rstrip('/')
    if not repository.startswith('https://github.com/'):
        raise ValueError('repository 必須為 GitHub HTTPS 網址')
    slug = repository.removeprefix('https://github.com/')
    if len(slug.split('/')) != 2:
        raise ValueError('repository 格式必須為 owner/name')
    evidence = {'checked_at': datetime.now(timezone.utc).isoformat(),
                'repository': repository, 'site_url': deployment['siteUrl'],
                'repository_pushed': False, 'pages_verified': False}
    evidence_path = ROOT / 'outputs/web/github_deployment.json'
    try:
        if not shutil.which('gh'):
            raise RuntimeError('尚未安裝 GitHub CLI；請安裝 gh 並執行 gh auth login。')
        run(['gh', 'auth', 'status'], capture=True)
        metadata = api('repos/' + slug)
        if metadata.get('private'):
            raise RuntimeError('目前 repository 非公開；請先確認 Pages 方案與可見性。')
        if not metadata.get('permissions', {}).get('push'):
            raise RuntimeError('目前登入帳號沒有推送此 repository 的權限。')
        branch = metadata.get('default_branch', 'main')
        if branch != 'main':
            raise RuntimeError('遠端預設分支不是 main；請先同步 workflow 分支，避免覆寫既有設定。')
        run([sys.executable, 'scripts/check_web_artifacts.py'])
        temporary = Path(tempfile.mkdtemp(prefix='hw2-public-release-'))
        exported, checkout = temporary / 'export', temporary / 'repository'
        run([sys.executable, 'scripts/export_public_repo.py', '--output', str(exported)])
        git = ['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential']
        run(git + ['clone', repository + '.git', str(checkout)])
        # 只複製公開白名單；遠端其他檔案保留，不連帶刪除。
        shutil.copytree(exported, checkout, dirs_exist_ok=True)
        name = run(['git', 'config', 'user.name'], capture=True)
        email = run(['git', 'config', 'user.email'], capture=True)
        run(['git', 'config', 'user.name', name], cwd=checkout)
        run(['git', 'config', 'user.email', email], cwd=checkout)
        run(['git', 'checkout', '-B', 'main'], cwd=checkout)
        run(['git', 'add', '.'], cwd=checkout)
        if run(['git', 'status', '--porcelain'], cwd=checkout, capture=True):
            run(['git', 'commit', '-m', 'Publish regression website and revised HW2 documentation'], cwd=checkout)
        run(git + ['push', '-u', 'origin', 'main'], cwd=checkout)
        evidence.update(repository_pushed=True,
                        commit=run(['git', 'rev-parse', 'HEAD'], cwd=checkout, capture=True))
        # 查詢 Pages：只有 HTTP 404 才建立，其他錯誤不能當成未啟用。
        probe = subprocess.run(['gh', 'api', 'repos/' + slug + '/pages'], capture_output=True, text=True)
        if probe.returncode == 0:
            api('repos/' + slug + '/pages', 'PUT', {'build_type': 'workflow'})
        elif 'HTTP 404' in probe.stderr:
            api('repos/' + slug + '/pages', 'POST', {'build_type': 'workflow'})
        else:
            raise RuntimeError('無法讀取 Pages 設定；請確認管理及 Pages 權限。')
        api('repos/' + slug + '/actions/workflows/pages.yml/dispatches', 'POST', {'ref': 'main'})
        deadline = time.monotonic() + max(0, args.wait_seconds)
        while time.monotonic() < deadline:
            runs = api('repos/' + slug + '/actions/workflows/pages.yml/runs?per_page=10').get('workflow_runs', [])
            matching = [r for r in runs if r.get('head_sha') == evidence['commit']]
            if matching and matching[0].get('conclusion') == 'success':
                evidence['workflow_url'] = matching[0]['html_url']
                with urllib.request.urlopen(deployment['siteUrl'], timeout=30) as response:
                    html = response.read().decode('utf-8')
                    if response.status != 200 or '迴歸研究室' not in html:
                        raise RuntimeError('網站首頁內容未通過驗證')
                for relative in ['data/flood.json', 'data/housing.json', 'data/research.json']:
                    with urllib.request.urlopen(deployment['siteUrl'] + relative, timeout=30) as response:
                        remote = response.read()
                    local = (ROOT / 'web' / relative).read_bytes()
                    if hashlib.sha256(remote).digest() != hashlib.sha256(local).digest():
                        raise RuntimeError('網站資料與本次公開檔案不同：' + relative)
                evidence['pages_verified'] = True
                break
            if matching and matching[0].get('conclusion') in ['failure', 'timed_out', 'action_required']:
                evidence['workflow_url'] = matching[0]['html_url']
                raise RuntimeError('Pages workflow 未成功，請查看 evidence 中的 workflow_url。')
            time.sleep(5)
        if not evidence['pages_verified']:
            evidence['note'] = '已推送並啟動 Pages；等待期限內尚未完成遠端驗證。'
    except Exception as error:
        evidence['error'] = str(error)
        print(str(error), file=sys.stderr)
    finally:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence['pages_verified'] else 1


if __name__ == '__main__':
    sys.exit(main())
