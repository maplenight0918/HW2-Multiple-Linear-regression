/* 網站只讀取實際分析輸出；自訂資料由 Python API 執行。 */
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const config = window.HW2_CONFIG || {};
const charts = {};
let current=null, dataset=null, generation=0, loadGeneration=0, busy=false;
let apiBase = localStorage.getItem('hw2-api-base') || config.apiBase || '';
const count = x => Number(x).toLocaleString('zh-TW');
const fmt = (x,d=4) => x==null || !Number.isFinite(Number(x)) ? '—' : Number(x).toLocaleString('zh-TW',{maximumFractionDigits:Math.abs(x)>=1000?0:d,minimumFractionDigits:Math.abs(x)<1 && x!==0?Math.min(d,4):0});
const pct = x => `${(x*100).toFixed(2)}%`;
const modelLabel = name => name==='LR_All'?'Linear Regression · All':name.startsWith('LR_KBest')?`Linear · KBest ${name.split('_').at(-1)}`:name.startsWith('LR_RFE')?`Linear · RFE ${name.split('_').at(-1)}`:name==='LR_LassoSelect'?'Linear · Lasso 篩選':name==='HGB_Summary'?'Gradient Boosting':name.replace('_',' · α=');
function setStatus(message, state='ready'){ $('status').textContent=message; $('status').className=`status ${state==='ready'?'':state}`; }
function safeUrl(url){try {const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}
function setBusy(value){busy=value; ['load-url','load-example','csv-file','run-analysis'].forEach(id=>$(id).disabled=value);}
async function api(path,options={}){
  if(config.hostedStatic && !apiBase) throw new Error('自訂分析服務尚未連線。請在「分析服務連線」設定已部署的服務網址，或先探索兩個內建題目。');
  const response=await fetch(apiBase.replace(/\/$/,'')+path,{...options,signal:AbortSignal.timeout(45000)});
  const data=await response.json().catch(()=>({detail:'伺服器未回傳有效資料。'}));
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:`請求失敗（HTTP ${response.status}）`);
  return data;
}
function plot(id,type,data,extra={}){
  if(charts[id]) charts[id].destroy();
  const unit=current.unit;
  charts[id]=new Chart($(id),{type,data,options:{responsive:true,maintainAspectRatio:false,animation:false,
    plugins:{legend:{display:false,labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label}: ${fmt(ctx.parsed.y ?? ctx.parsed.x)}`}}},
    scales:{x:{grid:{color:'#eff2f4'},ticks:{maxTicksLimit:6,font:{size:10}},title:{display:true,text:unit,font:{size:10}}},y:{grid:{color:'#eff2f4'},ticks:{maxTicksLimit:6,font:{size:10}},title:{display:true,text:unit,font:{size:10}}}},...extra}});
}
function renderCharts(){
  const p=current.predictions;
  const low=Math.min(...p.flatMap(v=>[v.actual,v.prediction])),high=Math.max(...p.flatMap(v=>[v.actual,v.prediction]));
  plot('actual-chart','scatter',{datasets:[{label:'測試樣本',data:p.map(v=>({x:v.actual,y:v.prediction})),backgroundColor:'#0c887c65',pointRadius:2.5},
    {label:'理想預測線',type:'line',data:[{x:low,y:low},{x:high,y:high}],borderColor:'#a4aeb5',borderDash:[5,5],borderWidth:1.5,pointRadius:0}]});
  charts['actual-chart'].options.scales.x.title.text=`真實 ${current.target}`;charts['actual-chart'].options.scales.y.title.text=`預測 ${current.target}`;charts['actual-chart'].update();
  $('actual-caption').textContent=`固定抽樣 ${count(p.length)} 筆測試樣本供繪圖；所有評估指標使用完整 ${count(current.split.test)} 筆測試集。單位：${current.unit}。`;
  plot('residual-chart','scatter',{datasets:[{label:'殘差',data:p.map(v=>({x:v.prediction,y:v.actual-v.prediction})),backgroundColor:'#8360be65',pointRadius:2.5},
    {label:'零殘差',type:'line',data:[{x:low,y:0},{x:high,y:0}],borderColor:'#a4aeb5',borderWidth:1,borderDash:[5,5],pointRadius:0}]});
  charts['residual-chart'].options.scales.x.title.text='預測值';charts['residual-chart'].options.scales.y.title.text=`殘差（${current.unit}）`;charts['residual-chart'].update();
  const ordered=[...p].sort((a,b)=>a.prediction-b.prediction);
  const intervalRows=ordered.filter((_,i)=>i%Math.max(1,Math.ceil(ordered.length/100))===0);
  plot('interval-chart','line',{labels:intervalRows.map((_,i)=>i+1),datasets:[
    {label:'下界',data:intervalRows.map(v=>v.lower),borderWidth:0,pointRadius:0,backgroundColor:'transparent'},
    {label:'上界',data:intervalRows.map(v=>v.upper),borderWidth:0,pointRadius:0,backgroundColor:'#1b9a7326',fill:'-1'},
    {label:'點預測',data:intervalRows.map(v=>v.prediction),borderColor:'#138576',borderWidth:2,pointRadius:0},
    {label:'真實值',data:intervalRows.map(v=>v.actual),borderColor:'#7955b9',backgroundColor:'#7955b9',showLine:false,pointRadius:2.4}
  ]});
  charts['interval-chart'].options.scales.x.title.text='展示樣本（依預測值由小到大排序）';charts['interval-chart'].update();
  $('interval-caption').textContent=`展示 ${intervalRows.length} 筆；真實值、點預測與上下界同步排序。區間半寬 q=${fmt(current.interval.q,6)} 只由 ${count(current.interval.calibration_n)} 筆校準資料決定，沒有使用測試集調整。`;
  const rows=current.models;
  plot('model-chart','bar',{labels:rows.map(r=>modelLabel(r.model)),datasets:[{label:'CV RMSE',data:rows.map(r=>r.cv_rmse),backgroundColor:'#aacfc4',borderRadius:3},{label:'Test RMSE',data:rows.map(r=>r.rmse),backgroundColor:'#7963ad',borderRadius:3}]},
    {indexAxis:'y',plugins:{legend:{display:true,position:'bottom',labels:{boxWidth:10,font:{size:10}}}},scales:{x:{beginAtZero:true,title:{display:true,text:`RMSE（${current.unit}）`,font:{size:10}},ticks:{maxTicksLimit:4,font:{size:9}},grid:{color:'#eff2f4'}},y:{ticks:{font:{size:9}},grid:{display:false}}}});
  const c=[...current.coefficients].sort((a,b)=>Math.abs(b.coefficient)-Math.abs(a.coefficient)).slice(0,12);
  $('coefficient-description').textContent=`${modelLabel(current.primary)} 的係數，按絕對值顯示前 ${c.length} 項；固定呈現 CV 選定的主模型。`;
  const coefficients=current.coefficients.map(r=>r.coefficient);
  $('coefficient-caption').textContent=current.id==='flood'
    ? `長條接近是實際結果：全部 ${coefficients.length} 項標準化係數介於 ${Math.min(...coefficients).toFixed(6)}～${Math.max(...coefficients).toFixed(6)}，沒有單一特徵明顯突出。滑鼠移到長條可看六位小數；這不代表真實世界的因果重要性相同。`
    : '數值欄係數表示增加 1 個訓練標準差的變化；類別欄表示相對參考組的差異，兩者須分別解讀。係數不是因果重要性排名。';
  plot('coefficient-chart','bar',{labels:c.map(r=>r.feature.length>22?r.feature.slice(0,20)+'…':r.feature),datasets:[{label:'係數',data:c.map(r=>r.coefficient),backgroundColor:c.map(r=>r.coefficient>=0?'#55a594':'#af91cb'),borderRadius:3}]},
    {indexAxis:'y',plugins:{legend:{display:false},tooltip:{callbacks:{title:items=>c[items[0].dataIndex].feature,label:ctx=>`係數：${Number(ctx.parsed.x).toLocaleString('zh-TW',{minimumFractionDigits:6,maximumFractionDigits:6})}`}}},scales:{x:{title:{display:true,text:'數值欄每 1 SD／類別由 0 到 1 的目標變化',font:{size:9}},ticks:{maxTicksLimit:4,font:{size:9}},grid:{color:'#eff2f4'}},y:{ticks:{font:{size:9}},grid:{display:false}}}});
}
function methodRows(method){return current.selection.filter(r=>method==='All'?r.model==='LR_All':r.model.startsWith(`LR_${method}`));}
function renderSelectionOptions(){
  const rows=methodRows($('selection-method').value);
  $('selection-k').innerHTML=rows.map(r=>`<option value="${esc(r.model)}">${r.features} 個模型特徵 · ${esc(r.model)}</option>`).join('');
  if(rows.length)renderSelection();
  else{$('selected-features').textContent='此資料沒有可用的候選結果。';$('selection-stats').textContent='';$('selection-explanation').textContent='欄位數過少或篩選後沒有有效輸入，詳見資料限制。';}
}
function renderSelection(){
  const row=current.selection.find(r=>r.model===$('selection-k').value);if(!row)return;
  const method=$('selection-method').value;
  $('selection-explanation').textContent={All:'保留所有有效輸入作為基準。比較後仍保留全部特徵，也是有效的特徵選擇結果。',KBest:'SelectKBest 使用 f_regression，依各特徵與 Target 的單變量線性關聯評分。',RFE:'RFE 反覆擬合線性回歸，逐步移除較弱特徵；能考慮共同建模後的係數。',LassoSelect:current.id==='flood'?'LassoCV 於訓練資料內選擇 alpha，再保留非零係數。本次保留 20 欄，未強制刪除特徵。':'以標準化 Target 與輸入，在各訓練折使用 Lasso(alpha=0.01) 篩選非零係數；不保證固定數量。'}[method];
  $('selection-stats').innerHTML=`<span>選用 <b>${row.features}</b> 個特徵</span><span>CV RMSE <b>${fmt(row.cv_rmse,6)}</b></span><span>Test RMSE <b>${row.rmse==null?'未評估':fmt(row.rmse,6)}</b></span>`;
  $('selected-features').innerHTML=row.selected_features.map(f=>`<span class="chip">${esc(f)}</span>`).join('');
}
function renderTable(){
  $('model-table').innerHTML='<table><thead><tr><th>模型</th><th>選用特徵</th><th>CV RMSE</th><th>MAE</th><th>MSE</th><th>RMSE</th><th>R²</th><th>Adjusted R²</th></tr></thead><tbody>'+current.models.map(r=>`<tr class="${r.model===current.primary?'primary-row':''}"><td class="model-name">${esc(modelLabel(r.model))}${r.model===current.primary?' ✓ 主模型':''}</td><td>${r.features}</td><td>${fmt(r.cv_rmse,6)}</td><td>${fmt(r.mae,6)}</td><td>${fmt(r.mse,8)}</td><td>${fmt(r.rmse,6)}</td><td>${fmt(r.r2,6)}</td><td>${fmt(r.adjusted_r2,6)}</td></tr>`).join('')+'</tbody></table>';
}
function renderPredictor(){
  $('predictor-summary').textContent=`調整 ${current.predictor.fields.length} 個輸入（預設為訓練集代表值）`;
  $('predictor-inputs').innerHTML=current.predictor.fields.map((f,i)=>`<div><label for="pred-${i}">${esc(f.name)}${current.id==='housing'&&f.name==='date'?'（距 1970-01-01 天數）':''}</label>`+(f.kind==='category'?`<select id="pred-${i}">${f.categories.map(c=>`<option ${c===f.value?'selected':''}>${esc(c)}</option>`).join('')}</select>`:`<input id="pred-${i}" type="number" step="any" value="${f.value}" required><small>訓練範圍 ${fmt(f.minimum)}～${fmt(f.maximum)}</small>`)+`</div>`).join('');
  current.predictor.fields.forEach((_,i)=>$(`pred-${i}`).addEventListener('input',predict));predict();
}
function predict(){
  const values={},warnings=[];
  for(const [i,f] of current.predictor.fields.entries()){
    const input=$(`pred-${i}`);const raw=input.value;
    if(f.kind==='numeric'&&(raw.trim()===''||!Number.isFinite(Number(raw)))){$('prediction-value').textContent='請輸入有效數值';$('prediction-range').textContent='—';$('prediction-warning').textContent=`${f.name} 不可空白或使用無限值。`;return;}
    values[f.name]=f.kind==='numeric'?Number(raw):raw;
    if(f.kind==='numeric'&&(values[f.name]<f.minimum||values[f.name]>f.maximum))warnings.push(f.name);
  }
  let value=current.predictor.intercept;
  for(const t of current.predictor.terms){const x=values[t.raw];value+=t.coefficient*(t.kind==='numeric'?(x-t.mean)/t.scale:Number(x===t.category));}
  if(!Number.isFinite(value)){$('prediction-value').textContent='輸入超出可計算範圍';$('prediction-range').textContent='—';$('prediction-warning').textContent='請縮小輸入數值。';return;}
  $('prediction-value').textContent=fmt(value,6);
  $('prediction-range').textContent=`${fmt(value-current.interval.q,6)} ～ ${fmt(value+current.interval.q,6)}`;
  const outOfBounds=current.id==='flood'&&(value-current.interval.q<0||value+current.interval.q>1);
  $('prediction-warning').textContent=warnings.length?`超出訓練範圍：${warnings.join('、')}。這是外插，預測與區間可靠性可能降低。`:(outOfBounds?'區間超出 0～1，線性模型不保證取值界限；保留原始區間，未裁切。':'數值輸入依訓練時的補值／標準化設定轉換；係數只表示條件關聯，不是因果影響。');
  $('prediction-warning').classList.toggle('error-text',warnings.length>0||outOfBounds);
}
function renderWorkflow(){
  const flood=current.id==='flood',house=current.id==='housing';
  const steps=[['Business Understanding','定義問題',flood?'以合成環境評分預測 FloodProbability，建立可解釋的 benchmark；不宣稱可預警真實洪災。':house?'使用房屋條件與地點解釋成交價，研究可解釋的房價基準；不作為未來市場價格保證。':'以所選數值欄位為預測目標。請自行確認預測目的、欄位可取得時間及資料使用權限。'],
    ['Data Understanding','理解資料',`${count(current.samples)} 筆原始資料、${current.raw_features} 個原始輸入；Target 為 ${current.target}。${house?'每屋僅保留首筆交易。':''}檢查型別、缺失與重複。`],
    ['Data Preparation','準備資料',`訓練 ${count(current.split.train)}、校準 ${count(current.split.calibration)}、測試 ${count(current.split.test)} 筆互斥。補值、編碼與標準化只在訓練折 fit。`],
    ['Modeling','建模與選擇',`在 ${count(current.cv_n)} 筆訓練資料做五折 CV，比較 All、SelectKBest、RFE、Lasso 篩選與正則化。主要模型：${modelLabel(current.primary)}。`],
    ['Evaluation','評估與區間','選定模型後才計算測試 MAE、MSE、RMSE、R²；檢視殘差與假設。校準集建立 95% split conformal，測試集只檢驗涵蓋率。'],
    ['Deployment','使用與重現','提供可載入的 Pipeline、網站即時新樣本預測與自訂 CSV 分析。原始輸入驗證、錯誤提示與下載文件協助重現。']];
  $('crisp-grid').innerHTML=steps.map((s,i)=>`<article class="card crisp-step"><span class="step-number">0${i+1} · ${s[0]}</span><h3>${s[1]}</h3><p>${esc(s[2])}</p></article>`).join('');
  const a=current.assumptions, pvalue=v=>v===0?'小於浮點可表示範圍':v==null?'—':Number(v).toExponential(3);
  $('assumptions').innerHTML=`<p><b>等變異：</b>Breusch–Pagan p=${pvalue(a.breusch_pagan_p)}。應結合殘差圖判斷；大樣本對微小偏差敏感。</p><p><b>常態性：</b>Jarque–Bera p=${pvalue(a.jarque_bera_p)}，殘差偏態 ${fmt(a.residual_skew)}。偏離常態可能影響傳統 OLS 推論；conformal 不要求常態，但仍需要交換性。</p><p><b>獨立性：</b>Durbin–Watson=${fmt(a.durbin_watson)}。資料沒有自然時間順序，不能據此證明誤差獨立。</p><p><b>線性與共線性：</b>需結合殘差與係數解讀。${a.max_vif?`最大 VIF=${fmt(a.max_vif)}。`:`主要模型設計矩陣秩 ${a.design_rank}／${a.design_columns}；秩不足時係數不唯一，預測仍可能可計算。`}</p>`;
  $('limitations').innerHTML=current.notes.map(n=>`<li>${esc(n)}</li>`).join('');
  $('eda-section').hidden=!flood;
}
function render(data){
  current=data;$('analysis-content').hidden=false;$('empty-state').hidden=true;
  const primary=data.models.find(r=>r.model===data.primary); const iv=data.interval;
  $('result-title').textContent=data.title;$('result-subtitle').textContent=data.subtitle;
  $('dataset-description').textContent=data.id==='flood'?'合成環境評分 → FloodProbability':data.id==='housing'?'房屋條件與地點 → 成交價格（USD）':'你的 CSV → 所選連續目標';
  $('dataset-facts').innerHTML=`<div><b>${count(data.samples)}</b><span>原始資料筆數</span></div><div><b>${data.raw_features}</b><span>原始輸入特徵</span></div>`;
  const source=safeUrl(data.source_url);$('source-link').hidden=!source;if(source)$('source-link').href=source;
  const total=data.split.train+data.split.calibration+data.split.test;
  $('split-display').innerHTML=`<div class="splitbar">${['train','calibration','test'].map(k=>`<span style="width:${data.split[k]/total*100}%"></span>`).join('')}</div><div class="splitlabels">${[['訓練','train'],['校準','calibration'],['測試','test']].map(([l,k])=>`<span>${l}<b>${count(data.split[k])}</b></span>`).join('')}</div>`;
  $('cv-setting').textContent=`訓練內 CV：${count(data.cv_n)} 筆 · 5 folds · seed 42`;
  $('metrics').innerHTML=[['測試 RMSE',fmt(primary.rmse,6),`誤差尺度 · ${data.unit}`],['測試 R²',fmt(primary.r2,4),'相對平均值基準的解釋程度'],['區間涵蓋率',pct(iv.coverage),'名目 95% · 完整測試集'],['主要模型特徵',String(primary.features),`${data.raw_features} 個原始輸入 → 編碼／篩選`]].map((a,i)=>`<div class="metric ${i===0?'highlight':''}"><span class="label">${a[0]}</span><strong>${a[1]}</strong><small>${a[2]}</small></div>`).join('');
  $('insight').textContent=data.id==='flood'?'實驗發現：保留全部 20 個特徵的線性模型表現最好；刪至 15 欄使 RMSE 約從 0.0201 升至 0.0324。特徵選擇的目的，是檢驗取捨，而不是一定要刪欄。':`訓練內 CV 選定 ${modelLabel(data.primary)}。測試區間涵蓋 ${pct(iv.coverage)} 的樣本，但平均寬度為 ${fmt(iv.average_width)} ${data.unit}；涵蓋率必須與區間寬度一起閱讀。`;
  $('interval-facts').innerHTML=`<div><small>名目／實際涵蓋率</small><b>95% / ${pct(iv.coverage)}</b></div><div><small>平均區間寬度</small><b>${fmt(iv.average_width,6)}</b></div><div><small>邊界檢查 · 未截斷</small><b>${count(iv.below_zero||0)} 筆下界小於 0${data.id==='flood'?` · ${iv.above_one||0} 筆上界大於 1`:''}</b></div>`;
  $('selection-method').value='All';renderSelectionOptions();renderCharts();renderTable();renderPredictor();renderWorkflow();
  setStatus(`分析已完成 · ${modelLabel(data.primary)} · CV 選模／獨立測試 · ${data.id==='custom'?'本次實際執行':'載入實際計算成果，無須重新訓練'}`);
}
async function chooseProblem(){
  const token=++generation;++loadGeneration;const problem=$('problem').value;setBusy(false);dataset=null;
  $('custom-panel').hidden=problem!=='custom';$('analysis-content').hidden=true;$('schema').hidden=true;$('source-link').hidden=true;
  $('empty-state').hidden=problem!=='custom';['dataset-facts','split-display','cv-setting','dataset-description'].forEach(id=>$(id).textContent='');
  if(problem==='custom'){setStatus('先載入資料，再選擇 Target 與特徵。');return;}
  setStatus('正在載入已驗證的分析成果…','busy');
  try{const r=await fetch(`data/${problem}.json`);if(!r.ok)throw new Error('讀取分析成果失敗。');const d=await r.json();if(token===generation)render(d);}catch(e){if(token===generation)setStatus(e.message,'error');}
}
function targetChanged(){
  const target=$('target').value;
  $('analysis-content').hidden=true;$('empty-state').hidden=false;
  $('feature-checks').innerHTML=dataset.columns.filter(c=>c.name!==target&&!/^(id|index)$|_id$/i.test(c.name)).map(c=>`<label><input type="checkbox" value="${esc(c.name)}" checked><span>${esc(c.name)} · ${c.kind==='numeric'?'數值':'類別'}</span></label>`).join('');
  $('run-analysis').disabled=busy;
}
function showSchema(data){
  dataset=data;$('schema').hidden=false;$('dataset-facts').innerHTML=`<div><b>${count(data.rows)}</b><span>資料筆數</span></div><div><b>${data.columns.length}</b><span>總欄位數</span></div>`;
  $('target').innerHTML=data.columns.filter(c=>c.kind==='numeric'&&!/^(id|index)$|_id$/i.test(c.name)).map(c=>`<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('');
  if([...$('target').options].some(o=>o.value===data.target))$('target').value=data.target;
  $('csv-preview').innerHTML='<table><thead><tr>'+data.columns.map(c=>`<th>${esc(c.name)}</th>`).join('')+'</tr></thead><tbody>'+data.preview.map(row=>'<tr>'+data.columns.map(c=>`<td>${esc(row[c.name])}</td>`).join('')+'</tr>').join('')+'</tbody></table>';
  targetChanged();setStatus(`已載入 ${count(data.rows)} 筆資料。請確認 Target 與輸入欄位，再執行分析。`);
}
async function loadData(file){
  const token=generation, loadToken=++loadGeneration;setBusy(true);$('schema').hidden=true;$('analysis-content').hidden=true;$('empty-state').hidden=false;dataset=null;setStatus('正在讀取 CSV…','busy');
  try{let result;if(file){const form=new FormData();form.append('file',file);result=await api('/api/upload',{method:'POST',body:form});}else{result=await api('/api/url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:$('csv-url').value.trim()})});}if(token===generation&&loadToken===loadGeneration)showSchema(result);}catch(e){if(token===generation&&loadToken===loadGeneration)setStatus(e.message,'error');}finally{if(token===generation&&loadToken===loadGeneration)setBusy(false);}
}
async function runAnalysis(){
  if(!dataset||busy)return;const token=generation,loadToken=loadGeneration;const started=Date.now();setBusy(true);$('analysis-content').hidden=true;setStatus('正在進行五折 CV 與特徵選擇…','busy');
  try{const job=await api('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset:dataset.id,target:$('target').value,features:[...document.querySelectorAll('#feature-checks input:checked')].map(e=>e.value)})});
    while(token===generation&&loadToken===loadGeneration){await new Promise(resolve=>setTimeout(resolve,900));if(token!==generation||loadToken!==loadGeneration)break;const result=await api(`/api/jobs/${job.job}`);if(result.status==='error')throw new Error(result.error);if(result.status==='done'){if(token===generation&&loadToken===loadGeneration)render(result.result);break;}setStatus(`正在分析 · ${Math.round((Date.now()-started)/1000)} 秒 · 資料較多時請稍候。`,'busy');if(Date.now()-started>600000)throw new Error('分析超過 10 分鐘；請減少資料欄位後再試。');}
  }catch(e){if(token===generation&&loadToken===loadGeneration)setStatus(e.message,'error');}finally{if(token===generation&&loadToken===loadGeneration)setBusy(false);}
}
async function init(){
  await document.fonts.load('14px HW2CJK');
  await document.fonts.ready;
  Chart.defaults.font.family='HW2CJK, system-ui, "Noto Sans TC", sans-serif';Chart.defaults.color='#647582';
  $('problem').addEventListener('change',chooseProblem);$('selection-method').addEventListener('change',renderSelectionOptions);$('selection-k').addEventListener('change',renderSelection);
  $('reset-inputs').addEventListener('click',renderPredictor);$('target').addEventListener('change',()=>{++loadGeneration;setBusy(false);targetChanged();});$('feature-checks').addEventListener('change',()=>{++loadGeneration;setBusy(false);$('analysis-content').hidden=true;$('empty-state').hidden=false;setStatus('特徵已變更，請重新執行分析。');});
  $('load-url').addEventListener('click',()=>loadData());$('csv-file').addEventListener('change',e=>{if(e.target.files[0])loadData(e.target.files[0]);});$('load-example').addEventListener('click',()=>{$('csv-url').value='https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv';loadData();});$('run-analysis').addEventListener('click',runAnalysis);
  $('api-base').value=apiBase;$('connect').addEventListener('click',async()=>{const requested=$('api-base').value.trim();if(requested&&!safeUrl(requested)){setStatus('請輸入有效 HTTP(S) 服務網址。','error');return;}apiBase=requested.replace(/\/$/,'');localStorage.setItem('hw2-api-base',apiBase);try{const r=await api('/api/health');if(r.service!=='hw2-regression')throw new Error('這個網址不是 HW2 分析服務。');setStatus('分析服務已連線，可以載入自訂 CSV。');}catch(e){setStatus(e.message,'error');}});
  if(safeUrl(config.repository)){$('github').href=config.repository;$('github').hidden=false;}
  try{const r=await fetch('data/research.json');if(!r.ok)throw new Error('研究摘要載入失敗');const research=await r.json();document.title=`迴歸研究室｜HW2 · ${research.student_id}`;document.querySelector('.student').textContent=research.student_id;document.querySelector('footer span').textContent=`${research.student_id} · Multiple Linear Regression HW2`;document.querySelector('.downloads a[href$=".ipynb"]').href=`downloads/${research.student_id}_hw2.ipynb`;$('notebooklm-summary').textContent=research.summary;$('source-list').innerHTML=research.sources.filter(s=>safeUrl(s.url)).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a>`).join('');}catch(e){$('notebooklm-summary').textContent='摘要暫時無法載入，請閱讀下載報告。';}
  const figs=[['01_target_distribution','Target 分布'],['02_feature_distributions','20 個特徵分布'],['03_correlation_heatmap','Pearson 相關矩陣'],['04_feature_target','特徵與 Target'],['05_boxplots','離群值與箱形圖'],['07_residual_distribution_qq','殘差分布與 Q-Q']];
  $('eda-gallery').innerHTML=figs.map(([file,label])=>`<a href="figures/${file}.png" target="_blank" rel="noopener"><img loading="lazy" src="figures/${file}.png" alt="${label}"><span>${label} ↗</span></a>`).join('');
  await chooseProblem();
}
init().catch(e=>setStatus(`頁面初始化失敗：${e.message}`,'error'));
