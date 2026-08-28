/*
script.js
------------------------------------------------------------
値動きウォッチ(Web版)の画面の動きをまとめたファイル。
app.py が提供するAPI(/api/watchlist, /api/chart_data, /api/fetch)を
呼び出して、ウォッチリストの表と比較グラフを描画する。

グラフは、外部のグラフ描画ライブラリを使わず、ブラウザ標準の
<canvas>要素だけで自前で描画している(要件定義書9章と同じ考え方で、
インターネット接続が不安定なときでも画面自体は表示できるようにするため。
外部ライブラリの読み込みに失敗すると、グラフだけが表示されなくなって
しまう問題を避けている)。
*/

// ------------------------------------------------------------
// 自前の折れ線グラフ描画クラス(Chart.jsなどの外部ライブラリを使わない)
// ------------------------------------------------------------
class SimpleLineChart {
  constructor(canvas, tooltipEl, legendEl) {
    this.canvas = canvas;
    this.tooltip = tooltipEl;
    this.legendEl = legendEl;
    this.labels = [];
    this.datasets = [];
    this.title = "";
    this.geom = null;

    this.canvas.addEventListener("mousemove", (e) => this._onMouseMove(e));
    this.canvas.addEventListener("mouseleave", () => this._onMouseLeave());
    window.addEventListener("resize", () => this.draw());
  }

  setData(labels, datasets, title) {
    this.labels = labels;
    this.datasets = datasets;
    this.title = title;
    this._renderLegend();
    this.draw();
  }

  _renderLegend() {
    this.legendEl.innerHTML = "";
    this.datasets.forEach((ds) => {
      const li = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = ds.borderColor || "#888";
      li.appendChild(swatch);
      li.appendChild(document.createTextNode(ds.label));
      this.legendEl.appendChild(li);
    });
  }

  draw(hoverIndex, highlightDs) {
    const canvas = this.canvas;
    const dpr = window.devicePixelRatio || 1;
    const cssWidth = canvas.clientWidth || 600;
    const cssHeight = canvas.clientHeight || 300;
    canvas.width = cssWidth * dpr;
    canvas.height = cssHeight * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    if (this.labels.length === 0 || this.datasets.length === 0) {
      ctx.fillStyle = "#888";
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        "表示できるデータがありません。「データを取得する」を押してください。",
        cssWidth / 2,
        cssHeight / 2
      );
      this.geom = null;
      return;
    }

    const padding = { top: 26, right: 16, bottom: 34, left: 52 };
    const plotWidth = Math.max(10, cssWidth - padding.left - padding.right);
    const plotHeight = Math.max(10, cssHeight - padding.top - padding.bottom);

    let minValue = Infinity;
    let maxValue = -Infinity;
    this.datasets.forEach((ds) => {
      ds.data.forEach((v) => {
        if (v !== null && v !== undefined && !Number.isNaN(v)) {
          if (v < minValue) minValue = v;
          if (v > maxValue) maxValue = v;
        }
      });
    });
    if (minValue === Infinity) {
      minValue = 0;
      maxValue = 1;
    }
    if (minValue === maxValue) {
      minValue -= 1;
      maxValue += 1;
    }
    const margin = (maxValue - minValue) * 0.08;
    minValue -= margin;
    maxValue += margin;

    const n = this.labels.length;
    const xForIndex = (i) => (n <= 1 ? padding.left + plotWidth / 2 : padding.left + (plotWidth * i) / (n - 1));
    const yForValue = (v) => padding.top + plotHeight * (1 - (v - minValue) / (maxValue - minValue));

    // タイトル
    if (this.title) {
      ctx.fillStyle = "#222";
      ctx.font = "bold 13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(this.title, cssWidth / 2, 16);
    }

    // Y軸の目盛り・横のグリッド線
    ctx.strokeStyle = "#e8e8e8";
    ctx.fillStyle = "#666";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "right";
    const yTickCount = 5;
    for (let t = 0; t <= yTickCount; t++) {
      const v = minValue + ((maxValue - minValue) * t) / yTickCount;
      const y = yForValue(v);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(cssWidth - padding.right, y);
      ctx.stroke();
      ctx.fillText(v.toFixed(1) + "%", padding.left - 6, y + 3);
    }

