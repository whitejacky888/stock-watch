"""
news.py
------------------------------------------------------------
指数・銘柄に関連するニュースを取得するファイルです。
要件定義書 7.6節(ニュース表示機能)に対応します。

【データの取得元(v0.14で変更)】
最初はyfinance内蔵のニュース機能(Yahoo Finance 米国版経由)を使って
いましたが、配信元が英語圏中心のため、日本語のニュースがほとんど
表示されないという問題がありました。そこで、Googleニュースが無料で
公開している「検索結果のRSS配信」という仕組みを使い、銘柄名で
ニュースを検索する方式に変更しました。日本語・日本向けの設定
(hl=ja&gl=JP&ceid=JP:ja)にしているため、日本語のニュースが中心に
取得できます。

【なぜAPIキーの登録なしで使えるのか】
Googleニュースの検索結果RSS(https://news.google.com/rss/search?...)は、
アカウント登録やAPIキーの発行をしなくても、誰でもそのURLに
アクセスするだけで結果(XML形式)を取得できる、公開されたフィード配信の
仕組みです。RSSはもともと「第三者が購読・表示すること」を想定した
仕組みのため、以前問題になったstooq.com(プログラムからのアクセスを
検知してブロックする対策がされていた)や、Yahoo!ファイナンス(日本版・
機械的な取得を利用規約で禁止している)とは性質が異なります。

※ Pythonの標準ライブラリ(urllib・xml)だけで実装しているため、
  新しく pip install するライブラリはありません。
"""

import datetime
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"


def _build_query_url(keyword):
    """
    Googleニュースの検索RSSのURLを組み立てる関数。
    hl(表示言語)・gl(国)・ceid(地域と言語の組み合わせ)を
    日本語・日本向けに固定している。
    """
    params = {
        "q": keyword,
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    }
    return GOOGLE_NEWS_RSS_URL + "?" + urllib.parse.urlencode(params)


def _parse_pubdate(text):
    """
    RSSの pubDate(例: "Mon, 01 Jan 2024 09:00:00 GMT")を
    datetime型に変換する関数。変換できなければ None を返す。
    """
    if not text:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _clean_title(title, publisher):
    """
    Googleニュースの見出しは、末尾に " - 配信元名" が付いていることが
    多い(配信元は別途 publisher として表示するため、ここでは取り除いて
    見出しだけをすっきり表示できるようにする)。
    """
    if title and publisher and title.endswith(" - " + publisher):
        return title[: -(len(publisher) + 3)]
    return title


def _fetch_raw_xml(url):
    """
    指定したURLからXML(RSS)のデータを取得する関数。
    通信エラーが起きた場合は None を返す(例外は出さない)。
    """
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()
    except Exception:
        return None


def fetch_news_for_ticker(ticker, limit=5):
    """
    1つのティッカー(指数・銘柄)について、Googleニュース経由で
    日本語の関連ニュースを取得する関数。
    検索キーワードには、銘柄の表示名(例: "ソニーグループ")を使う。

    戻り値は、ニュース辞書のリスト(最大 limit 件・取得できた順)。
    通信エラーやニュースが無い場合は、空リストを返す(例外は出さない)。

    各ニュース辞書には、どの銘柄のニュースかが分かるように
    "ticker_label"(表示名)と "ticker_color"(グラフと同じ固定色)も加える。
    """
    keyword = ticker["label"]
    url = _build_query_url(keyword)

    raw_xml = _fetch_raw_xml(url)
    if raw_xml is None:
        return []

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []

    results = []
    for item in root.findall("./channel/item")[:limit]:
        raw_title = item.findtext("title")
        if not raw_title:
            continue

        link = item.findtext("link")
        pub_date_text = item.findtext("pubDate")
        source_el = item.find("source")
        publisher = source_el.text if source_el is not None else None
        title = _clean_title(raw_title, publisher)

        results.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "published": _parse_pubdate(pub_date_text),
            "ticker_label": ticker["label"],
            "ticker_color": ticker.get("color"),
        })

    return results


def fetch_news_for_tickers(tickers, limit_per_ticker=5):
    """
    複数のティッカーについて、まとめてニュースを取得する関数。
    全ティッカー分のニュースをまとめたうえで、公開日時が新しい順に
    並べ替えて返す(日時が分からないニュースは一番後ろに回す)。
    """
    all_news = []
    for ticker in tickers:
        all_news.extend(fetch_news_for_ticker(ticker, limit=limit_per_ticker))

    def sort_key(entry):
        return entry["published"] or datetime.datetime.min

    all_news.sort(key=sort_key, reverse=True)
    return all_news
