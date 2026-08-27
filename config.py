# ==============================================================
# config.py
# ------------------------------------------------------------
# このファイルには、株価データを取得するための「設定」をまとめています。
# 難しい処理(プログラムのロジック)はここには書かず、
# 「自分の環境に合わせて書き換える値」だけを集めているのがポイントです。
# こうしておくと、他のファイル(fetch_data.py や plot_chart.py)の
# 中身を触らなくても、ここだけ直せば動きが変えられます。
#
# ※ 2026年8月:データ取得元をstooq.comからyfinanceに変更しました。
#    (理由:stooq.comがプログラムからの自動アクセスをブロックする対策を
#     しており、安定してデータを取得できなくなったため)
#    yfinanceはAPIキーなどの秘密の値が不要なため、以前あった
#    「stooq.comのAPIキー」の設定はこのファイルから削除しています。
#    (.env や .gitignore の仕組み自体は、将来ニュースAPIなど別の
#     秘密の値が必要になったときのために残してあります)
# ==============================================================

# ---- ① 追跡する指数・銘柄の一覧 ----
# 「基本の2指数」+「組み込み済み12社」(要件定義書 v0.6 の7.1節に対応)
#
# 各項目の意味:
#   key    : プログラム内部で使う短い識別名(英数字。ファイル名にも使う)
#   label  : グラフに表示する日本語の名前
#   symbol : yfinance(米国版Yahoo Finance経由)で使うシンボル
#            日本株は証券コードの後ろに ".T"(東証)を付ける(例: 6758.T)
#            指数は "^" で始まる特別な記号を使う(例: 日経平均=^N225)
#   kind   : "index"(指数) か "company"(個別銘柄)か
#            → グラフの線の種類(点線/実線)を変えるのに使う
#
# 新しい銘柄を追加したいときは、このリストに同じ形式で1行足すだけでOKです。
# (日本株の証券コードが分かれば、末尾に ".T" を付けるだけで大抵は使えます)
TICKERS = [
    # ---- 基本の2指数 ----
    {"key": "nikkei", "label": "日経平均株価", "symbol": "^N225", "kind": "index"},
    {"key": "nasdaq", "label": "NASDAQ総合指数", "symbol": "^IXIC", "kind": "index"},

    # ---- 組み込み済み12社(要件定義書 7.1節の表と対応) ----
    {"key": "keycoffee", "label": "キーコーヒー", "symbol": "2594.T", "kind": "company"},
    {"key": "kameda", "label": "亀田製菓", "symbol": "2220.T", "kind": "company"},
    {"key": "takeda", "label": "武田薬品工業", "symbol": "4502.T", "kind": "company"},
    {"key": "itoen", "label": "伊藤園", "symbol": "2593.T", "kind": "company"},
    {"key": "sekiko", "label": "石光商事", "symbol": "2750.T", "kind": "company"},
    {"key": "colowide", "label": "コロワイド", "symbol": "7616.T", "kind": "company"},
    {"key": "orix", "label": "オリックス", "symbol": "8591.T", "kind": "company"},
    {"key": "uoki", "label": "魚喜", "symbol": "2683.T", "kind": "company"},
    {"key": "tsukiji", "label": "築地魚市場", "symbol": "8039.T", "kind": "company"},
    {"key": "itoham", "label": "伊藤ハム米久ホールディングス", "symbol": "2296.T", "kind": "company"},
    {"key": "yokohamagyorui", "label": "横浜魚類", "symbol": "7443.T", "kind": "company"},
    {"key": "sony", "label": "ソニーグループ", "symbol": "6758.T", "kind": "company"},
]


# ---- ② 取得するデータの期間 ----
# 何日分さかのぼってデータを取るか(株式市場の営業日ではなく、暦日で指定)
DAYS_BACK = 400  # 約400日(1年強)分をさかのぼって取得する


# ---- ③ データの保存先フォルダ ----
# fetch_data.py が取得したCSVをここに保存し、plot_chart.py がここから読み込む
DATA_DIR = "data"
