'''Gate the momentum + low-vol BLEND on the walk-forward, the same way
prepare.evaluate gates a single strategy — the decisive test of whether the
regime-complementary blend is MORE sub-period-stationary than standalone
low-vol (which failed the stationarity gate 0.08 < 0.20).

For each scored walk-forward fold we run BOTH the momentum book and the low-vol
engine, combine their in-window daily returns (idle cash floored at 6.5%), and
score the blend's per-fold Sortino. Then we apply prepare's exact sub-period
bucketing + the anti_overfit stationarity / Bonferroni / RW-MC gates to the
blended stream. prepare.py is IMMUTABLE and reused, not edited.

Run:  uv run python -m experiments.gate_blend
'''
from __future__ import annotations

import importlib
from datetime import timedelta

import numpy as np
import pandas as pd

import prepare
from prepare import (
    BACKTEST_START, TEST_BOUNDARY, WARMUP_CALENDAR_DAYS, MIN_FOLD_UNIVERSE,
    _find_strategy_class, _load_feeds, _min_active_universe, _pit_universe,
    _score_window, _sub_period_sortinos, _walk_forward_folds,
)
from backtest.metrics import sortino
from backtest.anti_overfit import compute_rw_mc_null

CASH_D = (1.065) ** (1 / 252) - 1


def _cash_floored(score: dict) -> pd.Series:
    '''In-window daily returns with idle cash earning the 6.5% liquid floor.'''
    eq = score['equity_curve'].copy()
    if len(eq) < 2:
        return pd.Series(dtype=float)
    eq.index = pd.to_datetime(eq.index)
    ret = eq.pct_change().fillna(0.0)
    g = score['gross_exposure_daily'].copy()
    if len(g):
        g.index = pd.to_datetime(g.index)
        g = g.reindex(eq.index).ffill().fillna(0.0)
    else:
        g = pd.Series(0.0, index=eq.index)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return ret + idle * CASH_D


def _blend(lv: pd.Series, mom: pd.Series, mode: str) -> pd.Series:
    df = pd.concat([lv.rename('lv'), mom.rename('mom')], axis=1).dropna()
    if df.empty:
        return pd.Series(dtype=float)
    if mode == '50':
        return 0.5 * df['lv'] + 0.5 * df['mom']
    vlv = df['lv'].rolling(60, min_periods=20).std()
    vm = df['mom'].rolling(60, min_periods=20).std()
    w = (1 / vlv / (1 / vlv + 1 / vm)).shift(1).fillna(0.5).clip(0.05, 0.95)
    return w * df['lv'] + (1 - w) * df['mom']


def _stationarity_ratio(sorts):
    if len(sorts) < 2:
        return None
    floor = 1e-3
    signed = [s if abs(s) >= floor else (floor if s >= 0 else -floor) for s in sorts]
    lo, hi = min(signed), max(signed)
    return (lo / hi) if hi > 0 else (min(map(abs, signed)) / max(map(abs, signed)))


def main():
    import os
    prepare.INITIAL_CASH = float(os.environ.get('GB_CASH', '50000'))
    print(f'INITIAL_CASH = Rs{int(prepare.INITIAL_CASH):,}')
    lv_cls = _find_strategy_class(importlib.import_module('experiments.lowvol_engine'))
    mom_cls = _find_strategy_class(importlib.import_module('strategy'))

    # plan folds exactly like prepare.evaluate
    plan = []
    for (_ts, _te, val_s, val_e) in _walk_forward_folds(BACKTEST_START, TEST_BOUNDARY):
        members, fold_ubd = _pit_universe(val_e)
        if not members or _min_active_universe(fold_ubd, val_s, val_e) < MIN_FOLD_UNIVERSE:
            continue
        plan.append({'val_s': val_s, 'val_e': val_e, 'members': members, 'ubd': fold_ubd})
    print(f'{len(plan)} scorable folds')

    per_fold = {'lv': [], 'mom': [], '50': [], 'rp': []}
    fold_val_starts = []
    chained = {'lv': [50_000.0], 'mom': [50_000.0], '50': [50_000.0], 'rp': [50_000.0]}

    for i, p in enumerate(plan):
        feeds = _load_feeds(p['val_s'] - timedelta(days=WARMUP_CALENDAR_DAYS),
                            p['val_e'], p['members'])
        lv_s = _score_window(lv_cls, feeds, p['ubd'], score_start=p['val_s'])
        mom_s = _score_window(mom_cls, feeds, p['ubd'], score_start=p['val_s'])
        lv_cf = _cash_floored(lv_s)
        mom_cf = _cash_floored(mom_s)
        streams = {'lv': lv_cf, 'mom': mom_cf,
                   '50': _blend(lv_cf, mom_cf, '50'),
                   'rp': _blend(lv_cf, mom_cf, 'rp')}
        fold_val_starts.append(p['val_s'])
        for k, r in streams.items():
            per_fold[k].append(round(float(sortino(r)), 4) if len(r) > 1 and np.isfinite(sortino(r)) else None)
            last = chained[k][-1]
            for x in r.iloc[1:] if len(r) > 1 else []:
                last *= (1 + x)
                chained[k].append(last)
        print(f'  fold {i+1}/{len(plan)} {p["val_s"]}..{p["val_e"]} done', flush=True)

    print('\n===== per-fold Sortino & gates (cash-floored, Rs50k) =====')
    for k, label in [('lv', 'LOW-VOL alone'), ('mom', 'MOMENTUM alone'),
                     ('50', 'BLEND 50/50'), ('rp', 'BLEND risk-parity')]:
        finite = [s for s in per_fold[k] if s is not None]
        val_mean = float(np.mean(finite)) if finite else 0.0
        subs = _sub_period_sortinos(fold_val_starts, per_fold[k])
        ratio = _stationarity_ratio(subs)
        ch = pd.Series(chained[k]).pct_change().dropna().to_numpy()
        if ch.size >= 2 and val_mean > 0:
            agg_sortino = float(sortino(pd.Series(ch)))
            pct, rw = compute_rw_mc_null(ch, lambda a: float(sortino(pd.Series(a))))
            pval = float((np.sum(rw >= agg_sortino) + 1) / (len(rw) + 1))
        else:
            pct, pval = 0.0, 1.0
        stat_pass = (ratio is not None and ratio >= 0.20)
        bonf_pass = pval < 0.10
        rwmc_pass = pct >= 0.90
        print(f'\n{label}:')
        print(f'  val Sortino mean = {val_mean:.3f}')
        print(f'  sub-period Sortinos = {[round(x,3) for x in subs]}')
        print(f'  stationarity ratio = {ratio if ratio is None else round(ratio,4)}  '
              f'(need >=0.20)  -> {"PASS" if stat_pass else "FAIL"}')
        print(f'  Bonferroni p = {pval:.4f} (need <0.10) -> {"PASS" if bonf_pass else "FAIL"}; '
              f'RW-MC pct = {pct:.3f} (need >=0.90) -> {"PASS" if rwmc_pass else "FAIL"}')
        print(f'  >>> stationarity+bonferroni+rwmc: '
              f'{"ALL PASS" if (stat_pass and bonf_pass and rwmc_pass) else "FAIL"}')

    print('\nDONE')


if __name__ == '__main__':
    main()
