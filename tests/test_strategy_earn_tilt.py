"""Phase B earnings-confirmed concentration tilt — executable contract,
SKIPPED.

Phase B (categorical, parameter-free reorder of momentum's own selection
by PIT-SUE sign) was implemented and evaluated on `prepare.py research`
vs an identical tilt-off control (journal 2026-05-18). REVERTED: it is
fold-dependent on the only testable data — the 4 active 2024 folds were
+0.41 / −0.09 / −2.94 / +1.32 (one catastrophic), validation Sortino
−0.10, worst sub-period 2.32→1.995, ZERO drawdown benefit. With both the
*suppression* (Phase A) and *concentration* (Phase B) forms now failing
the same way, the binding constraint is data sufficiency: only ~3
independent testable PIT-earnings folds exist (2022+ NSE horizon +
8-quarter SUE burn-in, data ending 2025-02). No earnings overlay can be
shown *generic / non-overfit* on 3 folds; iterating more forms on them
would BE the overfit.

Skipped (not deleted — CLAUDE.md "don't pre-emptively delete"): this is
the contract to re-enable once a materially LONGER PIT fundamentals
history exists (forward + backward backfill → enough independent
earnings cycles for a real walk-forward + one sealed reveal). The
robust-SUE estimator + pipeline remain KEPT as infra.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Phase B tilt REVERTED (fold-dependent, fails robustness gate, "
    "no drawdown benefit) — see journal 2026-05-18. Root cause = only ~3 "
    "testable PIT-earnings folds; needs longer history before any earnings "
    "overlay can be validated as generic. Pipeline + robust SUE kept."
)

from prepare import count_hyperparameters  # noqa: E402
from strategy import IndiaMomentumQualityCarry  # noqa: E402


def test_parsimony_count_unchanged() -> None:
    # When re-enabled, the categorical tilt must add only bool/str
    # plumbing → tunable count stays 6 (no fitted knob — by design).
    assert count_hyperparameters(IndiaMomentumQualityCarry) == 6


def test_tilt_params_are_plumbing() -> None:
    p = dict(IndiaMomentumQualityCarry.params._getitems())
    assert p["enable_earn_tilt"] is True
    assert isinstance(p["earnings_db_path"], str)
    assert isinstance(p["fundamentals_db_path"], str)