    // 0%の基準線(強調)
    if (minValue < 0 && maxValue > 0) {
      const zeroY = yForValue(0);
      ctx.strokeStyle = "#999";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, zeroY);
      ctx.lineTo(cssWidth - padding.right, zeroY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // X軸の日付ラベル(間引いて表示)
    ctx.textAlign = "center";
    ctx.fillStyle = "#666";
    const maxLabels = Math.max(2, Math.floor(plotWidth / 85));
    const step = Math.max(1, Math.ceil(n / maxLabels));
    for (let i = 0; i < n; i += step) {
      ctx.fillText(this.labels[i], xForIndex(i), cssHeight - padding.bottom + 16);
    }
    if ((n - 1) % step !== 0) {
      ctx.fillText(this.labels[n - 1], xForIndex(n - 1), cssHeight - padding.bottom + 16);
    }

    // 各系列の折れ線
    this.datasets.forEach((ds) => {
      ctx.strokeStyle = ds.borderColor || "#888";
      ctx.lineWidth = 2;
      ctx.setLineDash(ds.dashed ? [5, 4] : []);
      ctx.beginPath();
      let started = false;
      ds.data.forEach((v, i) => {
        if (v === null || v === undefined || Number.isNaN(v)) {
          started = false;
          return;
        }
        const x = xForIndex(i);
        const y = yForValue(v);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // 枠線
    ctx.strokeStyle = "#ccc";
    ctx.strokeRect(padding.left, padding.top, plotWidth, plotHeight);

    this.geom = { padding, plotWidth, plotHeight, minValue, maxValue, n, xForIndex, yForValue, cssHeight };

    // カーソル位置(hoverIndex)があれば、縦線と、指している1本の線の点だけを強調表示する
    if (hoverIndex !== undefined && hoverIndex !== null && hoverIndex >= 0 && hoverIndex < n) {
      const x = xForIndex(hoverIndex);
      ctx.strokeStyle = "#999";
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, cssHeight - padding.bottom);
      ctx.stroke();
      ctx.setLineDash([]);

      if (highlightDs) {
        const v = highlightDs.data[hoverIndex];
        if (v !== null && v !== undefined && !Number.isNaN(v)) {
          const y = yForValue(v);
          // 白い縁取りをつけて、線が重なっていてもどの点か分かりやすくする
          ctx.fillStyle = "#fff";
          ctx.beginPath();
          ctx.arc(x, y, 5.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = highlightDs.borderColor || "#888";
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }

  // マウスの位置(Y座標)に一番近い系列を探す(複数の線が重なっていても、
  // カーソルが指している1本だけを特定するため)
  _findNearestDataset(idx, mouseY) {
    let nearest = null;
    let nearestDist = Infinity;
    this.datasets.forEach((ds) => {
      const v = ds.data[idx];
      if (v === null || v === undefined || Number.isNaN(v)) return;
      const y = this.geom.yForValue(v);
      const dist = Math.abs(y - mouseY);
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = ds;
      }
    });
    return nearest;
  }

  _onMouseMove(e) {
    if (!this.geom) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const relX = mouseX - this.geom.padding.left;
    const ratio = this.geom.plotWidth === 0 ? 0 : relX / this.geom.plotWidth;
    let idx = Math.round(ratio * (this.geom.n - 1));
    idx = Math.max(0, Math.min(this.geom.n - 1, idx));

    const nearest = this._findNearestDataset(idx, mouseY);
    this.draw(idx, nearest);
    this._showTooltip(e, idx, rect, nearest);
  }

  _onMouseLeave() {
    this.draw();
    this.tooltip.style.display = "none";
  }

  _showTooltip(e, idx, rect, ds) {
    if (!ds) {
      this.tooltip.style.display = "none";
      return;
    }
    const v = ds.data[idx];
    if (v === null || v === undefined || Number.isNaN(v)) {
      this.tooltip.style.display = "none";
      return;
    }
    const sign = v >= 0 ? "+" : "";
    const lines = [
      "<strong>" + this.labels[idx] + "</strong>",
      '<span style="color:' + (ds.borderColor || "#888") + '">●</span> ' +
        ds.label + ": " + sign + v.toFixed(2) + "%",
    ];
    this.tooltip.innerHTML = lines.join("<br>");
    this.tooltip.style.display = "block";

    let left = e.clientX - rect.left + 14;
    let top = e.clientY - rect.top + 14;
    // ツールチップが右端・下端にはみ出さないよう、簡単に補正する
    if (left + 160 > rect.width) left = e.clientX - rect.left - 170;
    if (top + 50 > rect.height) top = e.clientY - rect.top - 60;
    this.tooltip.style.left = left + "px";
    this.tooltip.style.top = top + "px";
  }
}

const priceChart = new SimpleLineChart(
  document.getElementById("priceChart"),
  document.getElementById("chart-tooltip"),
  document.getElementById("chart-legend")
);

async function loadWatchlist() {
  const res = await fetch("/api/watchlist");
  const items = await res.json();
  const tbody = document.querySelector("#watchlist-table tbody");
  tbody.innerHTML = "";

  items.forEach((item) => {
    const tr = document.createElement("tr");

    const statusText = item.hidden ? "非表示" : "表示中";
    const kindText = item.kind === "index" ? "指数" : "個別銘柄";

    let changeText = "(データ未取得。上のボタンで取得できます)";
    let changeClass = "";
    if (item.change_diff !== null && item.change_diff !== undefined) {
      const sign = item.change_diff >= 0 ? "+" : "";
      changeText = sign + item.change_diff.toFixed(2) + " (" + sign + item.change_pct.toFixed(2) + "%)";
      if (item.change_diff > 0) {
        changeClass = "up";
      } else if (item.change_diff < 0) {
        changeClass = "down";
      }
    }

    const nameColor = item.color || "#222";

    tr.innerHTML =
      '<td data-label="状態">' + statusText + "</td>" +
      '<td data-label="種別">' + kindText + "</td>" +
      '<td data-label="銘柄" style="color:' + nameColor + '"><strong>' + item.label + "</strong> (" + item.symbol + ")</td>" +
      '<td data-label="市場区分">' + item.market + "</td>" +
      '<td data-label="事業内容">' + item.business + "</td>" +
      '<td data-label="前日比" class="' + changeClass + '">' + changeText + "</td>";

    tbody.appendChild(tr);
  });
}

async function loadChart(periodIndex) {
  const res = await fetch("/api/chart_data?period=" + periodIndex);
  const data = await res.json();

  // すべての系列に出てくる日付をまとめて、横軸のラベルにする
  const labelSet = new Set();
  data.series.forEach((s) => s.dates.forEach((d) => labelSet.add(d)));
  const labels = Array.from(labelSet).sort();

  const datasets = data.series.map((s) => {
    const valueByDate = {};
    s.dates.forEach((d, i) => {
      valueByDate[d] = s.values[i];
    });
    // 日本市場と米国市場は休みの日(祝日)がずれているため、labelsには
    // 「この銘柄の市場は休みだった日」も混じっている。その日をそのまま
    // 空欄(null)にすると、その銘柄の線だけがその日1日分ぷつっと
    // 途切れて見えてしまう(実際には「休みで値が変わらなかった」だけ)。
    // そこで、データが無い日は直前の値を引き継いで、線を途切れさせない
    // ようにする(その銘柄のデータがまだ1件も無い、期間の先頭部分は
    // nullのままにしておく)。
    let lastValue = null;
    const values = labels.map((d) => {
      if (d in valueByDate) {
        lastValue = valueByDate[d];
      }
      return lastValue;
    });
    return {
      label: s.label,
      data: values,
      borderColor: s.color || "#888888",
      dashed: s.kind === "index",
    };
  });

  priceChart.setData(labels, datasets, "値動きウォッチ(変化率・" + data.period_label + ")");
}

function currentPeriodIndex() {
  return document.getElementById("period-select").value;
}

document.getElementById("fetch-btn").addEventListener("click", async () => {
  const statusText = document.getElementById("status-text");
  const btn = document.getElementById("fetch-btn");
  statusText.textContent = "データを取得しています...(銘柄数によっては少し時間がかかります)";
  btn.disabled = true;
  try {
    await fetch("/api/fetch", { method: "POST" });
    statusText.textContent = "取得が完了しました。";
    await loadWatchlist();
    await loadChart(currentPeriodIndex());
  } catch (e) {
    statusText.textContent = "取得に失敗しました。インターネット接続を確認してください。";
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("period-select").addEventListener("change", (e) => {
  loadChart(e.target.value);
});

// 画面を開いたときに、まず現在のデータで表とグラフを表示する
loadWatchlist();
loadChart(currentPeriodIndex());
