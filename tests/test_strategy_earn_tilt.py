"""Phase B earnings-confirmed concentration tilt — executable contract,
SKIPPED (DEFINITIVE negative; not data-starved).

After the NSE Integrated-Filing fetch fix (commit 2f65451) the
fundamentals were re-backfilled to 2026-03 and SUE re-materialised
densely across the SEALED window (2025-01..2026-05, 1446+619 rows). The
locked, parameter-free Phase B was then revealed ONCE on that
now-properly-powered sealed set (journal 2026-05-18):

  SEALED OFF→ON: Sortino 0.717→0.776 (+0.06, the only gain) but
  Calmar 0.793→0.497, max_dd 11.26%→11.83%, hit-rate 41.4%→22.6%
  (all WORSE). Research worst sub-period 2.32→2.00.

One metric up while drawdown, Calmar and consistency all degrade, with a
hit-rate collapse — the lumpy-luck / overfit signature, NOT a generic
edge. Both principled earnings overlays (Phase A suppression + Phase B
concentration) are now CONCLUSIVELY shown not to robustly improve the
momentum-quality + vol-targeted book — confirmed out-of-sample on 16
months, not 3 folds. The one-shot sealed reveal for this variant is
spent; do NOT iterate further earnings-overlay variants against it.

Skipped, not deleted (CLAUDE.md): contract retained only as historical
record. KEPT infra (strictly-better, reusable): the robust-SUE estimator
and the Integrated-Filing fetch fix (pipeline is now correct & current).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Phase B tilt REVERTED — DEFINITIVE: one-shot sealed reveal on "
    "the now-SUE-live 2025-01..2026-05 window showed worse Calmar / "
    "drawdown / hit-rate for a marginal Sortino bump (overfit/lumpy "
    "signature). Earnings overlay closed out. See journal 2026-05-18."
)

from prepare import count_hyperparameters  # noqa: E402
from strategy import IndiaMomentumQualityCarry  # noqa: E402


def test_parsimony_count_unchanged() -> None:
    assert count_hyperparameters(IndiaMomentumQualityCarry) == 6


def test_tilt_params_are_plumbing() -> None:
    p = dict(IndiaMomentumQualityCarry.params._getitems())
    assert p["enable_earn_tilt"] is True
    assert isinstance(p["earnings_db_path"], str)
    assert isinstance(p["fundamentals_db_path"], str)
