"""Fetch public history and compare events using local, free rules."""

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

USER_AGENT = "RekishiAI/1.0 (https://github.com/shoudaozhexiao-ux/rekishi-app-clean)"


class ServiceError(Exception):
    """A public error message that never includes credentials or raw responses."""


def read_json(request, timeout=25):
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 429:
            message = "利用上限または混雑により取得できません。時間をおいて再試行してください。"
        else:
            message = f"外部サービスへの接続に失敗しました（HTTP {exc.code}）。"
        raise ServiceError(message) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ServiceError("外部サービスからデータを取得できません。再試行してください。") from None


class EventParser(HTMLParser):
    """Read only the events section; retain month labels in nested lists."""

    def __init__(self):
        super().__init__()
        self.active = False
        self.heading = None
        self.items = []
        self.events = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "sup"):
            self.skip += 1
        if tag == "h2":
            self.heading = []
        if tag == "li" and self.active:
            if self.items:
                self.items[-1]["children"] = True
            self.items.append({"text": [], "children": False})

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading.append(data)
        elif self.items:
            self.items[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "sup"):
            self.skip = max(0, self.skip - 1)
        if tag == "h2" and self.heading is not None:
            label = "".join(self.heading).strip()
            self.active = label.startswith(("できごと", "出来事", "Events"))
            self.heading = None
        if tag == "li" and self.items:
            item = self.items.pop()
            if not item["children"]:
                parts = ["".join(parent["text"]) for parent in self.items]
                parts.append("".join(item["text"]))
                text = re.sub(r"\s+", " ", " ".join(parts)).strip()
                if len(text) >= 8:
                    self.events.append(text[:600])


