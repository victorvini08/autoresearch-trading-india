"""Live Health & Confidence — process-fidelity monitor for the forward run.

The single question this answers: **is the live book faithfully doing what the
validated backtest said it would do?** — NOT "will returns be good?" The latter
is unanswerable over weeks for this strategy (its edge is drawdown protection
concentrated in rare market stress, so short-horizon P&L is almost pure noise;
judging it on a month would be reading tea leaves). So instead of pretending to
forecast returns, we measure whether the *machine* is behaving as designed:

  * Fidelity (high signal, available from day one):
      - selection match     — are we holding the names the logic selected?
      - deployment           — is gross deployed what the strategy intended (~46%)?
      - cash-floor integrity — is LIQUIDCASE sitting in its target band?
      - cost realization     — is realized slippage within the cost model?
  * Behaviour (medium signal, accrues over weeks):
      - return + drawdown vs Nifty over the live window (the edge is *smaller*
        drawdowns, so we measure drawdown protection directly).

The output is advisory only — it renders a panel on the dashboard and changes
no behaviour (no halts, no sizing). The deliberate design choice (user, 2026-06):
it *advises*, nothing else. The capital-scaling decision becomes a green/red
checklist on process fidelity, NOT on whether the month was up.

Two heavier layers are intentionally deferred (see ``pending`` in the output):
the parallel-backtest tracking-error curve (trivially ~0 in mock; meaningful once
live, where it surfaces real execution divergence) and the slow multi-quarter
alpha-decay tripwire. Both need real live data / many months before they say
anything; building them on 2 weeks of mock would only manufacture false signal.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from storage import portfolio_db
from storage.portfolio_db import DEFAULT_DB_PATH, connect

REPO = Path(__file__).resolve().parent.parent
MACRO_DB = REPO / "storage" / "macro.duckdb"

# Thresholds. Mirrored from the existing layers so the panel agrees with them:
#   - slippage flags mirror reconciliation Q2 (50bps avg / 200bps max)
#   - floor band mirrors scripts/cash_floor.py (banded ±5%)
# Deployment is a WIDE band on purpose: the downside-vol-target moves gross
# around (~0.46 typical on the backtest), so we only flag gross that lands far
# from what the strategy *itself* intended this rebalance — not a fixed number.
_SLIPPAGE_AVG_FLAG_BPS = 50.0
_SLIPPAGE_MAX_FLAG_BPS = 200.0
_FLOOR_BAND = 0.05
_DEPLOY_OK = 0.05      # |actual − intended| gross within 5pp → ok
_DEPLOY_WARN = 0.12    # within 12pp → warn, beyond → flag

_RANK = {"ok": 0, "warn": 1, "flag": 2, "na": 0}


def _nifty_window(start: date, end: date) -> tuple[float, float]:
    """(total_return_pct, maxDD_pct) for Nifty 50 over [start, end] from the
    macro store — the SAME price index and dates the strategy is compared
    against (price index, not total-return; TR would be ~+1.2%/yr higher).

    Mirrors scripts.replay_paper._nifty_return so the dashboard and the replay
    harness quote the benchmark identically. Returns (nan, nan) when the macro
    store is missing or the window is too short to span two points.
    """
    import duckdb

    if not MACRO_DB.exists():
        return float("nan"), float("nan")
    c = duckdb.connect(str(MACRO_DB), read_only=True)
    try:
        rows = c.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_nifty_50' "
            "AND dt BETWEEN ? AND ? ORDER BY dt",
            [start, end],
        ).fetchall()
    except Exception:  # noqa: BLE001 — macro schema drift must not break the panel
        return float("nan"), float("nan")
    finally:
        c.close()
    v = [float(r[0]) for r in rows if r[0] is not None]
    if len(v) < 2:
        return float("nan"), float("nan")
    tot = (v[-1] / v[0] - 1.0) * 100.0
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)
    return tot, mdd * 100.0


def _dd_protection_pp(strat_mdd_pct: float, nifty_mdd_pct: float) -> float:
    """Drawdown protection in percentage points: POSITIVE = our worst dip was
    SHALLOWER than Nifty's (the strategy's actual edge). Both inputs are
    negative percentages (e.g. strat −0.53, nifty −1.42), so protection =
    |nifty| − |ours| = strat_mdd − nifty_mdd  (−0.53 − (−1.42) = +0.89)."""
    if nifty_mdd_pct != nifty_mdd_pct:  # NaN guard
        return float("nan")
    return strat_mdd_pct - nifty_mdd_pct


def _max_drawdown_pct(equity: list[float]) -> float:
    peak, mdd = equity[0], 0.0
    for x in equity:
        peak = max(peak, x)
        if peak > 0:
            mdd = min(mdd, x / peak - 1.0)
    return mdd * 100.0


def compute_live_health(
    mode: str = "dhan-paper",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Build the Live Health payload for ``mode``.

    Returns ``None`` when the bucket has no equity snapshots yet (nothing to
    judge). Never raises on missing optional inputs (macro store, targets,
    fills) — each contributing check degrades to status ``na`` so the panel
    still renders. The caller (dashboard) wraps this in try/except as a final
    backstop.
    """
    conn = connect(db_path)
    try:
        curve = portfolio_db.get_equity_curve(conn, mode=mode)
        if curve.empty:
            return None

        snap_dates = [d for d in curve["snapshot_date"]]
        equity = [float(x) for x in curve["mark_equity"]]
        start, end = snap_dates[0], snap_dates[-1]
        n_days = (end - start).days
        n_weeks = max(1, round(n_days / 7)) if n_days else 1

        # --- most recent strategy intent (desired_targets) -------------------
        tgt_date = conn.execute(
            "SELECT MAX(as_of_date) FROM desired_targets WHERE mode = ?", [mode]
        ).fetchone()[0]
        target_rows = (
            conn.execute(
                "SELECT ticker, target_fraction, source FROM desired_targets "
                "WHERE as_of_date = ? AND mode = ?",
                [tgt_date, mode],
            ).fetchall()
            if tgt_date
            else []
        )
        floor_tickers = {t for t, _f, s in target_rows if s == "cash_floor"} or {
            "LIQUIDCASE"
        }
        # A strategy target of 0.0 means "do NOT hold" (the strategy writes an
        # explicit zero for a name it just dropped, which drives the sell). Such
        # names are intended-FLAT, so they must NOT count as "intended to hold"
        # — otherwise every rebalance that drops a name false-flags selection.
        intended_strategy = {
            t: float(f)
            for t, f, s in target_rows
            if s != "cash_floor" and float(f) > 1e-9
        }
        intended_floor = sum(
            float(f) for _t, f, s in target_rows if s == "cash_floor"
        )
        intended_deploy = sum(intended_strategy.values())

        # --- what the broker actually holds (latest snapshot) ----------------
        snap = conn.execute(
            "SELECT MAX(snapshot_date) FROM broker_positions WHERE mode = ?",
            [mode],
        ).fetchone()[0]
        positions = (
            portfolio_db.get_positions_as_of(conn, snap, mode) if snap else {}
        )
        cash = (
            portfolio_db.get_cash_balance(conn, mode=mode, as_of=snap)
            if snap
            else 0.0
        )
        total_mark = sum((p.mark_value or 0.0) for p in positions.values())
        total_equity = float(cash or 0.0) + float(total_mark)
        floor_value = sum(
            (p.mark_value or 0.0)
            for t, p in positions.items()
            if t in floor_tickers
        )
        deployed_value = sum(
            (p.mark_value or 0.0)
            for t, p in positions.items()
            if t not in floor_tickers
        )
        held_strategy = {
            t
            for t, p in positions.items()
            if t not in floor_tickers and (p.quantity or 0.0) != 0.0
        }
        deployed_pct = deployed_value / total_equity if total_equity else 0.0
        floor_pct = floor_value / total_equity if total_equity else 0.0

        # latest fill date — slippage realization is judged on the most recent
        # day that actually traded (between rebalances nothing fills).
        fill_date = conn.execute(
            "SELECT MAX(CAST(filled_at AS DATE)) FROM actual_fills WHERE mode = ?",
            [mode],
        ).fetchone()[0]
    finally:
        conn.close()

    # ---- fidelity checks ----------------------------------------------------
    fidelity: list[dict[str, Any]] = []

    # 1. selection match
    if not intended_strategy:
        fidelity.append({
            "key": "selection", "label": "Holding the names the strategy selected?",
            "status": "na", "detail": "No strategy targets recorded yet.",
        })
    else:
        wanted = set(intended_strategy)
        missing = sorted(wanted - held_strategy)   # intended but not held
        extra = sorted(held_strategy - wanted)     # held but not intended
        n_off = len(missing) + len(extra)
        sel_status = "ok" if n_off == 0 else ("warn" if n_off == 1 else "flag")
        if n_off == 0:
            detail = (
                f"All {len(wanted)} selected names held, none extra "
                f"({', '.join(sorted(held_strategy)) or '—'})."
            )
        else:
            bits = []
            if missing:
                bits.append("intended-not-held: " + ", ".join(missing))
            if extra:
                bits.append("held-not-intended: " + ", ".join(extra))
            detail = "; ".join(bits)
        fidelity.append({
            "key": "selection",
            "label": "Holding the names the strategy selected?",
            "status": sel_status, "detail": detail,
        })

    # 2. deployment vs intended gross
    if not target_rows:
        fidelity.append({
            "key": "deployment", "label": "Deployed gross matches strategy intent?",
            "status": "na", "detail": "No targets recorded yet.",
        })
    else:
        diff = abs(deployed_pct - intended_deploy)
        dep_status = (
            "ok" if diff <= _DEPLOY_OK else ("warn" if diff <= _DEPLOY_WARN else "flag")
        )
        fidelity.append({
            "key": "deployment",
            "label": "Deployed gross matches strategy intent?",
            "status": dep_status,
            "detail": (
                f"Deployed {deployed_pct * 100:.1f}% vs intended "
                f"{intended_deploy * 100:.1f}% (Δ {diff * 100:.1f}pp). "
                f"Rest is the cash floor."
            ),
        })

    # 3. cash-floor integrity
    if not target_rows or intended_floor <= 0:
        fidelity.append({
            "key": "floor", "label": "Cash floor (LIQUIDCASE) inside its band?",
            "status": "na", "detail": "No cash-floor target recorded yet.",
        })
    else:
        fdiff = abs(floor_pct - intended_floor)
        floor_status = (
            "ok" if fdiff <= _FLOOR_BAND
            else ("warn" if fdiff <= 2 * _FLOOR_BAND else "flag")
        )
        fidelity.append({
            "key": "floor",
            "label": "Cash floor (LIQUIDCASE) inside its band?",
            "status": floor_status,
            "detail": (
                f"Floor {floor_pct * 100:.1f}% vs target {intended_floor * 100:.1f}% "
                f"(±{_FLOOR_BAND * 100:.0f}pp band)."
            ),
        })

    # 4. cost realization (reuse reconciliation Q2 on the latest fill day)
    cost_row = _cost_realization(fill_date, mode, db_path)
    fidelity.append(cost_row)

    # ---- behaviour (return + drawdown vs Nifty over the window) -------------
    base = equity[0] if equity[0] else float("nan")
    strat_ret = (equity[-1] / base - 1.0) * 100.0 if base == base and base else float("nan")
    strat_mdd = _max_drawdown_pct(equity)
    nifty_ret, nifty_mdd = _nifty_window(start, end)
    behavior = {
        "strategy_return_pct": strat_ret,
        "nifty_return_pct": nifty_ret,
        "excess_pp": (strat_ret - nifty_ret) if nifty_ret == nifty_ret else float("nan"),
        "strategy_maxdd_pct": strat_mdd,
        "nifty_maxdd_pct": nifty_mdd,
        # drawdown protection = how much shallower our worst dip was (positive = better)
        "dd_protection_pp": _dd_protection_pp(strat_mdd, nifty_mdd),
        "envelope_status": "na",
        "envelope_detail": (
            "Return-vs-backtest envelope and parallel-backtest tracking-error "
            "activate once the live book has accrued enough history "
            f"(currently ~{n_weeks}w). Over weeks, P&L is noise by design."
        ),
    }

    # ---- verdict (advisory) -------------------------------------------------
    worst = max((f["status"] for f in fidelity), key=lambda s: _RANK[s])
    if worst == "flag":
        v_status, headline = "RED", (
            "A fidelity check FAILED — the live book is not doing what the "
            "validated strategy intended. Investigate before adding capital."
        )
    elif worst == "warn":
        v_status, headline = "AMBER", (
            "Mostly faithful, with a minor deviation flagged below. Worth a "
            "look, not an alarm."
        )
    else:
        v_status, headline = "GREEN", (
            "The live book is faithfully tracking the validated strategy "
            "(right names, right gross, floor in band, costs in model)."
        )
    caveat = (
        f"This is a FIDELITY verdict, not a returns forecast. Over ~{n_weeks} "
        "week(s) realized P&L is dominated by noise — this strategy's edge is "
        "drawdown protection that only shows over full cycles (years). Judge "
        "the process now; judge returns much later."
    )

    # ---- capital-scaling checklist (advisory) -------------------------------
    checklist = [
        {
            "label": "Implementation faithful (names + gross + floor)",
            "status": worst if worst != "na" else "na",
            "detail": "All fidelity rows above green." if worst == "ok"
            else "See flagged fidelity row(s).",
        },
        {
            "label": "Realized costs within the model",
            "status": cost_row["status"],
            "detail": cost_row["detail"],
        },
        {
            "label": "Capital-scale robustness already gate-validated",
            "status": "ok",
            "detail": "Atomic gates passed at ₹50k AND ₹5L (pre-deployment).",
        },
        {
            "label": "Decide on PROCESS, not the month's P&L",
            "status": "na",
            "detail": "A green/red month is noise; scale when fidelity is green.",
        },
    ]

    return {
        "mode": mode,
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "n_days": n_days,
            "n_weeks": n_weeks,
            "n_snapshots": len(snap_dates),
        },
        "verdict": {"status": v_status, "headline": headline, "caveat": caveat},
        "fidelity": fidelity,
        "behavior": behavior,
        "capital_checklist": checklist,
        "pending": [
            "Parallel-backtest tracking error (live vs backtest on identical "
            "dates) — activates with live data.",
            "Slow multi-quarter alpha-decay tripwire → escalates to the LLM "
            "review (months out; never auto-acts).",
        ],
    }


def _cost_realization(
    fill_date: date | None, mode: str, db_path: Path | str
) -> dict[str, Any]:
    """Slippage-vs-model fidelity row, reusing reconciliation Q2 on the most
    recent fill day. Degrades to ``na`` when nothing has filled yet or the
    reconciliation module is unavailable."""
    if fill_date is None:
        return {
            "key": "cost", "label": "Realized slippage within the cost model?",
            "status": "na", "detail": "No fills yet to measure.",
        }
    try:
        from scripts.reconciliation import compute_reconciliation_for_date

        recon = compute_reconciliation_for_date(fill_date, mode=mode, db_path=db_path)
        q2 = recon.get("execution_matched_assumptions") or {}
        return {
            "key": "cost",
            "label": "Realized slippage within the cost model?",
            "status": q2.get("status", "na"),
            "detail": (q2.get("detail") or "no fill detail")
            + f"  (as of {fill_date.isoformat()})",
        }
    except Exception as e:  # noqa: BLE001 — never break the panel on recon drift
        return {
            "key": "cost", "label": "Realized slippage within the cost model?",
            "status": "na", "detail": f"reconciliation unavailable: {type(e).__name__}",
        }
