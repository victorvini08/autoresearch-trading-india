"""Phase A PEAD suppression — param plumbing & parsimony guard.

DEFERRED: Task 8 (strategy.py integration) is intentionally not yet
implemented (user-deferred — pipeline delivered first, strategy wiring
held for a separate, deliberate step). These assertions are kept as the
executable contract for when Phase A is wired; skipped until then so the
suite stays green.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Task 8 strategy PEAD integration deferred by user; "
    "data pipeline (Tasks 1-7,9,10) is complete and live."
)

from prepare import count_hyperparameters  # noqa: E402
from strategy import IndiaMomentumQualityCarry  # noqa: E402


def test_parsimony_count_unchanged() -> None:
    # PEAD must add only plumbing/bool params → tunable count stays 6.
    assert count_hyperparameters(IndiaMomentumQualityCarry) == 6


def test_pead_params_are_plumbing() -> None:
    p = dict(IndiaMomentumQualityCarry.params._getitems())
    assert p["enable_pead"] is True
    assert isinstance(p["earnings_db_path"], str)
    assert isinstance(p["fundamentals_db_path"], str)
