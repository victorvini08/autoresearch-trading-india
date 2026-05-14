"""Generate iterations/dashboard.html from per-iteration CSV artifacts.

Reads iterations/log.csv (one row per iteration) and each
iterations/<iter_id>/trades.csv, embeds them as inline JSON, writes a
self-contained HTML file with charts and per-iteration drill-down.
No external dependencies — opens directly via file:// in any browser.

What's shown per iteration:
  - decision badge + plain-language reason for KEPT/REVERTED/REJECTED
  - hypothesis the agent proposed
  - summary stats: sortino, Δ vs best-kept, calmar, total P&L, win rate,
    biggest winner / biggest loser, trade count
  - cumulative P&L curve over the validation period (more useful than
    per-trade scatter — shows when the strategy made or lost money)
  - top winners and bottom losers by ticker
  - full trade table (paginated)

What's shown across iterations:
  - sortino-over-iterations line chart with KEPT iterations highlighted
  - best-so-far reference line
  - headline summary: total iterations, KEPT count, best sortino

Re-run after every iteration; the HTML overwrites itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
ITER_DIR = REPO_ROOT / "iterations"
LOG_PATH = ITER_DIR / "log.csv"
DASHBOARD_PATH = ITER_DIR / "dashboard.html"


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Autoresearch dashboard</title>
<style>
  :root {{
    --bg: #fafafa;
    --panel: #fff;
    --border: #e3e3e3;
    --muted: #888;
    --text: #1f1f1f;
    --kept: #2a7d2a;
    --reverted: #c47a00;
    --rejected: #b13030;
    --accent: #2e6bd5;
  }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", Helvetica, sans-serif;
          margin: 0; background: var(--bg); color: var(--text); }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  h2 {{ font-size: 14px; margin: 0 0 10px; color: #555; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.04em; }}
  .meta {{ color: var(--muted); font-size: 12px; margin-bottom: 18px; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border);
            border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
  .summary-row {{ display: grid; grid-template-columns: repeat(4, 1fr);
                  gap: 12px; margin-bottom: 18px; }}
  .summary-card {{ background: var(--panel); border: 1px solid var(--border);
                   border-radius: 8px; padding: 14px; }}
  .summary-card .label {{ color: var(--muted); font-size: 11px;
                          text-transform: uppercase; letter-spacing: 0.04em;
                          margin-bottom: 4px; }}
  .summary-card .value {{ font-size: 22px; font-weight: 600; }}
  .summary-card .sub {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px;
            font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
            text-transform: uppercase; }}
  .badge.kept {{ background: #e6f4e6; color: var(--kept); }}
  .badge.reverted {{ background: #fbf0d8; color: var(--reverted); }}
  .badge.rejected {{ background: #fbe2e2; color: var(--rejected); }}
  .iter-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
  .iter-id {{ font-family: ui-monospace, "SF Mono", Menlo, monospace;
              font-size: 13px; color: #444; }}
  .reason {{ background: #f5f5f5; border-left: 3px solid var(--muted);
             padding: 8px 12px; font-size: 13px; margin: 8px 0;
             border-radius: 0 4px 4px 0; line-height: 1.5; }}
  .reason.reverted {{ border-color: var(--reverted); background: #fdf7e9; }}
  .reason.rejected {{ border-color: var(--rejected); background: #fbe9e9; }}
  .reason.kept {{ border-color: var(--kept); background: #ecf6ec; }}
  .reason b {{ color: var(--text); }}
  .hyp {{ font-size: 13px; color: #444; margin: 8px 0 12px;
          padding: 8px 12px; background: #f9f9f9; border-radius: 4px;
          border-left: 3px solid var(--accent); }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 10px; margin: 12px 0; }}
  .stat {{ padding: 10px 12px; background: #f7f7f7; border-radius: 6px; }}
  .stat .k {{ color: var(--muted); font-size: 10px;
              text-transform: uppercase; letter-spacing: 0.04em;
              margin-bottom: 2px; }}
  .stat .v {{ font-weight: 600; font-size: 15px; }}
  .stat .v.pos {{ color: var(--kept); }}
  .stat .v.neg {{ color: var(--rejected); }}
  .columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .columns h3 {{ font-size: 12px; margin: 0 0 6px; color: var(--muted);
                 text-transform: uppercase; letter-spacing: 0.04em; }}
  .ticker-list {{ font-family: ui-monospace, "SF Mono", Menlo, monospace;
                  font-size: 12px; }}
  .ticker-list .row {{ display: flex; justify-content: space-between;
                       padding: 4px 0; border-bottom: 1px dashed #eee; }}
  .ticker-list .row:last-child {{ border-bottom: none; }}
  .ticker-list .name {{ font-weight: 600; }}
  .ticker-list .pnl.pos {{ color: var(--kept); }}
  .ticker-list .pnl.neg {{ color: var(--rejected); }}
  input[type=range] {{ width: 100%; margin: 8px 0; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 8px; }}
  th, td {{ padding: 6px 8px; border-bottom: 1px solid #eee; text-align: left; }}
  th {{ background: #f7f7f7; font-weight: 600; color: #555;
         text-transform: uppercase; font-size: 10px; letter-spacing: 0.04em; }}
  td.win {{ color: var(--kept); }}
  td.loss {{ color: var(--rejected); }}
  td.num {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  svg {{ display: block; width: 100%; height: 240px; }}
  .axis {{ stroke: #ccc; stroke-width: 1; }}
  .grid {{ stroke: #eee; stroke-width: 1; }}
  .label {{ fill: #888; font-size: 10px; }}
  .empty {{ color: #999; font-style: italic; padding: 14px 0; text-align: center; }}
  details summary {{ cursor: pointer; color: var(--accent); font-size: 13px; padding: 6px 0; }}
</style>
</head>
<body>
<div class="wrap">

<h1>Autoresearch dashboard</h1>
<div class="meta">{n_iter} iterations · auto-generated · raw data in
<code>iterations/log.csv</code></div>

<div class="summary-row" id="headline"></div>

<div class="panel">
<h2>Sortino across iterations</h2>
<svg id="sortino-chart"></svg>
</div>

<div class="panel">
<h2>Iteration drill-down</h2>
<input type="range" id="iter-slider" min="0" max="{max_idx}" value="{max_idx}">
<div id="iter-detail"></div>
</div>

</div>

<script>
const ITERATIONS = {iterations_json};
const TRADES = {trades_json};

function el(id) {{ return document.getElementById(id); }}
function svgEl(name, attrs) {{
  const e = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}}
function clearSvg(id) {{
  const s = el(id);
  while (s.firstChild) s.removeChild(s.firstChild);
  return s;
}}
function fmtMoney(v) {{
  const sign = v < 0 ? "-" : "";
  const a = Math.abs(v);
  if (a >= 1000) return sign + "$" + a.toLocaleString(undefined, {{maximumFractionDigits: 0}});
  return sign + "$" + a.toFixed(2);
}}
function fmtPct(v) {{ return (v * 100).toFixed(1) + "%"; }}
function fmt3(v) {{ return Number(v).toFixed(3); }}

// ---------- headline summary ----------
function bestKeptSortino() {{
  let best = null, bestId = null;
  for (const it of ITERATIONS) {{
    if (it.decision !== "KEPT") continue;
    const s = Number(it.sortino);
    if (best === null || s > best) {{ best = s; bestId = it.id; }}
  }}
  return [best, bestId];
}}

function renderHeadline() {{
  const headline = el("headline");
  const total = ITERATIONS.length;
  const kept = ITERATIONS.filter(it => it.decision === "KEPT").length;
  const reverted = ITERATIONS.filter(it => it.decision === "REVERTED").length;
  const rejected = ITERATIONS.filter(it => it.decision === "REJECTED").length;
  const [bestSort, bestId] = bestKeptSortino();
  const latest = ITERATIONS[ITERATIONS.length - 1];
  const cells = [
    {{label: "Iterations", value: total,
     sub: `${{kept}} kept · ${{reverted}} reverted · ${{rejected}} rejected`}},
    {{label: "Best kept Sortino",
     value: bestSort !== null ? fmt3(bestSort) : "—",
     sub: bestId ? `iter ${{bestId.slice(-7)}}` : "no iteration accepted yet"}},
    {{label: "Acceptance rate",
     value: total ? ((kept / total) * 100).toFixed(0) + "%" : "—",
     sub: `${{kept}} / ${{total}}`}},
    {{label: "Latest decision",
     value: latest ? latest.decision : "—",
     sub: latest ? `iter ${{latest.id.slice(-7)}}` : ""}},
  ];
  headline.innerHTML = cells.map(c => `
    <div class="summary-card">
      <div class="label">${{c.label}}</div>
      <div class="value">${{c.value}}</div>
      <div class="sub">${{c.sub}}</div>
    </div>`).join("");
}}

// ---------- sortino-over-iterations ----------
function drawSortinoChart() {{
  const svg = clearSvg("sortino-chart");
  if (!ITERATIONS.length) return;
  const W = svg.clientWidth || 1100, H = 240;
  const padL = 50, padR = 20, padT = 18, padB = 32;
  const xs = ITERATIONS.map((_, i) => i);
  const ys = ITERATIONS.map(it => Number(it.sortino) || 0);
  const xmin = 0, xmax = Math.max(1, xs.length - 1);
  const ymin = Math.min(...ys, 0), ymax = Math.max(...ys, 0.5);
  const x = i => padL + (i - xmin) / (xmax - xmin) * (W - padL - padR);
  const y = v => padT + (1 - (v - ymin) / (ymax - ymin || 1)) * (H - padT - padB);

  // gridlines + zero line
  if (ymin < 0 && ymax > 0) {{
    svg.appendChild(svgEl("line", {{x1: padL, x2: W - padR, y1: y(0), y2: y(0),
      class: "grid", "stroke-dasharray": "2,3"}}));
  }}
  // axes
  svg.appendChild(svgEl("line", {{x1: padL, x2: padL, y1: padT, y2: H - padB, class: "axis"}}));
  svg.appendChild(svgEl("line", {{x1: padL, x2: W - padR, y1: H - padB, y2: H - padB, class: "axis"}}));
  // y labels
  [ymin, (ymin + ymax) / 2, ymax].forEach(v => {{
    const t = svgEl("text", {{x: padL - 6, y: y(v) + 3, "text-anchor": "end", class: "label"}});
    t.textContent = v.toFixed(2); svg.appendChild(t);
  }});

  // best-kept reference line
  const [bestSort] = bestKeptSortino();
  if (bestSort !== null) {{
    svg.appendChild(svgEl("line", {{x1: padL, x2: W - padR, y1: y(bestSort), y2: y(bestSort),
      stroke: "var(--kept)", "stroke-width": 1, "stroke-dasharray": "4,3", "stroke-opacity": 0.5}}));
    const lbl = svgEl("text", {{x: W - padR - 4, y: y(bestSort) - 4, "text-anchor": "end",
      class: "label", fill: "var(--kept)"}});
    lbl.textContent = `best kept: ${{fmt3(bestSort)}}`;
    svg.appendChild(lbl);
  }}

  // line connecting all iterations
  const pts = xs.map(i => `${{x(i)}},${{y(ys[i])}}`).join(" ");
  svg.appendChild(svgEl("polyline", {{points: pts, fill: "none",
    stroke: "#aaa", "stroke-width": "1.2", "stroke-opacity": 0.7}}));

  // dots: KEPT prominent, others dim. Click to jump.
  ITERATIONS.forEach((it, i) => {{
    const isKept = it.decision === "KEPT";
    const isReject = it.decision === "REJECTED";
    const fill = isKept ? "var(--kept)" : isReject ? "var(--rejected)" : "var(--reverted)";
    const r = isKept ? 5 : 3;
    const opacity = isKept ? 1 : 0.45;
    const c = svgEl("circle", {{cx: x(i), cy: y(ys[i]), r, fill,
      "fill-opacity": opacity, style: "cursor: pointer"}});
    const title = svgEl("title");
    title.textContent = `iter ${{it.id.slice(-7)}} (${{it.decision}})\\nsortino ${{ys[i].toFixed(3)}}`;
    c.appendChild(title);
    c.addEventListener("click", () => {{
      const slider = el("iter-slider");
      slider.value = i;
      renderIteration(i);
    }});
    svg.appendChild(c);
  }});
}}

// ---------- per-iteration trade summary ----------
function tradeSummary(iterId) {{
  const trades = TRADES[iterId] || [];
  if (!trades.length) {{
    return {{count: 0, totalPnl: 0, winRate: null, biggestWin: null,
            biggestLoss: null, byTicker: []}};
  }}
  let totalPnl = 0, wins = 0;
  let biggestWin = null, biggestLoss = null;
  const byTicker = new Map();
  for (const t of trades) {{
    const pnl = Number(t.pnl) || 0;
    totalPnl += pnl;
    if (pnl > 0) wins++;
    if (biggestWin === null || pnl > biggestWin.pnl) biggestWin = {{ticker: t.ticker, pnl}};
    if (biggestLoss === null || pnl < biggestLoss.pnl) biggestLoss = {{ticker: t.ticker, pnl}};
    byTicker.set(t.ticker, (byTicker.get(t.ticker) || 0) + pnl);
  }}
  const tickerArr = Array.from(byTicker.entries())
    .map(([ticker, pnl]) => ({{ticker, pnl}}))
    .sort((a, b) => b.pnl - a.pnl);
  return {{
    count: trades.length,
    totalPnl, winRate: wins / trades.length,
    biggestWin, biggestLoss, byTicker: tickerArr,
  }};
}}

// ---------- cumulative P&L curve over time ----------
function drawCumPnl(iterId, svg) {{
  const trades = (TRADES[iterId] || []).slice();
  if (!trades.length) {{
    const t = svgEl("text", {{x: "50%", y: "50%", "text-anchor": "middle", class: "label"}});
    t.textContent = "no trades to plot";
    svg.appendChild(t);
    return;
  }}
  // Sort trades by exit_date so the curve is chronological.
  trades.sort((a, b) => String(a.exit_date).localeCompare(String(b.exit_date)));
  const cum = [];
  let s = 0;
  for (const t of trades) {{ s += Number(t.pnl) || 0; cum.push({{date: t.exit_date, value: s}}); }}

  const W = svg.clientWidth || 1100, H = 240;
  const padL = 60, padR = 20, padT = 18, padB = 32;
  const ymin = Math.min(0, ...cum.map(p => p.value));
  const ymax = Math.max(0, ...cum.map(p => p.value));
  const xn = cum.length;
  const x = i => padL + (xn === 1 ? (W - padL - padR) / 2 : i / (xn - 1) * (W - padL - padR));
  const y = v => padT + (1 - (v - ymin) / (ymax - ymin || 1)) * (H - padT - padB);

  // zero line
  if (ymin < 0 && ymax > 0) {{
    svg.appendChild(svgEl("line", {{x1: padL, x2: W - padR, y1: y(0), y2: y(0),
      class: "grid", "stroke-dasharray": "2,3"}}));
  }}
  // axes
  svg.appendChild(svgEl("line", {{x1: padL, x2: padL, y1: padT, y2: H - padB, class: "axis"}}));
  svg.appendChild(svgEl("line", {{x1: padL, x2: W - padR, y1: H - padB, y2: H - padB, class: "axis"}}));
  // y labels in $
  [ymin, (ymin + ymax) / 2, ymax].forEach(v => {{
    const t = svgEl("text", {{x: padL - 6, y: y(v) + 3, "text-anchor": "end", class: "label"}});
    t.textContent = fmtMoney(v); svg.appendChild(t);
  }});
  // x labels: first and last date
  const xLabels = [
    {{i: 0, txt: cum[0].date}},
    {{i: xn - 1, txt: cum[xn - 1].date}},
  ];
  xLabels.forEach(L => {{
    const t = svgEl("text", {{x: x(L.i), y: H - padB + 14,
      "text-anchor": L.i === 0 ? "start" : "end", class: "label"}});
    t.textContent = String(L.txt).slice(0, 10); svg.appendChild(t);
  }});

  // area fill (positive = green tint, negative = red tint)
  const finalVal = cum[xn - 1].value;
  const fill = finalVal >= 0 ? "rgba(42,125,42,0.08)" : "rgba(177,48,48,0.08)";
  const stroke = finalVal >= 0 ? "var(--kept)" : "var(--rejected)";
  let pathD = `M ${{x(0)}} ${{y(0)}}`;
  for (let i = 0; i < xn; i++) pathD += ` L ${{x(i)}} ${{y(cum[i].value)}}`;
  pathD += ` L ${{x(xn - 1)}} ${{y(0)}} Z`;
  svg.appendChild(svgEl("path", {{d: pathD, fill, stroke: "none"}}));
  const linePts = cum.map((p, i) => `${{x(i)}},${{y(p.value)}}`).join(" ");
  svg.appendChild(svgEl("polyline", {{points: linePts, fill: "none",
    stroke, "stroke-width": "1.6"}}));
}}

// ---------- iteration detail panel ----------
function renderIteration(idx) {{
  const it = ITERATIONS[idx];
  const detail = el("iter-detail");
  if (!it) {{ detail.innerHTML = '<div class="empty">no iteration</div>'; return; }}

  const summary = tradeSummary(it.id);
  const [bestSort] = bestKeptSortino();
  const sortino = Number(it.sortino) || 0;
  const delta = bestSort !== null ? sortino - bestSort : null;
  const dec = it.decision.toLowerCase();

  // reason fallback when log.csv is older and didn't carry the field.
  const reason = it.reason ||
    (it.decision === "KEPT" ? "Sortino improved on previous KEPT, risk gates passed."
     : it.decision === "REVERTED" ? `Sortino did not improve on the last KEPT iteration${{!it.risk_passed ? " (risk gate also failed)" : ""}}.`
     : "Iteration could not be evaluated (crash, invalid edit, or unparseable LLM output).");

  // stats: pos/neg coloring on values where direction matters.
  const totalPnlClass = summary.totalPnl > 0 ? "pos" : summary.totalPnl < 0 ? "neg" : "";
  const deltaTxt = delta === null ? "—" : (delta >= 0 ? "+" : "") + fmt3(delta);
  const deltaClass = delta === null ? "" : delta >= 0 ? "pos" : "neg";

  // top winners / losers by ticker (best 5, worst 5)
  const winners = summary.byTicker.slice(0, 5);
  const losers = summary.byTicker.slice(-5).reverse();

  const winnerRows = winners.length ? winners.map(t => `
    <div class="row"><span class="name">${{t.ticker}}</span>
    <span class="pnl ${{t.pnl >= 0 ? 'pos' : 'neg'}}">${{fmtMoney(t.pnl)}}</span></div>`).join("")
    : '<div class="empty">no trades</div>';
  const loserRows = losers.length && losers[0].pnl < 0 ? losers.map(t => `
    <div class="row"><span class="name">${{t.ticker}}</span>
    <span class="pnl ${{t.pnl >= 0 ? 'pos' : 'neg'}}">${{fmtMoney(t.pnl)}}</span></div>`).join("")
    : '<div class="empty">no losing tickers</div>';

  detail.innerHTML = `
    <div class="iter-header">
      <span class="iter-id">iter ${{it.id}}</span>
      <span class="badge ${{dec}}">${{it.decision}}</span>
      <span style="color: var(--muted); font-size: 12px;">${{it.timestamp}}</span>
    </div>
    <div class="reason ${{dec}}"><b>Reason:</b> ${{escapeHtml(reason)}}</div>
    ${{it.hypothesis ? `<div class="hyp"><b>Hypothesis:</b> ${{escapeHtml(it.hypothesis)}}</div>` : ""}}
    <div class="stats">
      <div class="stat"><div class="k">Sortino</div>
        <div class="v">${{fmt3(sortino)}}</div></div>
      <div class="stat"><div class="k">Δ vs best kept</div>
        <div class="v ${{deltaClass}}">${{deltaTxt}}</div></div>
      <div class="stat"><div class="k">Calmar (mean)</div>
        <div class="v">${{fmt3(it.calmar)}}</div></div>
      <div class="stat"><div class="k">Trades</div>
        <div class="v">${{it.trade_count}}</div></div>
      <div class="stat"><div class="k">Total P&L</div>
        <div class="v ${{totalPnlClass}}">${{summary.count ? fmtMoney(summary.totalPnl) : "—"}}</div></div>
      <div class="stat"><div class="k">Win rate</div>
        <div class="v">${{summary.winRate === null ? "—" : fmtPct(summary.winRate)}}</div></div>
      <div class="stat"><div class="k">Biggest winner</div>
        <div class="v">${{summary.biggestWin ?
          summary.biggestWin.ticker + " " + fmtMoney(summary.biggestWin.pnl) : "—"}}</div></div>
      <div class="stat"><div class="k">Biggest loser</div>
        <div class="v">${{summary.biggestLoss ?
          summary.biggestLoss.ticker + " " + fmtMoney(summary.biggestLoss.pnl) : "—"}}</div></div>
    </div>
    <h2 style="margin-top: 16px;">Cumulative P&L over time</h2>
    <svg id="cum-pnl"></svg>
    <div class="columns" style="margin-top: 14px;">
      <div>
        <h3>Top 5 winners by ticker</h3>
        <div class="ticker-list">${{winnerRows}}</div>
      </div>
      <div>
        <h3>Bottom 5 losers by ticker</h3>
        <div class="ticker-list">${{loserRows}}</div>
      </div>
    </div>
    <details style="margin-top: 16px;">
      <summary>All trades (${{summary.count}})</summary>
      <table id="trade-table"><thead><tr>
        <th>#</th><th>Ticker</th><th>Entry</th><th>Exit</th>
        <th>P&L $</th><th>P&L %</th><th>Order $</th>
      </tr></thead><tbody></tbody></table>
    </details>
  `;

  drawCumPnl(it.id, el("cum-pnl"));

  const tbody = el("trade-table") ? el("trade-table").querySelector("tbody") : null;
  if (tbody) {{
    const trades = TRADES[it.id] || [];
    const rows = trades.slice(0, 200).map((tr, i) => {{
      const pnl = Number(tr.pnl) || 0;
      const cls = pnl > 0 ? "win" : pnl < 0 ? "loss" : "";
      return `<tr>
        <td class="num">${{i + 1}}</td>
        <td>${{tr.ticker || ""}}</td>
        <td class="num">${{tr.entry_date || ""}}</td>
        <td class="num">${{tr.exit_date || ""}}</td>
        <td class="num ${{cls}}">${{fmtMoney(pnl)}}</td>
        <td class="num ${{cls}}">${{fmtPct(Number(tr.pnl_pct) || 0)}}</td>
        <td class="num">${{fmtMoney(Number(tr.order_value_usd) || 0)}}</td>
      </tr>`;
    }}).join("");
    tbody.innerHTML = rows + (trades.length > 200 ?
      `<tr><td colspan="7" class="empty">… ${{trades.length - 200}} more rows in trades.csv</td></tr>` : "");
  }}
}}

function escapeHtml(s) {{
  return String(s).replace(/[&<>"']/g, c => (
    {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}}[c]
  ));
}}

renderHeadline();
drawSortinoChart();
const slider = el("iter-slider");
slider.addEventListener("input", e => renderIteration(Number(e.target.value)));
renderIteration(ITERATIONS.length - 1);
window.addEventListener("resize", () => {{
  drawSortinoChart();
  renderIteration(Number(slider.value));
}});
</script>
</body>
</html>
"""


