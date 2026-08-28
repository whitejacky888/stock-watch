"""
candle_chart.py
------------------------------------------------------------
1つの指数・銘柄について、「ローソク足チャート」「移動平均線」
「出来高」を表示するファイルです。
要件定義書 7.3節(将来拡張機能)・11章フェーズ6(ローソク足→移動平均線→
出来高の優先順で追加)に対応します。

【なぜ複数銘柄の比較グラフ(plot_chart.py)と別ファイルにしたか】
ローソク足は「始値・高値・安値・終値」という4つの価格を1本1本表示する
細かいグラフのため、複数の指数・銘柄を重ねて表示するのには向きません
(要件定義書7.3節でも「単一銘柄選択時」の機能として想定されています)。
そのため、1つの銘柄をじっくり見るための「詳細チャート」として、
plot_chart.py(複数銘柄の比較用の折れ線グラフ)とは別に実装しています。

【ローソク足の読み方(3.2節のおさらい)】
1本のローソクは、その日の「始値・終値・高値・安値」を表す。
終値が始値より高ければ「陽線」(このツールでは赤)、
低ければ「陰線」(このツールでは青)で描く。上下に伸びる細い線
(ヒゲ)は、その日の高値・安値を表す。
"""

import os
import csv
import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import config
import plot_chart  # 日本語フォント探索など、共通の処理を再利用する

# 移動平均線を計算する日数(要件定義書4章の用語集の例にならい、25日を既定値にする)
DEFAULT_MA_DAYS = 25

# 陽線(上昇)・陰線(下落)の色。前日比の色分け(main.py)と揃えている。
UP_COLOR = "#d62728"    # 赤(暖色)
DOWN_COLOR = "#1f77b4"  # 青(寒色)


