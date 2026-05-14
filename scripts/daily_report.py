"""Daily markdown report — what the trading pipeline did today.

Written to `state/reports/<as_of_date>.md`. Generated at the end of each
`scripts/run_live.py` invocation. The format is deliberately
human-grep-friendly so the operator can `cat state/reports/2026-05-13.md`
next morning and have the full day's story in one screen.

Sections (in order):
  1. Header — date, mode, status
  2. Pre-flight — halt state, premarket scan summary
  3. Targets — what the strategy wanted
  4. Orders & fills — what actually got placed
  5. Positions — current EOD snapshot
  6. P&L — today vs prior, account vs NIFTY benchmark (Phase 2 polish)
  7. Discrepancies — anything the system flagged for human review
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.executors.protocol import ExecutionSummary
from storage import portfolio_db

REPORTS_DIR = Path("state/reports")


def _fmt_inr(amount: float, *, signed: bool = False) -> str:
    """Format an INR amount with ₹ symbol, comma-grouping, and 2 decimals.

    For magnitudes >= 1 lakh we append the lakh/crore shorthand in
    parens — keeps the operator's mental model aligned with how Indian
    brokerage statements quote balances. Lakh = 10^5, crore = 10^7.
    """
    sign = "+" if (signed and amount > 0) else ("-" if amount < 0 else "")
    a = abs(amount)
    head = f"{sign}₹{a:,.2f}"
    if a >= 1e7:
        return f"{head} ({sign}{a / 1e7:.2f} cr)"
    if a >= 1e5:
        return f"{head} ({sign}{a / 1e5:.2f} L)"
    return head


def _fmt_inr_px(price: float) -> str:
    """Format a per-share price in INR (no lakh/crore shorthand)."""
    return f"₹{price:,.4f}"


@dataclass(frozen=True)
class ReportContext:
    """Everything the report needs that isn't on ExecutionSummary."""

    premarket_payload: dict | None = None
    benchmark_ticker: str = "NIFTY"


def generate(
    summary: ExecutionSummary,
    *,
    context: ReportContext | None = None,
    db_path: Path | None = None,
    reports_dir: Path | None = None,
) -> Path:
    """Render the daily report markdown. Returns the path written."""
    context = context or ReportContext()
    db_path = db_path or portfolio_db.DEFAULT_DB_PATH
    reports_dir = reports_dir or REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"{summary.as_of_date.isoformat()}.md"

    sections = [
        _header(summary),
        _preflight(summary, context),
        _targets(summary, db_path),
        _orders_fills(summary, db_path),
        _positions(summary, db_path),
        _pnl(summary, db_path, context),
        _discrepancies(summary, db_path),
        _footer(summary),
    ]
    out_path.write_text("\n\n".join(s for s in sections if s).rstrip() + "\n")
    return out_path


# ---- section builders ----

def _header(s: ExecutionSummary) -> str:
    status = "SKIPPED" if s.skipped else ("HALTED" if s.halt_set else "OK")
    lines = [
        f"# {s.as_of_date.isoformat()} — {s.mode} run [{status}]",
        "",
        f"- **As-of date (signal):** `{s.as_of_date.isoformat()}`",
        f"- **Fill date:** `{s.fill_date.isoformat() if s.fill_date else '—'}`",
        f"- **Mode:** `{s.mode}`",
        f"- **Status:** {status}",
    ]
    if s.skipped:
        lines.append(f"- **Skip reason:** {s.skipped_reason or '(unspecified)'}")
    if s.halt_set:
        lines.append(f"- **Halt reason:** {s.halt_reason or '(unspecified)'}")
    return "\n".join(lines)


def _preflight(s: ExecutionSummary, ctx: ReportContext) -> str:
    lines = ["## Pre-flight"]
    pm = ctx.premarket_payload
    if pm is None:
        lines.append("- Premarket scan: **not run** (or scan file missing)")
    else:
        vix = pm.get("vix", {})
        vix_level = vix.get("level")
        vix_flag = vix.get("flag")
        n_tickers = len(pm.get("tickers", {}) or {})
        n_gapped = sum(
            1 for v in (pm.get("tickers") or {}).values()
            if isinstance(v, dict) and v.get("gap_flag")
        )
        halt_recs = pm.get("halt_recommendations") or []
        lines.append(
            f"- Premarket scan: {n_tickers} held tickers scanned, "
            f"{n_gapped} gap-flagged, "
            f"VIX={vix_level!s} (flag={vix_flag})"
        )
        if halt_recs:
            lines.append(f"- Halt recommendations: {len(halt_recs)}")
            for rec in halt_recs:
                lines.append(f"  - {rec}")
    if s.notes:
        lines.append("- Run-time notes:")
        for n in s.notes:
            lines.append(f"  - {n}")
    return "\n".join(lines)


