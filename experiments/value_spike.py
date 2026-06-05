'''FEASIBILITY SPIKE — is VALUE worth a pre-2022 data backfill?

Builds a PIT earnings-yield value factor (TTM EPS / price) on the fundamentals
we already have (2022-2026), and answers the only two questions that decide
whether the backfill is worth it:

  Q1. Is value ANTI-CORRELATED to momentum cross-sectionally? (if value names
      ~= momentum names, value adds no diversification -> backfill pointless)
  Q2. Is value COMPLEMENTARY in returns? Does it do well when momentum does
      badly, and does a value+momentum combo smooth the regime profile?

This is a SPIKE, not a gate run: equal-weight top-quintile factor portfolios,
gross (no whole-share / costs), monthly. It will NOT pass the gates (3yr is too
short — that is exactly why we'd need the backfill); it only tells us whether
value BEHAVES as theory predicts in OUR universe before spending on data.

Book-to-market is intentionally omitted: the `equity` field mixes net-worth and
share-capital line items (RELIANCE alternates ~5T / ~67B), so B/M needs cleaning
first. Earnings yield uses only eps_basic (clean) + price.

Run:  uv run python -m experiments.value_spike
'''
from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from prepare import _pit_universe

PRICES_DB = 'storage/prices.duckdb'
FUND_DB = 'storage/fundamentals.duckdb'
MACRO_DB = 'storage/macro.duckdb'
START = date(2022, 1, 1)
END = date(2026, 5, 14)
VAL_START = date(2023, 7, 1)   # first date with 4 PIT quarters of TTM EPS
TOP_Q = 0.20                   # top-quintile portfolios
FYS = [('FY24', date(2023, 4, 1), date(2024, 3, 31)),
       ('FY25', date(2024, 4, 1), date(2025, 3, 31)),
       ('FY26p', date(2025, 4, 1), date(2026, 5, 14))]


def _prices():
    con = duckdb.connect(PRICES_DB, read_only=True)
    df = con.execute(
        "SELECT dt, ticker, close FROM daily_bars WHERE dt BETWEEN ? AND ? ",
        [START.isoformat(), END.isoformat()]).fetch_df()
    con.close()
    p = df.pivot_table(index='dt', columns='ticker', values='close')
    p.index = pd.to_datetime(p.index)
    return p.sort_index()


def _fundamentals():
    con = duckdb.connect(FUND_DB, read_only=True)
    df = con.execute(
        "SELECT ticker, period_end_date, broadcast_date, eps_basic, "
        "is_consolidated FROM fundamentals_quarterly "
        "WHERE eps_basic IS NOT NULL AND broadcast_date IS NOT NULL").fetch_df()
    con.close()
    # prefer consolidated when both exist for a (ticker, period)
    df['pref'] = df['is_consolidated'].fillna(False).astype(int)
    df = (df.sort_values(['ticker', 'period_end_date', 'pref'])
            .drop_duplicates(['ticker', 'period_end_date'], keep='last'))
    df['broadcast_date'] = pd.to_datetime(df['broadcast_date'])
    df['period_end_date'] = pd.to_datetime(df['period_end_date'])
    return {t: g.sort_values('period_end_date') for t, g in df.groupby('ticker')}


