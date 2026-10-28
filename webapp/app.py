"""FastAPI：公開 CSV／檔案載入、背景分析及網站預覽。"""
import csv
import io
import ipaddress
import os
import socket
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse,urljoin
import numpy as np
import pandas as pd
import urllib3
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .analysis import analyze,clean
ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=5_000_000
DATA={};JOBS={};STORE_LOCK=threading.Lock();ANALYSIS_LOCK=threading.Lock()
app=FastAPI(title='HW2 多元線性回歸分析',version='1.0.0')
app.add_middleware(GZipMiddleware,minimum_size=1000)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('ALLOWED_ORIGINS','https://maplenight0918.github.io,http://localhost:8000,http://127.0.0.1:8000').split(',')],allow_methods=['GET','POST'],allow_headers=['Content-Type'],allow_credentials=False)

def public_address(url):
    """只容許公網 HTTP(S)，並回傳已驗證 IP，下載時固定連到該 IP 避免 DNS rebinding。"""
    parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('請使用公開 HTTP(S) CSV 網址。')
    if parsed.port not in (None,80,443):
        raise ValueError('資料網址只支援標準 HTTP／HTTPS 連接埠。')
    addresses=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('資料來源必須是公開網路；不可讀取本機或內部網路。')
    return parsed,addresses[0][4][0]

def fetch_csv(url):
    started=time.monotonic()
    for _ in range(5):
        parsed,address=public_address(url)
        pool_cls=urllib3.HTTPSConnectionPool if parsed.scheme=='https' else urllib3.HTTPConnectionPool
        kwargs=dict(timeout=urllib3.Timeout(connect=8,read=8),maxsize=1,retries=False)
        if parsed.scheme=='https':kwargs.update(server_hostname=parsed.hostname,assert_hostname=parsed.hostname,cert_reqs='CERT_REQUIRED')
        with pool_cls(address,port=parsed.port or (443 if parsed.scheme=='https' else 80),**kwargs) as pool:
            path=parsed.path or '/'
            if parsed.query:path+='?'+parsed.query
            response=pool.request('GET',path,headers={'Host':parsed.hostname,'User-Agent':'HW2-Regression-Explorer/1.0'},redirect=False,preload_content=False)
            try:
                if response.status in (301,302,303,307,308):
                    url=urljoin(url,response.headers.get('Location',''));continue
                if response.status!=200:raise ValueError(f'資料來源回傳 HTTP {response.status}。')
                content=bytearray()
                for chunk in response.stream(65536,decode_content=True):
                    content.extend(chunk)
                    if len(content)>MAX_BYTES:raise ValueError('CSV 超過 5 MB 限制。')
                    if time.monotonic()-started>30:raise ValueError('資料下載逾時，請改用檔案上傳。')
                return bytes(content)
            finally:response.close()
    raise ValueError('網址重新導向次數過多。')

def ingest(raw,source):
    if len(raw)>MAX_BYTES:raise ValueError('CSV 超過 5 MB 限制。')
    try:
        text=raw.decode('utf-8-sig');header=next(csv.reader(io.StringIO(text)))
        if len(header)!=len(set(header)) or any(not x.strip() for x in header):raise ValueError('CSV 欄位名稱不能重複或空白。')
        d=pd.read_csv(io.StringIO(text),nrows=5001)
    except (UnicodeError,pd.errors.ParserError,StopIteration):
        raise ValueError('請提供 UTF-8、逗號分隔且有欄名的 CSV。')
    if not 50<=len(d)<=5000 or not 2<=len(d.columns)<=40:raise ValueError('自訂資料需 50～5,000 列、2～40 欄。內建大資料已事先完成分析。')
    d=d.replace([np.inf,-np.inf],np.nan)
    numeric=list(d.select_dtypes(include='number').columns)
    if not numeric:raise ValueError('找不到可作為回歸 Target 的數值欄位。')
    token=uuid.uuid4().hex
    with STORE_LOCK:
        for k in list(DATA):
            if time.time()-DATA[k][0]>1800:del DATA[k]
        if len(DATA)>=10:DATA.pop(next(iter(DATA)))
        DATA[token]=(time.time(),d)
    return clean(dict(id=token,source=source,rows=len(d),columns=[dict(name=c,kind='numeric' if c in numeric else 'category',missing=int(d[c].isna().sum())) for c in d],target=numeric[-1],preview=d.head(5).replace({np.nan:None}).to_dict('records')))

@app.get('/api/health')
def health():return {'status':'ok','service':'hw2-regression','limit_rows':5000}

class URLRequest(BaseModel):
    url:str=Field(min_length=1,max_length=2048)

@app.post('/api/url')
def url_load(req:URLRequest):
    try:return ingest(fetch_csv(req.url),req.url)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except Exception:raise HTTPException(400,'下載失敗或逾時，請確認 CSV 網址，或改用檔案上傳。')

@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    try:return ingest(await file.read(MAX_BYTES+1),file.filename or '上傳 CSV')
    except ValueError as exc:raise HTTPException(400,str(exc))
    finally:await file.close()

class AnalyzeRequest(BaseModel):
    dataset:str
    target:str
    features:list[str]=Field(min_length=1,max_length=39)

@app.post('/api/analyze')
def start_analysis(req:AnalyzeRequest):
    with STORE_LOCK:
        item=DATA.get(req.dataset)
        if item is None or time.time()-item[0]>1800:raise HTTPException(404,'資料已過期，請重新載入。')
        frame=item[1].copy()
    if not ANALYSIS_LOCK.acquire(blocking=False):raise HTTPException(429,'目前有分析進行中，請稍後再試。')
    key=uuid.uuid4().hex
    with STORE_LOCK:
        if len(JOBS)>=10:JOBS.pop(next(iter(JOBS)))
        JOBS[key]={'status':'running'}
    def run():
        try:
            result,_=analyze(frame,req.target,req.features)
            result.pop('_splits',None)
            result.update(id='custom',title='自訂資料分析',short='Custom Dataset',subtitle='使用自己的資料，檢驗線性回歸的表現。',source_url=None)
            state={'status':'done','result':result}
        except ValueError as exc:state={'status':'error','error':str(exc)}
        except Exception:state={'status':'error','error':'分析失敗；請檢查欄位型別、缺失值及有效資料筆數。'}
        finally:
            with STORE_LOCK:JOBS[key]=state
            ANALYSIS_LOCK.release()
    threading.Thread(target=run,daemon=True).start()
    return {'job':key}

@app.get('/api/jobs/{key}')
def job(key:str):
    with STORE_LOCK:state=JOBS.get(key)
    if state is None:raise HTTPException(404,'找不到分析工作；伺服器重啟後請重新執行。')
    return state

# 本機／Render 同時提供靜態頁面；GitHub Pages 只部署 web 匯出內容。
app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='web')
