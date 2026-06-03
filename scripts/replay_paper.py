"""Faithful paper-trading replay over a historical window.

Drives the REAL live path — ``DhanExecutor.execute_day`` (live-position seed ->
``generate_signals`` -> bounded gross construction -> whole-share sizing ->
``DhanMock`` fills -> ledger writes) -> ``daily_report`` — once per trading day,
exactly as the daily cron would, but compressed and against a FULLY ISOLATED
sandbox so the real paper ledger is never touched.

This is NOT the backtest (``prepare.py``). The backtest uses the idealized
cerebro engine; this exercises the same integration path the cron runs, which is
where the integration bugs lived (sim-vs-live divergence, whole-share rounding,
carry-forward leverage). Use it to watch exactly what the strategy + executor do
over weeks and to catch issues before they happen on the real account.

Fidelity boundary (be honest):
  * Fills are DhanMock (bhav close +/- slippage), not the real Dhan API — so
    real-broker quirks (partial fills, rejects, API hiccups) are NOT modelled.
  * The premarket gap/VIX overlay is skipped: it needs live pre-open quotes that
    don't exist historically. It is a live-only advisory halt, not where the
    strategy/executor bugs live, so ``skips=set()`` here.
Everything else — selection, retention band, sector caps, vol-targeted gross,
whole-share hold-band, the FIFO ledger, P&L, reports, dashboard — is the
production code path on the current (fixed) ``main``.

Usage:
    uv run python -m scripts.replay_paper --start 2026-03-02 --end 2026-05-02
    uv run python -m scripts.replay_paper --start 2026-03-02 --end 2026-05-02 --sandbox state/replay
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import duckdb  # noqa: E402

from storage import portfolio_db  # noqa: E402

PRICES_DB = REPO / "storage" / "prices.duckdb"


def _trading_days(start: date, end: date) -> list[date]:
    """NSE trading days = days with a bhav bar. Survivorship-free, exactly the
    calendar the strategy uses; auto-skips weekends AND holidays."""
    c = duckdb.connect(str(PRICES_DB), read_only=True)
    try:
        rows = c.execute(
            "SELECT DISTINCT dt FROM daily_bars WHERE dt >= ? AND dt <= ? ORDER BY dt",
            [start, end],
        ).fetchall()
    finally:
        c.close()
    return [r[0] for r in rows]


def _isolate_state(sandbox: Path) -> Path:
    """Redirect EVERY mutable-state path to the sandbox so the real ledger,
    halt file, and safety state are never touched. Returns the sandbox
    portfolio-db path."""
    sandbox.mkdir(parents=True, exist_ok=True)
    pf = sandbox / "portfolio.duckdb"
    if pf.exists():
        pf.unlink()  # always a fresh, clean account
    conn = portfolio_db.connect(pf)
    try:
        portfolio_db.init_schema(conn)  # empty ledger -> cash = _INITIAL_DEPOSIT (Rs100k)
    finally:
        conn.close()

    # Portfolio DB + halt file (used by default in risk_check / dashboard / etc.)
    portfolio_db.DEFAULT_DB_PATH = pf
    portfolio_db.HALT_FILE_PATH = sandbox / "halt.json"

    # Safety state machine writes/reads these; isolate so the replay starts
    # NORMAL (multiplier 1.0) and evolves independently of the real account.
    import scripts.safety_evaluator as se
    for attr, fname in (
        ("SAFETY_STATE_PATH", "safety_state.json"),
        ("RISK_MULTIPLIER_PATH", "risk_multiplier.json"),
        ("HALT_PATH", "halt.json"),
        ("HALT_FILE_PATH", "halt.json"),
    ):
        if hasattr(se, attr):
            setattr(se, attr, sandbox / fname)
    return pf


def _equity_now(pf: Path, as_of: date) -> tuple[float, float, float]:
    """(cash, invested_mark, equity) from the sandbox at end of `as_of`."""
    cash = portfolio_db.get_cash_balance(portfolio_db.connect(pf), mode="dhan-paper")
    c = duckdb.connect(str(pf), read_only=True)
    try:
        row = c.execute(
            "WITH latest AS (SELECT MAX(snapshot_date) sd FROM broker_positions "
            "WHERE mode='dhan-paper' AND snapshot_date <= ?) "
            "SELECT COALESCE(SUM(mark_value),0) FROM broker_positions bp, latest l "
            "WHERE bp.snapshot_date = l.sd AND bp.mode='dhan-paper' AND bp.quantity != 0",
            [as_of],
        ).fetchone()
    finally:
        c.close()
    invested = float(row[0] or 0.0)
    return cash, invested, cash + invested


def run_replay(start: date, end: date, sandbox: Path) -> dict:
    pf = _isolate_state(sandbox)
    reports_dir = sandbox / "reports"

    # Imports AFTER isolation so any module-level path captures see the sandbox.
    from scripts.executors.dhan import DhanExecutor
    from scripts import daily_report

    days = _trading_days(start, end)
    if not days:
        print(f"No trading days in {start}..{end}.")
        return {}
    print(f"Replaying {len(days)} trading days {days[0]} .. {days[-1]} "
          f"into sandbox {sandbox}/  (real ledger untouched)\n")
    print(f"{'date':12} {'dow':3} {'orders':>6} {'gross_buy':>11} "
          f"{'gross_sell':>11} {'equity':>11}  note")

    rebalance_days = 0
    for D in days:
        ex = DhanExecutor(mode="dhan-paper", portfolio_db=pf, prices_db=PRICES_DB)
        summary = ex.execute_day(D, skips=set())
        try:
            daily_report.generate(summary, db_path=pf, reports_dir=reports_dir)
        except Exception as e:  # noqa: BLE001 — report is cosmetic; don't abort the run
            print(f"  (report failed for {D}: {type(e).__name__}: {e})")
        cash, invested, equity = _equity_now(pf, D)
        n = getattr(summary, "n_orders", None)
        if n is None:
            n = len(getattr(summary, "orders", []) or [])
        gb = float(getattr(summary, "gross_buy_inr", 0.0) or getattr(summary, "gross_buy_usd", 0.0) or 0.0)
        gs = float(getattr(summary, "gross_sell_inr", 0.0) or getattr(summary, "gross_sell_usd", 0.0) or 0.0)
        if n and n > 0:
            rebalance_days += 1
        note = ""
        if getattr(summary, "skipped", False):
            note = f"SKIPPED: {getattr(summary, 'skipped_reason', '')[:40]}"
        print(f"{D.isoformat():12} {D.strftime('%a'):3} {n:>6} "
              f"{gb:>11,.0f} {gs:>11,.0f} {equity:>11,.0f}  {note}")

    return {"pf": pf, "reports_dir": reports_dir, "days": days,
            "trading_days": len(days), "active_days": rebalance_days}


def _pnl_breakdown(pf: Path) -> dict:
    """Realized (closed round-trips) + unrealized (open positions marked) +
    commissions, reconciling to equity − Rs100,000."""
    c = duckdb.connect(str(pf), read_only=True)
    try:
        realized, tax, n_round = c.execute(
            "SELECT COALESCE(SUM(realized_pnl_usd),0), COALESCE(SUM(tax_paid_usd),0), "
            "COUNT(*) FROM realized_trades WHERE mode='dhan-paper'"
        ).fetchone()
        comm = c.execute(
            "SELECT COALESCE(SUM(commission),0) FROM actual_fills WHERE mode='dhan-paper'"
        ).fetchone()[0]
        cost = c.execute(
            "SELECT COALESCE(SUM(qty_open*buy_price),0) FROM position_lots "
            "WHERE mode='dhan-paper' AND qty_open>0"
        ).fetchone()[0]
        mark = c.execute(
            "WITH l AS (SELECT MAX(snapshot_date) sd FROM broker_positions) "
            "SELECT COALESCE(SUM(mark_value),0) FROM broker_positions bp,l "
            "WHERE bp.snapshot_date=l.sd AND quantity!=0"
        ).fetchone()[0]
        ledger = c.execute(
            "SELECT COALESCE(SUM(amount_usd),0) FROM cash_ledger WHERE mode='dhan-paper'"
        ).fetchone()[0]
    finally:
        c.close()
    return {
        "realized": float(realized), "tax": float(tax), "n_round": int(n_round),
        "commissions": float(comm), "cost": float(cost), "mark": float(mark),
        "unrealized": float(mark) - float(cost), "cash": 100_000.0 + float(ledger),
    }


def _print_trade_log(pf: Path) -> None:
    c = duckdb.connect(str(pf), read_only=True)
    try:
        rows = c.execute(
            "SELECT so.as_of_date, so.ticker, so.side, so.quantity, af.fill_price "
            "FROM submitted_orders so LEFT JOIN actual_fills af ON af.order_id=so.order_id "
            "WHERE so.mode='dhan-paper' ORDER BY so.as_of_date, so.side DESC, so.ticker"
        ).fetchall()
    finally:
        c.close()
    print("\n=== TRADE LOG (every order placed during the replay) ===")
    cur = None
    for d, t, side, q, fp in rows:
        if d != cur:
            print(f"\n--- {d} ({d.strftime('%A')}) ---")
            cur = d
        px = f"@ Rs{fp:,.2f}" if fp is not None else ""
        print(f"   {side.upper():4} {t:12} x{int(q):<4} {px}")
    if not rows:
        print("  (no orders placed in the window)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Faithful paper-trading replay over a historical window.")
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    p.add_argument("--sandbox", type=Path, default=REPO / "state" / "replay")
    p.add_argument("--dashboard", action="store_true",
                   help="render the sandbox dashboard.html at the end")
    args = p.parse_args(argv)

    res = run_replay(args.start, args.end, args.sandbox)
    if not res:
        return 1
    _print_trade_log(res["pf"])
    p = _pnl_breakdown(res["pf"])
    equity = p["cash"] + p["mark"]
    ret = (equity - 100_000.0) / 100_000.0 * 100.0
    print(f"\n=== FINAL ({res['days'][-1]}) ===")
    print(f"  trading days replayed: {res['trading_days']}   days with orders: {res['active_days']}")
    print(f"  Realized P&L:    Rs {p['realized']:+,.2f}   "
          f"({p['n_round']} closed round-trips; est tax Rs{p['tax']:,.2f})")
    print(f"  Unrealized P&L:  Rs {p['unrealized']:+,.2f}   "
          f"(open holdings mark Rs{p['mark']:,.2f} vs cost Rs{p['cost']:,.2f})")
    print(f"  Commissions:     Rs {p['commissions']:,.2f}")
    print(f"  Net total P&L:   Rs {p['realized'] + p['unrealized'] - p['commissions']:+,.2f}")
    print(f"  Equity Rs{equity:,.2f} = cash Rs{p['cash']:,.2f} + holdings Rs{p['mark']:,.2f}   "
          f"return {ret:+.2f}%  (vs Rs100,000 start)")
    print(f"  per-day reports: {res['reports_dir']}/")

    if args.dashboard:
        from scripts import dashboard
        out = args.sandbox / "reports"
        dashboard.main(["--out-dir", str(out)])
        print(f"  dashboard: {out}/dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
