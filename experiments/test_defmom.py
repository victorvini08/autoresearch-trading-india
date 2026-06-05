'''Test IndiaDefensiveMomentum ("calmest winners", high-deployment) on the two
binding questions, @Rs5L:
  PART 1 — sub-period STATIONARITY gate (the one low-vol failed): per-fold
           Sortino over the walk-forward, raw AND cash-floored.
  PART 2 — RETURNS (continuous compounding) vs momentum / low-vol / Nifty.

Run:  uv run python -m experiments.test_defmom
'''
from __future__ import annotations

from datetime import date, timedelta

import backtrader as bt
import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    BACKTEST_START, TEST_BOUNDARY, WARMUP_CALENDAR_DAYS, MIN_FOLD_UNIVERSE,
    _load_feeds, _min_active_universe, _pit_universe, _score_window,
    _sub_period_sortinos, _walk_forward_folds,
)
from backtest.metrics import sortino
from backtest.engine import run_backtest
from strategy import IndiaMomentumQualityCarry
from experiments.lowvol_engine import IndiaLowVolatilityCarry
from experiments.defmom_engine import IndiaDefensiveMomentum

CASH = 500_000.0
CASH_D = (1.065) ** (1 / 252) - 1
MACRO_DB = 'storage/macro.duckdb'
RUN_START = date(2019, 7, 1)
RUN_END = date(2026, 5, 14)
TRADE_START = date(2022, 7, 1)
FYS = [('FY23', date(2022, 4, 1), date(2023, 3, 31)),
       ('FY24', date(2023, 4, 1), date(2024, 3, 31)),
       ('FY25', date(2024, 4, 1), date(2025, 3, 31)),
       ('FY26p', date(2025, 4, 1), date(2026, 5, 14))]


class MomCont(IndiaMomentumQualityCarry):
    def prenext(self): self.next()
class LVCont(IndiaLowVolatilityCarry):
    def prenext(self): self.next()
class DMCont(IndiaDefensiveMomentum):
    def prenext(self): self.next()


def _ratio(s):
    if len(s) < 2: return None
    f = 1e-3; sg = [x if abs(x) >= f else (f if x >= 0 else -f) for x in s]
    lo, hi = min(sg), max(sg)
    return lo / hi if hi > 0 else min(map(abs, sg)) / max(map(abs, sg))


def _cash_floored(score):
    eq = score['equity_curve'].copy()
    if len(eq) < 2: return pd.Series(dtype=float), pd.Series(dtype=float)
    eq.index = pd.to_datetime(eq.index)
    ret = eq.pct_change().fillna(0.0)
    g = score['gross_exposure_daily'].copy()
    if len(g):
        g.index = pd.to_datetime(g.index); g = g.reindex(eq.index).ffill().fillna(0.0)
    else:
        g = pd.Series(0.0, index=eq.index)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return ret, ret + idle * CASH_D


def part1_stationarity():
    prepare.INITIAL_CASH = CASH
    plan = []
    for (_a, _b, val_s, val_e) in _walk_forward_folds(BACKTEST_START, TEST_BOUNDARY):
        members, ubd = _pit_universe(val_e)
        if not members or _min_active_universe(ubd, val_s, val_e) < MIN_FOLD_UNIVERSE:
            continue
        plan.append({'val_s': val_s, 'val_e': val_e, 'members': members, 'ubd': ubd})
    raw, cf, starts = [], [], []
    for i, p in enumerate(plan):
        feeds = _load_feeds(p['val_s'] - timedelta(days=WARMUP_CALENDAR_DAYS), p['val_e'], p['members'])
        sc = _score_window(IndiaDefensiveMomentum, feeds, p['ubd'], score_start=p['val_s'])
        r_raw, r_cf = _cash_floored(sc)
        starts.append(p['val_s'])
        raw.append(round(float(sortino(r_raw)), 4) if len(r_raw) > 1 and np.isfinite(sortino(r_raw)) else None)
        cf.append(round(float(sortino(r_cf)), 4) if len(r_cf) > 1 and np.isfinite(sortino(r_cf)) else None)
        print(f'  fold {i+1}/{len(plan)} done', flush=True)
    print('\n=== PART 1: DEFENSIVE-MOMENTUM sub-period STATIONARITY @Rs5L ===')
    for label, per in [('raw (canonical)', raw), ('cash-floored', cf)]:
        subs = _sub_period_sortinos(starts, per); r = _ratio(subs)
        finite = [x for x in per if x is not None]
        print(f'  {label}: val Sortino mean={np.mean(finite):.3f}  '
              f'sub-periods={[round(x,3) for x in subs]}  '
              f'stationarity={r:.4f} -> {"PASS" if (r and r>=0.20) else "FAIL"}')


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute("SELECT dt,value FROM macro_daily WHERE series_id='index_nifty_50' ORDER BY dt").fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd(r):
    eq = (1 + r).cumprod().to_numpy(); return float((eq / np.maximum.accumulate(eq) - 1).min())


