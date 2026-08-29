"""
predict_chart.py
------------------------------------------------------------
フェーズ7:値動き予測(predict.py)の結果をグラフに描画するファイル。
要件定義書 7.9節(値動き予測・売買シグナル機能)に対応します。

直近の実績(終値の折れ線)に続けて、predict.py が計算した上位3件の
「予測ライン」を、確率(参考値)付きで重ねて表示します。

【重要】ここで表示する予測ラインは、過去の似た値動きパターンのあとに
実際どうなったかを統計的に参考表示しているだけであり、将来の値動きを
保証するものではありません(12章の免責事項)。この注意書きは、
誤解を防ぐためグラフ内にも必ず表示します(7.9節の要件)。
"""

import os
import io
import datetime

import matplotlib.pyplot as plt

import plot_chart  # 日本語フォント探索を再利用する
import predict

# 3本の予測ラインの色(陽線・陰線で使っている赤・青とは別系統の配色にする)
PATTERN_COLORS = ["#2ca02c", "#9467bd", "#8c564b"]  # 緑・紫・茶

# グラフに表示する「直近の実績」のおおよその日数(表示を見やすくするため)
HISTORY_DISPLAY_DAYS = 90


def _recent_slice(dates, closes, display_count):
    """直近display_count件分の (日付, 終値) だけを取り出す。"""
    if len(dates) <= display_count:
        return dates, closes
    return dates[-display_count:], closes[-display_count:]


def _future_business_dates(start_date, count):
    """
    start_date の翌日以降、土日を除いた日付をcount件分生成する。
    グラフの目盛り表示用の「目安の日付」であり、祝日までは考慮していない
    簡易的なものなので、実際の取引日と完全には一致しない場合がある。
    """
    result = []
    current = start_date
    while len(result) < count:
        current = current + datetime.timedelta(days=1)
        if current.weekday() < 5:  # 0=月曜〜4=金曜だけを対象にする
            result.append(current)
    return result


def _build_figure(ticker, dates, closes, patterns, horizon=predict.DEFAULT_HORIZON,
                   display_days=HISTORY_DISPLAY_DAYS):
    """
    直近の値動き(実績)の折れ線に続けて、上位3件の予測ラインを重ねた
    figure(matplotlibの図)を組み立てて返す関数。ターミナル版
    (plot_prediction、画面に表示・ファイル保存する)とWeb版
    (render_prediction_png、PNG画像として返す。フェーズ8-5)の両方から、
    この関数を呼び出して同じ描画ロジックを再利用する。

    ticker    : ウォッチリストの1件(辞書)
    dates, closes : そのティッカーの全期間の日付・終値のリスト
    patterns  : predict.build_predicted_lines() が返す予測パターンのリスト
    """
    font_name = plot_chart.find_japanese_font()
    if font_name:
        plt.rcParams["font.family"] = font_name
    else:
        print("※ 日本語フォントが見つかりませんでした。グラフの日本語が文字化けするかもしれません。")
    plt.rcParams["axes.unicode_minus"] = False

    recent_dates, recent_closes = _recent_slice(dates, closes, display_days)

    fig, ax = plt.subplots(figsize=(12, 6))

    history_x = list(range(len(recent_closes)))
    ax.plot(history_x, recent_closes, color="#333333", linewidth=2,
            label=ticker["label"] + "(実績)")

    boundary_x = history_x[-1]
    last_price = recent_closes[-1]
    future_dates = _future_business_dates(dates[-1], horizon)

    for i, pattern in enumerate(patterns):
        color = PATTERN_COLORS[i % len(PATTERN_COLORS)]
        future_x = list(range(boundary_x, boundary_x + 1 + len(pattern["future_prices"])))
        future_y = [last_price] + pattern["future_prices"]
        direction_label = predict.DIRECTION_LABELS.get(pattern["direction"], pattern["direction"])
        based_on_text = pattern["based_on_date"].strftime("%Y-%m-%d") + "頃と類似"
        label = "予測{}(確率{:.0f}%・{}) [{}]".format(
            i + 1, pattern["probability_pct"], direction_label, based_on_text)
        ax.plot(future_x, future_y, color=color, linewidth=2, linestyle="--",
                marker="o", markersize=3, label=label)

    ax.axvline(boundary_x, color="gray", linewidth=1, linestyle=":")

    # X軸の目盛り:実績部分は実際の日付、予測部分は目安の営業日を使う
    all_dates_for_ticks = list(recent_dates) + future_dates
    all_x_for_ticks = list(range(len(all_dates_for_ticks)))
    tick_step = max(1, len(all_dates_for_ticks) // 12)
    tick_positions = all_x_for_ticks[::tick_step]
    tick_labels = [all_dates_for_ticks[i].strftime("%Y-%m-%d") for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")

    ax.set_ylabel("価格")
    ax.set_xlabel("日付(点線より右は予測区間・目安の営業日)")
    ax.set_title(ticker["label"] + " 値動き予測(参考情報・過去の類似パターンより)", fontsize=14)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.text(
        0.5, 0.01,
        "※ 過去の似た値動きパターンをもとにした統計的な参考情報です。将来の値動きを保証するものではなく、投資判断の根拠にはできません。",
        ha="center", fontsize=9, color="#555555",
    )

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return fig


def plot_prediction(ticker, dates, closes, patterns, horizon=predict.DEFAULT_HORIZON,
                     display_days=HISTORY_DISPLAY_DAYS):
    """
    直近の値動き(実績)の折れ線に続けて、上位3件の予測ラインを表示する
    (ターミナル版)。

    ticker    : ウォッチリストの1件(辞書)
    dates, closes : そのティッカーの全期間の日付・終値のリスト
    patterns  : predict.build_predicted_lines() が返す予測パターンのリスト
    """
    fig = _build_figure(ticker, dates, closes, patterns, horizon=horizon, display_days=display_days)

    output_path = "predict_chart.png"
    fig.savefig(output_path, dpi=150)
    print("予測チャートを保存しました: " + os.path.abspath(output_path))

    try:
        print("グラフのウィンドウを閉じると、プログラムが終了します。")
        plt.show()
    except Exception as e:
        print("(グラフウィンドウの表示に失敗しました: " + str(e) + ")")
        print("代わりに " + os.path.abspath(output_path) + " を開いて確認してください。")


def render_prediction_png(ticker, dates, closes, patterns, horizon=predict.DEFAULT_HORIZON,
                           display_days=HISTORY_DISPLAY_DAYS):
    """
    Web版(フェーズ8-5)用:値動き予測のグラフを、ファイル保存や
    ウィンドウ表示をせず、PNG画像のバイト列として返す関数。
    GUI版の値動き予測画面(/api/predict_chart.png)から呼び出す。
    """
    fig = _build_figure(ticker, dates, closes, patterns, horizon=horizon, display_days=display_days)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)  # Webサーバーは動き続けるプロセスなので、使い終わった図は必ず閉じてメモリを解放する
    buf.seek(0)
    return buf.getvalue()
