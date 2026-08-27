"""
plot_chart.py
------------------------------------------------------------
fetch_data.py が data/ フォルダに保存したCSVファイルを読み込んで、
「変化率(%)」の折れ線グラフを1枚の画面に表示するプログラムです。

要件定義書(2.4節・7.3節)の考え方にならい、
「株価の絶対額」ではなく「期間の始点を0%とした変化率」で比較します。
理由: 日経平均(数万pt)とキーコーヒーの株価(数千円)のように、
      水準がまったく違うものを同じグラフで比べるには、
      %(パーセント)に揃えるのが公平だからです。

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


def load_series(ticker):
    """
    1つのティッカー(指数・銘柄)のCSVファイルを読み込み、
    (日付のリスト, 終値のリスト) のペア(タプル)として返す関数。

    データが無い/壊れている場合は (None, None) を返す。
    """
    file_path = os.path.join(config.DATA_DIR, ticker["key"] + ".csv")

    if not os.path.exists(file_path):
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
        print("  x " + ticker["label"] + ": 有効なデータが1件もありませんでした。")
        return None, None

    return dates, closes


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


def plot_all(tickers):
    """
    渡された「ティッカーの一覧(リスト)」についてデータを読み込み、
    1つのグラフに重ねて折れ線グラフを描画する処理。

    引数(Parameters)
    ----------
    tickers : list of dict
        グラフに表示したいティッカーの一覧。
        フェーズ2からは、呼び出し元(main.py)で「非表示(hidden)」の
        ものをあらかじめ除いたリストを渡す想定です
        (このグラフ側では hidden かどうかは見ていません)。
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

        pct = to_percent_change(closes)

        # 指数(日経平均・NASDAQ)は点線、個別銘柄は実線で区別する
        # (デザイン確認用プロトタイプでも同じルールを採用している)
        if ticker["kind"] == "index":
            line_style = "--"
            line_width = 1.8
        else:
            line_style = "-"
            line_width = 2.0

        ax.plot(dates, pct, linestyle=line_style, linewidth=line_width, label=ticker["label"])
        plotted_count += 1

    if plotted_count == 0:
        print("グラフに表示できるデータがありませんでした。")
        print("先に python fetch_data.py を実行して、データを取得してください。")
        return

    # 0%の位置に基準線を引く(上がっているか下がっているか一目でわかるように)
    ax.axhline(0, color="gray", linewidth=1, linestyle=":")

    ax.set_title("値動きウォッチ(実データ版・フェーズ2)", fontsize=14)
    ax.set_xlabel("日付")
    ax.set_ylabel("変化率(%) ※期間の始点を0%とした変化率")
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
    # このファイル単体で実行したときは、非表示中のものを除いた
    # ウォッチリストをそのままグラフ表示する
    items = watchlist.load_watchlist()
    visible_items = [item for item in items if not item["hidden"]]
    plot_all(visible_items)
