"""
predict.py
------------------------------------------------------------
フェーズ7:値動き予測・売買シグナル機能(要件定義書 7.9節)。

■ 算出方法(要件定義書 v0.16にて確定・v0.17にて移動平均線を組み合わせて
   拡張。13章の「引き続き検討中の項目」にあった「予測ラインの算出方法」は、
   以下の「過去の似たパターン探し」方式で実装しています。AIサービスは
   使っていません。

  1. 直近window日分(既定20営業日)について、(a)終値の変化率パターン
     (その期間の始点を0%とした変化率。2.4節と同じ考え方)と、
     (b)移動平均線からの乖離率パターン(終値が25日移動平均線からどれだけ
     離れているか、日ごとの%)の2種類を組み合わせて「現在の値動きパターン」
     とする(v0.17で追加。ご指定により出来高は組み合わせていない)。
  2. 同じ銘柄の過去データ全体から、同じ長さ(window日)のパターンを1日ずつ
     ずらしながらすべて取り出し、現在のパターンと(a)(b)それぞれどれだけ
     形が似ているか(差の二乗和)を計算し、合計したものを類似度とする
     (値が小さいほど似ている)。直近のデータ(現在のパターンと重なる区間)や、
     移動平均線がまだ計算できない期間(データの先頭付近)は比較対象から除外する。
  3. 似ている順に並べ、開始日が近すぎるものばかり選ばれて偏らないように
     一定日数以上離れたものだけを選びながら、代表的な上位3件を選ぶ。
  4. 選んだ各過去パターンについて、「その後horizon日分(既定10営業日)に
     実際どう動いたか」を取り出し、それを現在の株価に当てはめたものを
     「予測ライン」とする。
  5. 確率(参考値)は、似ている順の上位pool_size件(既定30件)の過去パターン
     のうち、その後の値動きが「上昇」「下降」「横ばい」のどれに該当したかを
     集計し、表示する各パターンが属する分類の出現割合(%)として計算する。
  6. 売買シグナルは、表示する3パターンを確率で重み付けした平均的な方向性
     から、「買い時の目安」「売り時の目安」「様子見」を参考として決める。

★ 重要な注意 ★
ここで計算する「予測ライン」「確率」「売買シグナル」は、あくまで
過去の似たような値動きのあとに実際どうなったか、という統計的な
参考情報です。将来の値動きを保証したり、投資判断の根拠となる
ものではありません(12章の免責事項を参照)。
"""

import candle_chart  # OHLCVデータの読み込みを再利用する

DEFAULT_WINDOW = 20       # 「現在の値動きパターン」として使う日数(営業日)
DEFAULT_HORIZON = 10      # その後何日分(営業日)を予測ラインにするか
DEFAULT_TOP_N = 3         # 表示する予測パターンの数(要件定義書の指定通り3)
DEFAULT_POOL_SIZE = 30    # 確率計算に使う「類似パターンの母集団」の件数
MIN_GAP_DAYS = 10         # 表示用に選ぶ過去パターン同士の開始日の最低間隔
FLAT_THRESHOLD_PCT = 2.0  # この範囲(±2%)以内の変化は「横ばい」とみなす

# 類似パターン探しに組み合わせる移動平均線の日数(v0.17)。
# 「14: 詳細チャートを表示する」の既定値(candle_chart.DEFAULT_MA_DAYS)と揃えている。
MA_DAYS_FOR_PATTERN = candle_chart.DEFAULT_MA_DAYS

DIRECTION_LABELS = {
    "up": "上昇",
    "down": "下降",
    "flat": "横ばい",
}


def _to_pct_change(values):
    """
    値のリストを、「最初の値を0%とした変化率(%)」のリストに変換する。
    plot_chart.to_percent_change() と同じ考え方(2.4節)。
    """
    base = values[0]
    if base == 0:
        return [0.0 for _ in values]
    return [(v / base - 1.0) * 100.0 for v in values]