def load_ohlcv(ticker, quiet=False):
    """
    1つのティッカーのCSVファイルを読み込み、日付・始値・高値・安値・終値・
    出来高のリストをまとめた辞書として返す関数。
    データが無い/壊れている場合は None を返す。
    """
    file_path = os.path.join(config.DATA_DIR, ticker["key"] + ".csv")

    if not os.path.exists(file_path):
        if not quiet:
            print("  x " + ticker["label"] + ": データファイルが見つかりません(" + file_path + ")")
            print("     先に「6: データを取得してグラフを表示する」などでデータを取得してください。")
        return None

    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        lower_to_original = {name.lower(): name for name in fieldnames}

        needed = ["date", "open", "high", "low", "close", "volume"]
        cols = {key: lower_to_original.get(key) for key in needed}
        if any(cols[key] is None for key in needed):
            if not quiet:
                print("  x " + ticker["label"] + ": CSVの形式が想定と違います(列名: " + str(fieldnames) + ")")
            return None

        for row in reader:
            try:
                d = datetime.datetime.strptime(row[cols["date"]], "%Y-%m-%d").date()
                o = float(row[cols["open"]])
                h = float(row[cols["high"]])
                low_v = float(row[cols["low"]])
                c = float(row[cols["close"]])
                v = float(row[cols["volume"]])
            except (ValueError, KeyError):
                # 日付や数値としてうまく読み取れない行(空行など)はスキップする
                continue
            dates.append(d)
            opens.append(o)
            highs.append(h)
            lows.append(low_v)
            closes.append(c)
            volumes.append(v)

    if len(dates) == 0:
        if not quiet:
            print("  x " + ticker["label"] + ": 有効なデータが1件もありませんでした。")
        return None

    return {"dates": dates, "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}


def _filter_recent(data, period_days):
    """
    OHLCVデータ(辞書)から、直近period_days日分だけを取り出す関数。
    plot_chart.filter_recent と同じ考え方(データの中の最新日を基準にする)。
    period_days が None の場合は、絞り込みをせずそのまま返す。
    """
    if period_days is None or len(data["dates"]) == 0:
        return data

    latest = data["dates"][-1]
    cutoff = latest - datetime.timedelta(days=period_days)

    keep_indexes = [i for i, d in enumerate(data["dates"]) if d >= cutoff]
    if len(keep_indexes) == 0:
        # 絞り込んだ結果0件になった場合は、元のデータをそのまま返す
        return data

    return {key: [values[i] for i in keep_indexes] for key, values in data.items()}


def _moving_average(closes, window):
    """
    終値のリストから、window日移動平均のリストを計算する関数。
    データがwindow日分に満たない先頭部分は None にする
    (matplotlibはNoneの点を線でつながずに飛ばして描画してくれる)。
    """
    result = []
    for i in range(len(closes)):
        if i + 1 < window:
            result.append(None)
        else:
            segment = closes[i + 1 - window : i + 1]
            result.append(sum(segment) / window)
    return result


def plot_candlestick(ticker, period_days=None, period_label=None, show_ma=True, ma_days=DEFAULT_MA_DAYS):
    """
    1つのティッカーについて、ローソク足チャート(上段)・出来高(下段)を
    表示する関数。show_ma=True のとき、上段に移動平均線を重ねて表示する。

    データが取得できていない場合は、何もせずメッセージだけ表示して終了する
    (呼び出し元でエラー処理をしなくてよいようにするため)。
    """
    data = load_ohlcv(ticker)
    if data is None:
        return

    data = _filter_recent(data, period_days)
    dates = data["dates"]
    opens, highs, lows, closes, volumes = data["open"], data["high"], data["low"], data["close"], data["volume"]

    font_name = plot_chart.find_japanese_font()
    if font_name:
        plt.rcParams["font.family"] = font_name
    else:
        print("※ 日本語フォントが見つかりませんでした。グラフの日本語が文字化けするかもしれません。")
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax_price, ax_volume) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    # 日付を「0, 1, 2, ...」という等間隔の番号として扱う
    # (株式市場が休みの土日・祝日をグラフ上で詰めて、隙間ができないようにするため)
    x_positions = list(range(len(dates)))
    body_width = 0.6

    for i in x_positions:
        is_up = closes[i] >= opens[i]
        color = UP_COLOR if is_up else DOWN_COLOR

        # ヒゲ(その日の高値〜安値を結ぶ細い線)
        ax_price.plot([i, i], [lows[i], highs[i]], color=color, linewidth=1)

        # 実体(始値〜終値を表す四角形)
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])
        if body_height == 0:
            # 始値と終値がぴったり同じ日は、四角が見えなくなってしまうので、
            # ごく薄い高さを持たせて「横線」として見えるようにする
            body_height = max((highs[i] - lows[i]) * 0.01, 0.01)
        rect = mpatches.Rectangle(
            (i - body_width / 2, body_bottom), body_width, body_height,
            facecolor=color, edgecolor=color,
        )
        ax_price.add_patch(rect)

    if show_ma:
        ma_values = _moving_average(closes, ma_days)
        ax_price.plot(x_positions, ma_values, color="#ff9900", linewidth=1.5,
                      label=str(ma_days) + "日移動平均線")
        ax_price.legend(loc="upper left", fontsize=9)

    ax_price.set_ylabel("価格")
    period_text = period_label if period_label else "全期間"
    ax_price.set_title(ticker["label"] + " ローソク足チャート(" + period_text + ")", fontsize=14)
    ax_price.grid(True, alpha=0.3)

    # ---- 出来高(下段の棒グラフ)。その日が陽線か陰線かで色を揃える ----
    volume_colors = [UP_COLOR if closes[i] >= opens[i] else DOWN_COLOR for i in x_positions]
    ax_volume.bar(x_positions, volumes, color=volume_colors, width=body_width)
    ax_volume.set_ylabel("出来高")
    ax_volume.set_xlabel("日付")
    ax_volume.grid(True, alpha=0.3)

    # ---- X軸の目盛りを日付ラベルにする(全部表示すると詰まりすぎるので間引く) ----
    tick_step = max(1, len(dates) // 10)
    tick_positions = x_positions[::tick_step]
    tick_labels = [dates[i].strftime("%Y-%m-%d") for i in tick_positions]
    ax_volume.set_xticks(tick_positions)
    ax_volume.set_xticklabels(tick_labels, rotation=45, ha="right")

    fig.tight_layout()

    # ---- 画像としても保存しておく(グラフウィンドウが開けない環境向け) ----
    output_path = "candle_chart.png"
    fig.savefig(output_path, dpi=150)
    print("ローソク足チャートを保存しました: " + os.path.abspath(output_path))

    try:
        print("グラフのウィンドウを閉じると、プログラムが終了します。")
        plt.show()
    except Exception as e:
        print("(グラフウィンドウの表示に失敗しました: " + str(e) + ")")
        print("代わりに " + os.path.abspath(output_path) + " を開いて確認してください。")
