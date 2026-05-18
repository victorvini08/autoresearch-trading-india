"""Improvement H — volatility-targeted gross exposure.

Replaces the crude 4-step `breadth_scaled_gross` (now the dominant risk
control since the sector-wiring bug fix lets gross actually deploy). The
canonical, most-replicated robust momentum overlay (Barroso-Santa-Clara
2015): deploy MORE in calm trends, LESS in high-vol / crash regimes,
targeting a constant ~12% annualised book volatility.

Invariants: long-only & never levered (0 ≤ gross ≤ 0.99); monotonically
DEcreasing in realised market volatility; thin cross-section → safe
neutral fallback.
"""
from __future__ import annotations

import numpy as np
import pytest

from strategy import _ANNUAL_VOL_TARGET, vol_targeted_gross

LB = 252  # vol window = min(126, max(63, 252//2)) = 126
T = 200


def _universe(sigma_daily: float, n: int = 30, seed: int = 0) -> dict:
    """n names sharing a common market factor with daily vol `sigma_daily`
    plus tiny idiosyncratic noise (averages out of the equal-weight mean —
    realistic structure: the function targets MARKET vol)."""
    rng = np.random.default_rng(seed)
    mkt = rng.normal(0.0003, sigma_daily, T)
    cbt = {}
    for i in range(n):
        idio = rng.normal(0.0, sigma_daily * 0.1, T)
        px = 100.0 * np.cumprod(1.0 + mkt + idio)
        cbt[f"N{i}"] = list(px)
    return cbt


def test_bounds_long_only_never_levered():
    for s in (0.002, 0.01, 0.03, 0.06):
        g = vol_targeted_gross(_universe(s), LB)
        assert 0.0 <= g <= 0.99


def test_calm_lowvol_trend_deploys_near_full():
    """~6% annual vol ⇒ 0.12/0.06 ≫ 1 ⇒ clipped to the 0.99 long-only cap
    (calm up-trend ⇒ fully invested ⇒ upside captured)."""
    sigma = 0.06 / np.sqrt(252)            # ~6% annualised
    assert vol_targeted_gross(_universe(sigma), LB) == pytest.approx(0.99)


def test_turbulent_highvol_de_risks_sharply():
    """~48% annual vol ⇒ gross ≈ 0.12/0.48 ≈ 0.25 (principled crash
    de-risking, not a bug)."""
    sigma = 0.48 / np.sqrt(252)
    g = vol_targeted_gross(_universe(sigma), LB)
    assert 0.15 < g < 0.40


def test_monotonic_decreasing_in_realised_vol():
    calm = vol_targeted_gross(_universe(0.30 / np.sqrt(252), seed=1), LB)
    wild = vol_targeted_gross(_universe(0.60 / np.sqrt(252), seed=1), LB)
    assert calm > wild
    assert 0.0 < wild <= calm <= 0.99


def test_thin_cross_section_safe_fallback():
    assert vol_targeted_gross(_universe(0.01, n=10), LB) == 0.75
    assert vol_targeted_gross({}, LB) == 0.75


def test_vol_target_is_a_sane_policy_constant():
    assert 0.05 <= _ANNUAL_VOL_TARGET <= 0.25


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