def _moving_average(closes, window):
    """
    終値のリストから、window日移動平均のリストを計算する。
    candle_chart._moving_average と同じ考え方(データがwindow日分に
    満たない先頭部分は None にする)。
    """
    result = []
    for i in range(len(closes)):
        if i + 1 < window:
            result.append(None)
        else:
            segment = closes[i + 1 - window: i + 1]
            result.append(sum(segment) / window)
    return result


def _to_ma_position(values, ma_values):
    """
    終値のリストを、対応する移動平均線からの乖離率(%)のリストに変換する。
    (終値 - 移動平均) / 移動平均 × 100。移動平均がまだ計算できない日は
    None を返す(呼び出し元で「MAが揃っている区間かどうか」の判定に使う)。
    """
    result = []
    for v, ma in zip(values, ma_values):
        if ma is None or ma == 0:
            result.append(None)
        else:
            result.append((v / ma - 1.0) * 100.0)
    return result


def _distance(pattern_a, pattern_b):
    """
    2つの値動きパターン(変化率のリスト)がどれだけ似ているかを表す数値。
    値が小さいほど、形が似ていることを意味する(差の二乗和)。
    """
    total = 0.0
    for a, b in zip(pattern_a, pattern_b):
        diff = a - b
        total += diff * diff
    return total


def _classify_direction(final_pct_change):
    """その後の値動き(最終的な変化率)を、上昇・下降・横ばいの3つに分類する。"""
    if final_pct_change > FLAT_THRESHOLD_PCT:
        return "up"
    elif final_pct_change < -FLAT_THRESHOLD_PCT:
        return "down"
    else:
        return "flat"


def find_similar_patterns(closes, window=DEFAULT_WINDOW, horizon=DEFAULT_HORIZON,
                           top_n=DEFAULT_TOP_N, pool_size=DEFAULT_POOL_SIZE,
                           min_gap_days=MIN_GAP_DAYS):
    """
    終値のリスト(古い日付→新しい日付の順)から、「現在の値動きパターン」に
    似た過去のパターンを探す。

    戻り値: (selected, pool) のタプル。
      selected: 表示用に選んだ上位top_n件(確率計算前の情報を含む辞書のリスト)
      pool:     確率計算用の母集団(似ている順にpool_size件)
      データが足りない場合は (None, None) を返す。
    """
    n = len(closes)
    if n < window + horizon + 1:
        return None, None

    # v0.17: 終値の変化率パターンに加えて、移動平均線からの乖離率パターンも
    # 組み合わせて類似度を判定する(ご指定により出来高は組み合わせない)。
    ma_values = _moving_average(closes, MA_DAYS_FOR_PATTERN)

    current_start = n - window
    current_pattern = _to_pct_change(closes[current_start:n])
    current_ma_pattern = _to_ma_position(closes[current_start:n], ma_values[current_start:n])
    if any(v is None for v in current_ma_pattern):
        # 直近window日分に移動平均線がまだ計算できない日が含まれる
        # (データがごく短い場合)。組み合わせ判定ができないため、
        # 「データ不足」として扱う。
        return None, None

    all_candidates = []
    last_valid_start = n - window - horizon  # これより後ろから始めると横幅が足りない
    for start in range(0, last_valid_start + 1):
        # 「現在のパターン」と重なる区間は、比較対象から除外する
        if start + window > current_start:
            continue

        hist_ma_pattern = _to_ma_position(closes[start:start + window], ma_values[start:start + window])
        if any(v is None for v in hist_ma_pattern):
            # この過去区間はまだ移動平均線が計算できていない(データの先頭付近)ため、
            # 比較対象から除外する。
            continue

        hist_pattern = _to_pct_change(closes[start:start + window])
        dist = _distance(current_pattern, hist_pattern) + _distance(current_ma_pattern, hist_ma_pattern)

        # そのパターンの直後、horizon日分の値動き(パターン終了日を0%とした変化率)
        outcome_slice = closes[start + window - 1: start + window + horizon]
        outcome_pct_full = _to_pct_change(outcome_slice)
        outcome_pct = outcome_pct_full[1:]  # 先頭の0%(基準日そのもの)を除く
        if len(outcome_pct) == 0:
            continue

        final_pct = outcome_pct[-1]
        all_candidates.append({
            "start_index": start,
            "distance": dist,
            "outcome_pct": outcome_pct,
            "final_pct": final_pct,
            "direction": _classify_direction(final_pct),
        })

    if len(all_candidates) == 0:
        return None, None

    all_candidates.sort(key=lambda c: c["distance"])

    # 確率計算用の母集団(似ている順にpool_size件。件数が足りなければ全件)
    pool = all_candidates[:pool_size]

    # 表示用の上位top_n件は、開始日が近すぎるものが重複して選ばれないようにする
    selected = []
    for c in all_candidates:
        too_close = False
        for s in selected:
            if abs(c["start_index"] - s["start_index"]) < min_gap_days:
                too_close = True
                break
        if not too_close:
            selected.append(c)
        if len(selected) >= top_n:
            break

    return selected, pool


