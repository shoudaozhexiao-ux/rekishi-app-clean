(function(root,factory){'use strict';var api=factory();if(typeof module==='object'&&module.exports){module.exports=api;}else{root.GozaiHistoryCore=api;}})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const THEMES = {
  "外交・政治": {
    "words": [
      "条約",
      "協定",
      "外交",
      "国交",
      "首脳",
      "選挙",
      "内閣",
      "憲法",
      "大統領",
      "国連"
    ],
    "forecast": "国際関係や政治制度の見直しが話題になり、対話や協定、政策の調整が注目される可能性があります。"
  },
  "科学・技術": {
    "words": [
      "技術",
      "科学",
      "開発",
      "コンピュータ",
      "電子",
      "衛星",
      "宇宙",
      "ロケット",
      "通信",
      "研究"
    ],
    "forecast": "新技術の実用化や通信・宇宙分野の開発が進み、利便性と安全性の両立が課題になる可能性があります。"
  },
  "経済・産業": {
    "words": [
      "経済",
      "銀行",
      "金融",
      "通貨",
      "貿易",
      "工場",
      "企業",
      "合併",
      "物価",
      "輸出",
      "発売"
    ],
    "forecast": "物価や貿易、企業活動の変化に対応するため、商品や事業の見直しが広がる可能性があります。"
  },
  "交通・インフラ": {
    "words": [
      "鉄道",
      "新幹線",
      "道路",
      "空港",
      "航空",
      "開通",
      "高速",
      "交通",
      "自動車",
      "橋"
    ],
    "forecast": "交通網や移動サービスの整備が注目され、老朽化対策と移動の利便性を両立する取り組みが進む可能性があります。"
  },
  "文化・メディア": {
    "words": [
      "映画",
      "音楽",
      "テレビ",
      "放送",
      "出版",
      "漫画",
      "文化",
      "芸術",
      "演劇",
      "博覧会"
    ],
    "forecast": "新しい作品や表現、情報の届け方が広がり、世代や国境を越えた文化交流が話題になる可能性があります。"
  },
  "スポーツ": {
    "words": [
      "五輪",
      "オリンピック",
      "大会",
      "野球",
      "サッカー",
      "優勝",
      "競技",
      "選手",
      "ワールドカップ"
    ],
    "forecast": "競技大会や選手の活躍が交流のきっかけとなり、競技環境や大会運営の改善が注目される可能性があります。"
  },
  "医療・健康": {
    "words": [
      "医療",
      "病院",
      "疾病",
      "感染",
      "ワクチン",
      "健康",
      "治療",
      "保健",
      "ウイルス"
    ],
    "forecast": "予防や医療体制の充実が重視され、検診や健康管理、医療へのアクセス改善が進む可能性があります。"
  },
  "環境・エネルギー": {
    "words": [
      "環境",
      "公害",
      "汚染",
      "原子力",
      "発電",
      "電力",
      "石油",
      "エネルギー",
      "気候"
    ],
    "forecast": "エネルギーの安定供給と環境保全を両立するため、設備や暮らし方の見直しが注目される可能性があります。"
  },
  "防災・安全": {
    "words": [
      "地震",
      "台風",
      "洪水",
      "火災",
      "事故",
      "墜落",
      "災害",
      "噴火",
      "爆発"
    ],
    "forecast": "過去の災害や事故を教訓とした点検、避難計画、安全対策が改めて重視される可能性があります。"
  },
  "教育・暮らし": {
    "words": [
      "教育",
      "学校",
      "大学",
      "学生",
      "住宅",
      "福祉",
      "労働",
      "人口",
      "出生"
    ],
    "forecast": "学びや働き方、生活支援の仕組みが見直され、地域や世代ごとの課題への対応が注目される可能性があります。"
  },
  "紛争・平和": {
    "words": [
      "戦争",
      "紛争",
      "停戦",
      "軍",
      "戦闘",
      "侵攻",
      "平和",
      "独立"
    ],
    "forecast": "安全保障や平和への取り組みが議論され、対立の緩和や協力体制の調整が課題になる可能性があります。"
  }
};
function yearRanges(currentYear){
  if(!Number.isInteger(currentYear))throw new Error('年の形式が正しくありません。');
  return {years:Array.from({length:20},(_,i)=>currentYear-80+i),forecastYear:currentYear-60};
}
function classify(event){
  const result=new Map();
  for(const [name,theme] of Object.entries(THEMES)){
    const words=new Set(theme.words.filter(w=>event.includes(w)));
    if(words.size)result.set(name,words);
  }
  return result;
}
function compareEvents(earlier,later,limit=10){
  if(later.year!==earlier.year+60)throw new Error('比較年は正確に60年差である必要があります。');
  if(limit<=0)return [];
  const candidates=[];
  earlier.events.forEach((left,i)=>{
    const lt=classify(left);
    later.events.forEach((right,j)=>{
      const rt=classify(right);
      const shared=[...lt.keys()].filter(k=>rt.has(k)).sort();
      if(!shared.length)return;
      const words=new Set();
      shared.forEach(k=>lt.get(k).forEach(w=>{if(rt.get(k).has(w))words.add(w);}));
      candidates.push({score:shared.length+words.size*3,i,j,themes:shared,words:[...words].sort()});
    });
  });
  candidates.sort((a,b)=>b.score-a.score||a.i-b.i||a.j-b.j);
  const leftUsed=new Set(),rightUsed=new Set(),pairs=[];
  for(const c of candidates){
    if(leftUsed.has(c.i)||rightUsed.has(c.j))continue;
    pairs.push({past:earlier.events[c.i],later:later.events[c.j],themes:c.themes,words:c.words});
    leftUsed.add(c.i);rightUsed.add(c.j);if(pairs.length>=limit)break;
  }
  return pairs;
}
function forecastFromHistory(currentYear,history,limit=3){
  if(history.year!==currentYear-60)throw new Error('今年の正確に60年前の資料が必要です。');
  const groups=Object.keys(THEMES).map((name,index)=>({name,index,events:[]}));
  history.events.forEach(event=>{const labels=classify(event);groups.forEach(g=>{if(labels.has(g.name))g.events.push(event);});});
  return groups.filter(g=>g.events.length).sort((a,b)=>b.events.length-a.events.length||a.index-b.index).slice(0,Math.max(0,limit)).map(g=>({
    year:currentYear,theme:g.name,prediction:`${currentYear}年には、${THEMES[g.name].forecast}`,
    evidence:g.events.slice(0,2),reason:`${history.year}年の資料に「${g.name}」に関する出来事があるため、同じ主題を今年に当てはめています。`
  }));
}
return {yearRanges,compareEvents,forecastFromHistory};
});
