"""
app.py
------------------------------------------------------------
フェーズ8-1:ブラウザで動くGUI版(Webアプリ)の入り口。

これまでのフェーズ1〜7は、ターミナルの「メニュー番号を選ぶ」形式の
プログラム(main.py)として作ってきましたが、将来的にスマートフォンでも
使えるようにする(要件定義書8章の「PWA化」)ための第一歩として、
ブラウザで表示できるWebアプリ版を追加します。フレームワークにはFlask
(Pythonでよく使われる、比較的シンプルなWebアプリ用のライブラリ)を使って
います。

【段階的に進めます(要件定義書11章フェーズ8)】
今回(フェーズ8-1)でGUI化したのは、次の2つだけです。
  ・ウォッチリストの一覧表示(前日比つき)
  ・複数銘柄の比較グラフ(折れ線・変化率、期間の切り替え)
銘柄の追加・非表示・削除、実額表示、用語集、ニュース、詳細チャート
(ローソク足・移動平均線・出来高)、値動き予測といった機能は、まだ
Web版には入っていません。次回以降のフェーズで少しずつ追加していく
予定です。それまでの間、これらの操作は今まで通り
    python main.py
(ターミナル版)から行ってください。ウォッチリストのデータ
(watchlist.json)や株価データ(data/フォルダの中のCSV)は、ターミナル版・
Web版のどちらからも同じファイルを読み書きするので、両方を使い分けても
内容は共有されます(片方で追加した銘柄は、もう片方にもすぐ反映されます)。

実行方法:
    python app.py
起動したら、ブラウザで http://127.0.0.1:5000 を開いてください。
(デスクトップのアイコンをクリックして自動で開く設定は、README.mdの
 「フェーズ8: GUI(Web)版について」を参照してください)
"""

from flask import Flask, jsonify, render_template, request

import watchlist
import fetch_data
import plot_chart

app = Flask(__name__)


@app.route("/")
def index():
    """トップページ(ウォッチリスト表示・グラフ表示の画面)を返す。"""
    period_options = [label for label, _ in plot_chart.PERIOD_OPTIONS]
    return render_template("index.html", period_options=period_options)


@app.route("/api/watchlist")
def api_watchlist():
    """
    ウォッチリストの中身(前日比つき)をJSON形式で返すAPI。
    画面側(script.js)がこれを取得して、一覧表を描画する。
    """
    items = watchlist.load_watchlist()
    result = []
    for item in items:
        diff, pct = plot_chart.get_latest_change(item)
        result.append({
            "key": item["key"],
            "label": item["label"],
            "symbol": item["symbol"],
            "kind": item["kind"],
            "hidden": item["hidden"],
            "market": item["market"],
            "business": item["business"],
            "color": item.get("color"),
            "change_diff": diff,
            "change_pct": pct,
        })
    return jsonify(result)


@app.route("/api/chart_data")
def api_chart_data():
    """
    比較グラフ用のデータ(表示中の銘柄の日付・変化率の系列)をJSONで返すAPI。
    クエリパラメータ period (PERIOD_OPTIONSのインデックス) で期間を指定する。
    """
    period_index = request.args.get("period", default=3, type=int)
    if period_index is None or period_index < 0 or period_index >= len(plot_chart.PERIOD_OPTIONS):
        period_index = 3
    period_label, period_days = plot_chart.PERIOD_OPTIONS[period_index]

    items = watchlist.load_watchlist()
    visible_items = [item for item in items if not item["hidden"]]

    series_list = []
    for item in visible_items:
        dates, closes = plot_chart.load_series(item, quiet=True)
        if dates is None:
            continue
        dates, closes = plot_chart.filter_recent(dates, closes, period_days)
        pct_values = plot_chart.to_percent_change(closes)
        series_list.append({
            "label": item["label"],
            "kind": item["kind"],
            "color": item.get("color"),
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "values": pct_values,
        })

    return jsonify({"period_label": period_label, "series": series_list})


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """
    「データを取得する」ボタンが押されたときのAPI。
    ターミナル版の「6」と同じく、fetch_data.fetch_all() を呼び出す。
    """
    items = watchlist.load_watchlist()
    fetch_data.fetch_all(items)
    return jsonify({"status": "ok", "count": len(items)})


if __name__ == "__main__":
    print("値動きウォッチ(Web版)を起動します。")
    print("ブラウザで http://127.0.0.1:5000 を開いてください。")
    app.run(host="127.0.0.1", port=5000, debug=False)
