const assert=require('node:assert/strict'),fs=require('node:fs');
let JSDOM;try{({JSDOM}=require('jsdom'));}catch(_){({JSDOM}=require('../../native-aquarium/node_modules/jsdom'));}
const core=fs.readFileSync(__dirname+'/../gozai-history/assets/core.js','utf8'),app=fs.readFileSync(__dirname+'/../gozai-history/assets/app.js','utf8');
const flush=async()=>{for(let i=0;i<6;i++)await new Promise(r=>setImmediate(r));};
async function main(){
 let current=2026,requests=[],failJapan=false,intervals=[],slowPast=null,delay=false,missing=false;
 const RealDate=Date;
 const dom=new JSDOM('<section id="history-test" class="gh-app" data-rest="https://gozaigozai.com/wp-json/gozai-history/v1/"></section>',{url:'https://gozaigozai.com/ai-rekishi/',runScripts:'dangerously',beforeParse(w){
  w.Date=class extends RealDate{constructor(...args){super(...(args.length?args:[`${current}-10-26T12:00:00Z`]));}};
  w.setInterval=fn=>{intervals.push(fn);return intervals.length;};
  w.fetch=async(url,options)=>{
   const u=new URL(url);requests.push(u);let body,ok=true;
   if(u.pathname.endsWith('/news'))body={items:[{title:'<img src=x onerror=alert(1)>',url:'javascript:alert(1)'},{title:'ニュース',url:'https://example.com/news'}],retrieved_at:'2026-10-26T00:00:00Z'};
   else{
    const year=Number(u.searchParams.get('year')),scope=u.searchParams.get('scope');
    if(delay&&year===1965){await new Promise(r=>{slowPast=r;});}
    if(missing&&scope==='japan'){ok=false;body={code:'gh_missing',message:'Wikipediaに個別記事がありません。比較する出来事を「世界」に切り替えてください。'};}
    else if(failJapan&&scope==='japan'){ok=false;body={message:'日本の取得に失敗しました'};}
    else body={year,scope,title:`${year}年`,events:['鉄道が開通','映画が公開','<img src=x onerror=alert(1)>鉄道の開通'],revision_url:'https://ja.wikipedia.org/w/index.php?oldid=1',retrieved_at:'2026-10-26T00:00:00Z'};
   }
   return {ok,json:async()=>body};
  };
 }});
 const w=dom.window,d=w.document;
 const script=d.createElement('script');script.textContent=core+'\n'+app;d.body.append(script);await flush();
 assert.equal(d.querySelectorAll('.gh-year-select option').length,20);assert.equal(d.querySelector('.gh-year-select').value,'1965');
 assert.equal(d.querySelectorAll('.gh-table tbody tr').length,3);assert.equal(d.querySelectorAll('.gh-card').length,4);
 assert.equal(d.querySelectorAll('.gh-app img').length,0,'external strings cannot inject HTML');
 assert.equal(d.querySelectorAll('a[href^="javascript:"]').length,0);
 assert.equal(requests.length,5);
 const form=d.querySelector('form'),q=d.querySelector('input');q.value='宇宙 & 科学';form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(requests.at(-1).searchParams.get('q'),'宇宙 & 科学');
 failJapan=true;d.querySelector('.gh-scope').value='japan';d.querySelector('.gh-scope').dispatchEvent(new w.Event('change'));await flush();assert.match(d.querySelector('.gh-comparison').textContent,/日本の取得に失敗/);assert(d.querySelector('.gh-forecast .gh-card'),'world forecast survives Japanese failure');
 failJapan=false;missing=true;d.querySelector('.gh-year-select').value='1946';d.querySelector('.gh-year-select').dispatchEvent(new w.Event('change'));assert.doesNotMatch(d.querySelector('.gh-comparison').textContent,/1965年の出来事/,'old results cleared during new request');await flush();assert.match(d.querySelector('.gh-comparison').textContent,/個別記事がありません/);assert.match(d.querySelector('.gh-comparison').textContent,/世界/);assert(d.querySelector('.gh-forecast .gh-card'),'available world forecast survives missing article');missing=false;current=2027;w.dispatchEvent(new w.Event('focus'));await flush();assert.equal(d.querySelector('.gh-year-select').value,'1966');assert.match(d.querySelector('.gh-year').textContent,/2027/);assert(requests.some(u=>u.searchParams.get('year')==='1967'));
 // Out-of-order fetches must never replace the latest selected year.
 current=2026;delay=true;w.dispatchEvent(new w.Event('focus'));await flush();d.querySelector('.gh-year-select').value='1964';d.querySelector('.gh-year-select').dispatchEvent(new w.Event('change'));await flush();assert.match(d.querySelector('.gh-comparison h4').textContent,/1964/);delay=false;slowPast();await flush();assert.match(d.querySelector('.gh-comparison h4').textContent,/1964/);
 assert.equal(d.querySelector('.gh-refresh').disabled,false);
 dom.window.close();console.log('PASS: UI controls, 4 independent sources, safe text/URLs, independent news, partial failure, live year rollover, stale-response protection');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
