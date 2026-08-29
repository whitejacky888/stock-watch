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
    this.isPercent = true;
    this.unit = "";
    this.geom = null;

    this.canvas.addEventListener("mousemove", (e) => this._onMouseMove(e));
    this.canvas.addEventListener("mouseleave", () => this._onMouseLeave());
    window.addEventListener("resize", () => this.draw());
  }

  // isPercent: true なら変化率(%)表示、false なら実額表示(フェーズ8-4)。
  // unit: 実額表示のときの単位("¥"・"$"・"pt")。銘柄によって単位が違うと
  // 分かりにくいというご指摘を受けて追加した(実額表示は表示中が1件の
  // ときしか選べないため、その1件の単位をそのまま使えばよい)。
  setData(labels, datasets, title, isPercent, unit) {
    this.labels = labels;
    this.datasets = datasets;
    this.title = title;
    this.isPercent = isPercent !== false;
    this.unit = unit || "";
    this._renderLegend();
    this.draw();
  }

  // 値を画面表示用の文字列に整形する(変化率なら "+12.34%"、実額なら
  // 単位に応じて "¥12,345" / "$123.45" / "32,500pt" のようにする。
  // 数値には3桁ごとの区切り(カンマ)を付ける)。
  // axis: true のときはY軸の目盛り用の簡易表示(符号なし・小数点1桁)にする。
  // 実額表示のときのY軸目盛りには単位を付けない(単位は縦軸の左上に
  // 1回だけ表示すれば十分で、目盛りすべてに付けると見づらいという
  // ご指摘を受けて、_drawAxisUnitLabel() で1回だけ表示するようにした)。
  _formatValue(v, options) {
    const axis = !!(options && options.axis);
    const digits = axis ? 1 : 2;
    if (this.isPercent) {
      const sign = !axis && v >= 0 ? "+" : "";
      return sign + v.toFixed(digits) + "%";
    }
    const rounded = v.toLocaleString("ja-JP", { maximumFractionDigits: digits });
    if (axis) {
      return rounded;
    }
    if (this.unit === "pt") {
      return rounded + "pt";
    }
    return this.unit + rounded;
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

    // top を少し広めに取っているのは、タイトルと一番上の目盛りの間に、
    // 単位ラベル(「(¥)」など)専用の行を、重ならないだけの余白を持たせて
    // 確保するため。
    const padding = { top: 44, right: 16, bottom: 34, left: 52 };
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
      ctx.fillText(this._formatValue(v, { axis: true }), padding.left - 6, y + 3);
    }

    // 実額表示のときは、縦軸の目盛り1つ1つに単位を付けず、縦軸の左上に
    // 「(¥)」のように1回だけ単位を表示する(¥・$・ptのどれなのかさえ
    // 分かればよく、全部の目盛りに付けると見づらいというご指摘への対応)。
    if (!this.isPercent && this.unit) {
      ctx.fillStyle = "#666";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText("(" + this.unit + ")", padding.left - 6, padding.top - 16);
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
    const lines = [
      "<strong>" + this.labels[idx] + "</strong>",
      '<span style="color:' + (ds.borderColor || "#888") + '">●</span> ' +
        ds.label + ": " + this._formatValue(v),
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

    // 列の並びは、銘柄の右隣に前日比を置き、市場区分・事業内容は
    // 補足情報として後ろに回している(ご指定のレイアウト)。
    tr.innerHTML =
      '<td data-label="状態"></td>' +
      '<td data-label="種別">' + kindText + "</td>" +
      '<td data-label="銘柄" style="color:' + nameColor + '"><strong>' + item.label + "</strong> (" + item.symbol + ")</td>" +
      '<td data-label="前日比" class="' + changeClass + '">' + changeText + "</td>" +
      '<td data-label="市場区分">' + item.market + "</td>" +
      '<td data-label="事業内容">' + item.business + "</td>" +
      '<td data-label="操作"></td>';

    // 「状態」セル自体を表示・非表示の切り替えボタンにする(フェーズ8-2)。
    // 表示中は赤の太字、非表示は黒の通常文字にして、押すと逆の状態に
    // なる(銘柄名などに記号が含まれていても問題が起きないよう、
    // DOM APIで作ってdatasetにキーを持たせている)。
    const statusCell = tr.firstElementChild;
    const statusToggle = document.createElement("span");
    statusToggle.className = "status-toggle " + (item.hidden ? "status-hidden" : "status-shown");
    statusToggle.textContent = item.hidden ? "非表示" : "表示中";
    statusToggle.title = item.hidden ? "クリックすると表示します" : "クリックすると非表示にします";
    statusToggle.dataset.key = item.key;
    statusToggle.dataset.hidden = String(item.hidden);
    statusCell.appendChild(statusToggle);

    // 「操作」セル。ソロ表示(フェーズ8-4)は指数・個別銘柄を問わず選べるが、
    // 削除(フェーズ8-3)は基本の2指数(日経平均・NASDAQ)にはできない
    // 仕様(7.1節)なので、個別銘柄のときだけリンクを出す。
    const opCell = tr.lastElementChild;
    const soloLink = document.createElement("span");
    soloLink.className = "solo-link";
    soloLink.textContent = "ソロ表示";
    soloLink.title = "この銘柄だけを表示し、他はすべて非表示にします";
    soloLink.dataset.key = item.key;
    soloLink.dataset.label = item.label;
    opCell.appendChild(soloLink);
    opCell.appendChild(document.createTextNode(" / "));

    if (item.kind === "company") {
      const deleteLink = document.createElement("span");
      deleteLink.className = "delete-link";
      deleteLink.textContent = "削除";
      deleteLink.dataset.key = item.key;
      deleteLink.dataset.label = item.label;
      opCell.appendChild(deleteLink);
    } else {
      const disabled = document.createElement("span");
      disabled.className = "delete-disabled";
      disabled.textContent = "(削除不可)";
      opCell.appendChild(disabled);
    }

    tbody.appendChild(tr);
  });

  // 表示中(非hidden)の件数に応じて、実額表示が選べるかどうかを切り替える
  // (フェーズ8-4。ターミナル版と同じく、表示中がちょうど1件のときだけ許可)。
  const visibleCount = items.filter((item) => !item.hidden).length;
  syncModeAvailability(visibleCount);
}

