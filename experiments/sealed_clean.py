'''CLEAN sealed-window reveal (2025-01-01 -> 2026-05-14) vs Nifty50, for the
low-vol engine, the locked momentum book, and the blend — at Rs50k and Rs5L.

Fixes the backtrader ragged-feed prenext gating that suppressed BOTH books in
the raw harness: the sealed union universe (_pit_universe(BACKTEST_END))
includes names that IPO'd DURING 2024-2025, whose first bar is well after the
warmup start; backtrader stays in prenext() (strategy dormant, no rebalancing)
until the LAST feed comes online (~2025-10), so deployment never happened for
most of the window. A name with no warmup history cannot be a low-vol selection
anyway (it lacks the 252-day vol lookback), so excluding feeds that start after
the warmup begins is decision-neutral for the books while letting next() run on
time. prepare.py is IMMUTABLE and NOT edited; this fix lives only in the runner.

Honest caveat (printed): the sealed window overlaps FY25/FY26, which were seen
when low-vol was discovered, so these numbers are INFORMATIVE, not a clean OOS
proof. No formal sealed reveal is committed.

Run:  uv run python -m experiments.sealed_clean
'''
from __future__ import annotations

import importlib
from datetime import timedelta

import backtrader as bt
import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    BACKTEST_END, TEST_BOUNDARY, WARMUP_CALENDAR_DAYS,
    _find_strategy_class, _load_feeds, _pit_universe,
)
from backtest.engine import run_backtest

MACRO_DB = 'storage/macro.duckdb'
CASH_D = (1.065) ** (1 / 252) - 1
# Feeds must cover the warmup; drop any whose first bar is after this cutoff so
# backtrader's next() starts on time (not blocked in prenext by a late IPO).
FEED_START_CUTOFF = TEST_BOUNDARY - timedelta(days=WARMUP_CALENDAR_DAYS - 40)


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute(
        "SELECT dt, value FROM macro_daily WHERE series_id='index_nifty_50' "
        "ORDER BY dt"
    ).fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd(r: pd.Series) -> float:
    eq = (1 + r).cumprod().to_numpy()
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def _sealed(mod_name: str, cash: float, feeds: dict, ubd: dict) -> dict:
    '''Run the sealed window via run_backtest (same engine as _score_window),
    then slice to the scored window [TEST_BOUNDARY, BACKTEST_END].'''
    prepare.INITIAL_CASH = cash
    cls = _find_strategy_class(importlib.import_module(mod_name))
    res = run_backtest(cls, feeds, initial_cash=cash,
                       strategy_kwargs={'universe_by_date': ubd})
    eq = res['equity_curve'].copy()
    eq.index = pd.to_datetime(eq.index)
    g = res['gross_exposure_daily'].copy()
    g.index = pd.to_datetime(g.index)
    st = pd.Timestamp(TEST_BOUNDARY)
    eq = eq[eq.index >= st]
    g = g[g.index >= st].reindex(eq.index).ffill().fillna(0.0)
    # normalise equity to the window start so total return is window-only
    eq = eq / eq.iloc[0]
    ret = eq.pct_change().fillna(0.0)
    return {'eq': eq, 'ret': ret, 'gross': g,
            'total': float(eq.iloc[-1] - 1.0),
            'maxdd': _maxdd(ret), 'avg_gross': float(g.mean())}


def main():
    nifty = _nifty()
    members, ubd = _pit_universe(BACKTEST_END)
    raw = _load_feeds(TEST_BOUNDARY - timedelta(days=WARMUP_CALENDAR_DAYS),
                      BACKTEST_END, members)
    feeds = {t: df for t, df in raw.items()
             if df.index.min().date() <= FEED_START_CUTOFF}
    dropped = len(raw) - len(feeds)
    print(f'feeds: {len(raw)} loaded, {dropped} dropped for first-bar > '
          f'{FEED_START_CUTOFF} (late IPOs, never low-vol selections), '
          f'{len(feeds)} kept')

    print('\n' + '=' * 72)
    print('SEALED 2025-01-01 -> 2026-05-14  vs Nifty50  (prenext-fixed)')
    print('INFORMATIVE only — window overlaps FY25/FY26 seen during discovery;')
    print('no formal sealed reveal committed.')
    print('=' * 72)

    for cash in (50_000.0, 500_000.0):
        lv = _sealed('experiments.lowvol_engine', cash, feeds, ubd)
        mom = _sealed('strategy', cash, feeds, ubd)
        idx = lv['eq'].index
        s = nifty[(nifty.index >= idx[0]) & (nifty.index <= idx[-1])]
        nret, ndd = float(s.iloc[-1] / s.iloc[0] - 1), _maxdd(s.pct_change().fillna(0.0))

        lv_idle = (1 - lv['gross'].shift(1).fillna(lv['gross'].iloc[0])).clip(0, 1)
        mom_idle = (1 - mom['gross'].shift(1).fillna(mom['gross'].iloc[0])).clip(0, 1)
        lv_cf = lv['ret'] + lv_idle * CASH_D
        mom_cf = mom['ret'] + mom_idle * CASH_D
        b50 = 0.5 * lv_cf + 0.5 * mom_cf
        vlv = lv_cf.rolling(60, min_periods=20).std()
        vm = mom_cf.rolling(60, min_periods=20).std()
        w = (1 / vlv / (1 / vlv + 1 / vm)).shift(1).fillna(0.5).clip(0.05, 0.95)
        brp = w * lv_cf + (1 - w) * mom_cf
        tot = lambda r: float((1 + r).prod() - 1.0)

        print(f'\n----- @ Rs{int(cash):,} -----')
        print(f'  Nifty50               : {nret*100:+7.2f}%   maxDD {ndd*100:6.1f}%')
        print(f'  LOW-VOL (raw)         : {lv["total"]*100:+7.2f}%   '
              f'maxDD {lv["maxdd"]*100:6.1f}%   avg gross {lv["avg_gross"]*100:.0f}%')
        print(f'  LOW-VOL + cash floor  : {tot(lv_cf)*100:+7.2f}%   '
              f'maxDD {_maxdd(lv_cf)*100:6.1f}%')
        print(f'  MOMENTUM (raw)        : {mom["total"]*100:+7.2f}%   '
              f'maxDD {mom["maxdd"]*100:6.1f}%   avg gross {mom["avg_gross"]*100:.0f}%')
        print(f'  MOMENTUM + cash floor : {tot(mom_cf)*100:+7.2f}%   '
              f'maxDD {_maxdd(mom_cf)*100:6.1f}%')
        print(f'  BLEND 50/50 (cf)      : {tot(b50)*100:+7.2f}%   '
              f'maxDD {_maxdd(b50)*100:6.1f}%')
        print(f'  BLEND risk-parity(cf) : {tot(brp)*100:+7.2f}%   '
              f'maxDD {_maxdd(brp)*100:6.1f}%')

    print('\nDONE')


if __name__ == '__main__':
    main()
