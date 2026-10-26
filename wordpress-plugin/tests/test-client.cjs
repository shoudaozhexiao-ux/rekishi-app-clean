const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const C=require('../gozai-history/assets/core.js');
for(const t of JSON.parse(fs.readFileSync(path.join(__dirname,'parity.json'),'utf8'))){assert.deepEqual(C.compareEvents(t.earlier,t.later),t.pairs);assert.deepEqual(C.forecastFromHistory(t.year,t.history),t.forecasts);}
assert.deepEqual(C.yearRanges(2026),{years:Array.from({length:20},(_,i)=>1946+i),forecastYear:1966});
assert.deepEqual(C.yearRanges(2027).years.slice(-1),[1966]);
assert.throws(()=>C.compareEvents({year:1965,events:[]},{year:2026,events:[]}));
assert.throws(()=>C.forecastFromHistory(2026,{year:1965,events:[]}));
assert.deepEqual(C.compareEvents({year:1965,events:['映画が公開']},{year:2025,events:['銀行が合併']}),[]);
console.log('PASS: 45 Python parity cases, year rollover ranges, unrelated events, exact-60-year guards');