function syncModeAvailability(visibleCount) {
  const modeSelect = document.getElementById("mode-select");
  const absoluteOption = modeSelect.querySelector('option[value="absolute"]');
  const note = document.getElementById("mode-note");

  if (visibleCount === 1) {
    absoluteOption.disabled = false;
    note.textContent = "";
  } else {
    if (modeSelect.value === "absolute") {
      modeSelect.value = "percent";
    }
    absoluteOption.disabled = true;
    note.textContent =
      "※実額表示は、表示中の銘柄がちょうど1つのときだけ選べます(現在: " + visibleCount + "件表示中)。";
  }
}

// ウォッチリストの「状態」表示(表示中/非表示)や「削除」リンクのクリックを、
// 表全体(tbody)で1つだけ受け止めて処理する(行を作り直すたびに
// 個別にリスナーを付け直さなくて済むようにするため)。
document.querySelector("#watchlist-table tbody").addEventListener("click", async (e) => {
  const toggleEl = e.target.closest(".status-toggle");
  if (toggleEl) {
    const key = toggleEl.dataset.key;
    const nextHidden = toggleEl.dataset.hidden !== "true"; // 今と逆の状態にする

    toggleEl.style.pointerEvents = "none";
    try {
      const res = await fetch("/api/toggle_hidden", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: key, hidden: nextHidden }),
      });
      if (res.ok) {
        await loadWatchlist();
        await loadChart(currentPeriodIndex());
      } else {
        const body = await res.json().catch(() => ({}));
        alert(body.message || "切り替えに失敗しました。");
        toggleEl.style.pointerEvents = "";
      }
    } catch (err) {
      alert("切り替えに失敗しました。通信状況を確認してください。");
      toggleEl.style.pointerEvents = "";
    }
    return;
  }

  const deleteEl = e.target.closest(".delete-link");
  if (deleteEl) {
    const key = deleteEl.dataset.key;
    const label = deleteEl.dataset.label;
    // ターミナル版と同じく、削除は元に戻せない操作なので必ず確認を挟む。
    const confirmed = window.confirm(label + " を本当に削除しますか?(この操作は元に戻せません)");
    if (!confirmed) return;

    deleteEl.style.pointerEvents = "none";
    try {
      const res = await fetch("/api/remove_company", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: key }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok) {
        await loadWatchlist();
        await loadChart(currentPeriodIndex());
      } else {
        alert(body.message || "削除に失敗しました。");
        deleteEl.style.pointerEvents = "";
      }
    } catch (err) {
      alert("削除に失敗しました。通信状況を確認してください。");
      deleteEl.style.pointerEvents = "";
    }
    return;
  }

  const soloEl = e.target.closest(".solo-link");
  if (soloEl) {
    const key = soloEl.dataset.key;
    soloEl.style.pointerEvents = "none";
    try {
      const res = await fetch("/api/solo_display", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: key }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok) {
        document.getElementById("status-text").textContent = body.message || "";
        await loadWatchlist();
        await loadChart(currentPeriodIndex());
      } else {
        alert(body.message || "切り替えに失敗しました。");
        soloEl.style.pointerEvents = "";
      }
    } catch (err) {
      alert("切り替えに失敗しました。通信状況を確認してください。");
      soloEl.style.pointerEvents = "";
    }
  }
});

