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
from datetime import date, datetime, time as dtime
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


def _isolate_state(sandbox: Path, initial_cash: float) -> Path:
    """Redirect EVERY mutable-state path to the sandbox so the real ledger,
    halt file, and safety state are never touched. Returns the sandbox
    portfolio-db path.

    `initial_cash` anchors the paper account's starting balance. It must be
    set on `_INITIAL_DEPOSIT_BY_MODE` (which get_cash_balance adds to the
    signed ledger sum) so the account boots with exactly this much cash —
    not the ₹100k module default. The DhanMock/DhanExecutor are also told
    the same number so the live-position seed cash matches."""
    sandbox.mkdir(parents=True, exist_ok=True)
    # Anchor the paper account's initial deposit to the requested capital so
    # get_cash_balance, the executor seed, and the mock broker all agree.
    portfolio_db._INITIAL_DEPOSIT_BY_MODE["dhan-paper"] = float(initial_cash)
    pf = sandbox / "portfolio.duckdb"
    if pf.exists():
        pf.unlink()  # always a fresh, clean account
    conn = portfolio_db.connect(pf)
    try:
        portfolio_db.init_schema(conn)  # empty ledger -> cash = initial_cash
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


def _restamp_ledger_to_sim_date(pf: Path, sim_date: date, real_today: date) -> None:
    """Re-stamp the cash-ledger rows the executor just wrote so their timestamp
    is the SIMULATED trading date, not the real wall-clock run time.

    The executor stamps cash_ledger.entry_at with datetime.now() (correct in
    production, where now ~ the trading day). Under historical replay that makes
    every entry land on the run date, so get_cash_balance(as_of=<past date>) —
    which filters CAST(entry_at AS DATE) <= as_of — excludes them and returns
    the UN-DEBITED initial cash. load_state then reports a phantom equity (cash
    never spent + position marks), inflating the peak and manufacturing a false
    drawdown that trips the max-DD halt (observed: a spurious −15.69% halt on a
    book that was actually ~−3%). Rows from prior days are already re-stamped to
    their own (past) dates, so matching on the real run date catches only the
    rows written by THIS execute_day call. (submitted_orders.as_of_date is
    already stamped with the simulated date by the executor, so it needs no fix.)
    """
    conn = portfolio_db.connect(pf)
    try:
        ts = datetime.combine(sim_date, dtime(15, 30))
        conn.execute(
            "UPDATE cash_ledger SET entry_at = ?, as_of_date = ? "
            "WHERE mode = 'dhan-paper' AND CAST(entry_at AS DATE) = ?",
            [ts, sim_date, real_today],
        )
    finally:
        conn.close()


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


def run_replay(start: date, end: date, sandbox: Path,
               initial_cash: float = 50_000.0) -> dict:
    pf = _isolate_state(sandbox, initial_cash)
    reports_dir = sandbox / "reports"

    # Imports AFTER isolation so any module-level path captures see the sandbox.
    from scripts.executors.dhan import DhanExecutor
    from scripts import daily_report

    days = _trading_days(start, end)
    if not days:
        print(f"No trading days in {start}..{end}.")
        return {}
    print(f"Replaying {len(days)} trading days {days[0]} .. {days[-1]} "
          f"into sandbox {sandbox}/  @ Rs{initial_cash:,.0f}  "
          f"(real ledger untouched)\n")
    print(f"{'date':12} {'dow':3} {'orders':>6} {'gross_buy':>11} "
          f"{'gross_sell':>11} {'equity':>11}  note")

    rebalance_days = 0
    for D in days:
        ex = DhanExecutor(mode="dhan-paper", portfolio_db=pf, prices_db=PRICES_DB,
                          initial_cash_inr=initial_cash)
        summary = ex.execute_day(D, skips=set())
        # Faithful clock: re-stamp the cash-ledger rows just written to the
        # SIMULATED date so the per-date equity/peak/drawdown (and thus the
        # max-DD halt) compute correctly under replay. Captured fresh each
        # iteration so a midnight rollover during a long run is harmless.
        _restamp_ledger_to_sim_date(pf, D, date.today())
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
            "trading_days": len(days), "active_days": rebalance_days,
            "initial_cash": initial_cash}


def _nifty_return(start: date, end: date) -> tuple[float, float]:
    """(total_return_pct, maxDD_pct) of Nifty 50 over [start, end] from the
    macro store — the SAME index/dates the equity result is compared against,
    so the comparison is apples-to-apples (price index; TR would be ~+1.2%/yr
    higher)."""
    macro = REPO / "storage" / "macro.duckdb"
    if not macro.exists():
        return float("nan"), float("nan")
    c = duckdb.connect(str(macro), read_only=True)
    try:
        rows = c.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_nifty_50' "
            "AND dt BETWEEN ? AND ? ORDER BY dt", [start, end],
        ).fetchall()
    finally:
        c.close()
    v = [float(r[0]) for r in rows if r[0] is not None]
    if len(v) < 2:
        return float("nan"), float("nan")
    tot = (v[-1] / v[0] - 1.0) * 100.0
    peak = v[0]
    mdd = 0.0
    for x in v:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)
    return tot, mdd * 100.0


def _pnl_breakdown(pf: Path, initial_cash: float) -> dict:
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
        "unrealized": float(mark) - float(cost),
        "cash": float(initial_cash) + float(ledger),
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
    p.add_argument("--initial-cash", type=float, default=50_000.0,
                   help="starting paper capital (default ₹50,000)")
    p.add_argument("--dashboard", action="store_true",
                   help="render the sandbox dashboard.html at the end")
    args = p.parse_args(argv)

    res = run_replay(args.start, args.end, args.sandbox, args.initial_cash)
    if not res:
        return 1
    _print_trade_log(res["pf"])
    cash0 = res["initial_cash"]
    p = _pnl_breakdown(res["pf"], cash0)
    equity = p["cash"] + p["mark"]
    ret = (equity - cash0) / cash0 * 100.0
    nifty_ret, nifty_dd = _nifty_return(res["days"][0], res["days"][-1])
    print(f"\n=== FINAL ({res['days'][-1]}) ===")
    print(f"  trading days replayed: {res['trading_days']}   days with orders: {res['active_days']}")
    print(f"  Realized P&L:    Rs {p['realized']:+,.2f}   "
          f"({p['n_round']} closed round-trips; est tax Rs{p['tax']:,.2f})")
    print(f"  Unrealized P&L:  Rs {p['unrealized']:+,.2f}   "
          f"(open holdings mark Rs{p['mark']:,.2f} vs cost Rs{p['cost']:,.2f})")
    print(f"  Commissions:     Rs {p['commissions']:,.2f}")
    print(f"  Net total P&L:   Rs {p['realized'] + p['unrealized'] - p['commissions']:+,.2f}")
    print(f"  Equity Rs{equity:,.2f} = cash Rs{p['cash']:,.2f} + holdings Rs{p['mark']:,.2f}   "
          f"return {ret:+.2f}%  (vs Rs{cash0:,.0f} start)")
    print(f"  Nifty 50 (same window): {nifty_ret:+.2f}%   maxDD {nifty_dd:.2f}%")
    print(f"  >>> STRATEGY {ret:+.2f}%  vs  NIFTY50 {nifty_ret:+.2f}%  "
          f"= {ret - nifty_ret:+.2f}pp")
    print(f"  per-day reports: {res['reports_dir']}/")

    if args.dashboard:
        from scripts import dashboard
        out = args.sandbox / "reports"
        dashboard.main(["--out-dir", str(out)])
        print(f"  dashboard: {out}/dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
