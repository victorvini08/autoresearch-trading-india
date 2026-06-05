'''Run the IndiaLowVolatilityCarry production candidate through the REAL
anti-overfit gates (prepare.evaluate research mode + backtest.anti_overfit),
then reveal the sealed 2025-01-01 -> 2026-05-14 window vs the Nifty and vs the
locked momentum book, at both Rs50k (canonical evaluator) and Rs5L (scale).

Honest caveat (printed): the sealed window overlaps FY25/FY26, which were
looked at when low-vol was discovered, so the sealed numbers are INFORMATIVE,
not a clean out-of-sample proof. The ATOMIC GATES (research mode) are the real
test — they can reject an overfit variant regardless of that contamination.
This script does NOT commit a formal sealed reveal (does not write
iterations/sealed_reveals.csv); it is an informational backtest.

Run:  uv run python -m experiments.gate_lowvol
'''
from __future__ import annotations

import importlib
from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    BACKTEST_END, TEST_BOUNDARY, WARMUP_CALENDAR_DAYS,
    _find_strategy_class, _load_feeds, _pit_universe, _score_window,
    count_hyperparameters,
)
from backtest.anti_overfit import StrategySummary, run_all_gates

LOWVOL_MOD = 'experiments.lowvol_engine'
MOM_MOD = 'strategy'
MACRO_DB = 'storage/macro.duckdb'
CASH_D = (1.065) ** (1 / 252) - 1   # liquid-fund idle-cash floor (6.5%/yr)


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute(
        "SELECT dt, value FROM macro_daily WHERE series_id='index_nifty_50' "
        "ORDER BY dt"
    ).fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd_from_returns(r: pd.Series) -> float:
    eq = (1 + r).cumprod().to_numpy()
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def _evaluate(mod_name: str) -> dict:
    '''Run research-mode walk-forward ONCE (deterministic; independent of the
    Bonferroni family size).'''
    mod = importlib.import_module(mod_name)
    prepare.INITIAL_CASH = 50_000.0          # canonical evaluator capital
    return prepare.evaluate(mod, mode='research')


def _gates_from(result: dict, mod_name: str, baseline_hyperparams: int,
                n_active_variants: int):
    ao = result['anti_overfit']
    summary = StrategySummary(
        iter_id=f'lowvol_candidate::{mod_name}',
        sortino_train_mean=ao['sortino_val_mean'],
        sortino_val_mean=ao['sortino_val_mean'],
        sortino_val_pvalue=ao['sortino_val_pvalue'],
        aggregate_dd=ao['aggregate_dd'],
        n_trades=ao['n_trades'],
        n_hyperparameters=ao['n_hyperparameters'],
        sub_period_sortinos=tuple(ao['sub_period_sortinos']),
        rw_mc_null_pct=ao['rw_mc_null_pct'],
        universe_respected=ao['universe_respected'],
    )
    return run_all_gates(
        summary,
        baseline_sortino=0.0,                 # parsimony N/A (no added params)
        n_active_variants=n_active_variants,
        baseline_hyperparams=baseline_hyperparams,
        skip_sealed=True,                     # sealed handled separately below
    )


def _sealed_score(mod_name: str, cash: float) -> dict:
    '''Replicate prepare's promotion sealed path and ALSO return the equity
    curve + gross, so we can compute total return vs Nifty (the promotion API
    only returns sortino/calmar/maxdd).'''
    prepare.INITIAL_CASH = cash
    mod = importlib.import_module(mod_name)
    cls = _find_strategy_class(mod)
    members, test_ubd = _pit_universe(BACKTEST_END)
    feeds = _load_feeds(
        TEST_BOUNDARY - timedelta(days=WARMUP_CALENDAR_DAYS),
        BACKTEST_END, members,
    )
    score = _score_window(cls, feeds, test_ubd, score_start=TEST_BOUNDARY)
    eq = score['equity_curve'].copy()
    eq.index = pd.to_datetime(eq.index)
    g = score['gross_exposure_daily'].copy()
    if len(g):
        g.index = pd.to_datetime(g.index)
        g = g.reindex(eq.index).ffill().fillna(0.0)
    else:
        g = pd.Series(0.0, index=eq.index)
    ret = eq.pct_change().fillna(0.0)
    total = float(eq.iloc[-1] / cash - 1.0) if len(eq) else 0.0
    return {
        'sortino': score['sortino'], 'calmar': score['calmar'],
        'max_dd': score['max_dd'], 'trade_count': score['trade_count'],
        'total_return': total, 'eq': eq, 'ret': ret, 'gross': g,
        'avg_gross': float(g.mean()) if len(g) else 0.0,
    }


def _fmt_gate(g) -> str:
    mark = 'PASS' if g.passed else 'FAIL'
    m = '' if g.metric is None else f'  metric={g.metric:.4f}'
    t = '' if g.threshold is None else f'  thr={g.threshold:.4f}'
    return f'  [{mark}] {g.name}{m}{t}\n         {g.reason}'