document.getElementById("show-all-btn").addEventListener("click", async () => {
  const statusText = document.getElementById("status-text");
  try {
    const res = await fetch("/api/show_all", { method: "POST" });
    const body = await res.json().catch(() => ({}));
    if (res.ok) {
      statusText.textContent = body.message || "全ての銘柄を表示に戻しました。";
      await loadWatchlist();
      await loadChart(currentPeriodIndex());
    } else {
      statusText.textContent = body.message || "失敗しました。";
    }
  } catch (err) {
    statusText.textContent = "失敗しました。通信状況を確認してください。";
  }
});

// ------------------------------------------------------------
// 銘柄の追加(フェーズ8-3)
// ターミナル版 main.py の handle_add と同じ流れ(シンボル入力 →
// yfinanceで会社名を自動確認 → 市場区分・事業内容を入力 → 確認して追加)を、
// 「確認する」→「この内容で追加する」の2段階フォームで再現している。
// ------------------------------------------------------------
let pendingAddSymbol = null;

function resetAddForm() {
  pendingAddSymbol = null;
  document.getElementById("add-symbol-input").value = "";
  document.getElementById("add-name-input").value = "";
  document.getElementById("add-market-input").value = "";
  document.getElementById("add-business-input").value = "";
  document.getElementById("add-lookup-result").textContent = "";
  document.getElementById("add-step1").style.display = "flex";
  document.getElementById("add-step2").style.display = "none";
}

document.getElementById("add-lookup-btn").addEventListener("click", async () => {
  const input = document.getElementById("add-symbol-input");
  const statusText = document.getElementById("add-status-text");
  const userInput = input.value.trim();
  if (userInput === "") {
    statusText.textContent = "証券コード・シンボルを入力してください。";
    return;
  }

  statusText.textContent = "yfinanceで情報を確認しています...";
  try {
    const res = await fetch("/api/lookup_company", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: userInput }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      statusText.textContent = body.message || "確認に失敗しました。";
      return;
    }

    pendingAddSymbol = body.symbol;
    statusText.textContent = "";
    const resultEl = document.getElementById("add-lookup-result");
    const nameInput = document.getElementById("add-name-input");
    if (body.name) {
      resultEl.textContent = "見つかりました: " + body.name + "(シンボル: " + body.symbol + ")";
      nameInput.value = body.name;
    } else {
      resultEl.textContent =
        "会社名を自動取得できませんでした(シンボル: " + body.symbol +
        ")。よろしければ下に表示名を直接入力してください。";
      nameInput.value = "";
    }
    document.getElementById("add-step1").style.display = "none";
    document.getElementById("add-step2").style.display = "flex";
  } catch (err) {
    statusText.textContent = "確認に失敗しました。通信状況を確認してください。";
  }
});

