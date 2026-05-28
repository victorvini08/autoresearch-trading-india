"""Reconciliation: the seven mechanical questions about live paper trading.

Pure read-only computation against portfolio.duckdb. Returns a structured
dict ready for JSON or dashboard rendering. No LLM, no opinions, no writes.

The questions, per (date, mode):

1. Did we hold what we intended?
       Compare submitted_orders status counts + flag any order where filled
       qty != requested qty.

2. Did execution match assumptions?
       Today's avg/min/max fill slippage in bps; flag if outside thresholds.

3. Did live constraints distort the book?
       Diff between desired_targets fractions and actual broker_positions
       fractions (gross drag + per-name drag).

4. Did T+1 cash math hold?
       Today's buy outflows must not exceed pre-day settled cash + today's
       non-sell inflows (deposits / dividends). Same-day sale proceeds
       cannot fund same-day buys per NSE T+1 settlement.

5. Did peak-equity drawdown cross 8% / 12% / 16% safety thresholds?
       8% = WATCH, 12% = RISK_REDUCED, 16% = HALTED_REVIEW. Thresholds
       calibrated to our backtest (aggregate max DD 12.2%, worst-fold 7.2%).

6. Corporate actions on held / recently-traded names today?
       Reads storage/corporate_actions.json — warns when an ex-date hits
       a name on the book so PnL/drift isn't misattributed.

7. FY tax reserve and deployable equity.
       Step 1.e: STCG (<12mo, 15%) + LTCG (≥12mo, 10% above ₹1L exemption),
       FY-to-date. Surfaces "FY26 tax reserve: ₹X (Y% of equity); deployable
       ₹Z" so paper-PnL isn't mistaken for compounding capital.

Each answer is `{"status": "ok" | "warn" | "flag", "detail": <str>, ...}`.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from storage.portfolio_db import (
    DEFAULT_DB_PATH,
    compute_fy_tax_reserve,
    connect,
    get_cash_balance,
    load_state,
)

# Safety-state DD thresholds — must stay in sync with data/safety_state.py
# (Step 2). Calibrated to our backtest: aggregate max DD 12.2%, worst-fold 7.2%.
DD_WATCH = 0.08
DD_RISK_REDUCED = 0.12
DD_HALTED_REVIEW = 0.16

# Execution flagging thresholds — conservative defaults; tune later
SLIPPAGE_AVG_FLAG_BPS = 50.0
SLIPPAGE_MAX_FLAG_BPS = 200.0

# Construction drag flag threshold (total gross drag, in bps)
CONSTRUCTION_DRAG_FLAG_BPS = 500.0

# Minimum per-name drag to report in the drag_rows list (50 bps)
PER_NAME_DRAG_REPORT_THRESHOLD = 0.005


def compute_reconciliation_for_date(
    d: date,
    mode: str = "dhan-paper",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Compute the reconciliation answers for (date, mode)."""
    conn = connect(db_path)
    try:
        return {
            "date": d.isoformat(),
            "mode": mode,
            "held_what_intended": _q1_held_what_intended(conn, d, mode),
            "execution_matched_assumptions": _q2_execution(conn, d, mode),
            "construction_drag": _q3_construction(conn, d, mode),
            "t1_cash_math": _q4_t1_cash_math(conn, d, mode),
            "drawdown_threshold": _q5_drawdown(conn, d, mode),
            "corporate_actions": _q6_corporate_actions(conn, d, mode),
            "tax_reserve": _q7_tax_reserve(conn, d, mode),
        }
    finally:
        conn.close()


# === Q1: did we hold what we intended? =====================================

# Map raw broker status strings into a normalized 4-bucket histogram so
# the dashboard reads "5 traded, 1 partial, 0 rejected, 0 pending"
# regardless of casing / legacy values (the pre-Step-1.d ledger wrote
# lowercase "filled"; we treat it as "traded").
_STATUS_BUCKETS = {
    "TRADED": "traded", "FILLED": "traded", "FILL": "traded",
    "PART_TRADED": "partial", "PARTIAL": "partial", "PARTIALLY_FILLED": "partial",
    "REJECTED": "rejected", "REJECT": "rejected",
    "CANCELLED": "cancelled", "CANCELED": "cancelled",
    "EXPIRED": "expired",
    "PENDING": "pending", "TRANSIT": "pending",
    "TIMEOUT": "pending", "UNKNOWN": "pending",
}


def _bucketize_statuses(raw_counts: dict[str, int]) -> dict[str, int]:
    out = {"traded": 0, "partial": 0, "rejected": 0, "cancelled": 0,
           "expired": 0, "pending": 0, "other": 0}
    for raw, n in raw_counts.items():
        bucket = _STATUS_BUCKETS.get((raw or "").upper(), "other")
        out[bucket] += n
    return out


