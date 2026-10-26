import streamlit as st
import streamlit.components.v1 as components
import feedparser
import urllib.parse
from manuscript import comparison_table, prediction_card
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError
from history_free import (
    fetch_history, compare_events, forecast_from_history, year_ranges, ServiceError, USER_AGENT,
)

# 1. ページ設定（和風なタイトル）
st.set_page_config(page_title="六十路の古年譜・預言書", layout="wide")

# ブラウザの端末時刻を取得し、取得後に描画する。
browser_year = components.declare_component(
    "browser_year", path=str(Path(__file__).parent / "browser_year")
)
current_year = browser_year(key="browser_year", default=None)
if current_year is None:
    st.info("ブラウザの現在年を取得しています。")
    st.stop()
if type(current_year) is not int or not 1900 <= current_year <= 9999:
    st.error("ブラウザの年を取得できません。端末の日付設定を確認してください。")
    st.stop()

# 和紙の配色と、読みやすい本文・見出し。
stylesheet = (Path(__file__).parent / "assets" / "manuscript.css").read_text(encoding="utf-8")
st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)

# 61〜80年前は実際の60年後と比較。60年前は今年の予想に使用する。
comparison_years, forecast_past_year = year_ranges(current_year)
st.sidebar.title("📜 観測の栞")
target_past_year = st.sidebar.select_slider(
    f"⏳ 比較する年（{comparison_years[0]}〜{comparison_years[-1]}年／80〜61年前）",
    options=comparison_years,
    value=comparison_years[-1],
    key=f"comparison_year_{current_year}",
)
comparison_scope = st.sidebar.radio("比較する出来事", options=["日本", "世界"], index=1)
scope = "japan" if comparison_scope == "日本" else "world"
st.sidebar.caption(f"ブラウザの現在年：{current_year}年")
st.sidebar.button("🔄 歴史データを再取得")
st.sidebar.caption("表示・年の変更・再取得のたびに資料を更新します。")
search_query = st.sidebar.text_input("🔍 ニュース検索", value="人工知能", max_chars=200)

st.markdown(
    '<div class="manuscript-cover">'
    '<div class="kicker">古年譜 ・ 預言之書</div>'
    '<h1>六十年の連環</h1>'
    '<p>歴史をひもとき、今年を想う。</p>'
    f'<span class="year-stamp">{current_year}年の巻</span>'
    '</div>',
    unsafe_allow_html=True,
)

# 互いに独立した資料を取得。失敗した資料だけを表示不能にする。
later_year = target_past_year + 60
requests = list(dict.fromkeys([
    (target_past_year, scope), (later_year, scope),
    (forecast_past_year, "japan"), (forecast_past_year, "world"),
]))
histories, failures = {}, {}
with st.spinner("比較と予想に使う歴史資料を取得しています…"):
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = {executor.submit(fetch_history, year, region): (year, region) for year, region in requests}
        for task in as_completed(tasks):
            key = tasks[task]
            try:
                histories[key] = task.result()
            except ServiceError as exc:
                failures[key] = str(exc)


def source(history):
    st.link_button(f"出典：Wikipedia「{history['title']}」", history["revision_url"])
    st.caption(f"取得時刻（UTC）：{history['retrieved_at']} ／「出来事」節より抜粋・CC BY-SA")


def show_events(history, label):
    with st.expander(label):
        for number, event in enumerate(history["events"], 1):
            st.write(f"[{number}] {event}")
    source(history)


st.header("壱　六十年を隔てた出来事")
st.subheader(f"{comparison_scope}：{target_past_year}年 ↔ {later_year}年")
st.caption(
    f"今年の{current_year - target_past_year}年前と{current_year - later_year}年前の資料を比較。"
    "共通テーマによる対応候補で、因果関係や60年周期の証明ではありません。"
)
past = histories.get((target_past_year, scope))
later = histories.get((later_year, scope))
if past and later:
    pairs = compare_events(past, later)
    if pairs:
        st.markdown(comparison_table(pairs, target_past_year, later_year), unsafe_allow_html=True)
    else:
        st.info("取得した出来事には共通テーマが見つかりませんでした。別の年や地域を選べます。")
left, right = st.columns(2)
with left:
    if past:
        show_events(past, f"{target_past_year}年の取得した出来事")
    else:
        st.error(f"{target_past_year}年：{failures.get((target_past_year, scope), '資料を取得できません。')}")
with right:
    if later:
        show_events(later, f"{later_year}年の取得した出来事")
    else:
        st.error(f"{later_year}年：{failures.get((later_year, scope), '資料を取得できません。')}")

st.write("---")
st.header(f"弐　{current_year}年を想う")
st.subheader(f"{forecast_past_year}年の出来事を手掛かりに")
st.caption(
    "日本と世界の60年前の出来事を別々に分類し、件数の多いテーマから最大3件ずつ予想します。"
    "予想文はルールによる仮説です。"
)
japan_column, world_column = st.columns(2)
for column, region, label in [
    (japan_column, "japan", "🇯🇵 日本"), (world_column, "world", "🌏 世界"),
]:
    with column:
        st.subheader(label)
        history = histories.get((forecast_past_year, region))
        if not history:
            st.error(failures.get((forecast_past_year, region), "資料を取得できません。"))
            continue
        predictions = forecast_from_history(current_year, history)
        if not predictions:
            st.info("取得した出来事に分類できるテーマがないため、予想を表示できません。")
        for prediction in predictions:
            st.markdown(prediction_card(prediction), unsafe_allow_html=True)
        show_events(history, f"根拠資料：{forecast_past_year}年の出来事")

st.caption("世界欄は各国の出来事を扱う年記事を参照するため、日本の出来事が含まれる場合があります。")

# --- ニュース ---
st.header("参　現在の瓦版")
encoded = urllib.parse.quote(search_query)
try:
    request = Request(
        f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja",
        headers={"User-Agent": USER_AGENT},
    )
    with urlopen(request, timeout=15) as response:
        feed = feedparser.parse(response.read())
    for entry in feed.entries[:5]:
        st.write(f"◆ {entry.title}")
        if urllib.parse.urlparse(entry.link).scheme in ("https", "http"):
            st.link_button("詳しく読む", entry.link)
except (URLError, TimeoutError, OSError):
    st.info("ニュースを取得できません。時間をおいて再試行してください。")
