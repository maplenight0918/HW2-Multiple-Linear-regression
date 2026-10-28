"""下載繪圖及 PDF 所用的開源繁體中文字型。"""
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
for relative,url in [
 ('assets/NotoSansCJKtc-Regular.otf','https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf'),
 ('assets/NotoSansSymbols2-Regular.ttf','https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf'),
 ('assets/NotoSansSymbols2-OFL.txt','https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/OFL.txt'),
 ('assets/font_license.txt','https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE')]:
    path=ROOT/relative
    if not path.exists():
        response=requests.get(url,timeout=180);response.raise_for_status();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(response.content)
        print('已下載：',relative)