document.getElementById("add-cancel-btn").addEventListener("click", () => {
  resetAddForm();
  document.getElementById("add-status-text").textContent = "追加を中止しました。";
});

document.getElementById("add-confirm-btn").addEventListener("click", async () => {
  const statusText = document.getElementById("add-status-text");
  const name = document.getElementById("add-name-input").value.trim();
  const market = document.getElementById("add-market-input").value.trim();
  const business = document.getElementById("add-business-input").value.trim();

  if (!pendingAddSymbol) {
    statusText.textContent = "もう一度シンボルを確認してください。";
    return;
  }
  if (name === "") {
    statusText.textContent = "会社の表示名を入力してください。";
    return;
  }

  const btn = document.getElementById("add-confirm-btn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/add_company", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: pendingAddSymbol, name: name, market: market, business: business }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.ok) {
      statusText.textContent = body.message || "追加しました。";
      resetAddForm();
      await loadWatchlist();
      await loadChart(currentPeriodIndex());
    } else {
      statusText.textContent = body.message || "追加に失敗しました。";
    }
  } catch (err) {
    statusText.textContent = "追加に失敗しました。通信状況を確認してください。";
  } finally {
    btn.disabled = false;
  }
});

async function loadChart(periodIndex) {
  const requestedMode = currentModeValue();
  const res = await fetch("/api/chart_data?period=" + periodIndex + "&mode=" + requestedMode);
  const data = await res.json();

  // 実額表示を要求しても、表示中の銘柄が1件でなければサーバー側で
  // "percent" に戻される(フェーズ8-4)。実際に使われたモードに、
  // 表示モードの選択欄も合わせておく。
  const modeSelect = document.getElementById("mode-select");
  if (modeSelect.value !== data.mode) {
    modeSelect.value = data.mode;
  }
  const isPercent = data.mode !== "absolute";

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

  // 実額表示のときは、銘柄ごとに単位(¥/$/pt)が違うので、タイトルにも
  // 表示しておく(実額の場合、サーバー側の制約により系列は必ず1件になる)。
  const unit = data.series.length > 0 ? data.series[0].unit : "";
  const modeLabel = isPercent ? "変化率" : "実額(" + unit + ")";
  priceChart.setData(labels, datasets, "値動きウォッチ(" + modeLabel + "・" + data.period_label + ")", isPercent, unit);
}

function currentPeriodIndex() {
  return document.getElementById("period-select").value;
}

function currentModeValue() {
  return document.getElementById("mode-select").value;
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

document.getElementById("mode-select").addEventListener("change", () => {
  loadChart(currentPeriodIndex());
});

// ブラウザ(このページ)を開いている間、数秒おきにサーバーへ「まだ
// 使っています」の合図(heartbeat)を送る。ブラウザを閉じる、または
// このページから離れると自動的に送信が止まり、サーバー側がそれを
// 検知してアプリを自動終了する仕組みになっている(app.py参照。
// 「アイコンから起動したアプリを、ブラウザを閉じたら自動で終了させて
// ほしい」というご要望に対応するために追加した)。
function sendHeartbeat() {
  fetch("/api/heartbeat", { method: "POST" }).catch(() => {
    // サーバーが終了処理中などで送信に失敗しても、ここでは何もしない
    // (次のheartbeatも失敗し続ければ、いずれサーバー側は終了する)
  });
}
sendHeartbeat();
setInterval(sendHeartbeat, 3000);

// 画面を開いたときに、まず現在のデータで表とグラフを表示する
loadWatchlist();
loadChart(currentPeriodIndex());
