"""Strategy B (branch mean-reversion-quant-strategy) — unit tests for the
long-only residual mean-reversion stat-arb signal core.

The signal math is extracted into pure functions (no backtrader scaffold)
so the bug-prone parts — rolling OLS, factor construction, residual
z-scoring direction — are unit-testable in isolation, mirroring how
`resolve_active_universe` was extracted for the momentum strategy.

Design: docs/superpowers/specs/2026-05-15-strategy-b-residual-reversal-statarb-design.md
"""
from pathlib import Path

import numpy as np
import pytest

from strategy import (
    market_factor,
    ols_beta,
    reversion_scores,
    smb_factor,
)

ROOT = Path(__file__).parent.parent


# ── ols_beta: closed-form least squares with intercept ──────────────────


def test_ols_beta_recovers_known_coefficients():
    rng = np.random.RandomState(0)
    f1 = rng.randn(50).tolist()
    f2 = rng.randn(50).tolist()
    # y = 2.0 + 3.0*f1 - 1.5*f2 exactly (no noise) → coefficients recovered.
    y = [2.0 + 3.0 * a - 1.5 * b for a, b in zip(f1, f2)]
    coef = ols_beta(y, [f1, f2])
    assert coef is not None
    intercept, b1, b2 = coef
    assert intercept == pytest.approx(2.0, abs=1e-6)
    assert b1 == pytest.approx(3.0, abs=1e-6)
    assert b2 == pytest.approx(-1.5, abs=1e-6)


def test_ols_beta_none_when_fewer_rows_than_params():
    # 2 rows, 3 params (intercept + 2 factors) → underdetermined → None.
    assert ols_beta([0.1, 0.2], [[1.0, 2.0], [3.0, 4.0]]) is None


def test_ols_beta_collinear_factor_still_yields_in_span_fit():
    """A constant factor is collinear with the intercept: the coefficients
    are not unique, but the FITTED values (hence the residuals — the actual
    signal) still are. ols_beta must return a least-norm solution, not None
    — otherwise the strategy goes inert whenever a factor has near-zero
    variance (a real low-dispersion regime), which the warmup regression
    test caught."""
    const = [1.0] * 5
    varying = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [0.1 + 0.05 * v for v in varying]  # exactly affine in `varying`
    coef = ols_beta(y, [const, varying])
    assert coef is not None
    intercept, b_const, b_var = coef
    fitted = [
        intercept + b_const * c + b_var * v
        for c, v in zip(const, varying)
    ]
    np.testing.assert_allclose(fitted, y, atol=1e-9)


# ── market_factor: equal-weight cross-sectional mean per day ────────────


def test_market_factor_is_equal_weight_mean_per_day():
    rbt = {"A": [0.01, 0.02], "B": [0.03, 0.04]}
    assert market_factor(rbt) == pytest.approx([0.02, 0.03])


# ── smb_factor: small-ADV tercile minus large-ADV tercile ───────────────


def test_smb_factor_small_minus_large_by_adv_tercile():
    # A=lowest ADV (small), C=highest ADV (large), B=middle (excluded from
    # the tercile spread). SMB = mean(small) - mean(large).
    rbt = {"A": [0.05, 0.05], "B": [0.03, 0.03], "C": [0.01, 0.01]}
    adv = {"A": 1.0, "B": 2.0, "C": 3.0}
    assert smb_factor(rbt, adv) == pytest.approx([0.04, 0.04])


# ── reversion_scores: direction is the whole ballgame ───────────────────


def test_reversion_scores_ranks_oversold_first_overbought_last():
    """A name with a sharp NEGATIVE idiosyncratic move over the formation
    window (large negative factor residual) is the most oversold → must get
    the HIGHEST score. A symmetric positive-shock name gets the LOWEST.

    The shocked names sit in the MIDDLE ADV band so the SMB tercile factor
    is built from plain names only and cannot absorb their shock — the
    shock stays in the residual, which is the whole point of the signal.
    """
    beta_window, formation_days = 30, 3
    rng = np.random.RandomState(7)
    market = rng.randn(beta_window) * 0.01 + 0.0004
    rbt: dict[str, list[float]] = {}
    adv: dict[str, float] = {}
    for i in range(7):  # plain names, ADV 1..7 → they form the SMB terciles
        beta = 0.8 + 0.05 * i
        idio = rng.randn(beta_window) * 0.003
        rbt[f"P{i}"] = (beta * market + idio).tolist()
        adv[f"P{i}"] = float(i + 1)
    for name, sign, a in (("OVERSOLD", -1.0, 3.5), ("OVERBOUGHT", 1.0, 4.5)):
        r = market + rng.randn(beta_window) * 0.003
        r[-formation_days:] += sign * 0.08  # idiosyncratic, orthogonal shock
        rbt[name] = r.tolist()
        adv[name] = a  # middle ADV band → excluded from both SMB terciles

    scores = reversion_scores(rbt, adv, beta_window, formation_days)

    assert set(scores) == set(rbt)
    ranked = sorted(scores, key=scores.get, reverse=True)
    assert ranked[0] == "OVERSOLD"
    assert ranked[-1] == "OVERBOUGHT"


def test_reversion_scores_omits_insufficient_history():
    beta_window, formation_days = 12, 3
    rng = np.random.RandomState(3)
    market = rng.randn(beta_window) * 0.01
    rbt = {
        "FULL_A": (1.0 * market + rng.randn(beta_window) * 0.002).tolist(),
        "FULL_B": (0.9 * market + rng.randn(beta_window) * 0.002).tolist(),
        "FULL_C": (1.1 * market + rng.randn(beta_window) * 0.002).tolist(),
        "SHORT": market[:5].tolist(),  # < beta_window history → dropped
    }
    adv = {"FULL_A": 1.0, "FULL_B": 2.0, "FULL_C": 3.0, "SHORT": 4.0}
    scores = reversion_scores(rbt, adv, beta_window, formation_days)
    assert "SHORT" not in scores
    assert {"FULL_A", "FULL_B", "FULL_C"} <= set(scores)


# ── trade-contract source guard (repo invariant style) ──────────────────


def test_strategy_uses_order_target_percent_only():
    """scripts.signal_today capture + the program.md contract require every
    position change to go through order_target_percent. A future edit that
    introduces self.buy()/self.close() must fail loudly here."""
    src = (ROOT / "strategy.py").read_text()
    assert "self.buy(" not in src
    assert "self.close(" not in src
    assert "order_target_percent" in src


def test_single_strategy_class_is_residual_reversal():
    import strategy as s
    from prepare import _find_strategy_class, count_hyperparameters

    cls = _find_strategy_class(s)
    assert cls.__name__ == "IndiaResidualReversalStatArb"
    # Parsimony footprint matched to the momentum book (7 counted knobs) so
    # neither autoresearch loop starts with a parsimony-gate advantage.
    assert count_hyperparameters(cls) == 7
