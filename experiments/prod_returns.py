'''Production returns: the locked momentum book (IndiaMomentumQualityCarry),
RAW and with the cash floor (idle cash -> liquid fund @6.5%), per FY @Rs5L,
cost-aware, PIT, continuous. The numbers we lock in as "momentum + cash".

Run:  uv run python -m experiments.prod_returns
'''
from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import _load_feeds, _pit_universe
from backtest.engine import run_backtest
from strategy import IndiaMomentumQualityCarry

CASH = 500_000.0
CASH_D = (1.065) ** (1 / 252) - 1
RUN_START = date(2019, 7, 1)
RUN_END = date(2026, 5, 14)
TRADE_START = date(2022, 7, 1)
FYS = [('FY23 (flat/bear)', date(2022, 4, 1), date(2023, 3, 31)),
       ('FY24 (bull)', date(2023, 4, 1), date(2024, 3, 31)),
       ('FY25 (neutral)', date(2024, 4, 1), date(2025, 3, 31)),
       ('FY26p (risk-off)', date(2025, 4, 1), date(2026, 5, 14))]


class MomCont(IndiaMomentumQualityCarry):
    def prenext(self): self.next()


def _nifty():
    con = duckdb.connect('storage/macro.duckdb', read_only=True)
    df = con.execute("SELECT dt,value FROM macro_daily WHERE series_id='index_nifty_50' ORDER BY dt").fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd(r):
    eq = (1 + r).cumprod().to_numpy(); return float((eq / np.maximum.accumulate(eq) - 1).min())


def main():
    prepare.INITIAL_CASH = CASH
    members, ubd = _pit_universe(RUN_END)
    feeds = _load_feeds(RUN_START, RUN_END, members)
    res = run_backtest(MomCont, feeds, initial_cash=CASH, strategy_kwargs={'universe_by_date': ubd})
    eq = res['equity_curve'].copy(); eq.index = pd.to_datetime(eq.index)
    g = res['gross_exposure_daily'].copy(); g.index = pd.to_datetime(g.index); g = g.reindex(eq.index).ffill().fillna(0.0)
    raw = eq.pct_change().fillna(0.0)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    cf = raw + idle * CASH_D
    nifty = _nifty()
    nyrs = (RUN_END - TRADE_START).days / 365.25

    def fy(r, a, b):
        x = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]; return float((1 + x).prod() - 1)
    def nret(a, b):
        s = nifty[(nifty.index >= pd.Timestamp(a)) & (nifty.index <= pd.Timestamp(b))]
        return float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0

    print('=' * 70)
    print('PRODUCTION = MOMENTUM + CASH FLOOR  (Rs5L, cost-aware, PIT)')
    print('cash floor = idle gross parked in a liquid fund @ 6.5%/yr')
    print('=' * 70)
    print(f'avg deployment (gross): {g[g.index>=pd.Timestamp(TRADE_START)].mean()*100:.0f}%  '
          f'(rest earns the cash floor)\n')
    print(f'{"Financial Year":20}{"Nifty50":>10}{"Mom (raw)":>12}{"Mom + CASH":>12}')
    for label, a, b in FYS:
        print(f'{label:20}{nret(a,b)*100:>+9.1f}%{fy(raw,a,b)*100:>+11.1f}%{fy(cf,a,b)*100:>+11.1f}%')
    print('-' * 54)
    ca, cb = TRADE_START, RUN_END
    cum_raw = fy(raw, ca, cb); cum_cf = fy(cf, ca, cb); cum_n = nret(ca, cb)
    print(f'{"CUMULATIVE":20}{cum_n*100:>+9.1f}%{cum_raw*100:>+11.1f}%{cum_cf*100:>+11.1f}%')
    print(f'{"CAGR":20}{((1+cum_n)**(1/nyrs)-1)*100:>+9.1f}%'
          f'{((1+cum_raw)**(1/nyrs)-1)*100:>+11.1f}%{((1+cum_cf)**(1/nyrs)-1)*100:>+11.1f}%')
    tr = raw[raw.index >= pd.Timestamp(TRADE_START)]; tcf = cf[cf.index >= pd.Timestamp(TRADE_START)]
    nf = nifty[nifty.index >= pd.Timestamp(TRADE_START)].pct_change().fillna(0)
    print(f'{"max drawdown":20}{_maxdd(nf)*100:>9.1f}%{_maxdd(tr)*100:>11.1f}%{_maxdd(tcf)*100:>11.1f}%')
    print('\nDONE')


if __name__ == '__main__':
    main()
