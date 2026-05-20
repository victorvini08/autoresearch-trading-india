"""Single-file HTML dashboard for the dhan-paper / dhan-live ledger.

Output: `state/reports/dashboard.html` — a self-contained file that:

  - Two tabs at the top: **Dhan Paper** (brokers.dhan_mock-simulated fills)
    and **Dhan Live** (real Dhan API fills, post 4-week paper validation).
  - Each tab has its own slider, metric tiles, equity chart, tables.
  - Embeds every day's data as JSON at build time (no server needed).
  - All currency formatted in ₹ (lakh/crore shorthand for large amounts).

Idempotent — called by `run_live.py` after `daily_report.generate()` so the
dashboard refreshes every daily run.

CLI:
    uv run python -m scripts.dashboard
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from storage import portfolio_db

REPORTS_DIR = Path("state/reports")
DASHBOARD_FILENAME = "dashboard.html"

# Mode strings that count as "real (live) broker activity" in the ledger.
# Kept as a tuple so additional live modes (sandbox, demo, etc.) can be
# added without touching the bucket aggregation logic.
REAL_MODES = ("dhan-live",)
PAPER_MODES = ("dhan-paper",)


def build(
    *,
    db_path: Path | None = None,
    reports_dir: Path | None = None,
) -> Path:
    """Query the ledger (both paper + real buckets) and write the dashboard HTML."""
    reports_dir = reports_dir or REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / DASHBOARD_FILENAME

    data = _query_all(db_path=db_path)
    html = _render_html(data)
    out_path.write_text(html)
    return out_path


# --------- data layer ---------

def _query_all(*, db_path: Path | None) -> dict:
    """Build the dashboard payload. Two buckets — dhan-paper and dhan-live."""
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "paper": _query_bucket(modes=PAPER_MODES, db_path=db_path),
        "real": _query_bucket(modes=REAL_MODES, db_path=db_path),
    }


def _query_bucket(*, modes: tuple[str, ...], db_path: Path | None) -> dict:
    """Build the per-bucket sub-payload.

    A "bucket" can span multiple ledger modes if/when additional live
    variants land (e.g. a 'dhan-sandbox' mode for API integration tests).
    For v1 it's one mode per bucket: dhan-paper for the paper tab and
    dhan-live for the live tab.
    """
    db_path = db_path or portfolio_db.DEFAULT_DB_PATH

    with portfolio_db.connect(db_path) as conn:
        placeholders = ",".join(["?"] * len(modes))
        rows = conn.execute(
            f"SELECT DISTINCT d FROM ("
            f"  SELECT as_of_date AS d FROM submitted_orders WHERE mode IN ({placeholders}) "
            f"  UNION ALL "
            f"  SELECT snapshot_date AS d FROM broker_positions WHERE mode IN ({placeholders}) "
            f"  UNION ALL "
            f"  SELECT as_of_date AS d FROM discrepancies "
            f"    WHERE mode IN ({placeholders}) AND as_of_date IS NOT NULL "
            f") ORDER BY d",
            list(modes) * 3,
        ).fetchall()
        all_dates: list[date] = [r[0] for r in rows]

        by_date: dict[str, dict] = {}
        equity_curve: list[dict] = []
        for d in all_dates:
            entry = _query_one_day(conn, modes=modes, d=d)
            by_date[d.isoformat()] = entry
            equity_curve.append({
                "date": d.isoformat(),
                "equity": entry["total_equity_usd"],
            })

    return {
        "modes_included": list(modes),
        "dates": [d.isoformat() for d in all_dates],
        "by_date": by_date,
        "equity_curve": equity_curve,
    }


def _query_one_day(conn, *, modes: tuple[str, ...], d: date) -> dict:
    """All-cells query for one (date, bucket) combo."""
    placeholders = ",".join(["?"] * len(modes))

    target_rows = conn.execute(
        f"SELECT ticker, target_fraction, mode FROM desired_targets "
        f"WHERE as_of_date = ? AND mode IN ({placeholders}) "
        f"ORDER BY target_fraction DESC",
        [d, *modes],
    ).fetchall()
    targets = [
        {"ticker": t, "target_fraction": float(f), "mode": m}
        for t, f, m in target_rows
    ]

    # Orders shown for day D = anything that "happened" on D:
    #   - orders submitted today (as_of_date = D), OR
    #   - orders whose fill landed today (filled_at::date = D)
    # In dhan-paper / dhan-live (signal-on-T, fills-on-T intraday) the
    # signal-day and fill-day are the SAME day, so the UNION collapses
    # cleanly to one row per (order, day). The clause is kept identical
    # to the US repo's so the equity-curve logic continues to work if
    # a future mode reintroduces next-day-open fills.
    order_rows = conn.execute(
        f"SELECT so.order_id, so.ticker, so.side, so.quantity, so.limit_price, "
        f"       so.status, so.mode, so.as_of_date, "
        f"       af.fill_price, af.filled_at, af.commission "
        f"FROM submitted_orders so "
        f"LEFT JOIN actual_fills af ON af.order_id = so.order_id "
        f"WHERE so.mode IN ({placeholders}) AND ("
        f"  so.as_of_date = ? OR CAST(af.filled_at AS DATE) = ?"
        f") "
        f"ORDER BY COALESCE(CAST(af.filled_at AS DATE), so.as_of_date), so.side, so.ticker",
        [*modes, d, d],
    ).fetchall()

    # Realized P&L per sell order (aggregated across FIFO lots consumed).
    # One sell can consume multiple buy lots → multiple realized_trades rows;
    # we sum the P&L, weighted-avg the buy_price, and capture holding-day range.
    # Buys remain None — no realization until they're sold.
    rt_rows = conn.execute(
        f"SELECT af.order_id, "
        f"       SUM(rt.realized_pnl_usd) AS pnl, "
        f"       SUM(rt.buy_price * rt.qty) / NULLIF(SUM(rt.qty), 0) AS avg_buy, "
        f"       MIN(rt.holding_days) AS min_hold, "
        f"       MAX(rt.holding_days) AS max_hold, "
        f"       SUM(rt.tax_paid_usd) AS tax "
        f"FROM realized_trades rt "
        f"JOIN actual_fills af ON af.fill_id = rt.sell_fill_id "
        f"JOIN submitted_orders so ON so.order_id = af.order_id "
        f"WHERE so.mode IN ({placeholders}) AND ("
        f"  so.as_of_date = ? OR CAST(af.filled_at AS DATE) = ?"
        f") "
        f"GROUP BY af.order_id",
        [*modes, d, d],
    ).fetchall()
    realized_by_order = {
        oid: {
            "realized_pnl_usd": float(pnl) if pnl is not None else None,
            "avg_buy_price": float(avg_buy) if avg_buy is not None else None,
            "holding_days_min": int(min_h) if min_h is not None else None,
            "holding_days_max": int(max_h) if max_h is not None else None,
            "tax_estimate_usd": float(tax) if tax is not None else None,
        }
        for oid, pnl, avg_buy, min_h, max_h, tax in rt_rows
    }

    orders = [
        {
            "order_id": oid,
            "ticker": ticker,
            "side": side,
            "quantity": float(qty),
            "limit_price": float(lp) if lp is not None else None,
            "status": status,
            "mode": mode,
            "as_of_date": aod.isoformat() if aod else None,
            "fill_price": float(fp) if fp is not None else None,
            "filled_at": fa.isoformat(timespec="seconds") if fa else None,
            "commission": float(comm) if comm is not None else None,
            **realized_by_order.get(oid, {
                "realized_pnl_usd": None,
                "avg_buy_price": None,
                "holding_days_min": None,
                "holding_days_max": None,
                "tax_estimate_usd": None,
            }),
        }
        for oid, ticker, side, qty, lp, status, mode, aod, fp, fa, comm in order_rows
    ]
    # n_orders/n_fills mean DIFFERENT things now that orders can appear on
    # two days (signal-day + fill-day). Per-day summary metrics should
    # reflect activity that actually touched the account on that day:
    #   - n_orders: orders SUBMITTED today (signal activity)
    #   - n_fills:  fills LANDED today (broker activity / money movement)
    # Dollar aggregates are from fills landed today — that's when cash moved.
    d_iso = d.isoformat()

    def _is_fill_today(o):
        fa = o.get("filled_at")
        return o.get("fill_price") is not None and fa is not None and fa[:10] == d_iso

    def _is_order_today(o):
        return o.get("as_of_date") == d_iso

    n_orders = sum(1 for o in orders if _is_order_today(o))
    n_fills = sum(1 for o in orders if _is_fill_today(o))
    gross_buy = sum(
        (o["fill_price"] or 0) * o["quantity"]
        for o in orders if o["side"] == "buy" and _is_fill_today(o)
    )
    gross_sell = sum(
        (o["fill_price"] or 0) * o["quantity"]
        for o in orders if o["side"] == "sell" and _is_fill_today(o)
    )
    total_commission = sum(
        o["commission"] or 0 for o in orders if _is_fill_today(o)
    )
    # Realized P&L = sum of P&L on sells that filled today, summed across
    # the FIFO lots they consumed. `today_pnl_usd` (computed by load_state)
    # is the mark-to-market account-level change which INCLUDES this chunk;
    # surfacing realized separately lets the dashboard show how much of
    # today's PnL came from closing positions vs M2M on still-open ones.
    realized_pnl_today = sum(
        o["realized_pnl_usd"] or 0
        for o in orders
        if o["side"] == "sell" and _is_fill_today(o)
    )
    realized_tax_today = sum(
        o["tax_estimate_usd"] or 0
        for o in orders
        if o["side"] == "sell" and _is_fill_today(o)
    )

    # Positions: aggregate across modes in the bucket. Latest snapshot
    # date on-or-before `d` for ANY mode in the bucket — we pick the
    # max-date for each mode then take all of them combined.
    pos_rows = conn.execute(
        f"WITH latest_per_mode AS ("
        f"  SELECT mode, MAX(snapshot_date) AS snap_d FROM broker_positions "
        f"  WHERE mode IN ({placeholders}) AND snapshot_date <= ? GROUP BY mode "
        f") "
        f"SELECT bp.ticker, bp.quantity, bp.mark_price, bp.mark_value, bp.mode, bp.snapshot_date "
        f"FROM broker_positions bp "
        f"JOIN latest_per_mode l ON l.mode = bp.mode AND l.snap_d = bp.snapshot_date "
        f"WHERE bp.quantity != 0 "
        f"ORDER BY bp.mark_value DESC NULLS LAST",
        [*modes, d],
    ).fetchall()
    positions = [
        {
            "ticker": t,
            "qty": float(q),
            "mark_price": float(mp) if mp is not None else None,
            "mark_value": float(mv) if mv is not None else None,
            "mode": mode,
            "snapshot_date": sd.isoformat() if sd else None,
        }
        for t, q, mp, mv, mode, sd in pos_rows
    ]
    positions_mark = sum(p["mark_value"] or 0 for p in positions)
    # Invested value = sum of (qty_open × buy_price) across currently open
    # lots, for every mode in the bucket. This is what we ACTUALLY PAID for
    # the still-held shares (slippage + ref-price baked in via buy_price).
    # Total return = mark - invested; per-position view of execution-cost
    # drag and mark-to-market P&L without the cash side polluting it.
    invested_row = conn.execute(
        f"SELECT COALESCE(SUM(qty_open * buy_price), 0.0) "
        f"FROM position_lots WHERE mode IN ({placeholders}) AND qty_open > 0",
        [*modes],
    ).fetchone()
    positions_invested = float(invested_row[0] or 0.0)

    # Cash + peak + today-PnL across all modes in the bucket.
    # We sum across modes; the assumption is one bucket = one logical
    # account (paper-bucket = dhan-paper; live-bucket = dhan-live; in
    # v1 there's exactly one mode per bucket).
    cash_usd = 0.0
    peak_equity = 0.0
    today_pnl = 0.0
    halted_any = False
    for m in modes:
        state = portfolio_db.load_state(conn, mode=m, as_of=d)
        cash_usd += state.cash_usd
        # Peak should be the max across modes (best single account-day).
        peak_equity = max(peak_equity, state.peak_equity)
        today_pnl += state.today_pnl_usd
        halted_any = halted_any or state.halted

    disc_rows = conn.execute(
        f"SELECT kind, ticker, resolution, notes, mode FROM discrepancies "
        f"WHERE as_of_date = ? AND mode IN ({placeholders}) ORDER BY detected_at",
        [d, *modes],
    ).fetchall()
    discrepancies = [
        {"kind": k, "ticker": t, "resolution": r,
         "notes": (n or "")[:300], "mode": m}
        for k, t, r, n, m in disc_rows
    ]

    total_equity = cash_usd + positions_mark
    drawdown_pct = (
        (total_equity - peak_equity) / peak_equity
        if peak_equity > 0 else 0.0
    )

    return {
        "date": d.isoformat(),
        "targets": targets,
        "orders": orders,
        "positions": positions,
        "cash_usd": float(cash_usd),
        "total_equity_usd": float(total_equity),
        "peak_equity_usd": float(peak_equity),
        "today_pnl_usd": float(today_pnl),
        "positions_invested_inr": float(positions_invested),
        "positions_mark_inr": float(positions_mark),
        "drawdown_pct": float(drawdown_pct),
        "halted": bool(halted_any),
        "discrepancies": discrepancies,
        "n_orders": n_orders,
        "n_fills": n_fills,
        "gross_buy_usd": float(gross_buy),
        "gross_sell_usd": float(gross_sell),
        "total_commission_usd": float(total_commission),
        "realized_pnl_today_usd": float(realized_pnl_today),
        "realized_tax_today_usd": float(realized_tax_today),
    }


# --------- rendering ---------

def _render_html(data: dict) -> str:
    payload_json = json.dumps(data, separators=(",", ":"))
    return _HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Trading Dashboard</title>
<style>
  :root {
    --bg: #fafbfc;
    --panel: #ffffff;
    --border: #e5e7eb;
    --text: #111827;
    --muted: #6b7280;
    --positive: #10b981;
    --negative: #ef4444;
    --accent: #2563eb;
    --warning: #f59e0b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.5;
  }
  .container { max-width: 1280px; margin: 0 auto; padding: 32px 24px; }
  h1 { margin: 0 0 4px 0; font-size: 28px; letter-spacing: -0.02em; }
  .subtitle { color: var(--muted); font-size: 14px; margin-bottom: 24px; }

  /* Tabs */
  .tabs {
    display: flex; gap: 4px; margin-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .tab {
    padding: 10px 20px; cursor: pointer;
    border: none; background: none;
    color: var(--muted); font-size: 14px; font-weight: 500;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color 0.15s, border-color 0.15s;
  }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab .count {
    display: inline-block; background: var(--border); color: var(--text);
    padding: 1px 7px; border-radius: 10px; font-size: 11px;
    margin-left: 6px; font-weight: 600;
  }
  .tab.active .count { background: #dbeafe; color: var(--accent); }

  .slider-row {
    display: flex; align-items: center; gap: 12px;
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px; margin-bottom: 20px;
  }
  .slider-row button {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 12px; cursor: pointer;
    font-size: 16px; color: var(--text);
  }
  .slider-row button:hover:not(:disabled) { background: #f3f4f6; }
  .slider-row button:disabled { opacity: 0.4; cursor: not-allowed; }
  #date-slider { flex: 1; height: 6px; -webkit-appearance: none; appearance: none;
    background: var(--border); border-radius: 3px; outline: none; }
  #date-slider:disabled { opacity: 0.4; }
  #date-slider::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 20px; height: 20px; background: var(--accent);
    border-radius: 50%; cursor: pointer;
  }
  #date-slider::-moz-range-thumb {
    width: 20px; height: 20px; background: var(--accent);
    border-radius: 50%; cursor: pointer; border: none;
  }
  #current-date { font-weight: 600; min-width: 110px; text-align: center; font-size: 15px; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    background: #eff6ff; color: var(--accent); font-size: 12px; font-weight: 500;
  }
  .badge.halted { background: #fef2f2; color: var(--negative); }
  .badge.empty { background: #f3f4f6; color: var(--muted); }

  .metrics-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
    margin-bottom: 20px;
  }
  /* Holdings is the headline card — give it 2 columns so the sub-metrics
     (Invested · 1D · Total returns) sit on one line, not wrapped. */
  .metrics-grid .card-wide { grid-column: span 2; }
  @media (max-width: 800px) {
    .metrics-grid { grid-template-columns: repeat(2, 1fr); }
    .metrics-grid .card-wide { grid-column: span 2; }
  }
  .card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px;
  }
  .card h2 { margin: 0 0 12px 0; font-size: 16px; font-weight: 600; }
  .metric-label { color: var(--muted); font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.04em; }
  .metric-value { font-size: 28px; font-weight: 600; margin-top: 4px; letter-spacing: -0.01em; }
  .metric-sub { color: var(--muted); font-size: 12px; margin-top: 4px; }
  .positive { color: var(--positive); }
  .negative { color: var(--negative); }
  .warning { color: var(--warning); }

  .chart-card { padding: 16px 20px 20px; margin-bottom: 20px; }
  .chart-card canvas { width: 100% !important; height: 260px !important; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead th {
    text-align: left; font-weight: 500; color: var(--muted);
    padding: 8px 12px; border-bottom: 1px solid var(--border);
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;
  }
  tbody td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; }
  tbody tr:last-child td { border-bottom: none; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.ticker { font-weight: 600; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 500; text-transform: uppercase; }
  .pill-buy { background: #d1fae5; color: #065f46; }
  .pill-sell { background: #fee2e2; color: #991b1b; }
  .pill-filled { background: #dbeafe; color: #1e40af; }
  .pill-pending { background: #fef3c7; color: #92400e; }
  .pill-cancelled { background: #f3f4f6; color: #4b5563; }
  .pill-rejected { background: #fee2e2; color: #991b1b; }

  .empty-state {
    color: var(--muted); font-style: italic; padding: 16px 0; text-align: center;
  }
  .empty-tab {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 64px 24px; text-align: center;
    color: var(--muted);
  }
  .empty-tab h3 { color: var(--text); margin: 0 0 8px 0; font-size: 18px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 800px) { .two-col { grid-template-columns: 1fr; } }
  .footer { margin-top: 32px; color: var(--muted); font-size: 12px; }
  .modes-line { color: var(--muted); font-size: 12px; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="container">
  <h1>Trading Dashboard</h1>
  <div class="subtitle">
    Generated: <span id="generated-at"></span>
  </div>

  <div class="tabs">
    <button class="tab" data-bucket="paper">
      Dhan Paper <span class="count" id="count-paper">0</span>
    </button>
    <button class="tab" data-bucket="real">
      Dhan Live <span class="count" id="count-real">0</span>
    </button>
  </div>

  <div id="bucket-content"></div>

  <div class="footer">
    Built by <code>scripts/dashboard.py</code> after every <code>scripts/run_live.py</code>
    invocation. Dhan Paper = brokers.dhan_mock-simulated; Dhan Live = real Dhan API.
    Single-file static HTML — open <code>state/reports/dashboard.html</code>.
  </div>
</div>

<template id="tab-template">
  <div class="modes-line"></div>
  <div class="slider-row">
    <button class="btn-prev">←</button>
    <span class="current-date">—</span>
    <input type="range" class="date-slider" min="0" max="0" step="1" value="0" />
    <button class="btn-next">→</button>
    <span class="status-badge"></span>
  </div>
  <div class="metrics-grid">
    <div class="card card-wide"><div class="metric-label">Holdings — current value</div>
      <div class="metric-value m-current-value">—</div>
      <div class="metric-sub" style="margin-top:10px; white-space:nowrap">
        <span class="metric-label" style="margin-right:6px">Invested</span>
        <span class="m-invested-value">—</span>
        &nbsp;·&nbsp;
        <span class="metric-label" style="margin-right:6px">1D</span>
        <span class="m-today-pnl">—</span> <span class="m-today-pnl-pct"></span>
        &nbsp;·&nbsp;
        <span class="metric-label" style="margin-right:6px">Total returns</span>
        <span class="m-total-returns">—</span> <span class="m-total-returns-pct"></span>
      </div>
      <div class="metric-sub m-realized-pnl-today" style="margin-top:6px"></div></div>
    <div class="card"><div class="metric-label">Cash</div>
      <div class="metric-value m-cash">—</div>
      <div class="metric-sub m-cash-pct"></div>
      <div class="metric-sub" style="margin-top:6px">
        <span class="metric-label" style="margin-right:6px">Net worth</span>
        <span class="m-total-equity">—</span>
      </div>
      <div class="metric-sub m-drawdown"></div></div>
    <div class="card"><div class="metric-label">Fills Today</div>
      <div class="metric-value m-trades">—</div>
      <div class="metric-sub m-commission"></div></div>
  </div>
  <div class="card chart-card">
    <h2>Cumulative Equity</h2>
    <canvas class="equity-chart"></canvas>
  </div>
  <div class="card" style="margin-bottom:20px">
    <h2>Orders &amp; Fills</h2>
    <div class="orders-section"></div>
  </div>
  <div class="two-col">
    <div class="card"><h2>Positions</h2>
      <div class="metric-sub positions-snap-date" style="margin-bottom:8px"></div>
      <div class="positions-section"></div></div>
    <div class="card"><h2>Targets</h2>
      <div class="targets-section"></div></div>
  </div>
  <div class="card" style="margin-top:20px"><h2>Discrepancies</h2>
    <div class="discrepancies-section"></div></div>
</template>

<template id="empty-template">
  <div class="empty-tab">
    <h3 class="empty-title">No data yet</h3>
    <p class="empty-body"></p>
  </div>
</template>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const DATA = __PAYLOAD_JSON__;

// INR formatting: ₹ symbol, en-IN grouping (lakh/crore comma style), 2dp.
// For magnitudes >= 1 lakh we append a (L) or (cr) shorthand — matches
// how Indian brokerage statements quote balances.
const fmtINR = (v) => {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  const head = sign + '₹' + abs.toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
  if (abs >= 1e7) return head + ' (' + sign + (abs / 1e7).toFixed(2) + ' cr)';
  if (abs >= 1e5) return head + ' (' + sign + (abs / 1e5).toFixed(2) + ' L)';
  return head;
};
const fmtINRpx = (v) =>
  (v < 0 ? '-' : '') + '₹' + Math.abs(v).toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 4,
  });
const fmtPct = (v) => (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%';
const fmtSignedINR = (v) => (v >= 0 ? '+' : '') + fmtINR(v);
const cls = (v) => v >= 0 ? 'positive' : 'negative';

// Back-compat aliases — the rest of the dashboard JS references these
// names; defining them here lets the swap stay surgical.
const fmtUSD = fmtINR;
const fmtSignedUSD = fmtSignedINR;

// One Chart.js instance per bucket, reused across slider moves.
const _charts = {};

function renderDay(bucketEl, bucket, iso) {
  const day = bucket.by_date[iso];
  if (!day) return;
  bucketEl.querySelector('.current-date').textContent = iso;

  // IMPORTANT: every `.className = '...'` MUST preserve the marker class
  // (e.g. m-today-pnl). querySelector relies on it for the next slider move.
  const pnl = day.today_pnl_usd;
  const pnlEl = bucketEl.querySelector('.m-today-pnl');
  pnlEl.textContent = fmtSignedUSD(pnl);
  pnlEl.className = 'metric-value m-today-pnl ' + cls(pnl);
  const pnlPctEl = bucketEl.querySelector('.m-today-pnl-pct');
  const baseEquity = day.total_equity_usd - pnl;
  if (baseEquity > 0) {
    const ret = pnl / baseEquity;
    pnlPctEl.textContent = fmtPct(ret);
    pnlPctEl.className = 'metric-sub m-today-pnl-pct ' + cls(ret);
  } else {
    pnlPctEl.textContent = '';
    pnlPctEl.className = 'metric-sub m-today-pnl-pct';
  }
  // Realized P&L breakdown — how much of today's PnL came from sells closing positions.
  const rpEl = bucketEl.querySelector('.m-realized-pnl-today');
  if (day.realized_pnl_today_usd !== undefined && day.realized_pnl_today_usd !== 0) {
    const rp = day.realized_pnl_today_usd;
    const tax = day.realized_tax_today_usd || 0;
    rpEl.innerHTML = '<span class="' + cls(rp) + '">Realized: ' + fmtSignedUSD(rp) + '</span>'
      + (tax > 0 ? ' <span style="color:var(--muted)">(est tax: ' + fmtUSD(tax) + ')</span>' : '');
    rpEl.className = 'metric-sub m-realized-pnl-today';
  } else {
    rpEl.innerHTML = '<span style="color:var(--muted)">No realized P&L today</span>';
    rpEl.className = 'metric-sub m-realized-pnl-today';
  }

  // Holdings: invested (sum of qty_open * buy_price across open lots) +
  // current value (mark-to-market) + total returns. Cash is shown as a
  // separate card; total equity = holdings + cash is a footnote.
  const invested = day.positions_invested_inr || 0;
  const current = day.positions_mark_inr || 0;
  const totRet = current - invested;
  bucketEl.querySelector('.m-current-value').textContent = fmtUSD(current);
  bucketEl.querySelector('.m-invested-value').textContent = fmtUSD(invested);
  const trEl = bucketEl.querySelector('.m-total-returns');
  trEl.textContent = fmtSignedUSD(totRet);
  trEl.className = 'm-total-returns ' + cls(totRet);
  const trpEl = bucketEl.querySelector('.m-total-returns-pct');
  if (invested > 0) {
    const r = totRet / invested;
    trpEl.textContent = '(' + fmtPct(r) + ')';
    trpEl.className = 'm-total-returns-pct ' + cls(r);
  } else {
    trpEl.textContent = '';
    trpEl.className = 'm-total-returns-pct';
  }

  bucketEl.querySelector('.m-total-equity').textContent = fmtUSD(day.total_equity_usd);
  const ddEl = bucketEl.querySelector('.m-drawdown');
  ddEl.textContent = 'Peak: ' + fmtUSD(day.peak_equity_usd)
    + '  (DD ' + fmtPct(day.drawdown_pct) + ')';
  ddEl.className = 'metric-sub m-drawdown ' + (day.drawdown_pct < 0 ? 'negative' : 'positive');

  bucketEl.querySelector('.m-cash').textContent = fmtUSD(day.cash_usd);
  bucketEl.querySelector('.m-cash-pct').textContent = day.total_equity_usd > 0
    ? (100 * day.cash_usd / day.total_equity_usd).toFixed(1) + '% of equity'
    : '';

  // "Fills today" tile shows the money-movement count + submitted (intent) count.
  bucketEl.querySelector('.m-trades').textContent = day.n_fills
    + (day.n_orders > 0 ? ' (' + day.n_orders + ' new orders)' : '');
  bucketEl.querySelector('.m-commission').textContent =
    'Commission: ' + fmtUSD(day.total_commission_usd);

  const statusEl = bucketEl.querySelector('.status-badge');
  if (day.halted) {
    statusEl.textContent = 'HALTED';
    statusEl.className = 'status-badge badge halted';
  } else {
    statusEl.textContent = '';
    statusEl.className = 'status-badge';
  }

  // Orders
  const ordersDiv = bucketEl.querySelector('.orders-section');
  if (day.orders.length === 0) {
    ordersDiv.innerHTML = '<div class="empty-state">No orders this day.</div>';
  } else {
    const rows = day.orders.map(o => {
      const limPx = o.limit_price !== null ? fmtUSD(o.limit_price) : '—';
      const fillPx = o.fill_price !== null ? fmtUSD(o.fill_price) : '—';
      const filledAt = o.filled_at || '—';
      const comm = o.commission !== null ? fmtUSD(o.commission) : '—';
      const signalDate = o.as_of_date || '—';
      const fillIso = o.filled_at ? o.filled_at.slice(0, 10) : null;
      const isFillToday = fillIso === iso;
      const isSubToday = o.as_of_date === iso;
      let activity = '';
      if (isFillToday && isSubToday) activity = '<span class="pill pill-filled">same-day</span>';
      else if (isFillToday) activity = '<span class="pill pill-filled">filled</span>';
      else if (isSubToday) activity = '<span class="pill pill-pending">submitted</span>';
      // P&L column: realized P&L (sells only; FIFO-aggregated across consumed
      // buy lots). Avg buy price + holding-days range as a tooltip-ish sub-line.
      let pnlCell = '—';
      if (o.side === 'sell' && o.realized_pnl_usd !== null && o.realized_pnl_usd !== undefined) {
        const pnl = o.realized_pnl_usd;
        const cell = `<span class="${cls(pnl)}">${fmtSignedUSD(pnl)}</span>`;
        let sub = '';
        if (o.avg_buy_price !== null && o.avg_buy_price !== undefined) {
          sub += `<div class="metric-sub" style="font-size:11px;margin-top:2px">avg buy ${fmtUSD(o.avg_buy_price)}`;
          if (o.holding_days_min !== null && o.holding_days_min !== undefined) {
            const hd = (o.holding_days_min === o.holding_days_max)
              ? `${o.holding_days_min}d` : `${o.holding_days_min}-${o.holding_days_max}d`;
            sub += ` · held ${hd}`;
          }
          sub += `</div>`;
        }
        pnlCell = cell + sub;
      }
      return `<tr>
        <td class="ticker">${o.ticker}</td>
        <td><span class="pill pill-${o.side}">${o.side}</span></td>
        <td class="num">${o.quantity.toFixed(4)}</td>
        <td class="num">${limPx}</td>
        <td class="num">${fillPx}</td>
        <td class="num">${comm}</td>
        <td class="num">${pnlCell}</td>
        <td><span class="pill pill-${o.status}">${o.status}</span></td>
        <td>${signalDate}</td>
        <td>${filledAt}</td>
        <td>${activity}</td>
      </tr>`;
    }).join('');
    ordersDiv.innerHTML = `<table>
      <thead><tr>
        <th>Ticker</th><th>Side</th><th class="num">Qty</th>
        <th class="num">Limit Px</th><th class="num">Fill Px</th>
        <th class="num">Comm</th><th class="num">Realized P&amp;L</th>
        <th>Status</th>
        <th>Signal Date</th><th>Filled At</th><th>Today's Activity</th>
      </tr></thead>
      <tbody>${rows}</tbody></table>`;
  }

  // Positions
  const posDiv = bucketEl.querySelector('.positions-section');
  const snapDateEl = bucketEl.querySelector('.positions-snap-date');
  if (day.positions.length === 0) {
    posDiv.innerHTML = '<div class="empty-state">No open positions.</div>';
    snapDateEl.textContent = '';
  } else {
    const rows = day.positions.map(p => `<tr>
      <td class="ticker">${p.ticker}</td>
      <td class="num">${p.qty.toFixed(4)}</td>
      <td class="num">${p.mark_price !== null ? fmtUSD(p.mark_price) : '—'}</td>
      <td class="num">${p.mark_value !== null ? fmtUSD(p.mark_value) : '—'}</td>
    </tr>`).join('');
    posDiv.innerHTML = `<table>
      <thead><tr>
        <th>Ticker</th><th class="num">Qty</th>
        <th class="num">Mark</th><th class="num">Value</th>
      </tr></thead>
      <tbody>${rows}</tbody></table>`;
    const snapDates = [...new Set(day.positions.map(p => p.snapshot_date).filter(Boolean))];
    snapDateEl.textContent = 'Snapshot date(s): ' + snapDates.join(', ');
  }

  // Targets
  const tgtDiv = bucketEl.querySelector('.targets-section');
  if (day.targets.length === 0) {
    tgtDiv.innerHTML = '<div class="empty-state">No targets for this day.</div>';
  } else {
    const rows = day.targets.map(t => `<tr>
      <td class="ticker">${t.ticker}</td>
      <td class="num">${fmtPct(t.target_fraction)}</td>
    </tr>`).join('');
    tgtDiv.innerHTML = `<table>
      <thead><tr><th>Ticker</th><th class="num">Target %</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  }

  // Discrepancies
  const discDiv = bucketEl.querySelector('.discrepancies-section');
  if (day.discrepancies.length === 0) {
    discDiv.innerHTML = '<div class="empty-state">No discrepancies.</div>';
  } else {
    const rows = day.discrepancies.map(d => `<tr>
      <td>${d.kind}</td>
      <td class="ticker">${d.ticker || '—'}</td>
      <td>${d.resolution || '—'}</td>
      <td>${d.notes || ''}</td>
    </tr>`).join('');
    discDiv.innerHTML = `<table>
      <thead><tr><th>Kind</th><th>Ticker</th><th>Resolution</th><th>Notes</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  }
}

function renderChart(bucketEl, bucket, highlightIso, bucketKey) {
  const canvas = bucketEl.querySelector('.equity-chart');
  if (!canvas) return;
  const labels = bucket.equity_curve.map(p => p.date);
  const values = bucket.equity_curve.map(p => p.equity);
  const pointRadius = labels.map(d => d === highlightIso ? 6 : 0);
  if (_charts[bucketKey]) {
    _charts[bucketKey].data.datasets[0].pointRadius = pointRadius;
    _charts[bucketKey].update('none');
    return;
  }
  _charts[bucketKey] = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true, tension: 0.2, pointRadius,
        pointBackgroundColor: '#2563eb',
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => '₹' + v.toLocaleString('en-IN') } },
        x: { ticks: { autoSkip: true, maxTicksLimit: 12 } },
      },
    },
  });
}

function mountTab(bucketKey, bucket) {
  const root = document.getElementById('bucket-content');
  root.innerHTML = '';
  if (!bucket.dates || bucket.dates.length === 0) {
    const tpl = document.getElementById('empty-template').content.cloneNode(true);
    tpl.querySelector('.empty-body').innerHTML = bucketKey === 'paper'
      ? 'No dhan-paper runs yet. Run <code>uv run python -m scripts.run_live</code> to start.'
      : 'No dhan-live activity yet. Once the live executor starts writing fills with mode=' +
        bucket.modes_included.map(m => '<code>' + m + '</code>').join(' or ') +
        ' (post 4-week paper validation), they will appear here.';
    root.appendChild(tpl);
    return;
  }
  const tpl = document.getElementById('tab-template').content.cloneNode(true);
  root.appendChild(tpl);
  const bucketEl = root.firstElementChild ? root : root;  // template inserts children directly

  // After cloneNode + appendChild, root contains the section nodes. Set up bindings.
  const slider = root.querySelector('.date-slider');
  const prevBtn = root.querySelector('.btn-prev');
  const nextBtn = root.querySelector('.btn-next');
  root.querySelector('.modes-line').innerHTML =
    'Modes included: ' + bucket.modes_included.map(m => '<code>' + m + '</code>').join(', ');

  slider.min = 0;
  slider.max = bucket.dates.length - 1;
  slider.value = bucket.dates.length - 1;

  const update = (idx) => {
    slider.value = idx;
    const iso = bucket.dates[idx];
    renderDay(root, bucket, iso);
    renderChart(root, bucket, iso, bucketKey);
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === bucket.dates.length - 1;
  };

  slider.addEventListener('input', e => update(parseInt(e.target.value, 10)));
  prevBtn.addEventListener('click', () => update(Math.max(0, parseInt(slider.value, 10) - 1)));
  nextBtn.addEventListener('click', () => update(
    Math.min(bucket.dates.length - 1, parseInt(slider.value, 10) + 1)));

  update(bucket.dates.length - 1);
}

function init() {
  document.getElementById('generated-at').textContent = DATA.generated_at;
  document.getElementById('count-paper').textContent = (DATA.paper.dates || []).length;
  document.getElementById('count-real').textContent = (DATA.real.dates || []).length;

  const tabs = document.querySelectorAll('.tab');
  const switchTo = (key) => {
    tabs.forEach(t => t.classList.toggle('active', t.dataset.bucket === key));
    // Drop the chart instance for the bucket we're leaving so it
    // rebuilds clean on next entry (avoids stale canvas refs).
    Object.keys(_charts).forEach(k => {
      if (k !== key && _charts[k]) { _charts[k].destroy(); delete _charts[k]; }
    });
    mountTab(key, DATA[key]);
  };

  tabs.forEach(t => t.addEventListener('click', () => switchTo(t.dataset.bucket)));
  // Default tab: paper if it has data, else real, else paper.
  const defaultBucket = (DATA.paper.dates || []).length > 0 ? 'paper'
    : (DATA.real.dates || []).length > 0 ? 'real' : 'paper';
  switchTo(defaultBucket);
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
"""


# --------- CLI ---------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=None,
                   help="Reports directory (default: state/reports/)")
    args = p.parse_args(argv)

    out_path = build(reports_dir=args.out_dir)
    print(f"[dashboard] wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