def calc_probability(candidate, pool):
    """
    母集団(pool)の中で、candidateと同じ方向(上昇/下降/横ばい)になった
    ものが占める割合(%)を返す。これを「確率(参考値)」として表示する。
    """
    if not pool:
        return 0.0
    same_direction_count = sum(1 for p in pool if p["direction"] == candidate["direction"])
    return (same_direction_count / len(pool)) * 100.0


def build_predicted_lines(ticker, window=DEFAULT_WINDOW, horizon=DEFAULT_HORIZON,
                           top_n=DEFAULT_TOP_N, pool_size=DEFAULT_POOL_SIZE):
    """
    main.py から呼び出す、フェーズ7のメイン処理。

    戻り値: (dates, closes, patterns) のタプル。
      dates, closes: そのティッカーの全期間の日付・終値のリスト(グラフ描画用)
      patterns: 確率が高い順に並べた辞書のリスト。各要素は
        {"future_prices": [...], "probability_pct": 数値,
         "direction": "up"/"down"/"flat", "based_on_date": 日付}
      データが不足している場合は (None, None, None) を返す。
    """
    data = candle_chart.load_ohlcv(ticker)
    if data is None:
        return None, None, None
    dates, closes = data["dates"], data["close"]

    selected, pool = find_similar_patterns(
        closes, window=window, horizon=horizon, top_n=top_n, pool_size=pool_size)
    if selected is None:
        return None, None, None

    latest_price = closes[-1]
    patterns = []
    for c in selected:
        probability_pct = calc_probability(c, pool)
        future_prices = [latest_price * (1.0 + pct / 100.0) for pct in c["outcome_pct"]]
        patterns.append({
            "future_prices": future_prices,
            "probability_pct": probability_pct,
            "direction": c["direction"],
            "based_on_date": dates[c["start_index"]],
        })

    # 要件定義書7.9節の指定通り、確率(的中期待度)が高い順に並べる
    patterns.sort(key=lambda p: p["probability_pct"], reverse=True)

    return dates, closes, patterns


def summarize_signal(patterns):
    """
    表示する予測パターン(patterns)を確率で重み付けした平均的な方向性から、
    「買い時の目安」「売り時の目安」「様子見」を参考として判定する。

    戻り値: (見出しの文字列, 補足説明の文字列) のタプル。
    """
    if not patterns:
        return "様子見(参考)", "似たパターンが見つからなかったため、判断できません。"

    direction_value = {"up": 1, "down": -1, "flat": 0}
    weighted_total = 0.0
    weight_sum = 0.0
    for p in patterns:
        weight = p["probability_pct"]
        weighted_total += direction_value[p["direction"]] * weight
        weight_sum += weight

    if weight_sum == 0:
        return "様子見(参考)", "似たパターンの確率がすべて0%だったため、判断できません。"

    average_score = weighted_total / weight_sum

    if average_score > 0.3:
        return "買い時の目安(参考)", "似た過去パターンの多くが、その後上昇していました。"
    elif average_score < -0.3:
        return "売り時の目安(参考)", "似た過去パターンの多くが、その後下落していました。"
    else:
        return "様子見(参考)", "似た過去パターンの結果が上昇・下降で分かれており、判断が難しい状況です。"
