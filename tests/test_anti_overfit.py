"""Unit tests for `backtest.anti_overfit` gates."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backtest.anti_overfit import (
    BASELINE_HYPERPARAMS,
    DEFAULT_PARSIMONY_DELTA_SORTINO,
    RW_MC_PERMUTATIONS,
    StrategySummary,
    _sortino_rows,
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
from backtest.metrics import sortino as _scalar_sortino


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


def test_random_walk_mc_threshold_is_90th_pct() -> None:
    # Loosened 0.95→0.90 (2026-05-16) so real-but-noisy edges can clear.
    assert random_walk_mc_gate(_summary(rw_pct=0.90)).passed
    assert random_walk_mc_gate(_summary(rw_pct=0.99)).passed
    assert not random_walk_mc_gate(_summary(rw_pct=0.89)).passed
    assert not random_walk_mc_gate(_summary(rw_pct=0.50)).passed


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


# ── Regression tests for the 2026-05-16 root-cause fixes ──────────────────


def test_compute_rw_mc_null_is_non_degenerate() -> None:
    """Guards the 2026-05-16 RW-MC bugfix. The OLD null permuted return ORDER
    and Sortino is order-invariant, so every draw equalled the original →
    zero-variance null → Bonferroni p was pure tie-noise and ~every variant
    failed. The fixed null demeans + bootstraps, so it MUST have real spread
    and not collapse onto the observed Sortino."""
    rng = np.random.default_rng(7)

    def sortino_fn(rs):
        downside = rs[rs < 0]
        if downside.size == 0:
            return float("inf")
        return float(rs.mean() / (downside.std() + 1e-9))

    # Non-degeneracy: a no-edge (zero-mean) series — the null must have real
    # spread and must NOT collapse onto the observed Sortino (the old
    # order-permutation bug produced zero variance here).
    flat = rng.standard_normal(252)
    flat_orig = sortino_fn(flat)
    _, rw = compute_rw_mc_null(flat, sortino_fn, n_permutations=2000, rng=rng)
    assert np.std(rw) > 1e-3                       # non-degenerate spread
    assert len(np.unique(np.round(rw, 6))) > 100   # not all the same value
    assert np.mean(np.isclose(rw, flat_orig)) < 0.05  # null ≠ observed

    # Discriminating power: a genuinely strong edge must land in the tail.
    strong = 0.3 + 0.2 * rng.standard_normal(252)
    strong_pct, _ = compute_rw_mc_null(
        strong, sortino_fn, n_permutations=2000, rng=rng
    )
    assert strong_pct > 0.90


def test_parsimony_no_added_params_passes_even_when_not_improving() -> None:
    """Double-jeopardy fix: with NO added hyperparameters parsimony is N/A and
    must pass unconditionally — even if Sortino fell below baseline. The
    strict-improvement check lives solely in scripts/loop.py now; parsimony
    must not also reject the same variant for the same reason."""
    res = parsimony_gate(
        _summary(val=1.40, n_params=BASELINE_HYPERPARAMS),
        baseline_sortino=2.17,   # variant is WORSE than baseline
    )
    assert res.passed
    assert "no added hyperparameters" in res.reason


def test_sub_period_stationarity_sign_flip_fails() -> None:
    """A profitable sub-period and a LOSING one is the strongest evidence of
    regime-fit. The old abs() logic scored (1.5, -1.5, 1.4) as ratio
    1.4/1.5≈0.93 and PASSED — backwards. Signed logic must FAIL it."""
    res = sub_period_stationarity_gate(_summary(sub_periods=(1.5, -1.5, 1.4)))
    assert not res.passed
    assert res.metric is not None and res.metric <= 0.0


def test_sub_period_stationarity_lenient_floor_is_0_20() -> None:
    """Loosened 0.30→0.20. A 1.0/0.22/1.0 spread (ratio 0.22) now PASSES
    where it failed under the old 0.30 floor — real edges have off-years."""
    res = sub_period_stationarity_gate(_summary(sub_periods=(1.0, 0.22, 1.0)))
    assert res.passed
    assert abs(res.metric - 0.22) < 1e-6


def test_bonferroni_default_alpha_is_0_10() -> None:
    """Default alpha relaxed 0.05→0.10. p=0.009 at N=10 → threshold 0.010
    PASSES now; it would have failed at the old 0.05/10=0.005."""
    res = bonferroni_gate(_summary(pvalue=0.009), n_active_variants=10)
    assert res.passed


# ── Regression: vectorized RW-MC (2026-05-16 speedup) ────────────────────


def test_sortino_rows_matches_scalar_sortino_exactly() -> None:
    """The vectorized per-row Sortino MUST equal backtest.metrics.sortino for
    every row, including the edge cases the scalar function special-cases:
    no negative returns (+inf / 0.0), exactly one negative (std ddof=1 → NaN
    → treated as 0 → floored), and normal rows."""
    rng = np.random.default_rng(123)
    rows = [
        rng.standard_normal(64),               # normal
        np.abs(rng.standard_normal(64)) + 0.1,  # no downside, mean>0 → +inf
        -np.abs(rng.standard_normal(64)),       # all negative
        np.r_[np.full(63, 0.01), -0.02],        # exactly ONE negative
        np.r_[np.full(62, 0.01), -0.02, -0.03],  # exactly TWO negatives
        np.zeros(64),                           # all zero → no downside, mean 0
        rng.standard_normal(64) * 5.0,          # high variance
    ]
    M = np.vstack(rows)
    vec = _sortino_rows(M)
    for i, r in enumerate(rows):
        scal = _scalar_sortino(pd.Series(r))
        v = vec[i]
        if np.isinf(scal) or np.isinf(v):
            assert np.isinf(scal) and np.isinf(v) and np.sign(scal) == np.sign(v), (
                f"row {i}: inf mismatch scalar={scal} vec={v}"
            )
        else:
            assert np.isclose(v, scal, rtol=1e-9, atol=1e-12), (
                f"row {i}: scalar={scal} vec={v}"
            )


def test_compute_rw_mc_null_default_is_2000_permutations() -> None:
    rng = np.random.default_rng(1)
    returns = rng.standard_normal(256) + 0.05
    _, rw = compute_rw_mc_null(returns, rng=rng)
    assert RW_MC_PERMUTATIONS == 2000
    assert rw.shape == (2000,)


def test_compute_rw_mc_null_still_discriminates_after_vectorization() -> None:
    """End-to-end: a strong edge lands in the upper tail, pure noise does
    not — the vectorized path preserves the gate's discriminating power."""
    rng = np.random.default_rng(9)
    strong = 0.3 + 0.2 * rng.standard_normal(256)
    strong_pct, rw = compute_rw_mc_null(strong, n_permutations=2000, rng=rng)
    assert strong_pct > 0.90
    assert np.std(rw) > 1e-3                       # non-degenerate
    assert len(np.unique(np.round(rw, 6))) > 100

    flat = rng.standard_normal(256)
    flat_pct, _ = compute_rw_mc_null(flat, n_permutations=2000, rng=rng)
    assert flat_pct < strong_pct