def _targets(s: ExecutionSummary, db_path: Path) -> str:
    with portfolio_db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ticker, target_fraction, source FROM desired_targets "
            "WHERE as_of_date = ? AND mode = ? "
            "ORDER BY target_fraction DESC",
            [s.as_of_date, s.mode],
        ).fetchall()
    if not rows:
        return "## Targets\n\n_(no targets recorded for this day)_"
    lines = ["## Targets", "", "| Ticker | Target % | Source |", "|---|---:|---|"]
    for ticker, frac, source in rows:
        lines.append(f"| {ticker} | {frac:+.2%} | {source or '—'} |")
    return "\n".join(lines)


def _orders_fills(s: ExecutionSummary, db_path: Path) -> str:
    lines = ["## Orders & fills"]
    lines.append(
        f"- Orders submitted: **{s.n_orders}**   "
        f"Fills observed: **{s.n_fills}**"
    )
    lines.append(
        f"- Gross buys: **{_fmt_inr(s.gross_buy_usd)}**   "
        f"Gross sells: **{_fmt_inr(s.gross_sell_usd)}**   "
        f"Commission: **{_fmt_inr(s.total_commission_usd)}**"
    )
    if s.n_orders == 0:
        return "\n".join(lines)
    with portfolio_db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT so.ticker, so.side, so.quantity, so.limit_price, so.status, "
            "       af.fill_price, af.filled_at "
            "FROM submitted_orders so "
            "LEFT JOIN actual_fills af ON af.order_id = so.order_id "
            "WHERE so.as_of_date = ? AND so.mode = ? "
            "ORDER BY so.side, so.ticker",
            [s.as_of_date, s.mode],
        ).fetchall()
    lines.append("")
    lines.append("| Ticker | Side | Qty | Lim Px | Fill Px | Status | Filled At |")
    lines.append("|---|---|---:|---:|---:|---|---|")
    for ticker, side, qty, limit_price, status, fill_price, filled_at in rows:
        lp = _fmt_inr_px(limit_price) if limit_price is not None else "—"
        fp = _fmt_inr_px(fill_price) if fill_price is not None else "—"
        fa = filled_at.isoformat(timespec="seconds") if filled_at else "—"
        lines.append(
            f"| {ticker} | {side} | {qty:.4f} | {lp} | {fp} | {status} | {fa} |"
        )
    return "\n".join(lines)


def _positions(s: ExecutionSummary, db_path: Path) -> str:
    with portfolio_db.connect(db_path) as conn:
        snap_date = conn.execute(
            "SELECT MAX(snapshot_date) FROM broker_positions WHERE mode = ?",
            [s.mode],
        ).fetchone()[0]
        if snap_date is None:
            return "## Positions\n\n_(no snapshot in ledger yet)_"
        rows = conn.execute(
            "SELECT ticker, quantity, mark_price, mark_value "
            "FROM broker_positions WHERE snapshot_date = ? AND mode = ? "
            "  AND quantity != 0 "
            "ORDER BY mark_value DESC NULLS LAST",
            [snap_date, s.mode],
        ).fetchall()
        cash = portfolio_db.get_cash_balance(conn, mode=s.mode, as_of=snap_date)
    lines = [f"## Positions (snapshot {snap_date.isoformat()})"]
    if not rows:
        lines.append("- _all cash, no open positions_")
    else:
        lines.append("")
        lines.append("| Ticker | Qty | Mark Px | Mark Value |")
        lines.append("|---|---:|---:|---:|")
        total_mv = 0.0
        for ticker, qty, mark, mv in rows:
            total_mv += mv or 0.0
            lines.append(
                f"| {ticker} | {qty:.4f} | {_fmt_inr_px(mark)} | {_fmt_inr(mv or 0.0)} |"
            )
        lines.append(f"| **TOTAL** | | | **{_fmt_inr(total_mv)}** |")
    lines.append("")
    lines.append(f"- **Cash:** {_fmt_inr(cash)}")
    return "\n".join(lines)


