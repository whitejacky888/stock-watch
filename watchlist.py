"""
watchlist.py
------------------------------------------------------------
「ウォッチリスト」(追跡する指数・銘柄の一覧)を管理するファイルです。

フェーズ1では、追跡する銘柄は config.py に固定で書かれていましたが、
フェーズ2では要件定義書 7.1節・7.5節・7.8節に対応するために、
  ・銘柄を自由に追加・削除できる
  ・一時的に「非表示」にできる(データは消さず、表示だけ隠す)
  ・次回起動時も同じ構成を覚えている(保存・読み込み)
という機能が必要になりました。そこで、ウォッチリストの中身を
"watchlist.json" というファイルに保存し、このファイルで読み書きを
一括して管理するようにしています。

【JSON(ジェイソン)とは】
Pythonの辞書(dict)やリストを、そのままファイルに保存できる形式です。
人間が見ても読みやすいテキスト形式なので、興味があれば
watchlist.json をVS Codeで直接開いて中身を覗いてみてください。

【1件分のデータの形(辞書)】
{
    "key":     "sony",              # プログラム内部の識別名(ファイル名にも使う)
    "label":   "ソニーグループ",       # 画面に表示する名前
    "symbol":  "6758.T",            # yfinanceで使うシンボル
    "kind":    "company",           # "index"(指数) か "company"(個別銘柄)
    "market":  "東証プライム",         # 市場区分(個別銘柄のみ。指数は "-")
    "business": "エレクトロニクス・ゲーム・映画・金融など幅広く手がけるグループ",
    "hidden":  False,               # True なら「非表示」中
    "color":   "#e6194b",           # グラフの線の色(この会社専用に固定・下記コラム参照)
}

【グラフの色を「会社ごとに固定」にしている理由】
以前は、グラフを描くmatplotlib(マットプロットリブ)というライブラリの
「自動で色を割り当てる機能」に任せていました。しかしこれは、
「そのとき画面に表示されている順番」に沿って色を割り振る仕組みのため、
銘柄を非表示にしたり追加したりして表示順が変わるたびに、
同じ会社でも違う色になってしまう、という問題がありました。
そこで、会社ごとに「専用の色」を1つ決めて watchlist.json に保存しておき、
常にその色を使う(=表示順が変わっても色は変わらない)ようにしています。
"""

import json
import os

import yfinance as yf

WATCHLIST_FILE = "watchlist.json"

# 個別銘柄として同時に登録できる最大数(要件定義書 7.1節)
MAX_COMPANIES = 15

# ---- グラフの色パレット ----
# 基本の2指数(2件)+ 個別銘柄(最大15件)= 最大17件を、すべて見分けやすい
# 色にできるように、17色ぶんの「はっきり違う色」を用意しています。
# (人間の目で見て区別しやすいよう、あえて似た色同士が並ばないようにしています)
COLOR_PALETTE = [
    "#e6194b",  # 赤
    "#3cb44b",  # 緑
    "#4363d8",  # 青
    "#f58231",  # オレンジ
    "#911eb4",  # 紫
    "#46f0f0",  # シアン
    "#f032e6",  # マゼンタ
    "#9a6324",  # 茶
    "#800000",  # マルーン
    "#808000",  # オリーブ
    "#000075",  # ネイビー
    "#808080",  # グレー
    "#000000",  # 黒
    "#bcf60c",  # ライム
    "#008080",  # ティール
    "#c71585",  # 濃いピンク
    "#b8860b",  # ダークゴールド
]


def _pick_unused_color(items):
    """
    現在ウォッチリストで使われていない色を、パレットから1つ選ぶ関数。
    (最大17件までしか登録できない仕様なので、パレットが尽きることはない)
    """
    used = set(item.get("color") for item in items if item.get("color"))
    for color in COLOR_PALETTE:
        if color not in used:
            return color
    return COLOR_PALETTE[0]  # 万が一すべて使われていた場合の保険(通常は起こらない)


