"""
plot_chart.py
------------------------------------------------------------
fetch_data.py が data/ フォルダに保存したCSVファイルを読み込んで、
折れ線グラフを1枚の画面に表示するプログラムです。

要件定義書(2.4節・7.3節)の考え方にならい、基本は
「株価の絶対額」ではなく「期間の始点を0%とした変化率」で比較します。
理由: 日経平均(数万pt)とキーコーヒーの株価(数千円)のように、
      水準がまったく違うものを同じグラフで比べるには、
      %(パーセント)に揃えるのが公平だからです。

フェーズ3より、以下の2つの切り替えに対応しました(7.3節)。
  ・表示期間の切り替え(1ヶ月/3ヶ月/6ヶ月/1年/5年)
  ・変化率⇔実額表示の切り替え(実額表示は、表示中の銘柄が1つだけのときのみ)

このファイル単体で実行すると、グラフ表示だけを行います。
    python plot_chart.py
(先に python fetch_data.py でデータを取得しておく必要があります)
"""

import os
import csv
import datetime

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

import config
import watchlist  # ウォッチリスト(追跡する銘柄の一覧)を管理するファイル


def find_japanese_font():
    """
    日本語(会社名など)がグラフの中で文字化けしないように、
    パソコンにインストールされている日本語フォントを探す関数。
    見つからなければ None を返す(その場合、文字化けする可能性がある)。
    """
    candidates = [
        "Yu Gothic", "Meiryo", "MS Gothic",                  # Windows でよくあるフォント
        "Hiragino Sans", "Hiragino Kaku Gothic ProN",        # Mac でよくあるフォント
        "Noto Sans CJK JP", "IPAexGothic", "TakaoGothic",    # Linux でよくあるフォント
    ]
    installed_names = set(f.name for f in fm.fontManager.ttflist)
    for name in candidates:
        if name in installed_names:
            return name
    return None


def load_series(ticker, quiet=False):
    """
    1つのティッカー(指数・銘柄)のCSVファイルを読み込み、
    (日付のリスト, 終値のリスト) のペア(タプル)として返す関数。

    データが無い/壊れている場合は (None, None) を返す。

    quiet : bool
        True の場合、データが無い場合などのメッセージを表示しない。
        (例: フェーズ4で追加した「前日比」をウォッチリスト一覧に
         表示する際、データ未取得の銘柄が複数あってもエラーメッセージが
         大量に出て見づらくならないようにするため)
    """
    file_path = os.path.join(config.DATA_DIR, ticker["key"] + ".csv")

    if not os.path.exists(file_path):
        if not quiet:
            print("  x " + ticker["label"] + ": データファイルが見つかりません(" + file_path + ")")
            print("     先に python fetch_data.py を実行してください。")
        return None, None

    dates = []
    closes = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # fetch_data.py が保存するCSVは通常 "Date,Open,High,Low,Close,Volume" という列名だが、
        # 念のため大文字・小文字を区別せずに列を探せるようにしておく
        fieldnames = reader.fieldnames or []
        lower_to_original = {}
        for name in fieldnames:
            lower_to_original[name.lower()] = name

        date_col = lower_to_original.get("date")
        close_col = lower_to_original.get("close")

        if date_col is None or close_col is None:
            if not quiet:
                print("  x " + ticker["label"] + ": CSVの形式が想定と違います(列名: " + str(fieldnames) + ")")
            return None, None

        for row in reader:
            try:
                d = datetime.datetime.strptime(row[date_col], "%Y-%m-%d").date()
                c = float(row[close_col])
            except (ValueError, KeyError):
                # 日付や数値としてうまく読み取れない行(空行など)はスキップする
                continue
            dates.append(d)
            closes.append(c)

    if len(closes) == 0:
        if not quiet:
            print("  x " + ticker["label"] + ": 有効なデータが1件もありませんでした。")
        return None, None

    return dates, closes