def _pnl(s: ExecutionSummary, db_path: Path, ctx: ReportContext) -> str:
    """Today's daily-P&L line + benchmark comparison.

    Benchmark return is left as a placeholder for now — wiring a proper
    NIFTY daily-return read against prices.duckdb is a Phase 5.5 polish.
    """
    with portfolio_db.connect(db_path) as conn:
        state = portfolio_db.load_state(conn, mode=s.mode, as_of=s.as_of_date)
    lines = ["## P&L"]
    lines.append(
        f"- **Today's mark-equity:** {_fmt_inr(state.mark_equity)}   "
        f"**Peak:** {_fmt_inr(state.peak_equity)}   "
        f"**Today P&L:** {_fmt_inr(state.today_pnl_usd, signed=True)}"
    )
    if state.peak_equity > 0:
        dd = (state.mark_equity - state.peak_equity) / state.peak_equity
        lines.append(f"- **Drawdown from peak:** {dd:+.2%}")
    lines.append(
        f"- **Benchmark ({ctx.benchmark_ticker}) comparison:** "
        "_(deferred to Phase 5.5)_"
    )
    return "\n".join(lines)


def _discrepancies(s: ExecutionSummary, db_path: Path) -> str:
    if s.n_discrepancies == 0:
        return "## Discrepancies\n\n_(none)_"
    with portfolio_db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT kind, ticker, resolution, notes "
            "FROM discrepancies WHERE as_of_date = ? AND mode = ? "
            "ORDER BY detected_at",
            [s.as_of_date, s.mode],
        ).fetchall()
    lines = [f"## Discrepancies ({s.n_discrepancies})", "",
             "| Kind | Ticker | Resolution | Notes |", "|---|---|---|---|"]
    for kind, ticker, resolution, notes in rows:
        notes_clean = (notes or "").replace("|", "\\|")[:200]
        lines.append(
            f"| {kind} | {ticker or '—'} | {resolution or '—'} | {notes_clean} |"
        )
    return "\n".join(lines)


def _footer(s: ExecutionSummary) -> str:
    parts = [
        "---",
        "_Generated by `scripts/daily_report.py` "
        f"(mode={s.mode}, gross turnover {_fmt_inr(s.gross_turnover_usd)})._",
    ]
    return "\n".join(parts)


# ---- CLI for ad-hoc re-rendering ----

def main(argv: list[str] | None = None) -> int:
    """Re-render a report for an existing ledger row. Used for backfills."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", type=date.fromisoformat, required=True)
    p.add_argument("--mode", default="dhan-paper")
    args = p.parse_args(argv)

    with portfolio_db.connect() as conn:
        n_orders, gross_buy, gross_sell = conn.execute(
            "SELECT COUNT(*), "
            "  COALESCE(SUM(CASE WHEN side='buy' THEN quantity * limit_price ELSE 0 END), 0), "
            "  COALESCE(SUM(CASE WHEN side='sell' THEN quantity * limit_price ELSE 0 END), 0) "
            "FROM submitted_orders WHERE as_of_date = ? AND mode = ?",
            [args.date, args.mode],
        ).fetchone()
        n_fills, total_commission = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(commission), 0) FROM actual_fills af "
            "JOIN submitted_orders so ON af.order_id = so.order_id "
            "WHERE so.as_of_date = ? AND so.mode = ?",
            [args.date, args.mode],
        ).fetchone()
        (n_discrepancies,) = conn.execute(
            "SELECT COUNT(*) FROM discrepancies WHERE as_of_date = ? AND mode = ?",
            [args.date, args.mode],
        ).fetchone()
    summary = ExecutionSummary(
        mode=args.mode,
        as_of_date=args.date,
        fill_date=None,
        n_orders=int(n_orders),
        n_fills=int(n_fills),
        gross_buy_usd=float(gross_buy),
        gross_sell_usd=float(gross_sell),
        total_commission_usd=float(total_commission),
        n_discrepancies=int(n_discrepancies),
    )
    path = generate(summary)
    print(f"[daily_report] wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
