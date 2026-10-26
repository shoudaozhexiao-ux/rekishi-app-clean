(function(){
'use strict';
const C=window.GozaiHistoryCore;
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function link(text,url){const a=node('a',text);try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))throw new Error();a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}catch(_){return node('span',text);}return a;}
function init(root){
 if(root.dataset.ready)return;
 root.dataset.ready='true';
 if(!C){root.replaceChildren(node('p','歴史アプリを読み込めませんでした。ページを再読み込みしてください。','gh-error'));return;}
 const prefix=root.id,api=root.dataset.rest;
 let year=new Date().getFullYear(),historyTicket=0,newsTicket=0,historyAbort=null,newsAbort=null;
 root.innerHTML=`<header class="gh-cover"><p class="gh-kicker">古年譜 ・ 預言之書</p><h2>六十年の連環</h2><p>歴史をひもとき、今年を想う。</p><span class="gh-year"></span></header>
 <div class="gh-controls"><div><label for="${prefix}-year">比較する年</label><select id="${prefix}-year" class="gh-year-select"></select></div><div><label for="${prefix}-scope">比較する出来事</label><select id="${prefix}-scope" class="gh-scope"><option value="world">世界</option><option value="japan">日本</option></select></div><button type="button" class="gh-refresh">資料を再読み込み</button></div>
 <p class="gh-help">歴史資料は最大1時間、ニュースは最大15分保存します。再読み込みでも保存期間内は同じ資料を使います。</p>
 <p class="gh-status" role="status" aria-live="polite"></p>
 <section class="gh-comparison" aria-label="過去と60年後の比較"></section>
 <section class="gh-forecast" aria-label="今年の予想"></section>
 <section class="gh-news"><h3>参　現在の瓦版</h3><form class="gh-news-form"><label for="${prefix}-query">ニュース検索</label><div class="gh-search-row"><input id="${prefix}-query" type="search" maxlength="80" value="人工知能" required><button type="submit">検索</button></div></form><p class="gh-news-status" role="status" aria-live="polite"></p><div class="gh-news-results"></div></section>`;
 const select=root.querySelector('.gh-year-select'),scope=root.querySelector('.gh-scope'),status=root.querySelector('.gh-status');
 const comparison=root.querySelector('.gh-comparison'),forecast=root.querySelector('.gh-forecast');
 const refresh=root.querySelector('.gh-refresh'),newsStatus=root.querySelector('.gh-news-status'),newsResults=root.querySelector('.gh-news-results');
 function setYears(){const r=C.yearRanges(year);select.replaceChildren(...r.years.map(y=>{const o=node('option',`${y}年 ↔ ${y+60}年`);o.value=String(y);return o;}));select.value=String(r.years[r.years.length-1]);root.querySelector('.gh-year').textContent=`${year}年の巻`;}
 function message(error){if(error.name==='AbortError')return '';return error.message||'資料を取得できません。時間をおいて再試行してください。';}
 async function request(path,params,signal){
  const url=new URL(api,window.location.href);url.pathname=url.pathname.replace(/\/$/,'')+'/'+path;
  // rest_url can use ?rest_route= on sites without pretty permalinks.
  if(url.searchParams.has('rest_route')){const route=url.searchParams.get('rest_route').replace(/\/$/,'');url.pathname=new URL(api,window.location.href).pathname;url.searchParams.set('rest_route',route+'/'+path);}
  Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,String(v)));
  let response;
  try{response=await fetch(url.href,{signal,credentials:'omit',headers:{Accept:'application/json'}});}catch(e){if(e.name==='AbortError')throw e;throw new Error('通信できませんでした。接続を確認して再試行してください。');}
  let data;try{data=await response.json();}catch(_){throw new Error('サーバーから資料を読み取れませんでした。');}
  if(!response.ok)throw new Error(typeof data.message==='string'?data.message:'資料を取得できませんでした。');
  if(path==='history'&&(!Array.isArray(data.events)||!data.events.every(x=>typeof x==='string')||!Number.isInteger(data.year)))throw new Error('歴史資料の形式を確認できません。');
  return data;
 }
 function source(data){
  const box=node('div',undefined,'gh-source');box.append(link(`出典：Wikipedia「${data.title}」`,data.revision_url));
  const time=new Date(data.retrieved_at);const formatted=Number.isNaN(time.getTime())?'不明':time.toLocaleString('ja-JP');
  box.append(node('p',`取得：${formatted} ／「出来事」節より抜粋・CC BY-SA${data.stale?' ／現在は更新できないため、保存済み資料を表示しています。':''}`));return box;
 }
 function events(data,label){const details=node('details');details.append(node('summary',label));const list=node('ol');data.events.forEach(t=>list.append(node('li',t)));details.append(list,source(data));return details;}
 function renderComparison(past,later,failures){
  comparison.replaceChildren(node('h3','壱　六十年を隔てた出来事'),node('h4',`${scope.value==='japan'?'日本':'世界'}：${select.value}年 ↔ ${Number(select.value)+60}年`));
  comparison.append(node('p','共通テーマによる対応候補です。因果関係や60年周期の証明ではありません。','gh-help'));
  if(past&&later){
   const pairs=C.compareEvents(past,later);
   if(pairs.length){
    const table=node('table',undefined,'gh-table');table.setAttribute('aria-label','60年差の出来事の比較');
    const head=node('thead'),headRow=node('tr');[`${past.year}年の出来事`,`${later.year}年の出来事`,'共通テーマ'].forEach(t=>{const th=node('th',t);th.scope='col';headRow.append(th);});head.append(headRow);const body=node('tbody');
    pairs.forEach(p=>{const tr=node('tr');[p.past,p.later,`${p.themes.join('・')}\n共通する語：${p.words.join('・')||'同じ分類の異なる語'}`].forEach((text,i)=>{const td=node('td',text);td.dataset.label=[`${past.year}年`,`${later.year}年`,'共通テーマ'][i];tr.append(td);});body.append(tr);});table.append(head,body);comparison.append(table);
   }else comparison.append(node('p','取得した出来事に共通テーマが見つかりませんでした。別の年や地域を選べます。'));
  }
  const columns=node('div',undefined,'gh-columns');
  for(const [data,key,label] of [[past,'past',`${select.value}年`],[later,'later',`${Number(select.value)+60}年`]])columns.append(data?events(data,`${label}の取得した出来事`):node('p',`${label}：${failures[key]||'資料を取得できません。'}`,'gh-error'));
  comparison.append(columns);
 }
 function renderForecast(japan,world,failures){
  forecast.replaceChildren(node('h3',`弐　${year}年を想う`),node('p',`${year-60}年の出来事を手掛かりに。予想文はテーマ別のルールによる仮説です。`,'gh-help'));
  const columns=node('div',undefined,'gh-columns');
  for(const [data,key,label] of [[japan,'japan','🇯🇵 日本'],[world,'world','🌏 世界']]){
   const col=node('div');col.append(node('h4',label));
   if(!data)col.append(node('p',failures[key]||'資料を取得できません。','gh-error'));
   else{
    const predictions=C.forecastFromHistory(year,data);
    if(!predictions.length)col.append(node('p','分類できるテーマがないため、予想を表示できません。'));
    predictions.forEach(p=>{const card=node('article',undefined,'gh-card');card.append(node('h5',p.theme),node('p',p.prediction));const detail=node('details');detail.append(node('summary','過去の手掛かりと理由を読む'),node('p',p.reason));const ul=node('ul');p.evidence.forEach(t=>ul.append(node('li',t)));detail.append(ul);card.append(detail);col.append(card);});
    col.append(events(data,`根拠資料：${year-60}年の出来事`));
   }
   columns.append(col);
  }
  forecast.append(columns,node('p','世界欄には日本の出来事が含まれる場合があります。予想の的中や未来の出来事を保証するものではありません。','gh-help'));
 }
 async function loadHistory(){
  const ticket=++historyTicket;if(historyAbort)historyAbort.abort();historyAbort=new AbortController();const signal=historyAbort.signal;
  status.textContent='歴史資料を取得しています…';comparison.setAttribute('aria-busy','true');forecast.setAttribute('aria-busy','true');refresh.disabled=true;
  const old=Number(select.value),region=scope.value;
  const inputs=[['past',old,region],['later',old+60,region],['japan',year-60,'japan'],['world',year-60,'world']];
  const results={},failures={};
  await Promise.all(inputs.map(async([key,y,s])=>{try{const data=await request('history',{year:y,scope:s},signal);if(data.year!==y||data.scope!==s)throw new Error('指定した年・地域と資料が一致しません。');results[key]=data;}catch(e){failures[key]=message(e);}}));
  if(ticket!==historyTicket)return;
  renderComparison(results.past,results.later,failures);renderForecast(results.japan,results.world,failures);
  comparison.removeAttribute('aria-busy');forecast.removeAttribute('aria-busy');refresh.disabled=false;
  const failed=Object.values(failures).filter(Boolean).length;status.textContent=failed?'一部の資料を取得できませんでした。取得できた資料を表示しています。':'歴史資料を表示しました。';
 }
 async function loadNews(){
  const query=root.querySelector('input[type="search"]').value.trim();if(!query){newsStatus.textContent='検索語を入力してください。';return;}
  const ticket=++newsTicket;if(newsAbort)newsAbort.abort();newsAbort=new AbortController();newsStatus.textContent='ニュースを取得しています…';newsResults.replaceChildren();
  try{
   const data=await request('news',{q:query},newsAbort.signal);if(ticket!==newsTicket)return;
   if(!Array.isArray(data.items))throw new Error('ニュースの形式を確認できません。');
   const list=node('ul');data.items.slice(0,5).forEach(item=>{const li=node('li');li.append(link(item.title,item.url));list.append(li);});newsResults.append(list);
   newsStatus.textContent=data.items.length?`取得：${new Date(data.retrieved_at).toLocaleString('ja-JP')}${data.stale?' ／保存済みニュースを表示しています。':''}`:'該当するニュースがありません。';
  }catch(e){if(ticket===newsTicket)newsStatus.textContent=message(e);}
 }
 function rollover(){const next=new Date().getFullYear();if(next!==year){year=next;setYears();loadHistory();}}
 select.addEventListener('change',loadHistory);scope.addEventListener('change',loadHistory);refresh.addEventListener('click',loadHistory);
 root.querySelector('form').addEventListener('submit',e=>{e.preventDefault();loadNews();});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)rollover();});window.addEventListener('focus',rollover);setInterval(rollover,60000);
 setYears();loadHistory();loadNews();
}
function boot(){document.querySelectorAll('.gh-app[data-rest]').forEach(init);}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