def main():
    print('=' * 74)
    print('PART A — ATOMIC ANTI-OVERFIT GATES (research mode, walk-forward 2020-2024)')
    print('         canonical evaluator @ Rs50k; the REAL overfit test')
    print('=' * 74)

    mom_mod = importlib.import_module(MOM_MOD)
    mom_hyper = count_hyperparameters(_find_strategy_class(mom_mod))
    print(f'baseline (momentum book) hyperparameters = {mom_hyper}')

    # Evaluate the low-vol walk-forward ONCE (deterministic).
    result = _evaluate(LOWVOL_MOD)
    ao = result['anti_overfit']
    sp = result['side_panel']
    print(f'\nvalidation Sortino mean = {ao["sortino_val_mean"]:.4f}   '
          f'(folds={result["validation_folds"]}, trades={ao["n_trades"]}, '
          f'aggDD={ao["aggregate_dd"]*100:.1f}%)')
    print(f'per-fold Sortinos: {result["per_fold_sortinos"]}')
    print(f'sub-period Sortinos: '
          f'{[round(x,3) for x in ao["sub_period_sortinos"]]}')
    print(f'pre-tax mean fold return={sp["pre_tax_return_mean"]*100:+.2f}%  '
          f'calmar_mean={sp["calmar_mean"]:.3f}  '
          f'hit_rate={sp["hit_rate_mean"]*100:.1f}%')

    # Bonferroni honesty: apply gates at N=1 (lenient) and N=10 (family cap;
    # honest given the broad factor search this candidate emerged from).
    for n_active in (1, 10):
        gate_run = _gates_from(result, LOWVOL_MOD, mom_hyper, n_active)
        print(f'\n----- atomic gates @ n_active_variants={n_active} -----')
        for g in gate_run.results:
            print(_fmt_gate(g))
        print(f'  >>> ALL ATOMIC GATES (n={n_active}): '
              f'{"PASS" if gate_run.passed else "FAIL"} <<<')

    # Momentum book research metrics for the anchor comparison.
    print('\n----- MOMENTUM book (current strategy) — research metrics -----')
    mres = _evaluate(MOM_MOD)
    mao = mres['anti_overfit']
    print(f'validation Sortino mean = {mao["sortino_val_mean"]:.4f}   '
          f'(folds={mres["validation_folds"]}, trades={mao["n_trades"]}, '
          f'aggDD={mao["aggregate_dd"]*100:.1f}%)')
    print(f'sub-period Sortinos: '
          f'{[round(x,3) for x in mao["sub_period_sortinos"]]}')

    # ── Sealed window ──────────────────────────────────────────────────────
    print('\n' + '=' * 74)
    print('PART B — SEALED WINDOW 2025-01-01 -> 2026-05-14  (vs Nifty50)')
    print('         INFORMATIVE, not a clean OOS proof (window overlaps the')
    print('         FY25/FY26 data seen when low-vol was found). No formal')
    print('         sealed reveal is committed.')
    print('=' * 74)

    nifty = _nifty()
    for cash in (50_000.0, 500_000.0):
        lv = _sealed_score(LOWVOL_MOD, cash)
        mom = _sealed_score(MOM_MOD, cash)
        idx = lv['eq'].index
        s = nifty[(nifty.index >= idx[0]) & (nifty.index <= idx[-1])]
        nifty_ret = float(s.iloc[-1] / s.iloc[0] - 1.0)
        nifty_dd = _maxdd_from_returns(s.pct_change().fillna(0.0))

        # idle-cash floor (6.5%) on each book's un-deployed cash
        lv_idle = (1 - lv['gross'].shift(1).fillna(lv['gross'].iloc[0])).clip(0, 1)
        mom_idle = (1 - mom['gross'].shift(1).fillna(mom['gross'].iloc[0])).clip(0, 1)
        lv_cf = lv['ret'] + lv_idle * CASH_D
        mom_cf = mom['ret'] + mom_idle * CASH_D
        # 50/50 and risk-parity blends of the two cash-floored books
        blend50 = 0.5 * lv_cf + 0.5 * mom_cf
        vlv = lv_cf.rolling(60, min_periods=20).std()
        vm = mom_cf.rolling(60, min_periods=20).std()
        w = (1 / vlv / (1 / vlv + 1 / vm)).shift(1).fillna(0.5).clip(0.05, 0.95)
        blend_rp = w * lv_cf + (1 - w) * mom_cf

        def tot(r):
            return float((1 + r).prod() - 1.0)

        print(f'\n----- @ Rs{int(cash):,} -----')
        print(f'  Nifty50                : {nifty_ret*100:+7.2f}%   '
              f'maxDD {nifty_dd*100:6.1f}%')
        print(f'  LOW-VOL engine (raw)   : {lv["total_return"]*100:+7.2f}%   '
              f'maxDD {lv["max_dd"]*100:6.1f}%   sortino {lv["sortino"]:.3f}   '
              f'avg gross {lv["avg_gross"]*100:.0f}%  trades {lv["trade_count"]}')
        print(f'  LOW-VOL + cash floor   : {tot(lv_cf)*100:+7.2f}%   '
              f'maxDD {_maxdd_from_returns(lv_cf)*100:6.1f}%')
        print(f'  MOMENTUM (raw)         : {mom["total_return"]*100:+7.2f}%   '
              f'maxDD {mom["max_dd"]*100:6.1f}%   sortino {mom["sortino"]:.3f}   '
              f'avg gross {mom["avg_gross"]*100:.0f}%  trades {mom["trade_count"]}')
        print(f'  MOMENTUM + cash floor  : {tot(mom_cf)*100:+7.2f}%   '
              f'maxDD {_maxdd_from_returns(mom_cf)*100:6.1f}%')
        print(f'  BLEND 50/50 (cf)       : {tot(blend50)*100:+7.2f}%   '
              f'maxDD {_maxdd_from_returns(blend50)*100:6.1f}%')
        print(f'  BLEND risk-parity (cf) : {tot(blend_rp)*100:+7.2f}%   '
              f'maxDD {_maxdd_from_returns(blend_rp)*100:6.1f}%')

        # decision-relevant sealed comparison (informational, not committed)
        better = lv['sortino'] > mom['sortino'] and lv['sortino'] > 0
        print(f'  sealed-Sortino check   : low-vol {lv["sortino"]:.3f} '
              f'{">" if better else "<="} momentum {mom["sortino"]:.3f}  '
              f'-> {"low-vol better" if better else "momentum better"}')

    print('\nDONE')


if __name__ == '__main__':
    main()