def render_dashboard(repo_root: Path = REPO_ROOT) -> None:
    """Read iterations/log.csv + per-iteration trades.csv files, write
    a self-contained dashboard.html into iterations/."""
    iter_dir = repo_root / "iterations"
    log_path = iter_dir / "log.csv"
    if not log_path.exists():
        return

    log = pd.read_csv(log_path)
    iterations: list[dict] = []
    trades_by_id: dict[str, list[dict]] = {}
    for _, row in log.iterrows():
        iter_id = str(row["iteration_id"])
        trades_csv = iter_dir / iter_id / "trades.csv"
        has_csv = trades_csv.exists()
        iterations.append({
            "id": iter_id,
            "timestamp": str(row.get("timestamp", "")),
            "decision": str(row.get("decision", "")),
            "sortino": float(row.get("sortino", 0) or 0),
            "calmar": float(row.get("calmar", 0) or 0),
            "trade_count": int(row.get("trade_count", 0) or 0),
            "risk_passed": bool(row.get("risk_passed", False)),
            "hypothesis": str(row.get("hypothesis", ""))[:300],
            "reason": str(row.get("reason", ""))[:500],
            "trades_retained": has_csv,
        })
        if has_csv:
            df = pd.read_csv(trades_csv)
            for c in df.columns:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].astype(float)
            trades_by_id[iter_id] = df.to_dict(orient="records")

    html = _HTML_TEMPLATE.format(
        iterations_json=json.dumps(iterations, default=str),
        trades_json=json.dumps(trades_by_id, default=str),
        n_iter=len(iterations),
        max_idx=max(0, len(iterations) - 1),
    )
    (iter_dir / "dashboard.html").write_text(html)


if __name__ == "__main__":
    render_dashboard()
    print(f"wrote {DASHBOARD_PATH}")