def get_latest_change(ticker):
    """
    直近2営業日分のデータから、「前日比」「騰落率(%)」を計算する関数。
    要件定義書 7.4節(前日比・騰落率を分かりやすく表示する)に対応。

    データがまだ取得されていない場合や、データが1件以下しかない場合は
    (None, None) を返す(呼び出し元で「未取得」などの表示にする)。
    """
    dates, closes = load_series(ticker, quiet=True)
    if closes is None or len(closes) < 2:
        return None, None

    latest = closes[-1]
    previous = closes[-2]
    diff = latest - previous
    pct = (diff / previous) * 100.0 if previous != 0 else 0.0
    return diff, pct


def to_percent_change(closes):
    """
    終値のリストを、「最初の日を0%とした変化率(%)」のリストに変換する関数。
    例: [1000, 1050, 900] → [0.0, +5.0, -10.0]
    """
    base = closes[0]
    result = []
    for c in closes:
        pct = (c / base - 1.0) * 100.0
        result.append(pct)
    return result


def get_unit(ticker):
    """
    実額表示のときに使う「単位」を返す関数(フェーズ8-4の改良)。
    実額は銘柄ごとに単位がバラバラなので、グラフやツールチップに
    はっきり表示できるよう、次のルールで判定する。

      ・指数(日経平均・NASDAQ)        → "pt"(ポイント。円やドルではない)
      ・日本株(シンボルが ".T" で終わる) → "¥"
      ・それ以外(米国株など)           → "$"

    watchlist.normalize_symbol() が、日本株の証券コードには必ず ".T" を
    付ける仕様になっていることを利用した簡易判定(厳密な通貨判定では
    ないが、本ツールが扱う銘柄の範囲では十分)。
    """
    if ticker["kind"] == "index":
        return "pt"
    if ticker["symbol"].upper().endswith(".T"):
        return "¥"
    return "$"


def filter_recent(dates, closes, period_days):
    """
    (日付のリスト, 終値のリスト) から、直近 period_days日分だけを
    取り出す関数。

    「直近」の基準は、実行した日の「今日」ではなく、そのティッカーの
    データの中で一番新しい日付を使う。理由: 株式市場が休みの日
    (土日・祝日)があるため、「今日」を基準にすると、銘柄によって
    最新データの日付がずれて、グラフの見た目が不自然になることがあるため。
    """
    if len(dates) == 0:
        return dates, closes

    latest = dates[-1]
    cutoff = latest - datetime.timedelta(days=period_days)

    filtered_dates = []
    filtered_closes = []
    for d, c in zip(dates, closes):
        if d >= cutoff:
            filtered_dates.append(d)
            filtered_closes.append(c)

    if len(filtered_dates) == 0:
        # 絞り込んだ結果0件になってしまった場合(データが少なすぎる等)は、
        # 何も表示されないよりはマシなので、元のデータをそのまま返す
        return dates, closes

    return filtered_dates, filtered_closes


# 表示期間の選択肢(要件定義書 7.3節)。
# タプルの中身は (メニューに表示する名前, さかのぼる日数)。
PERIOD_OPTIONS = [
    ("1ヶ月", 30),
    ("3ヶ月", 90),
    ("6ヶ月", 180),
    ("1年", 365),
    ("5年", 1825),
]


