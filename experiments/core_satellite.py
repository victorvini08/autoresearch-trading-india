"""Core-satellite frontier: a STATIC w_idx slice in the Nifty 50 index
(implementable as NIFTYBEES, a policy sleeve held outside strategy.py's
selection) + (1 - w_idx) in the locked defensive book WITH its production
cash floor (idle gross parked in a liquid fund @ ~6.5%/yr).

Why this is the honest return lever (and the last untested one):
  - The fitted-alpha search is exhausted (77 iterations + 15 experiment
    families; every higher-return fitted variant fails worst-regime gates).
  - The blend has ZERO fitted parameters — its return source is the equity
    risk premium (priced, accepted ex ante), not a discovered anomaly, so
    there is nothing to overfit and no sealed budget to spend. This is the
    same epistemic class as the cash floor: a deterministic allocation
    policy, not a strategy-code change.
  - multi_engine.py only ever tested sleeves on IDLE cash (time-varying,
    anti-defensive: idle peaks exactly in crashes). A STATIC core is the
    structurally different, untested configuration. scripts/blend_frontier.py
    instrumented this on validation-era windows but was never run to a
    recorded conclusion; this script extends it to the full PIT-tradeable
    era with the production cash floor and a cash-instead-of-book control.

Honest accounting notes (all biases run AGAINST the blend):
  - Index leg uses the Nifty 50 PRICE index: dividends (~+1.2%/yr for the
    TR index that NIFTYBEES actually tracks) are NOT credited.
  - Blend arithmetic is daily constant-mix; real implementation is biweekly
    band rebalancing (difference second-order, turnover of a static-weight
    sleeve is a few %/yr -> cost drag ~0.01%/yr at Dhan CNC rates).
  - Everything after VAL_END (2024-12-31) is the SPENT sealed era, shown as
    ILLUSTRATION ONLY (zero-parameter arithmetic on known series, not used
    to fit anything) — it contains the only true crash in the tradeable era.

Run:  PREPARE_MAX_WORKERS=1 uv run python -m experiments.core_satellite
"""
from __future__ import annotations

import importlib
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    WARMUP_CALENDAR_DAYS,
    _find_strategy_class,
    _load_feeds,
    _pit_universe,
    _score_window,
)

MACRO_DB = Path("storage/macro.duckdb")
RESULTS = Path("experiments/results")
CASH = 500_000
CASH_YIELD_DAILY = (1.065) ** (1 / 252) - 1  # liquid fund ~6.5%/yr
BOOK_MODULE = "strategy"  # the locked IndiaMomentumQualityCarry

SPAN_START = date(2022, 7, 1)   # first >=200-name PIT snapshot (tradeable era)
SPAN_END = date(2026, 6, 5)
VAL_END = date(2024, 12, 31)    # beyond this = spent-sealed ILLUSTRATION era

W_IDX = [0.00, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00]

FYS = [
    ("FY23p", date(2022, 7, 1), date(2023, 3, 31), "flat/bear (from 2022-07)"),
    ("FY24", date(2023, 4, 1), date(2024, 3, 31), "roaring bull"),
    ("FY25", date(2024, 4, 1), date(2025, 3, 31), "neutral"),
    ("FY26p", date(2025, 4, 1), SPAN_END, "risk-off + 2026Q1 crash"),
]


def _nifty_returns(idx: pd.DatetimeIndex) -> pd.Series:
    con = duckdb.connect(str(MACRO_DB), read_only=True)
    try:
        df = con.execute(
            "SELECT dt, value FROM macro_daily WHERE series_id='index_nifty_50' "
            "AND dt BETWEEN ? AND ? ORDER BY dt",
            [SPAN_START - timedelta(days=10), SPAN_END],
        ).fetch_df()
    finally:
        con.close()
    s = pd.Series(
        df["value"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(df["dt"])).normalize(),
    )
    s = s[~s.index.duplicated(keep="last")]
    p = s.reindex(s.index.union(idx)).ffill().reindex(idx)
    return p.pct_change().fillna(0.0)


def _maxdd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1.0).min()) if len(r) else 0.0


def _sortino(r: pd.Series) -> float:
    if len(r) == 0:
        return float("nan")
    dn = r[r < 0]
    dd = float(np.sqrt(np.mean(dn**2))) if len(dn) else 0.0
    return float(r.mean() / dd * np.sqrt(252)) if dd > 0 else float("inf")


def _cagr(r: pd.Series) -> float:
    if len(r) == 0:
        return float("nan")
    tot = float((1 + r).prod())
    yrs = len(r) / 252.0
    return tot ** (1 / yrs) - 1.0


def _slice(r: pd.Series, a: date, b: date) -> pd.Series:
    return r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]


