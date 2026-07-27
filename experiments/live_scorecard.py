"""Monthly live-strategy scorecard — the honest "is it working?" answer.

Run on the VM (read-only DB access) each monthly-review day, alongside the
LLM review. Reports the pre-registered metrics only:

  1. Time-weighted return (TWR) since go-live vs NIFTY (NIFTYBEES) — TWR so
     deposits/withdrawals don't masquerade as performance.
  2. Max drawdown of the TWR index vs NIFTY's over the same window.
  3. Cost drag: modeled commissions + known one-time charges, annualized,
     vs the ~2.3%/yr replay-modeled DP/charge drag.
  4. The replay envelope for context: continuous 2019-2026 ~+13.4%/yr at
     -17.9% maxDD (vs NIFTY +11.1%/-38.4%); known soft spot = crash-recovery
     V-bounces (2020-Q2 replay: -24.9pp vs index).

Usage:  uv run python -m experiments.live_scorecard [--mode dhan-live]
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb

PORTFOLIO_DB = Path("storage/portfolio.duckdb")
PRICES_DB = Path("storage/prices.duckdb")
BENCH = "NIFTYBEES"

# External cash flows that are NOT performance. kind='deposit' rows are always
# flows. The quarterly running-account settlement sweep (broker -> bank and
# back) lands in kind='reconcile' and must be flow-classified by hand — add
# each occurrence here. Any OTHER reconcile row with |amount| >= 500 triggers
# a loud warning to classify it.
KNOWN_FLOW_RECONCILES = {
    (date(2026, 7, 4), -986.96),   # Q1 FY27 settlement sweep out (to bank)
    (date(2026, 7, 7), 987.00),    # user re-deposited the sweep
}
FLOW_WARN_THRESHOLD = 500.0


def build(mode: str) -> str:
    pc = duckdb.connect(str(PORTFOLIO_DB), read_only=True)
    pr = duckdb.connect(str(PRICES_DB), read_only=True)

    snaps = [r[0] for r in pc.execute(
        "SELECT DISTINCT snapshot_date FROM broker_positions WHERE mode = ? "
        "ORDER BY 1", [mode]).fetchall()]
    if not snaps:
        return "no live snapshots yet"

    # equity + net external flow per snapshot date
    eq, flows = {}, {}
    for d in snaps:
        mark = pc.execute(
            "SELECT COALESCE(SUM(mark_value),0) FROM broker_positions "
            "WHERE mode = ? AND snapshot_date = ?", [mode, d]).fetchone()[0]
        cash = pc.execute(
            "SELECT COALESCE(SUM(amount_usd),0) FROM cash_ledger "
            "WHERE mode = ? AND as_of_date <= ?", [mode, d]).fetchone()[0]
        eq[d] = float(mark) + float(cash)
    def _next_snap(d0):
        # A weekend/holiday flow (e.g. the Sat 07-25 deposit) first shows up in
        # the NEXT trading day's equity mark — attribute it there, or the jump
        # counts as return.
        for s_d in snaps:
            if s_d >= d0:
                return s_d
        return snaps[-1]

    for d, amt, kind in pc.execute(
            "SELECT as_of_date, amount_usd, kind FROM cash_ledger "
            "WHERE mode = ? AND kind IN ('deposit','reconcile')", [mode]).fetchall():
        amt = float(amt)
        is_flow = (kind == "deposit") or ((d, round(amt, 2)) in KNOWN_FLOW_RECONCILES)
        if is_flow:
            sd = _next_snap(d)
            flows[sd] = flows.get(sd, 0.0) + amt
        elif abs(amt) >= FLOW_WARN_THRESHOLD:
            print(f"  !! UNCLASSIFIED large reconcile {d} Rs.{amt:,.2f} — "
                  f"add to KNOWN_FLOW_RECONCILES if it is a transfer, not P&L")

    # TWR index: r_t = (E_t - F_t) / E_{t-1}; flows on the first snapshot are
    # the opening capital (index starts at 1.0 there).
    idx, series = 1.0, []
    prev = None
    for d in snaps:
        f = flows.get(d, 0.0)
        if prev is None:
            series.append((d, idx))
        else:
            if eq[prev] > 0:
                idx *= (eq[d] - f) / eq[prev]
            series.append((d, idx))
        prev = d
    twr = (idx - 1.0) * 100

    nb = dict(pr.execute(
        "SELECT dt, close FROM daily_bars WHERE ticker = ? AND dt >= ? "
        "ORDER BY dt", [BENCH, snaps[0]]).fetchall())
    nb_dates = [d for d in snaps if d in nb]
    bench_ret = ((nb[nb_dates[-1]] / nb[nb_dates[0]]) - 1.0) * 100 if len(nb_dates) > 1 else 0.0

    def maxdd(vals):
        peak, worst = float("-inf"), 0.0
        for v in vals:
            peak = max(peak, v)
            worst = min(worst, v / peak - 1.0)
        return worst * 100

    dd_strat = maxdd([v for _, v in series])
    dd_bench = maxdd([nb[d] for d in nb_dates]) if nb_dates else 0.0

    commissions = -float(pc.execute(
        "SELECT COALESCE(SUM(amount_usd),0) FROM cash_ledger "
        "WHERE mode = ? AND kind = 'commission'", [mode]).fetchone()[0])
    n_days = max(1, (snaps[-1] - snaps[0]).days)
    avg_eq = sum(eq.values()) / len(eq)
    drag_ann = (commissions / avg_eq) * (365 / n_days) * 100

    lines = [
        f"LIVE STRATEGY SCORECARD — {mode} — {snaps[0]} .. {snaps[-1]} ({len(snaps)} sessions)",
        "",
        f"  TWR since go-live : {twr:+.2f}%   vs {BENCH}: {bench_ret:+.2f}%   edge: {twr - bench_ret:+.2f}pp",
        f"  Max drawdown      : {dd_strat:.2f}%  vs {BENCH}: {dd_bench:.2f}%",
        f"  Equity now        : Rs.{eq[snaps[-1]]:,.2f}",
        f"  Modeled commissions Rs.{commissions:,.2f} -> ~{drag_ann:.2f}%/yr annualized "
        f"(replay-modeled total drag ~2.3%/yr; one-time setup charges excluded)",
        "",
        "  Replay envelope   : full-cycle ~+13.4%/yr @ maxDD -17.9% (NIFTY +11.1%/-38.4%);",
        "                      expect LAG in melt-ups & V-recoveries, PROTECTION in declines.",
        "  Verdict inputs    : judge on full cycle + the first real drawdown, not any month.",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", default=None)
    args = p.parse_args(argv)
    from scripts.execution_mode import resolve_execution_mode
    print(build(resolve_execution_mode(args.mode)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
