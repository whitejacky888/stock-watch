"""
fetch_data.py
------------------------------------------------------------
stooq.com から、config.py で指定した指数・銘柄の株価データを
CSV形式でダウンロードして、data/ フォルダにファイルとして保存するプログラムです。

【このファイルでやっていること(全体の流れ)】
  1. config.py から「取得したいティッカーの一覧」と「APIキー」を読み込む
  2. ティッカー(指数・銘柄)を1つずつ、stooq.com にリクエスト(お願い)を送る
  3. 返ってきたCSVのテキストをファイルとして保存する
  4. うまくいかなかった場合は、エラーの内容を分かりやすく表示する

このファイル単体で実行すると、データ取得だけを行います。
    python fetch_data.py
"""

import os
import datetime

import requests  # インターネット上のデータを取得するための定番ライブラリ

import config  # 同じフォルダにある config.py を読み込む(設定値をまとめて使うため)


def build_stooq_url(symbol, date_from, date_to):
    """
    stooq.com からCSVデータをダウンロードするためのURLを組み立てる関数。

    引数(Parameters)
    ----------
    symbol : str
        stooq.com上のシンボル(例: "^nkx", "6758.jp")
    date_from : str
        取得したい期間の開始日("20250101" のようなYYYYMMDD形式)
    date_to : str
        取得したい期間の終了日(同上)

    戻り値(Returns)
    -------
    str
        完成したURL文字列
    """
    # stooq.com のCSVダウンロード用エンドポイント(URLの決まった形)
    #   s      = シンボル(何のデータが欲しいか)
    #   i      = 間隔("d"=日次、"w"=週次、"m"=月次)
    #   d1, d2 = 取得したい期間の開始日・終了日(YYYYMMDD形式)
    #   apikey = 個人のAPIキー(2026年4月以降、stooq側の仕様変更により必須)
    base_url = "https://stooq.com/q/d/l/"
    query = (
        "?s=" + symbol
        + "&i=d"
        + "&d1=" + date_from
        + "&d2=" + date_to
        + "&apikey=" + config.STOOQ_API_KEY
    )
    return base_url + query


def fetch_one_ticker(ticker, date_from, date_to):
    """
    ティッカー1件分のCSVデータをダウンロードし、テキストとして返す関数。
    取得に失敗した場合は None(「何もない」を表すPythonの特別な値)を返す。
    """
    url = build_stooq_url(ticker["symbol"], date_from, date_to)
    print("  取得中: " + ticker["label"] + " (" + ticker["symbol"] + ") ...")

    try:
        # timeout=15 : 15秒たっても応答がなければあきらめる(プログラムが固まるのを防ぐ)
        # headers を付けているのは、一部のサイトが「ブラウザ以外からのアクセス」を
        # 拒否することがあるための、念のための対策
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    except requests.exceptions.RequestException as e:
        # ネットワークエラー(ネットに繋がっていない、サーバーが応答しない等)
        print("    x ネットワークエラー: " + str(e))
        return None

    if response.status_code != 200:
        print("    x サーバーからエラーが返されました(HTTP " + str(response.status_code) + ")")
        return None

    csv_text = response.text

    # APIキーが未設定・間違っている場合、stooqはCSVの代わりに
    # 「apikey」や「exceeded(制限を超えました)」といった文字を含む
    # エラーメッセージを返してくることがあるので、それを検出する
    lowered = csv_text.lower()
    if "apikey" in lowered or "exceeded" in lowered:
        print("    x APIキーが未設定か、正しくない可能性があります。")
        print("      config.py の STOOQ_API_KEY を確認してください。")
        print("      (サーバーからの応答の先頭: " + repr(csv_text[:120]) + ")")
        return None

    # データが1行(見出しの行)しかない、または空っぽ ＝ 実質エラーなのではじく
    lines = csv_text.strip().splitlines()
    if len(lines) < 2:
        print("    x データが取得できませんでした(空のデータが返ってきました)。")
        return None

    print("    OK 取得成功(" + str(len(lines) - 1) + "日分)")
    return csv_text


def fetch_all():
    """
    config.py に登録されているすべてのティッカーのデータを取得し、
    data/ フォルダにCSVファイルとして保存するメインの処理。
    """
    # 保存先フォルダがなければ作る(exist_ok=True: すでにあってもエラーにしない)
    os.makedirs(config.DATA_DIR, exist_ok=True)

    # 取得する期間を計算する(「今日」から DAYS_BACK 日さかのぼる)
    today = datetime.date.today()
    date_from = (today - datetime.timedelta(days=config.DAYS_BACK)).strftime("%Y%m%d")
    date_to = today.strftime("%Y%m%d")

    print("データ取得期間: " + date_from + " 〜 " + date_to)
    print("-" * 50)

    success_count = 0
    for ticker in config.TICKERS:
        csv_text = fetch_one_ticker(ticker, date_from, date_to)
        if csv_text is None:
            continue  # このティッカーは失敗。for文の次のティッカーに進む

        # ファイル名は「key.csv」にする(例: nikkei.csv, sony.csv)
        file_path = os.path.join(config.DATA_DIR, ticker["key"] + ".csv")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(csv_text)

        success_count += 1

    print("-" * 50)
    print("完了: " + str(success_count) + " / " + str(len(config.TICKERS)) + " 件のデータを取得しました。")
    print("保存先フォルダ: " + os.path.abspath(config.DATA_DIR))

    if success_count == 0:
        print("")
        print("※ 1件も取得できませんでした。よくある原因:")
        print("   ・config.py の STOOQ_API_KEY が空、または間違っている")
        print("   ・インターネットに接続されていない")


# ------------------------------------------------------------
# このファイルを「直接」実行したときだけ fetch_all() を呼び出す、という書き方です。
# (他のファイルから import して部品として使うときには、自動実行されないようにするための
#  Pythonの定番テクニックです)
# ------------------------------------------------------------
if __name__ == "__main__":
    fetch_all()