def main() -> None:
    prepare.INITIAL_CASH = CASH
    base_cls = _find_strategy_class(importlib.import_module(BOOK_MODULE))
    # ragged-feed prenext fix (see experiments/returns_compare.py): late-IPO
    # feeds otherwise keep the strategy dormant until the youngest feed is up.
    cls = type("BookCont", (base_cls,), {"prenext": lambda self: self.next()})

    members, ubd = _pit_universe(SPAN_END)
    # CLOCK FIX: datas[0] drives _is_rebalance_today; alphabetical order puts
    # 360ONE (first bar 2023-01-23) first -> dead clock -> no rebalances
    # before that date. Anchor datas[0] to the deepest-history member.
    con = duckdb.connect("storage/prices.duckdb", read_only=True)
    try:
        meta = {
            r[0]: (r[1], -r[2])
            for r in con.execute(
                "SELECT ticker, min(dt), count(*) FROM daily_bars "
                "WHERE ticker IN (SELECT unnest(?::varchar[])) GROUP BY ticker",
                [list(members)],
            ).fetchall()
        }
    finally:
        con.close()
    members = sorted(members, key=lambda t: (*meta.get(t, (date.max, 0)), t))
    feeds = _load_feeds(
        SPAN_START - timedelta(days=WARMUP_CALENDAR_DAYS), SPAN_END, members
    )
    print(f"feeds {len(feeds)}; running continuous book @ Rs{CASH:,.0f} "
          f"{SPAN_START}..{SPAN_END} ...", flush=True)
    score = _score_window(cls, feeds, ubd, score_start=SPAN_START)

    eq = score["equity_curve"].copy()
    gross = score["gross_exposure_daily"].copy()
    eq.index = pd.to_datetime(eq.index).normalize()
    gross.index = pd.to_datetime(gross.index).normalize()
    eq = eq[eq.index >= pd.Timestamp(SPAN_START)]
    gross = gross.reindex(eq.index).ffill().fillna(0.0)

    r_book = eq.pct_change().fillna(0.0)
    idle = (1.0 - gross.shift(1).fillna(gross.iloc[0])).clip(0.0, 1.0)
    r_book_cf = r_book + idle * CASH_YIELD_DAILY          # production policy
    r_idx = _nifty_returns(eq.index)
    r_cash = pd.Series(CASH_YIELD_DAILY, index=eq.index)

    # persist the curve so future blend arithmetic never needs a re-run
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "equity": eq, "gross": gross, "r_book": r_book,
        "r_book_cf": r_book_cf, "r_nifty50": r_idx,
    }).to_csv(RESULTS / "core_satellite_book_curve.csv")

    print(f"book days={len(eq)}  avg gross={gross.mean()*100:.1f}%", flush=True)

    def blend(w: float) -> pd.Series:
        return w * r_idx + (1 - w) * r_book_cf

    def control(w: float) -> pd.Series:
        return w * r_idx + (1 - w) * r_cash

    # ---------- full tradeable era ----------
    print("\n=== CORE-SATELLITE FRONTIER — full PIT-tradeable era "
          f"{SPAN_START}..{SPAN_END} (Rs5L, cost-aware book, price-index core) ===")
    hdr = (f"{'w_idx':>6} | {'CAGR':>7} {'maxDD':>7} {'Sortino':>8} | "
           f"{'ctlCAGR':>8} {'ctlDD':>7} | " +
           " ".join(f"{l:>8}" for l, *_ in FYS))
    print(hdr)
    for w in W_IDX:
        rb, rc = blend(w), control(w)
        fy = " ".join(
            f"{(1 + _slice(rb, a, b)).prod() - 1:+8.1%}" for _, a, b, _ in FYS
        )
        tag = {0.0: "  <- current production", 1.0: "  <- pure index"}.get(w, "")
        print(f"{w:>6.2f} | {_cagr(rb):>+7.1%} {_maxdd(rb):>7.1%} "
              f"{_sortino(rb):>8.2f} | {_cagr(rc):>+8.1%} {_maxdd(rc):>7.1%} | "
              f"{fy}{tag}")

    # ---------- validation era only (selection basis) ----------
    print(f"\n=== VALIDATION ERA ONLY {SPAN_START}..{VAL_END} "
          "(halves = sub-period sanity, no sign-flip wanted) ===")
    print(f"{'w_idx':>6} | {'CAGR':>7} {'maxDD':>7} {'Sortino':>8} | "
          f"{'half1 Sor':>9} {'half2 Sor':>9}")
    for w in W_IDX:
        rv = _slice(blend(w), SPAN_START, VAL_END)
        mid = rv.index[len(rv) // 2]
        s1, s2 = _sortino(rv[rv.index <= mid]), _sortino(rv[rv.index > mid])
        print(f"{w:>6.2f} | {_cagr(rv):>+7.1%} {_maxdd(rv):>7.1%} "
              f"{_sortino(rv):>8.2f} | {s1:>9.2f} {s2:>9.2f}")

    # ---------- spent-sealed era: ILLUSTRATION ONLY ----------
    a, b = date(2025, 1, 1), SPAN_END
    print(f"\n=== SPENT-SEALED ERA {a}..{b} — ILLUSTRATION ONLY "
          "(contains the only true crash: 2026Q1 Nifty −14.6%) ===")
    print(f"{'w_idx':>6} | {'total':>7} {'maxDD':>7} | {'ctl total':>9} {'ctlDD':>7}")
    for w in W_IDX:
        rs, rc = _slice(blend(w), a, b), _slice(control(w), a, b)
        print(f"{w:>6.2f} | {(1+rs).prod()-1:>+7.1%} {_maxdd(rs):>7.1%} | "
              f"{(1+rc).prod()-1:>+9.1%} {_maxdd(rc):>7.1%}")

    ni = _slice(r_idx, a, b)
    print(f"  Nifty50 over this window: {(1+ni).prod()-1:+.1%}  "
          f"maxDD {_maxdd(ni):.1%}")
    print("\nNOTE: index leg is the PRICE index — NIFTYBEES tracks TOTAL return "
          "(~+1.2%/yr extra, uncounted). All biases run against the blend.")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
