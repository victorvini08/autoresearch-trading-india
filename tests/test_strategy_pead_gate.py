"""Phase A PEAD asymmetric suppression — executable contract, SKIPPED.

Phase A was wired into strategy.py and evaluated on the corrected engine
with the robustified SUE signal (journal 2026-05-18). It REVERTED: in
every walk-forward fold where the signal was active (2024-04→2025-02 — the
only span with computable SUE) it was strictly worse (per-fold Sortino
−0.17/−0.91/−0.07), the worst sub-period degraded 2.32→2.03, and it gave
ZERO drawdown benefit (aggregate_dd flat) — failing the
robustness-over-validation-Sortino gate. The PIT pipeline + the SUE
estimator robustification (Hampel/MAD + clip) were KEPT as infrastructure.

Skipped (not deleted — CLAUDE.md "don't pre-emptively delete"): this
remains the contract for a future re-attempt once a LONGER fundamentals
history exists (the 2022+ NSE horizon + 8-quarter SUE burn-in left only
~1yr testable here) or for Phase B's categorical positive tilt.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Phase A REVERTED on the honest engine (fails robustness gate; "
    "strictly worse in all 3 active folds, no drawdown benefit) — see "
    "journal 2026-05-18. Pipeline + SUE robustification retained as infra."
)

from prepare import count_hyperparameters  # noqa: E402
from strategy import IndiaMomentumQualityCarry  # noqa: E402


def test_parsimony_count_unchanged() -> None:
    # When re-wired, PEAD must add only bool/str plumbing → count stays 6.
    assert count_hyperparameters(IndiaMomentumQualityCarry) == 6


def test_pead_params_are_plumbing() -> None:
    p = dict(IndiaMomentumQualityCarry.params._getitems())
    assert p["enable_pead"] is True
    assert isinstance(p["earnings_db_path"], str)
    assert isinstance(p["fundamentals_db_path"], str)
