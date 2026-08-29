"""
app.py
------------------------------------------------------------
フェーズ8:ブラウザで動くGUI版(Webアプリ)の入り口。

これまでのフェーズ1〜7は、ターミナルの「メニュー番号を選ぶ」形式の
プログラム(main.py)として作ってきましたが、将来的にスマートフォンでも
使えるようにする(要件定義書8章の「PWA化」)ための第一歩として、
ブラウザで表示できるWebアプリ版を追加します。フレームワークにはFlask
(Pythonでよく使われる、比較的シンプルなWebアプリ用のライブラリ)を使って
います。

【段階的に進めます(要件定義書11章フェーズ8)】
これまでにGUI化したのは、次の5つです。
  ・ウォッチリストの一覧表示(前日比つき)【フェーズ8-1】
  ・複数銘柄の比較グラフ(折れ線・変化率、期間の切り替え)【フェーズ8-1】
  ・銘柄の表示・非表示の切り替え【フェーズ8-2】
  ・銘柄の追加・削除【フェーズ8-3】
  ・実額表示・ソロ表示(1銘柄だけを表示)【フェーズ8-4】
用語集、ニュース、詳細チャート(ローソク足・移動平均線・出来高)、
値動き予測といった機能は、まだWeb版には入っていません。次回以降の
フェーズで少しずつ追加していく予定です。それまでの間、これらの操作は
今まで通り
    python main.py
(ターミナル版)から行ってください。ウォッチリストのデータ
(watchlist.json)や株価データ(data/フォルダの中のCSV)は、ターミナル版・
Web版のどちらからも同じファイルを読み書きするので、両方を使い分けても
内容は共有されます(片方で変更した内容は、もう片方にもすぐ反映されます)。

実行方法:
    python app.py
起動したら、ブラウザで http://127.0.0.1:5000 を開いてください。
(デスクトップのアイコンをクリックして自動で開く設定は、README.mdの
 「フェーズ8: GUI(Web)版について」を参照してください)
"""

import os
import signal
import threading
import time

from flask import Flask, jsonify, render_template, request

import watchlist
import fetch_data
import plot_chart

app = Flask(__name__)


# ==============================================================
# ブラウザを閉じたら自動的にアプリを終了する仕組み(デスクトップの
# アイコンから起動したとき、今までは `pkill -f "python3 app.py"` を
# 手動で実行しないと終了できなかったが、「ブラウザを閉じたら自動で
# 終わってほしい」というご要望を受けて追加した)。
#
# 仕組み:
#   ・ブラウザ側(script.js)が、ページを開いている間、数秒おきに
#     /api/heartbeat を呼び出して「まだ使っています」の合図を送る。
#   ・サーバー側では、この見張り役スレッド(watchdog)が数秒おきに
#     「最後にheartbeatを受け取ってからどれくらい経ったか」を確認し、
#     HEARTBEAT_TIMEOUT_SECONDS 以上heartbeatが来なければ、ブラウザが
#     閉じられた(またはタブが閉じられた)とみなしてプロセスごと終了する。
#   ・起動直後、まだ一度もheartbeatを受け取っていない間は判定を行わない
#     (ブラウザがまだ開かれていないだけなのに、誤って終了しないため)。
#   ・複数のタブ・ウィンドウで開いている場合も、どれか1つが送るheartbeatで
#     生き続けるので、全部のタブ・ウィンドウを閉じたときだけ終了する。
_heartbeat_lock = threading.Lock()
_last_heartbeat_at = None  # 最後にheartbeatを受け取った時刻(time.time())。未受信ならNone。

HEARTBEAT_TIMEOUT_SECONDS = 10  # この秒数以上heartbeatが来なければ終了する
WATCHDOG_INTERVAL_SECONDS = 3   # この間隔で確認する


def _record_heartbeat():
    global _last_heartbeat_at
    with _heartbeat_lock:
        _last_heartbeat_at = time.time()


def _seconds_since_last_heartbeat():
    with _heartbeat_lock:
        last = _last_heartbeat_at
    if last is None:
        return None
    return time.time() - last


def _watchdog_loop():
    while True:
        time.sleep(WATCHDOG_INTERVAL_SECONDS)
        elapsed = _seconds_since_last_heartbeat()
        if elapsed is None:
            continue  # まだブラウザからのheartbeatを一度も受け取っていない
        if elapsed > HEARTBEAT_TIMEOUT_SECONDS:
            print("ブラウザが閉じられたようなので、アプリを終了します。")
            os.kill(os.getpid(), signal.SIGTERM)
            return


def start_watchdog():
    """
    ブラウザ監視用の見張り役スレッドを起動する。デーモンスレッド
    (daemon=True)にしているので、このスレッドが残っていても
    プログラム全体の終了(Ctrl+Cなど)を妨げない。
    """
    t = threading.Thread(target=_watchdog_loop, daemon=True)
    t.start()


@app.route("/")
def index():
    """トップページ(ウォッチリスト表示・グラフ表示の画面)を返す。"""
    period_options = [label for label, _ in plot_chart.PERIOD_OPTIONS]
    return render_template("index.html", period_options=period_options)


