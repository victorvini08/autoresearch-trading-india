'''RETURNS comparison (not Sortino): momentum vs low-vol vs blend vs Nifty, at
Rs5L, REAL strategy classes (not synthetic baskets), cost-aware, PIT-correct,
continuous compounding.

A single continuous backtest 2019-07 -> 2026-05-14 per book. To avoid the
backtrader ragged-feed prenext gating (late-IPO feeds keep the strategy dormant
until the last feed is up), each book is subclassed so prenext() runs the same
logic as next() — the strategy trades among whatever names already have enough
history + PIT-universe membership, exactly as it would live. The book sits in
cash until the PIT universe is dense (~2022-07), so the honest tradeable window
is FY23..FY26p. Idle cash earns the 6.5% liquid-fund floor.

Run:  uv run python -m experiments.returns_compare
'''
from __future__ import annotations

from datetime import date, timedelta

import backtrader as bt
import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import _load_feeds, _pit_universe
from backtest.engine import run_backtest
from strategy import IndiaMomentumQualityCarry
from experiments.lowvol_engine import IndiaLowVolatilityCarry

MACRO_DB = 'storage/macro.duckdb'
CASH = 500_000.0
CASH_D = (1.065) ** (1 / 252) - 1
RUN_START = date(2019, 7, 1)
RUN_END = date(2026, 5, 14)

FYS = [
    ('FY23', date(2022, 4, 1), date(2023, 3, 31), 'flat/bear'),
    ('FY24', date(2023, 4, 1), date(2024, 3, 31), 'roaring bull'),
    ('FY25', date(2024, 4, 1), date(2025, 3, 31), 'neutral'),
    ('FY26p', date(2025, 4, 1), date(2026, 5, 14), 'risk-off'),
]
TRADE_START = date(2022, 7, 1)   # PIT universe becomes dense here


class MomCont(IndiaMomentumQualityCarry):
    def prenext(self):
        self.next()


class LVCont(IndiaLowVolatilityCarry):
    def prenext(self):
        self.next()


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute("SELECT dt, value FROM macro_daily WHERE "
                     "series_id='index_nifty_50' ORDER BY dt").fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd(r):
    eq = (1 + r).cumprod().to_numpy()
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def _run(cls, feeds, ubd):
    res = run_backtest(cls, feeds, initial_cash=CASH,
                       strategy_kwargs={'universe_by_date': ubd})
    eq = res['equity_curve'].copy(); eq.index = pd.to_datetime(eq.index)
    g = res['gross_exposure_daily'].copy(); g.index = pd.to_datetime(g.index)
    g = g.reindex(eq.index).ffill().fillna(0.0)
    ret = eq.pct_change().fillna(0.0)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return pd.DataFrame({'ret': ret, 'ret_cf': ret + idle * CASH_D, 'gross': g})


def _cum(r):
    return float((1 + r).prod() - 1.0)


def _slice(df, a, b):
    return df[(df.index >= pd.Timestamp(a)) & (df.index <= pd.Timestamp(b))]


def main():
    prepare.INITIAL_CASH = CASH
    members, ubd = _pit_universe(RUN_END)
    feeds = _load_feeds(RUN_START, RUN_END, members)
    print(f'feeds {len(feeds)}; running continuous Rs{int(CASH):,} backtests...')
    mom = _run(MomCont, feeds, ubd)
    lv = _run(LVCont, feeds, ubd)

    # align + blends (cash-floored)
    idx = mom.index.union(lv.index)
    m = mom.reindex(idx).fillna(0.0); l = lv.reindex(idx).fillna(0.0)
    b50 = 0.5 * m['ret_cf'] + 0.5 * l['ret_cf']
    vlv = l['ret_cf'].rolling(60, min_periods=20).std()
    vm = m['ret_cf'].rolling(60, min_periods=20).std()
    w = (1 / vlv / (1 / vlv + 1 / vm)).shift(1).fillna(0.5).clip(0.05, 0.95)
    brp = w * l['ret_cf'] + (1 - w) * m['ret_cf']
    nifty = _nifty()

    series = {
        'Nifty50': None,
        'MOMENTUM (raw)': m['ret'], 'MOMENTUM +cashfloor': m['ret_cf'],
        'LOW-VOL (raw)': l['ret'], 'LOW-VOL +cashfloor': l['ret_cf'],
        'BLEND 50/50 (cf)': b50, 'BLEND risk-parity (cf)': brp,
    }

    print('\n' + '=' * 90)
    print('RETURNS @ Rs5L — real classes, cost-aware, PIT-correct (tradeable era FY23-FY26p)')
    print('=' * 90)
    hdr = f'{"":24}' + ''.join(f'{fy:>11}' for fy, *_ in FYS) + f'{"CUM":>11}{"CAGR":>9}{"maxDD":>9}'
    print(hdr)
    # Nifty row
    def nifty_ret(a, b):
        s = nifty[(nifty.index >= pd.Timestamp(a)) & (nifty.index <= pd.Timestamp(b))]
        return float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0
    nrow = ''.join(f'{nifty_ret(a,b)*100:>+10.1f}%' for _, a, b, _ in FYS)
    ncum = nifty_ret(TRADE_START, RUN_END)
    nyrs = (RUN_END - TRADE_START).days / 365.25
    ncagr = (1 + ncum) ** (1 / nyrs) - 1
    s = nifty[(nifty.index >= pd.Timestamp(TRADE_START))]
    ndd = _maxdd(s.pct_change().fillna(0.0))
    print(f'{"Nifty50":24}{nrow}{ncum*100:>+10.1f}%{ncagr*100:>+8.1f}%{ndd*100:>8.1f}%')

    for name, r in series.items():
        if name == 'Nifty50' or r is None:
            continue
        fy_cells = ''.join(f'{_cum(_slice(r.to_frame("x"), a, b)["x"])*100:>+10.1f}%'
                           for _, a, b, _ in FYS)
        trade = r[r.index >= pd.Timestamp(TRADE_START)]
        cum = _cum(trade)
        cagr = (1 + cum) ** (1 / nyrs) - 1
        dd = _maxdd(trade)
        print(f'{name:24}{fy_cells}{cum*100:>+10.1f}%{cagr*100:>+8.1f}%{dd*100:>8.1f}%')

    print('\nNote: CUM/CAGR/maxDD over the PIT-tradeable era 2022-07 -> 2026-05 '
          f'({nyrs:.1f}y). Pre-2022 the real PIT universe is ~5 names (untradeable);')
    print('the earlier synthetic "FY21 +48%" low-vol recovery was a survivorship '
          'artifact the real PIT strategy cannot reproduce.')
    print('DONE')


if __name__ == '__main__':
    main()
