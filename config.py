# ==============================================================
# config.py
# ------------------------------------------------------------
# このファイルには、株価データを取得するための「設定」をまとめています。
# 難しい処理(プログラムのロジック)はここには書かず、
# 「自分の環境に合わせて書き換える値」だけを集めているのがポイントです。
# こうしておくと、他のファイル(fetch_data.py や plot_chart.py)の
# 中身を触らなくても、ここだけ直せば動きが変えられます。
# ==============================================================

# ---- ① stooq.com のAPIキー ----
# stooq.com は 2026年4月頃から、データ取得に「APIキー」が必要になりました。
# 以下の手順で、自分専用のAPIキーを取得してください。
#
#   1. ブラウザで次のURLを開く(例:ソニーグループのページ)
#      https://stooq.com/q/d/?s=6758.jp&get_apikey
#   2. 画像認証(CAPTCHA)が出てきたら解く
#   3. 表示された画面や、その後にダウンロードされるCSVのURLの中に
#      「apikey=◯◯◯◯◯◯」という文字列があるので、◯◯◯◯◯◯の部分をコピーする
#   4. 下の STOOQ_API_KEY = "" の "" の中に貼り付ける
#
# 例: STOOQ_API_KEY = "AbCdEfGh12345"
#
# ※ このキーは個人のものなので、他の人に見せたり、
#    公開の場所(GitHubなど)にアップロードしたりしないよう注意してください。
STOOQ_API_KEY = ""  # ← ここに取得したAPIキーを貼り付けてください


# ---- ② 追跡する指数・銘柄の一覧 ----
# 「基本の2指数」+「組み込み済み12社」(要件定義書 v0.6 の7.1節に対応)
#
# 各項目の意味:
#   key    : プログラム内部で使う短い識別名(英数字。ファイル名にも使う)
#   label  : グラフに表示する日本語の名前
#   symbol : stooq.com 上でのシンボル(このコードでデータを検索する)
#   kind   : "index"(指数) か "company"(個別銘柄)か
#            → グラフの線の種類(点線/実線)を変えるのに使う
#
# 新しい銘柄を追加したいときは、このリストに同じ形式で1行足すだけでOKです。
TICKERS = [
    # ---- 基本の2指数 ----
    {"key": "nikkei", "label": "日経平均株価", "symbol": "^nkx", "kind": "index"},
    {"key": "nasdaq", "label": "NASDAQ総合指数", "symbol": "^ndq", "kind": "index"},

    # ---- 組み込み済み12社(要件定義書 7.1節の表と対応) ----
    {"key": "keycoffee", "label": "キーコーヒー", "symbol": "2594.jp", "kind": "company"},
    {"key": "kameda", "label": "亀田製菓", "symbol": "2220.jp", "kind": "company"},
    {"key": "takeda", "label": "武田薬品工業", "symbol": "4502.jp", "kind": "company"},
    {"key": "itoen", "label": "伊藤園", "symbol": "2593.jp", "kind": "company"},
    {"key": "sekiko", "label": "石光商事", "symbol": "2750.jp", "kind": "company"},
    {"key": "colowide", "label": "コロワイド", "symbol": "7616.jp", "kind": "company"},
    {"key": "orix", "label": "オリックス", "symbol": "8591.jp", "kind": "company"},
    {"key": "uoki", "label": "魚喜", "symbol": "2683.jp", "kind": "company"},
    {"key": "tsukiji", "label": "築地魚市場", "symbol": "8039.jp", "kind": "company"},
    {"key": "itoham", "label": "伊藤ハム米久ホールディングス", "symbol": "2296.jp", "kind": "company"},
    {"key": "yokohamagyorui", "label": "横浜魚類", "symbol": "7443.jp", "kind": "company"},
    {"key": "sony", "label": "ソニーグループ", "symbol": "6758.jp", "kind": "company"},
]


# ---- ③ 取得するデータの期間 ----
# 何日分さかのぼってデータを取るか(株式市場の営業日ではなく、暦日で指定)
DAYS_BACK = 400  # 約400日(1年強)分をさかのぼって取得する


# ---- ④ データの保存先フォルダ ----
# fetch_data.py が取得したCSVをここに保存し、plot_chart.py がここから読み込む
DATA_DIR = "data"