def plot_all(tickers, period_days=None, period_label=None, mode="percent"):
    """
    渡された「ティッカーの一覧(リスト)」についてデータを読み込み、
    1つのグラフに重ねて折れ線グラフを描画する処理。

    引数(Parameters)
    ----------
    tickers : list of dict
        グラフに表示したいティッカーの一覧。
        呼び出し元(main.py)で「非表示(hidden)」のものをあらかじめ
        除いたリストを渡す想定です(このグラフ側では hidden かどうかは見ていません)。
    period_days : int または None
        直近何日分を表示するか。None の場合は絞り込みをせず全期間を使う。
    period_label : str または None
        グラフのタイトルに表示する期間の名前(例: "6ヶ月")。
    mode : str
        "percent"(変化率、複数銘柄の比較用・既定値) または
        "absolute"(実額。要件定義書7.3節の「ソロ表示」用で、
        銘柄が1つだけのときの利用を想定。呼び出し元でチェックする)
    """
    font_name = find_japanese_font()
    if font_name:
        plt.rcParams["font.family"] = font_name
    else:
        print("※ 日本語フォントが見つかりませんでした。グラフの日本語が文字化けするかもしれません。")

    # マイナス記号(-)が文字化けするのを防ぐためのおまじない設定
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(12, 6))

    plotted_count = 0
    for ticker in tickers:
        dates, closes = load_series(ticker)
        if dates is None:
            continue  # このティッカーはスキップして、次のティッカーへ

        if period_days is not None:
            dates, closes = filter_recent(dates, closes, period_days)

        if mode == "absolute":
            values = closes
        else:
            values = to_percent_change(closes)

        # 指数(日経平均・NASDAQ)は点線、個別銘柄は実線で区別する
        # (デザイン確認用プロトタイプでも同じルールを採用している)
        if ticker["kind"] == "index":
            line_style = "--"
            line_width = 1.8
        else:
            line_style = "-"
            line_width = 2.0

        # 会社(銘柄)ごとに固定した色を使う(watchlist.py参照)。
        # 万が一 "color" が無い古いデータの場合でも落ちないように、
        # その場合だけmatplotlibの自動色に任せる(Noneを渡すと自動になる)。
        line_color = ticker.get("color")

        ax.plot(dates, values, linestyle=line_style, linewidth=line_width,
                 color=line_color, label=ticker["label"])
        plotted_count += 1

    if plotted_count == 0:
        print("グラフに表示できるデータがありませんでした。")
        print("先に python fetch_data.py を実行して、データを取得してください。")
        return

    period_text = period_label if period_label else "全期間"

    if mode == "absolute":
        # 実額表示のときは、0%の基準線ではなく単位の説明だけにする
        ax.set_ylabel("実額(円・pt など、銘柄ごとの単位)")
        title_mode = "実額"
    else:
        # 0%の位置に基準線を引く(上がっているか下がっているか一目でわかるように)
        ax.axhline(0, color="gray", linewidth=1, linestyle=":")
        ax.set_ylabel("変化率(%) ※期間の始点を0%とした変化率")
        title_mode = "変化率"

    ax.set_title("値動きウォッチ(実データ版・フェーズ6・" + period_text + "・" + title_mode + ")", fontsize=14)
    ax.set_xlabel("日付")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)

    fig.autofmt_xdate()  # 日付ラベル同士が重ならないように、斜めに表示する
    plt.tight_layout()

    # ---- グラフを画像ファイルとしても保存しておく ----
    # (グラフのウィンドウがうまく表示されない環境でも、この画像を開けば内容を確認できる)
    output_path = "chart.png"
    fig.savefig(output_path, dpi=150)
    print(str(plotted_count) + " 件の指数・銘柄をグラフに表示します。")
    print("グラフ画像を保存しました: " + os.path.abspath(output_path))

    # ---- 画面にグラフのウィンドウを表示する ----
    try:
        print("グラフのウィンドウを閉じると、プログラムが終了します。")
        plt.show()
    except Exception as e:
        # 環境によっては、グラフを画面に表示する機能(GUI)が使えないことがある。
        # その場合でも、上で保存した chart.png を開けば内容を確認できる。
        print("(グラフウィンドウの表示に失敗しました: " + str(e) + ")")
        print("代わりに " + os.path.abspath(output_path) + " を開いて確認してください。")


if __name__ == "__main__":
    # このファイル単体で実行したときは、非表示中のものを除いたウォッチリストを、
    # 既定の期間(1年)・変化率表示でグラフ表示する
    items = watchlist.load_watchlist()
    visible_items = [item for item in items if not item["hidden"]]
    default_label, default_days = PERIOD_OPTIONS[3]  # "1年"
    plot_all(visible_items, period_days=default_days, period_label=default_label, mode="percent")
