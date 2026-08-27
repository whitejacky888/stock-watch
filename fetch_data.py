"""
fetch_data.py
------------------------------------------------------------
yfinance ライブラリを使って、config.py で指定した指数・銘柄の株価データを
取得し、CSV形式で data/ フォルダにファイルとして保存するプログラムです。

【なぜstooq.comからyfinanceに変更したのか】
最初はstooq.comというサイトから直接データをダウンロードしていましたが、
実際に動かしてみたところ、stooq側の「プログラムからの機械的なアクセスを
検知してブロックする仕組み(bot対策)」に引っかかり、本物のデータの代わりに
「ブラウザで見てください(JavaScriptを有効にしてください)」という案内の
HTMLページが返ってきてしまうことが分かりました。
そこで、株価データ取得のために広く使われているPythonライブラリ
「yfinance」(米国版Yahoo Finance経由でデータを取得するライブラリ)に
切り替えました。yfinanceはAPIキーなどの登録も不要です。

【このファイルでやっていること(全体の流れ)】
  1. watchlist.py から「取得したいティッカーの一覧」を読み込む(呼び出し元から渡される)
  2. ティッカー(指数・銘柄)を1つずつ、yfinance経由でデータを取得する
  3. 取得したデータの必要な列だけを取り出し、CSVファイルとして保存する
  4. うまくいかなかった場合は、エラーの内容を分かりやすく表示する

このファイル単体で実行すると、watchlist.json に登録されている
すべての銘柄(非表示中のものも含む)のデータ取得だけを行います。
    python fetch_data.py

※ フェーズ2より、「非表示」の銘柄もデータ取得は続けています
  (表示のON/OFFと、データ取得の有無は別の話にしているためです。
   こうしておくと、再表示したときにすぐ最新のグラフが見られます)。
"""

import os
import datetime

import yfinance as yf  # pip install yfinance でインストールするライブラリ

import config  # 同じフォルダにある config.py を読み込む(設定値をまとめて使うため)
import watchlist  # ウォッチリスト(追跡する銘柄の一覧)を管理するファイル


def fetch_one_ticker(ticker, date_from, date_to):
    """
    ティッカー1件分の株価データを取得し、pandasの「DataFrame」
    (表形式のデータを扱う入れ物)として返す関数。
    取得に失敗した場合は None(「何もない」を表すPythonの特別な値)を返す。

    引数(Parameters)
    ----------
    ticker : dict
        watchlist.json の中の1件分(key, label, symbol, kind などを持つ)
    date_from : datetime.date
        取得したい期間の開始日
    date_to : datetime.date
        取得したい期間の終了日(この日を含む)
    """
    print("  取得中: " + ticker["label"] + " (" + ticker["symbol"] + ") ...")

    try:
        yf_ticker = yf.Ticker(ticker["symbol"])
        # yfinanceの end は「その日を含まない」仕様なので、
        # date_to の翌日を指定することで date_to 当日分まで取得できるようにする
        history = yf_ticker.history(
            start=date_from,
            end=date_to + datetime.timedelta(days=1),
        )
    except Exception as e:
        # ネットワークエラーや、yfinance内部のエラーなどをまとめて受け止める
        print("    x 取得中にエラーが発生しました: " + str(e))
        return None

    if history.empty:
        print("    x データが取得できませんでした(空のデータが返ってきました)。")
        print("      config.py の symbol(銘柄コード)が正しいか確認してください。")
        return None

    print("    OK 取得成功(" + str(len(history)) + "日分)")
    return history


def fetch_all(tickers):
    """
    渡された「ティッカーの一覧(リスト)」のデータを取得し、
    data/ フォルダにCSVファイルとして保存するメインの処理。

    引数(Parameters)
    ----------
    tickers : list of dict
        watchlist.load_watchlist() が返すウォッチリスト(またはその一部)
    """
    # 保存先フォルダがなければ作る(exist_ok=True: すでにあってもエラーにしない)
    os.makedirs(config.DATA_DIR, exist_ok=True)

    # 取得する期間を計算する(「今日」から DAYS_BACK 日さかのぼる)
    today = datetime.date.today()
    date_from = today - datetime.timedelta(days=config.DAYS_BACK)
    date_to = today

    print("データ取得期間: " + date_from.strftime("%Y-%m-%d") + " 〜 " + date_to.strftime("%Y-%m-%d"))
    print("-" * 50)

    success_count = 0
    for ticker in tickers:
        history = fetch_one_ticker(ticker, date_from, date_to)
        if history is None:
            continue  # このティッカーは失敗。for文の次のティッカーに進む

        # yfinanceが返す表には Open/High/Low/Close/Volume 以外に
        # Dividends(配当)や Stock Splits(株式分割)といった列も含まれるが、
        # 本ツールで使うのは値動きに関する5列だけなので、それだけを取り出す
        columns_to_keep = ["Open", "High", "Low", "Close", "Volume"]
        trimmed = history[columns_to_keep]

        # ファイル名は「key.csv」にする(例: nikkei.csv, sony.csv)
        # index_label="Date" : 日付(表の一番左の列)の見出しを "Date" にする
        # date_format="%Y-%m-%d" : 日付を "2026-08-27" のような形式で保存する
        #   (plot_chart.py がこの形式を前提に読み込むため)
        file_path = os.path.join(config.DATA_DIR, ticker["key"] + ".csv")
        trimmed.to_csv(file_path, index_label="Date", date_format="%Y-%m-%d")

        success_count += 1

    print("-" * 50)
    print("完了: " + str(success_count) + " / " + str(len(tickers)) + " 件のデータを取得しました。")
    print("保存先フォルダ: " + os.path.abspath(config.DATA_DIR))

    if success_count == 0:
        print("")
        print("※ 1件も取得できませんでした。よくある原因:")
        print("   ・インターネットに接続されていない")
        print("   ・yfinanceのバージョンが古い(以下のコマンドで更新してみてください)")
        print("     pip install --upgrade yfinance")


# ------------------------------------------------------------
# このファイルを「直接」実行したときだけ fetch_all() を呼び出す、という書き方です。
# (他のファイルから import して部品として使うときには、自動実行されないようにするための
#  Pythonの定番テクニックです)
# ------------------------------------------------------------
if __name__ == "__main__":
    fetch_all(watchlist.load_watchlist())