def _run_cont(cls, feeds, ubd):
    res = run_backtest(cls, feeds, initial_cash=CASH, strategy_kwargs={'universe_by_date': ubd})
    eq = res['equity_curve'].copy(); eq.index = pd.to_datetime(eq.index)
    g = res['gross_exposure_daily'].copy(); g.index = pd.to_datetime(g.index); g = g.reindex(eq.index).ffill().fillna(0.0)
    ret = eq.pct_change().fillna(0.0)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return ret, ret + idle * CASH_D, g


def part2_returns():
    prepare.INITIAL_CASH = CASH
    members, ubd = _pit_universe(RUN_END)
    feeds = _load_feeds(RUN_START, RUN_END, members)
    print(f'\n=== PART 2: RETURNS @Rs5L (continuous, tradeable FY23-FY26p) ===')
    nifty = _nifty()
    dm_raw, dm_cf, dm_g = _run_cont(DMCont, feeds, ubd)
    mom_raw, mom_cf, _ = _run_cont(MomCont, feeds, ubd)
    lv_raw, lv_cf, _ = _run_cont(LVCont, feeds, ubd)
    nyrs = (RUN_END - TRADE_START).days / 365.25

    def cum(r, a=TRADE_START, b=RUN_END):
        x = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
        return float((1 + x).prod() - 1)
    def fy(r, a, b):
        x = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
        return float((1 + x).prod() - 1)
    def nret(a, b):
        s = nifty[(nifty.index >= pd.Timestamp(a)) & (nifty.index <= pd.Timestamp(b))]
        return float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0

    print(f'{"":26}' + ''.join(f'{fyl:>9}' for fyl, *_ in FYS) + f'{"CUM":>9}{"CAGR":>8}{"maxDD":>8}{"avgGr":>7}')
    rows = [('Nifty50', None, None, None),
            ('MOMENTUM +cf', mom_cf, None, None),
            ('LOW-VOL +cf', lv_cf, None, None),
            ('DEF-MOM raw', dm_raw, None, dm_g),
            ('DEF-MOM +cf', dm_cf, None, dm_g)]
    # Nifty
    print(f'{"Nifty50":26}' + ''.join(f'{nret(a,b)*100:>+8.1f}%' for _, a, b in FYS) +
          f'{nret(TRADE_START,RUN_END)*100:>+8.1f}%' +
          f'{((1+nret(TRADE_START,RUN_END))**(1/nyrs)-1)*100:>+7.1f}%' +
          f'{_maxdd(nifty[nifty.index>=pd.Timestamp(TRADE_START)].pct_change().fillna(0))*100:>7.1f}%{"":>7}')
    for name, r, _u, g in rows[1:]:
        c = cum(r); cagr = (1 + c) ** (1 / nyrs) - 1
        tr = r[r.index >= pd.Timestamp(TRADE_START)]
        avgg = f'{g[g.index>=pd.Timestamp(TRADE_START)].mean()*100:>6.0f}%' if g is not None else f'{"":>7}'
        print(f'{name:26}' + ''.join(f'{fy(r,a,b)*100:>+8.1f}%' for _, a, b in FYS) +
              f'{c*100:>+8.1f}%{cagr*100:>+7.1f}%{_maxdd(tr)*100:>7.1f}%{avgg}')


def main():
    part1_stationarity()
    part2_returns()
    print('\nDONE')


if __name__ == '__main__':
    main()