def _default_watchlist():
    """
    初回起動時(watchlist.json がまだ存在しないとき)に使う、
    初期状態のウォッチリストを作る関数。
    要件定義書 7.1節の「基本の2指数」+「組み込み済み12社」に対応する。
    """
    return [
        # ---- 基本の2指数(削除はできない。非表示のみ可能) ----
        {"key": "nikkei", "label": "日経平均株価", "symbol": "^N225", "kind": "index",
         "market": "-", "business": "東証プライムの代表的な225銘柄から算出される、日本を代表する株価指数",
         "hidden": False, "color": COLOR_PALETTE[0]},
        {"key": "nasdaq", "label": "NASDAQ総合指数", "symbol": "^IXIC", "kind": "index",
         "market": "-", "business": "米国NASDAQ市場に上場する銘柄から算出される株価指数(IT・ハイテク企業が多い)",
         "hidden": False, "color": COLOR_PALETTE[1]},

        # ---- 組み込み済み12社(要件定義書 7.1節の表と対応) ----
        {"key": "keycoffee", "label": "キーコーヒー", "symbol": "2594.T", "kind": "company",
         "market": "東証スタンダード", "business": "コーヒー製品の製造・販売", "hidden": False,
         "color": COLOR_PALETTE[2]},
        {"key": "kameda", "label": "亀田製菓", "symbol": "2220.T", "kind": "company",
         "market": "東証プライム", "business": "米菓(せんべい・柿の種など)の製造・販売", "hidden": False,
         "color": COLOR_PALETTE[3]},
        {"key": "takeda", "label": "武田薬品工業", "symbol": "4502.T", "kind": "company",
         "market": "東証プライム", "business": "国内最大手の医薬品メーカー", "hidden": False,
         "color": COLOR_PALETTE[4]},
        {"key": "itoen", "label": "伊藤園", "symbol": "2593.T", "kind": "company",
         "market": "東証プライム", "business": "緑茶飲料など飲料の製造・販売(「お〜いお茶」など)", "hidden": False,
         "color": COLOR_PALETTE[5]},
        {"key": "sekiko", "label": "石光商事", "symbol": "2750.T", "kind": "company",
         "market": "東証スタンダード", "business": "コーヒー・食品原材料の輸入・卸売", "hidden": False,
         "color": COLOR_PALETTE[6]},
        {"key": "colowide", "label": "コロワイド", "symbol": "7616.T", "kind": "company",
         "market": "東証プライム", "business": "「牛角」などを展開する外食チェーン", "hidden": False,
         "color": COLOR_PALETTE[7]},
        {"key": "orix", "label": "オリックス", "symbol": "8591.T", "kind": "company",
         "market": "東証プライム", "business": "リース・金融・保険など幅広く手がける総合金融グループ", "hidden": False,
         "color": COLOR_PALETTE[8]},
        {"key": "uoki", "label": "魚喜", "symbol": "2683.T", "kind": "company",
         "market": "東証スタンダード", "business": "水産物・食品の卸売", "hidden": False,
         "color": COLOR_PALETTE[9]},
        {"key": "tsukiji", "label": "築地魚市場", "symbol": "8039.T", "kind": "company",
         "market": "東証スタンダード", "business": "水産物の卸売(築地市場を拠点とする卸売業者)", "hidden": False,
         "color": COLOR_PALETTE[10]},
        {"key": "itoham", "label": "伊藤ハム米久ホールディングス", "symbol": "2296.T", "kind": "company",
         "market": "東証プライム", "business": "ハム・ソーセージなど食肉加工品の大手(伊藤ハムの持株会社)", "hidden": False,
         "color": COLOR_PALETTE[11]},
        {"key": "yokohamagyorui", "label": "横浜魚類", "symbol": "7443.T", "kind": "company",
         "market": "東証スタンダード", "business": "水産物の卸売(横浜市中央卸売市場を拠点)", "hidden": False,
         "color": COLOR_PALETTE[12]},
        {"key": "sony", "label": "ソニーグループ", "symbol": "6758.T", "kind": "company",
         "market": "東証プライム", "business": "エレクトロニクス・ゲーム・映画・金融など幅広く手がけるグループ",
         "hidden": False, "color": COLOR_PALETTE[13]},
    ]


def load_watchlist():
    """
    watchlist.json を読み込んで、ウォッチリスト(辞書のリスト)を返す関数。
    ファイルがまだ存在しない場合(初回起動時)は、初期状態を作って
    保存してから返す。
    """
    if not os.path.exists(WATCHLIST_FILE):
        items = _default_watchlist()
        save_watchlist(items)
        return items

    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    # ---- 古い形式のファイルへの対応(移行処理) ----
    # 以前のバージョンで作られた watchlist.json には "color" が入っていないため、
    # 読み込み時に不足していれば自動で割り当てて、そのまま保存し直す。
    # (こうしておくことで、既存のユーザーも次回起動時から色が固定される)
    changed = False
    for item in items:
        if not item.get("color"):
            item["color"] = _pick_unused_color(items)
            changed = True
    if changed:
        save_watchlist(items)

    return items