def _q1_held_what_intended(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    statuses = conn.execute(
        "SELECT status, COUNT(*) FROM submitted_orders "
        "WHERE as_of_date = ? AND mode = ? GROUP BY status",
        [d, mode],
    ).fetchall()
    raw_counts = {s: c for s, c in statuses}
    total_orders = sum(raw_counts.values())

    if total_orders == 0:
        return {
            "status": "ok",
            "detail": "No orders submitted today (no rebalance).",
            "status_counts": {},
            "buckets": _bucketize_statuses({}),
            "mismatches": [],
        }

    buckets = _bucketize_statuses(raw_counts)

    # Find orders where the SUM of actual fills doesn't equal requested qty.
    # Captures: partial fills, rejected orders, cancelled orders.
    mismatches = conn.execute(
        """
        SELECT so.ticker, so.side, so.quantity AS requested,
               COALESCE(SUM(af.quantity), 0.0) AS filled, so.status
        FROM submitted_orders so
        LEFT JOIN actual_fills af ON so.order_id = af.order_id
        WHERE so.as_of_date = ? AND so.mode = ?
        GROUP BY so.order_id, so.ticker, so.side, so.quantity, so.status
        HAVING ABS(COALESCE(SUM(af.quantity), 0.0) - so.quantity) > 0.001
        ORDER BY ABS(so.quantity - COALESCE(SUM(af.quantity), 0.0)) DESC
        """,
        [d, mode],
    ).fetchall()
    mismatch_rows = [
        {
            "ticker": t,
            "side": s,
            "requested": float(req),
            "filled": float(fil),
            "status": st,
        }
        for t, s, req, fil, st in mismatches
    ]

    # Compose a precise summary string. Only mention non-zero buckets so the
    # common path ("5 traded") stays clean and noteworthy paths
    # ("3 traded, 1 partial, 1 rejected") stand out.
    parts = []
    for label, key in (
        ("traded", "traded"),
        ("partial", "partial"),
        ("rejected", "rejected"),
        ("cancelled", "cancelled"),
        ("expired", "expired"),
        ("pending", "pending"),
    ):
        if buckets[key] > 0:
            parts.append(f"{buckets[key]} {label}")
    summary = ", ".join(parts) if parts else f"{total_orders} order(s)"

    if not mismatch_rows:
        return {
            "status": "ok",
            "detail": f"{summary} — all filled as intended.",
            "status_counts": raw_counts,
            "buckets": buckets,
            "mismatches": [],
        }
    return {
        "status": "flag",
        "detail": (
            f"{summary} — {len(mismatch_rows)} of {total_orders} "
            "did not fill cleanly."
        ),
        "status_counts": raw_counts,
        "buckets": buckets,
        "mismatches": mismatch_rows[:10],
    }


# === Q2: did execution match assumptions? ==================================

def _q2_execution(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT AVG(slippage_bps), MIN(slippage_bps), MAX(slippage_bps), COUNT(*)
        FROM actual_fills
        WHERE CAST(filled_at AS DATE) = ? AND mode = ?
          AND slippage_bps IS NOT NULL
        """,
        [d, mode],
    ).fetchone()
    avg_bps, min_bps, max_bps, n = row
    if not n:
        return {
            "status": "ok",
            "detail": "No fills today; no execution to assess.",
            "fill_count": 0,
        }

    flag = (avg_bps and avg_bps > SLIPPAGE_AVG_FLAG_BPS) or (
        max_bps and max_bps > SLIPPAGE_MAX_FLAG_BPS
    )
    return {
        "status": "flag" if flag else "ok",
        "detail": (
            f"{n} fill(s), avg slippage {avg_bps:.1f} bps "
            f"(min {min_bps:.1f}, max {max_bps:.1f})."
        ),
        "fill_count": int(n),
        "avg_bps": float(avg_bps),
        "min_bps": float(min_bps),
        "max_bps": float(max_bps),
    }


# === Q3: did live constraints distort the book? ============================

def _q3_construction(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    targets = conn.execute(
        "SELECT ticker, target_fraction FROM desired_targets "
        "WHERE as_of_date = ? AND mode = ?",
        [d, mode],
    ).fetchall()
    if not targets:
        return {
            "status": "ok",
            "detail": "No targets today (no rebalance).",
            "drag_rows": [],
        }

    try:
        state = load_state(conn, mode, d)
    except Exception as e:
        return {
            "status": "ok",
            "detail": f"Could not load state ({e}). Construction drag skipped.",
        }
    if state.mark_equity <= 0:
        return {
            "status": "ok",
            "detail": "Equity ≤ 0; cannot compute construction drag.",
        }

    positions = conn.execute(
        "SELECT ticker, COALESCE(mark_value, 0.0) FROM broker_positions "
        "WHERE snapshot_date = ? AND mode = ?",
        [d, mode],
    ).fetchall()
    actual_frac_by_ticker = {
        t: (mv / state.mark_equity) for t, mv in positions
    }

    drag_rows: list[dict[str, Any]] = []
    total_target = 0.0
    total_actual = 0.0
    for ticker, target_frac in targets:
        actual = actual_frac_by_ticker.get(ticker, 0.0)
        drag = target_frac - actual
        total_target += target_frac
        total_actual += actual
        if abs(drag) > PER_NAME_DRAG_REPORT_THRESHOLD:
            drag_rows.append(
                {
                    "ticker": ticker,
                    "target_fraction": float(target_frac),
                    "actual_fraction": float(actual),
                    "drag_bps": float(drag * 10000),
                }
            )

    drag_rows.sort(key=lambda r: abs(r["drag_bps"]), reverse=True)
    total_drag_bps = (total_target - total_actual) * 10000
    flag = abs(total_drag_bps) > CONSTRUCTION_DRAG_FLAG_BPS

    return {
        "status": "flag" if flag else "ok",
        "detail": (
            f"Construction drag: {total_drag_bps:+.0f} bps "
            f"(target gross {total_target*100:.1f}%, "
            f"actual {total_actual*100:.1f}%)."
        ),
        "total_drag_bps": float(total_drag_bps),
        "total_target_pct": float(total_target * 100),
        "total_actual_pct": float(total_actual * 100),
        "drag_rows": drag_rows[:10],
    }


# === Q4: did T+1 cash math hold? ===========================================

def _q4_t1_cash_math(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    # Pre-day settled cash = balance as of EOD yesterday. Uses the existing
    # ledger DAO so initial_deposit and prior-day sells (settled by today's
    # NSE morning) are included consistently with the rest of the system.
    pre_day_cash = get_cash_balance(conn, mode=mode, as_of=d - timedelta(days=1))

    # Today's buy outflows (recorded as negative amounts in cash_ledger).
    todays_buys_row = conn.execute(
        """
        SELECT COALESCE(SUM(ABS(amount_usd)), 0.0) FROM cash_ledger
        WHERE mode = ? AND kind = 'buy'
          AND CAST(entry_at AS DATE) = ?
        """,
        [mode, d],
    ).fetchone()
    todays_buys = float(todays_buys_row[0])

    # Today's non-sell inflows that DO fund same-day buys (deposit, dividend).
    # 'sell' rows are deliberately excluded — they settle T+1.
    todays_inflows_row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_usd), 0.0) FROM cash_ledger
        WHERE mode = ? AND kind IN ('deposit', 'dividend')
          AND CAST(entry_at AS DATE) = ?
        """,
        [mode, d],
    ).fetchone()
    todays_inflows = float(todays_inflows_row[0])

    available_for_buys = pre_day_cash + todays_inflows

    if todays_buys == 0.0:
        return {
            "status": "ok",
            "detail": "No buys today; T+1 cash math not exercised.",
            "todays_buys": 0.0,
            "available_for_buys": float(available_for_buys),
        }
    if todays_buys > available_for_buys + 1.0:  # ₹1 tolerance for rounding
        return {
            "status": "flag",
            "detail": (
                f"T+1 violation: ₹{todays_buys:,.0f} of today's buys exceeded "
                f"₹{available_for_buys:,.0f} pre-day cash + same-day non-sell "
                "inflows. Same-day sale proceeds appear to have funded buys."
            ),
            "todays_buys": float(todays_buys),
            "available_for_buys": float(available_for_buys),
            "pre_day_cash": float(pre_day_cash),
            "todays_inflows": float(todays_inflows),
        }
    return {
        "status": "ok",
        "detail": (
            f"₹{todays_buys:,.0f} in buys within "
            f"₹{available_for_buys:,.0f} available; T+1 OK."
        ),
        "todays_buys": float(todays_buys),
        "available_for_buys": float(available_for_buys),
    }


# === Q5: peak-equity drawdown ==============================================

def _q5_drawdown(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    try:
        state = load_state(conn, mode, d)
    except Exception as e:
        return {"status": "ok", "detail": f"Could not load state ({e})."}

    if state.peak_equity <= 0:
        return {
            "status": "ok",
            "detail": "No equity history yet; no drawdown to compute.",
            "dd_pct": 0.0,
        }

    dd_frac = (state.peak_equity - state.mark_equity) / state.peak_equity

    if dd_frac >= DD_HALTED_REVIEW:
        crossed = "HALTED_REVIEW (≥16%)"
        status = "flag"
    elif dd_frac >= DD_RISK_REDUCED:
        crossed = "RISK_REDUCED (≥12%)"
        status = "flag"
    elif dd_frac >= DD_WATCH:
        crossed = "WATCH (≥8%)"
        status = "warn"
    else:
        crossed = None
        status = "ok"

    return {
        "status": status,
        "detail": (
            f"DD {dd_frac*100:.2f}% from peak ₹{state.peak_equity:,.0f}; "
            + (f"crossed {crossed}." if crossed else "within NORMAL band.")
        ),
        "dd_pct": float(dd_frac * 100),
        "peak_equity": float(state.peak_equity),
        "today_equity": float(state.mark_equity),
        "threshold_crossed": crossed,
    }


# === Q7: FY-to-date tax reserve (deployable equity) =======================

def _q7_tax_reserve(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    """FY-to-date STCG+LTCG reserve. The reserve is the amount of equity
    we should NOT count as deployable, since it's owed to the tax authority
    at FY end. Surfaces a single line: deployable = equity − reserve.

    Status semantics:
      ok    — reserve <  5% of equity (small)
      warn  — reserve in [5%, 15%) — material but not large
      flag  — reserve ≥ 15% (large; deployable is meaningfully constrained)
    """
    reserve = compute_fy_tax_reserve(conn, mode=mode, as_of=d)

    try:
        state = load_state(conn, mode, d)
        equity = float(state.mark_equity)
    except Exception:
        equity = 0.0

    reserve_inr = float(reserve["total_reserve_inr"])
    deployable = max(0.0, equity - reserve_inr)
    reserve_pct = (reserve_inr / equity * 100) if equity > 0 else 0.0

    if reserve_pct >= 15.0:
        status = "flag"
    elif reserve_pct >= 5.0:
        status = "warn"
    else:
        status = "ok"

    if reserve["n_trades"] == 0:
        detail = (
            f"{reserve['fy_label']}: no realised trades yet; tax reserve ₹0."
        )
    else:
        detail = (
            f"{reserve['fy_label']} tax reserve ₹{reserve_inr:,.0f} "
            f"({reserve_pct:.1f}% of equity); deployable ₹{deployable:,.0f}."
        )

    return {
        "status": status,
        "detail": detail,
        "fy_label": reserve["fy_label"],
        "total_reserve_inr": reserve_inr,
        "stcg_reserve_inr": float(reserve["stcg_reserve_inr"]),
        "ltcg_reserve_inr": float(reserve["ltcg_reserve_inr"]),
        "equity_inr": equity,
        "deployable_inr": deployable,
        "reserve_pct": reserve_pct,
        "n_trades": int(reserve["n_trades"]),
    }


# === Q6: corporate actions affecting our book =============================

def _q6_corporate_actions(
    conn: duckdb.DuckDBPyConnection, d: date, mode: str
) -> dict[str, Any]:
    """Any corporate actions on `d` that touched a name we hold or recently
    traded. Informational — surfaces dividends, splits, bonuses, etc. so
    they're not mistaken for unexplained PnL or position drift.
    """
    from data.corporate_actions import (
        format_action_summary,
        get_actions_for_tickers_on_date,
        load_corporate_actions,
    )

    actions = load_corporate_actions()
    if not actions:
        return {
            "status": "ok",
            "detail": "No corporate-action ledger yet.",
            "events": [],
        }

    # Names that could be affected: anything held today + anything traded
    # in the past 60 days (dividends often go ex- shortly after a sale).
    tickers_row = conn.execute(
        """
        SELECT ticker FROM broker_positions
        WHERE mode = ? AND snapshot_date = ?
        UNION
        SELECT ticker FROM realized_trades
        WHERE mode = ? AND sell_date >= ? AND sell_date <= ?
        """,
        [mode, d, mode, d - timedelta(days=60), d],
    ).fetchall()
    relevant_tickers = {r[0] for r in tickers_row}

    hits = get_actions_for_tickers_on_date(actions, relevant_tickers, d)
    if not hits:
        return {
            "status": "ok",
            "detail": "No corporate actions today on held/recent names.",
            "events": [],
        }

    events = [
        {
            "ticker": ca.ticker,
            "type": ca.type,
            "value": ca.value,
            "new_symbol": ca.new_symbol,
            "summary": format_action_summary(ca),
        }
        for ca in hits
    ]
    return {
        "status": "warn",
        "detail": (
            f"{len(hits)} CA event(s) today: "
            + "; ".join(e["summary"] for e in events)
        ),
        "events": events,
    }