@app.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    """
    ブラウザ(script.js)がページを開いている間、数秒おきに呼び出すAPI。
    「まだ使っています」の合図として、最後に受け取った時刻を更新するだけの
    軽い処理。ブラウザを閉じたら自動的にアプリを終了する仕組み(本ファイル
    冒頭のwatchdog参照)のために追加した。
    """
    _record_heartbeat()
    return jsonify({"status": "ok"})


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
    比較グラフ用のデータ(表示中の銘柄の日付・数値の系列)をJSONで返すAPI。
    クエリパラメータ period (PERIOD_OPTIONSのインデックス) で期間を、
    mode ("percent" または "absolute") で表示モードを指定する(フェーズ8-4)。

    実額("absolute")表示は、ターミナル版と同じく表示中の銘柄がちょうど
    1つのときだけ許可する(7.3節。単位(円・ptなど)が銘柄ごとに違うため、
    複数銘柄を実額のまま重ねると値の小さい方が見えなくなってしまう)。
    それ以外の場合は、要求されても自動的に "percent" にフォールバックする。
    実際に使ったモードはレスポンスの "mode" に入れて返すので、画面側
    (script.js)はこれを見て表示モードの選択欄を実態に合わせて補正する。

    各系列には "unit"(単位。指数は"pt"、日本株は"¥"、米国株は"$")も
    含める。実額表示は¥なのか$なのかptなのか分かりにくいというご指摘を
    受けて追加した(plot_chart.get_unit参照)。
    """
    period_index = request.args.get("period", default=3, type=int)
    if period_index is None or period_index < 0 or period_index >= len(plot_chart.PERIOD_OPTIONS):
        period_index = 3
    period_label, period_days = plot_chart.PERIOD_OPTIONS[period_index]

    items = watchlist.load_watchlist()
    visible_items = [item for item in items if not item["hidden"]]

    requested_mode = request.args.get("mode", default="percent")
    if requested_mode not in ("percent", "absolute"):
        requested_mode = "percent"
    if requested_mode == "absolute" and len(visible_items) != 1:
        requested_mode = "percent"
    mode = requested_mode

    series_list = []
    for item in visible_items:
        dates, closes = plot_chart.load_series(item, quiet=True)
        if dates is None:
            continue
        dates, closes = plot_chart.filter_recent(dates, closes, period_days)
        if mode == "absolute":
            values = closes
        else:
            values = plot_chart.to_percent_change(closes)
        series_list.append({
            "label": item["label"],
            "kind": item["kind"],
            "color": item.get("color"),
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "values": values,
            "unit": plot_chart.get_unit(item),
        })

    return jsonify({"period_label": period_label, "series": series_list, "mode": mode})


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """
    「データを取得する」ボタンが押されたときのAPI。
    ターミナル版の「6」と同じく、fetch_data.fetch_all() を呼び出す。
    """
    items = watchlist.load_watchlist()
    fetch_data.fetch_all(items)
    return jsonify({"status": "ok", "count": len(items)})


@app.route("/api/toggle_hidden", methods=["POST"])
def api_toggle_hidden():
    """
    ウォッチリストの1件の「表示中/非表示」を切り替えるAPI(フェーズ8-2)。
    ターミナル版のメニュー「3: 銘柄を非表示にする」「4: 非表示中の銘柄を
    再表示する」と同じ処理(watchlist.set_hidden)を、GUI版のボタンから
    呼び出せるようにしたもの。基本の2指数(日経平均・NASDAQ)も、削除は
    できないが非表示にすることはできる仕様(7.1節)のため、ここでは
    kindによる制限はかけていない。
    リクエストボディ(JSON)例: {"key": "keycoffee", "hidden": true}
    """
    payload = request.get_json(silent=True) or {}
    key = payload.get("key")
    hidden = bool(payload.get("hidden"))

    items = watchlist.load_watchlist()
    index = next((i for i, item in enumerate(items) if item["key"] == key), None)
    if index is None:
        return jsonify({"status": "error", "message": "指定された銘柄が見つかりません。"}), 404

    ok, message = watchlist.set_hidden(items, index, hidden)
    if not ok:
        return jsonify({"status": "error", "message": message}), 400
    return jsonify({"status": "ok", "message": message})


@app.route("/api/lookup_company", methods=["POST"])
def api_lookup_company():
    """
    銘柄追加(フェーズ8-3)の、追加前の下調べ用API。
    証券コード・シンボルを受け取り、
      ・個別銘柄の登録数がすでに上限に達していないか
      ・同じシンボルがすでに登録されていないか
    をチェックしたうえで、yfinanceで会社名の自動取得を試みる。
    (ターミナル版 main.py の handle_add 前半と同じ考え方をAPI化したもの。
     ここではまだウォッチリストへの追加は行わない。実際の追加は
     この結果を画面で確認してもらってから /api/add_company で行う)
    リクエストボディ(JSON)例: {"input": "7203"}
    """
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("input") or "").strip()
    if user_input == "":
        return jsonify({"status": "error", "message": "証券コード・シンボルを入力してください。"}), 400

    items = watchlist.load_watchlist()
    if watchlist.count_companies(items) >= watchlist.MAX_COMPANIES:
        message = ("個別銘柄はすでに上限の" + str(watchlist.MAX_COMPANIES) +
                   "社に達しています。追加するには、先に何か1社を削除してください。")
        return jsonify({"status": "error", "message": message}), 400

    symbol = watchlist.normalize_symbol(user_input)
    if watchlist.find_by_symbol(items, symbol) is not None:
        return jsonify({"status": "error", "message": "そのシンボル(" + symbol + ")はすでにウォッチリストに登録されています。"}), 400

    name = watchlist.fetch_company_name(symbol)
    return jsonify({"status": "ok", "symbol": symbol, "name": name})


@app.route("/api/add_company", methods=["POST"])
def api_add_company():
    """
    銘柄をウォッチリストに追加するAPI(フェーズ8-3)。
    事前に /api/lookup_company で確認したシンボル・会社名に、市場区分・
    事業内容(どちらも空欄可・その場合は「不明」「(未入力)」になる)を
    添えて呼び出す。実際の登録処理は watchlist.add_company が行う
    (ターミナル版と共通)。
    リクエストボディ(JSON)例:
      {"symbol": "7203.T", "name": "トヨタ自動車", "market": "東証プライム", "business": "自動車"}
    """
    payload = request.get_json(silent=True) or {}
    symbol = (payload.get("symbol") or "").strip()
    name = (payload.get("name") or "").strip()
    market = (payload.get("market") or "").strip() or "不明"
    business = (payload.get("business") or "").strip() or "(未入力)"

    if symbol == "" or name == "":
        return jsonify({"status": "error", "message": "シンボルと会社の表示名は必須です。"}), 400

    items = watchlist.load_watchlist()
    ok, message = watchlist.add_company(items, symbol, name, market, business)
    if not ok:
        return jsonify({"status": "error", "message": message}), 400
    return jsonify({"status": "ok", "message": message})


@app.route("/api/remove_company", methods=["POST"])
def api_remove_company():
    """
    ウォッチリストから1件を完全に削除するAPI(フェーズ8-3)。
    「削除」であって「非表示」ではないため、元に戻せない(データも消える)。
    基本の2指数(日経平均・NASDAQ)は削除できない仕様のため、
    watchlist.remove_company側でチェックしてエラーメッセージを返す。
    リクエストボディ(JSON)例: {"key": "keycoffee"}
    """
    payload = request.get_json(silent=True) or {}
    key = payload.get("key")

    items = watchlist.load_watchlist()
    index = next((i for i, item in enumerate(items) if item["key"] == key), None)
    if index is None:
        return jsonify({"status": "error", "message": "指定された銘柄が見つかりません。"}), 404

    ok, message = watchlist.remove_company(items, index)
    if not ok:
        return jsonify({"status": "error", "message": message}), 400
    return jsonify({"status": "ok", "message": message})


@app.route("/api/solo_display", methods=["POST"])
def api_solo_display():
    """
    「1つの銘柄だけを表示する(ソロ表示)」API(フェーズ8-4)。
    指定した1件だけを表示中にし、それ以外の全件を非表示にする。
    ターミナル版のメニュー「9」(main.handle_solo)と同じ処理を、指数・
    個別銘柄を問わずGUIから呼び出せるようにしたもの。データを削除する
    わけではないので、「全ての銘柄を表示に戻す」(/api/show_all)でいつでも
    元に戻せる。
    リクエストボディ(JSON)例: {"key": "keycoffee"}
    """
    payload = request.get_json(silent=True) or {}
    key = payload.get("key")

    items = watchlist.load_watchlist()
    index = next((i for i, item in enumerate(items) if item["key"] == key), None)
    if index is None:
        return jsonify({"status": "error", "message": "指定された銘柄が見つかりません。"}), 404

    for i, item in enumerate(items):
        item["hidden"] = (i != index)
    watchlist.save_watchlist(items)

    message = items[index]["label"] + " だけを表示するようにしました(他の銘柄はすべて非表示になりました)。"
    return jsonify({"status": "ok", "message": message})


@app.route("/api/show_all", methods=["POST"])
def api_show_all():
    """
    「全ての銘柄を表示に戻す」API(フェーズ8-4)。
    ターミナル版のメニュー「10」(main.handle_show_all)と同じ処理。
    ソロ表示や個別の非表示操作で隠した銘柄を、まとめて表示中に戻す。
    """
    items = watchlist.load_watchlist()
    if len(items) == 0:
        return jsonify({"status": "error", "message": "ウォッチリストに何も登録されていません。"}), 400

    for item in items:
        item["hidden"] = False
    watchlist.save_watchlist(items)

    message = "全ての銘柄(" + str(len(items)) + " 件)を表示に戻しました。"
    return jsonify({"status": "ok", "message": message})


if __name__ == "__main__":
    print("値動きウォッチ(Web版)を起動します。")
    print("ブラウザで http://127.0.0.1:5000 を開いてください。")
    print("(ブラウザを閉じると、しばらくして自動的にこのアプリも終了します)")
    start_watchdog()
    app.run(host="127.0.0.1", port=5000, debug=False)