def save_watchlist(items):
    """
    ウォッチリスト(辞書のリスト)を watchlist.json に保存する関数。
    indent=2 : 人間が読みやすいように、インデント(字下げ)を付けて保存する
    ensure_ascii=False : 日本語がそのまま読める形で保存する(文字コードの都合の設定)
    """
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def count_companies(items):
    """ウォッチリストの中で、種別が「個別銘柄(company)」の件数を数える関数。"""
    return len([item for item in items if item["kind"] == "company"])


def find_by_symbol(items, symbol):
    """
    シンボル(例: "6758.T")が一致する項目を探す関数。
    見つからなければ None を返す。
    """
    for item in items:
        if item["symbol"].lower() == symbol.lower():
            return item
    return None


def normalize_symbol(user_input):
    """
    ユーザーが入力した文字列を、yfinanceで使えるシンボルの形に整える関数。

    ルール:
      - 数字4桁だけの場合(例: "7203") → 日本株とみなし、末尾に ".T" を付ける
      - すでに記号やアルファベットが含まれる場合(例: "AAPL", "7203.T") → そのまま使う

    このルールにより、日本株は証券コードをそのまま入力するだけで済むようにしています。
    """
    text = user_input.strip().upper()
    if text.isdigit() and len(text) == 4:
        return text + ".T"
    return text


def fetch_company_name(symbol):
    """
    yfinanceを使って、シンボルに対応する会社名(表示名)を取得する関数。
    取得できない場合(シンボルが誤っている、通信エラーなど)は None を返す。

    ※ 市場区分(東証プライム、など)や事業内容の一言説明は、yfinanceからは
       確実に取得できないため、この関数では扱わず、追加時にユーザー自身に
       入力してもらう形にしています。
    """
    try:
        info = yf.Ticker(symbol).info
    except Exception:
        return None

    # yfinanceのバージョンによって、会社名が入っているキー名が異なることがあるため、
    # 候補をいくつか順番に試す
    name = info.get("longName") or info.get("shortName") or info.get("displayName")
    return name


def add_company(items, symbol, label, market, business):
    """
    新しい個別銘柄をウォッチリストに追加する関数。
    追加できた場合は (True, "成功メッセージ") を、
    できなかった場合は (False, "失敗理由") を返す。
    """
    if count_companies(items) >= MAX_COMPANIES:
        return False, "個別銘柄はすでに上限の" + str(MAX_COMPANIES) + "社に達しています。追加するには、先に何か1社を削除してください。"

    if find_by_symbol(items, symbol) is not None:
        return False, "そのシンボル(" + symbol + ")はすでにウォッチリストに登録されています。"

    # key(内部識別名・ファイル名用)は、シンボルの "." や "^" を "_" に置き換えて作る
    key = symbol.lower().replace(".", "_").replace("^", "")

    items.append({
        "key": key,
        "label": label,
        "symbol": symbol,
        "kind": "company",
        "market": market,
        "business": business,
        "hidden": False,
        "color": _pick_unused_color(items),
    })
    save_watchlist(items)
    return True, label + "(" + symbol + ")を追加しました。"


def remove_company(items, index):
    """
    ウォッチリストの index番目(0始まり)の項目を完全に削除する関数。
    基本の2指数(kind == "index")は削除できない仕様のため、
    呼び出す前に kind をチェックすること。
    戻り値は (True, メッセージ) か (False, メッセージ)。
    """
    if index < 0 or index >= len(items):
        return False, "番号が正しくありません。"

    item = items[index]
    if item["kind"] == "index":
        return False, "基本の2指数(日経平均・NASDAQ)は削除できません。非表示にすることはできます。"

    removed = items.pop(index)
    save_watchlist(items)
    return True, removed["label"] + "を削除しました。"


def set_hidden(items, index, hidden):
    """
    ウォッチリストの index番目の項目の「非表示」状態を切り替える関数。
    hidden に True を渡すと非表示に、False を渡すと再表示にする。
    """
    if index < 0 or index >= len(items):
        return False, "番号が正しくありません。"

    items[index]["hidden"] = hidden
    save_watchlist(items)

    action = "非表示にしました" if hidden else "再表示しました"
    return True, items[index]["label"] + "を" + action + "。"