def _ttm_eps(fund_t, asof):
    '''TTM EPS = sum of last 4 quarters with broadcast_date <= asof.'''
    g = fund_t[fund_t['broadcast_date'] <= asof]
    if len(g) < 4:
        return None
    return float(g['eps_basic'].iloc[-4:].sum())


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute("SELECT dt,value FROM macro_daily WHERE "
                     "series_id='index_nifty_50' ORDER BY dt").fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def main():
    px = _prices()
    fund = _fundamentals()
    nifty = _nifty()
    dates = px.index
    # monthly rebalance = first trading day of each month in [VAL_START, END]
    rebal = [g.index[0] for _, g in px[px.index >= pd.Timestamp(VAL_START)]
             .groupby(px[px.index >= pd.Timestamp(VAL_START)].index.to_period('M'))]
    rebal = [d for d in rebal if d <= pd.Timestamp(END)]

    corrs = []
    rets = {'VALUE': [], 'MOMENTUM': [], 'COMBO': [], 'dates': []}
    for i in range(len(rebal) - 1):
        d, d_next = rebal[i], rebal[i + 1]
        members = set(_pit_universe(d.date())[0])
        loc = dates.get_indexer([d])[0]
        if loc < 252:
            continue
        rows = {}
        for t in members:
            if t not in px.columns or t not in fund:
                continue
            p_now = px[t].iloc[loc]
            p_21 = px[t].iloc[loc - 21]
            p_252 = px[t].iloc[loc - 252]
            if not (np.isfinite(p_now) and np.isfinite(p_21) and np.isfinite(p_252)
                    and p_now > 0 and p_252 > 0):
                continue
            ttm = _ttm_eps(fund[t], d)
            if ttm is None:
                continue
            rows[t] = {'mom': p_21 / p_252 - 1.0, 'ep': ttm / p_now}
        if len(rows) < 30:
            continue
        df = pd.DataFrame(rows).T
        rho = spearmanr(df['ep'], df['mom']).correlation
        corrs.append(rho)
        # forward return of an equal-weight top-quintile portfolio
        k = max(5, int(len(df) * TOP_Q))

        def fwd(names):
            r = []
            for t in names:
                a, b = px[t].iloc[loc], px[t].reindex([d_next]).iloc[0]
                if np.isfinite(a) and np.isfinite(b) and a > 0:
                    r.append(b / a - 1.0)
            return float(np.mean(r)) if r else 0.0

        val_names = df['ep'].nlargest(k).index
        mom_names = df['mom'].nlargest(k).index
        df['combo'] = 0.5 * df['ep'].rank(pct=True) + 0.5 * df['mom'].rank(pct=True)
        combo_names = df['combo'].nlargest(k).index
        rets['VALUE'].append(fwd(val_names))
        rets['MOMENTUM'].append(fwd(mom_names))
        rets['COMBO'].append(fwd(combo_names))
        rets['dates'].append(d_next)

    print('=' * 72)
    print('VALUE FEASIBILITY SPIKE — earnings-yield (TTM E/P) on 2023-07..2026-05')
    print('(equal-weight top-quintile, gross, monthly — SPIKE not a gate run)')
    print('=' * 72)
    c = np.array(corrs)
    print(f'\nQ1. Cross-sectional Spearman(value, momentum):')
    print(f'    mean={c.mean():+.3f}  median={np.median(c):+.3f}  '
          f'%months negative={100*np.mean(c<0):.0f}%  (n={len(c)} months)')
    print(f'    -> {"ANTI-correlated (value is a genuinely different bet -> diversifies)" if c.mean()<-0.05 else ("~UNCORRELATED (mild diversification)" if c.mean()<0.05 else "POSITIVELY correlated (value ~= momentum -> NO diversification)")}')

    ser = {k: pd.Series(rets[k], index=pd.to_datetime(rets['dates']))
           for k in ('VALUE', 'MOMENTUM', 'COMBO')}
    print(f'\nQ2. Return-stream correlation value vs momentum (monthly): '
          f'{ser["VALUE"].corr(ser["MOMENTUM"]):+.3f}')

    def cum(s, a=None, b=None):
        x = s if a is None else s[(s.index >= pd.Timestamp(a)) & (s.index <= pd.Timestamp(b))]
        return float((1 + x).prod() - 1)
    def nret(a, b):
        s = nifty[(nifty.index >= pd.Timestamp(a)) & (nifty.index <= pd.Timestamp(b))]
        return float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0

    print('\n    Per-FY returns (gross top-quintile):')
    print(f'    {"":10}' + ''.join(f'{fy:>10}' for fy, *_ in FYS) + f'{"CUM":>10}')
    print(f'    {"Nifty":10}' + ''.join(f'{nret(a,b)*100:>+9.1f}%' for _, a, b in FYS)
          + f'{nret(VAL_START,END)*100:>+9.1f}%')
    for k in ('VALUE', 'MOMENTUM', 'COMBO'):
        print(f'    {k:10}' + ''.join(f'{cum(ser[k],a,b)*100:>+9.1f}%' for _, a, b in FYS)
              + f'{cum(ser[k])*100:>+9.1f}%')

    # complementarity: in the worst momentum months, how did value do?
    mom = ser['MOMENTUM']; val = ser['VALUE']
    worst = mom.nsmallest(max(3, len(mom) // 5)).index
    print(f'\n    Complementarity check — in momentum\'s worst {len(worst)} months:')
    print(f'      momentum avg = {mom[worst].mean()*100:+.2f}%/mo   '
          f'value avg = {val[worst].mean()*100:+.2f}%/mo   '
          f'-> value {"CUSHIONS" if val[worst].mean() > mom[worst].mean() else "does NOT cushion"} momentum drawdowns')
    print('\nDONE')


if __name__ == '__main__':
    main()
