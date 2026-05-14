"""Unit tests for `backtest.anti_overfit` gates."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from backtest.anti_overfit import (
    BASELINE_HYPERPARAMS,
    DEFAULT_PARSIMONY_DELTA_SORTINO,
    StrategySummary,
    bonferroni_gate,
    compute_rw_mc_null,
    has_been_revealed,
    parsimony_gate,
    random_walk_mc_gate,
    record_sealed_reveal,
    run_all_gates,
    sealed_test_gate,
    sub_period_stationarity_gate,
)


def _summary(
    *,
    iter_id: str = "iter_test",
    val: float = 1.5,
    pvalue: float = 0.01,
    dd: float = 0.10,
    n_trades: int = 200,
    n_params: int = BASELINE_HYPERPARAMS,
    sub_periods: tuple[float, ...] = (1.4, 1.5, 1.6, 1.5),
    rw_pct: float = 0.98,
) -> StrategySummary:
    return StrategySummary(
        iter_id=iter_id,
        sortino_train_mean=val,
        sortino_val_mean=val,
        sortino_val_pvalue=pvalue,
        aggregate_dd=dd,
        n_trades=n_trades,
        n_hyperparameters=n_params,
        sub_period_sortinos=sub_periods,
        rw_mc_null_pct=rw_pct,
    )


def test_bonferroni_passes_strict() -> None:
    res = bonferroni_gate(_summary(pvalue=0.001), n_active_variants=10, alpha=0.05)
    assert res.passed  # 0.001 < 0.005


def test_bonferroni_rejects_when_correction_binds() -> None:
    res = bonferroni_gate(_summary(pvalue=0.04), n_active_variants=10, alpha=0.05)
    assert not res.passed  # 0.04 >= 0.005


def test_random_walk_mc_passes_at_95th() -> None:
    assert random_walk_mc_gate(_summary(rw_pct=0.95)).passed
    assert random_walk_mc_gate(_summary(rw_pct=0.99)).passed
    assert not random_walk_mc_gate(_summary(rw_pct=0.90)).passed


def test_parsimony_passes_at_baseline_params() -> None:
    res = parsimony_gate(
        _summary(val=1.0, n_params=BASELINE_HYPERPARAMS),
        baseline_sortino=0.9,
    )
    assert res.passed   # 0 excess params, 0 required improvement


def test_parsimony_fails_when_extra_param_not_earning() -> None:
    res = parsimony_gate(
        _summary(val=0.95, n_params=BASELINE_HYPERPARAMS + 1),
        baseline_sortino=0.90,
    )
    # 1 excess param requires +0.10 Sortino; actual improvement 0.05 → fail
    assert not res.passed


def test_parsimony_passes_when_extra_params_pay() -> None:
    res = parsimony_gate(
        _summary(val=1.15, n_params=BASELINE_HYPERPARAMS + 1),
        baseline_sortino=0.90,
    )
    # 1 excess param requires +0.10; actual +0.25 → pass
    assert res.passed


def test_sub_period_stationarity_passes_when_stable() -> None:
    res = sub_period_stationarity_gate(
        _summary(sub_periods=(1.0, 1.1, 0.9, 1.05))
    )
    assert res.passed   # min/max = 0.9/1.1 ≈ 0.82 > 0.30


def test_sub_period_stationarity_fails_on_regime_dependence() -> None:
    res = sub_period_stationarity_gate(
        _summary(sub_periods=(2.0, 0.4, 2.1, 1.9))
    )
    assert not res.passed   # 0.4/2.1 ≈ 0.19 < 0.30


def test_sealed_reveal_records_and_blocks_retry(tmp_path: Path) -> None:
    log = tmp_path / "sealed_reveals.csv"
    iter_id = "iter_abc"
    res = sealed_test_gate(iter_id, sealed_sortino=1.0, baseline_sortino=0.5, log_path=log)
    assert res.passed
    assert has_been_revealed(iter_id, log)
    # Second call must raise
    with pytest.raises(RuntimeError):
        sealed_test_gate(iter_id, sealed_sortino=0.8, baseline_sortino=0.5, log_path=log)


def test_sealed_reveal_log_rows_have_decision(tmp_path: Path) -> None:
    log = tmp_path / "sealed_reveals.csv"
    sealed_test_gate("iter_x", 1.5, 1.0, log_path=log)
    sealed_test_gate("iter_y", 0.3, 1.0, log_path=log)
    rows = list(csv.DictReader(log.open()))
    assert {r["iter_id"] for r in rows} == {"iter_x", "iter_y"}
    decisions = {r["iter_id"]: r["decision"] for r in rows}
    assert decisions["iter_x"] == "KEEP"
    assert decisions["iter_y"] == "REVERT"


def test_run_all_gates_short_circuits_sealed_on_failure(tmp_path: Path) -> None:
    log = tmp_path / "sealed_reveals.csv"
    # rw_pct < 0.95 → random-walk gate fails → sealed reveal should NOT be attempted
    summary = _summary(iter_id="iter_blocked", rw_pct=0.50)
    run = run_all_gates(
        summary,
        baseline_sortino=0.5,
        n_active_variants=5,
        sealed_sortino=1.0,
        sealed_log_path=log,
    )
    assert not run.passed
    assert not has_been_revealed("iter_blocked", log)


def test_compute_rw_mc_null_returns_pct_in_unit_interval() -> None:
    rng = np.random.default_rng(42)
    returns = rng.standard_normal(252)
    def sortino_fn(rs):
        downside = rs[rs < 0]
        if downside.size == 0:
            return float("inf")
        return float(rs.mean() / (downside.std() + 1e-9))

    pct, rw = compute_rw_mc_null(returns, sortino_fn, n_permutations=200, rng=rng)
    assert 0.0 <= pct <= 1.0
    assert rw.shape == (200,)