def fetch_history(year, scope="world"):
    """No persistent cache: obtain the selected year's latest revision each time."""
    if scope not in ("japan", "world"):
        raise ValueError("Unknown history scope")
    title = f"{year}年の日本" if scope == "japan" else f"{year}年"
    params = urlencode({
        "action": "parse", "page": title, "prop": "text|revid",
        "format": "json", "formatversion": 2, "redirects": 1,
        "disableeditsection": 1,
    })
    request = Request(
        f"https://ja.wikipedia.org/w/api.php?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    data = read_json(request)
    parsed = data.get("parse", {})
    html = parsed.get("text", "")
    if not isinstance(html, str):
        raise ServiceError("歴史データの形式を読み取れません。")
    parser = EventParser()
    parser.feed(html)
    events = list(dict.fromkeys(parser.events))
    if not events:
        raise ServiceError(f"{year}年の出来事を取得できません。別の年を選ぶか再試行してください。")
    # Spread the sample over the whole year instead of taking only January.
    if len(events) > 36:
        events = [events[round(i * (len(events) - 1) / 35)] for i in range(36)]
    revision = parsed.get("revid")
    url = f"https://ja.wikipedia.org/wiki/{quote(title)}"
    return {
        "year": year, "scope": scope, "title": title, "events": events, "revision": revision,
        "url": url,
        "revision_url": f"https://ja.wikipedia.org/w/index.php?oldid={revision}" if revision else url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# 共通する語から主題を分類する。史実の因果関係を証明するものではない。
THEMES = {
    "外交・政治": {
        "words": ("条約", "協定", "外交", "国交", "首脳", "選挙", "内閣", "憲法", "大統領", "国連"),
        "forecast": "国際関係や政治制度の見直しが話題になり、対話や協定、政策の調整が注目される可能性があります。",
    },
    "科学・技術": {
        "words": ("技術", "科学", "開発", "コンピュータ", "電子", "衛星", "宇宙", "ロケット", "通信", "研究"),
        "forecast": "新技術の実用化や通信・宇宙分野の開発が進み、利便性と安全性の両立が課題になる可能性があります。",
    },
    "経済・産業": {
        "words": ("経済", "銀行", "金融", "通貨", "貿易", "工場", "企業", "合併", "物価", "輸出", "発売"),
        "forecast": "物価や貿易、企業活動の変化に対応するため、商品や事業の見直しが広がる可能性があります。",
    },
    "交通・インフラ": {
        "words": ("鉄道", "新幹線", "道路", "空港", "航空", "開通", "高速", "交通", "自動車", "橋"),
        "forecast": "交通網や移動サービスの整備が注目され、老朽化対策と移動の利便性を両立する取り組みが進む可能性があります。",
    },
    "文化・メディア": {
        "words": ("映画", "音楽", "テレビ", "放送", "出版", "漫画", "文化", "芸術", "演劇", "博覧会"),
        "forecast": "新しい作品や表現、情報の届け方が広がり、世代や国境を越えた文化交流が話題になる可能性があります。",
    },
    "スポーツ": {
        "words": ("五輪", "オリンピック", "大会", "野球", "サッカー", "優勝", "競技", "選手", "ワールドカップ"),
        "forecast": "競技大会や選手の活躍が交流のきっかけとなり、競技環境や大会運営の改善が注目される可能性があります。",
    },
    "医療・健康": {
        "words": ("医療", "病院", "疾病", "感染", "ワクチン", "健康", "治療", "保健", "ウイルス"),
        "forecast": "予防や医療体制の充実が重視され、検診や健康管理、医療へのアクセス改善が進む可能性があります。",
    },
    "環境・エネルギー": {
        "words": ("環境", "公害", "汚染", "原子力", "発電", "電力", "石油", "エネルギー", "気候"),
        "forecast": "エネルギーの安定供給と環境保全を両立するため、設備や暮らし方の見直しが注目される可能性があります。",
    },
    "防災・安全": {
        "words": ("地震", "台風", "洪水", "火災", "事故", "墜落", "災害", "噴火", "爆発"),
        "forecast": "過去の災害や事故を教訓とした点検、避難計画、安全対策が改めて重視される可能性があります。",
    },
    "教育・暮らし": {
        "words": ("教育", "学校", "大学", "学生", "住宅", "福祉", "労働", "人口", "出生"),
        "forecast": "学びや働き方、生活支援の仕組みが見直され、地域や世代ごとの課題への対応が注目される可能性があります。",
    },
    "紛争・平和": {
        "words": ("戦争", "紛争", "停戦", "軍", "戦闘", "侵攻", "平和", "独立"),
        "forecast": "安全保障や平和への取り組みが議論され、対立の緩和や協力体制の調整が課題になる可能性があります。",
    },
}


def year_ranges(current_year):
    return list(range(current_year - 80, current_year - 60)), current_year - 60


def classify(event):
    return {
        name: {word for word in theme["words"] if word in event}
        for name, theme in THEMES.items()
        if any(word in event for word in theme["words"])
    }


def compare_events(earlier, later, limit=10):
    if limit <= 0:
        return []
    if later["year"] != earlier["year"] + 60:
        raise ValueError("Comparison must be exactly 60 years apart")
    candidates = []
    for left_index, left in enumerate(earlier["events"]):
        left_themes = classify(left)
        for right_index, right in enumerate(later["events"]):
            right_themes = classify(right)
            shared = set(left_themes) & set(right_themes)
            if not shared:
                continue
            words = set().union(*(left_themes[name] & right_themes[name] for name in shared))
            score = len(shared) + len(words) * 3
            candidates.append((score, left_index, right_index, sorted(shared), sorted(words)))
    candidates.sort(key=lambda pair: (-pair[0], pair[1], pair[2]))
    used_left, used_right, pairs = set(), set(), []
    for _, left_index, right_index, themes, words in candidates:
        if left_index in used_left or right_index in used_right:
            continue
        pairs.append({
            "past": earlier["events"][left_index], "later": later["events"][right_index],
            "themes": themes, "words": words,
        })
        used_left.add(left_index)
        used_right.add(right_index)
        if len(pairs) >= limit:
            break
    return pairs


def forecast_from_history(current_year, history, limit=3):
    if history["year"] != current_year - 60:
        raise ValueError("Forecast evidence must be exactly 60 years ago")
    grouped = {name: [] for name in THEMES}
    for event in history["events"]:
        for name in classify(event):
            grouped[name].append(event)
    ranked = sorted(grouped, key=lambda name: -len(grouped[name]))
    return [{
        "year": current_year, "theme": name,
        "prediction": f"{current_year}年には、{THEMES[name]['forecast']}",
        "evidence": grouped[name][:2],
        "reason": f"{history['year']}年の資料に「{name}」に関する出来事があるため、同じ主題を今年に当てはめています。",
    } for name in ranked if grouped[name]][:limit]
