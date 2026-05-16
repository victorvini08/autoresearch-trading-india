"""Anti-overfit gates for the autoresearch loop's KEEP/REVERT decisions.

These gates sit alongside the catastrophe-validator (`backtest.risk`) and the
walk-forward Sortino logic in `prepare.py`. The catastrophe validator catches
blow-ups; the gates here catch the subtler failure of strategies that look
good on the validation period purely because the loop explored a lot of
variants and the noise threshold was crossed.

Each gate accepts (compact) summary statistics from a walk-forward run and
returns a `GateResult` flagging pass/fail with a structured reason. Callers
(typically `scripts.loop` and `prepare.py`) compose multiple gates; a variant
is KEPT only if every gate passes.

Five gates implemented here:

  1. **Sealed-test reveal**  — gating a "promotion" event: reveal the strategy
     against the 2024-01..2026-05 sealed window EXACTLY ONCE per variant.
  2. **Bonferroni p-value**  — significance threshold adjusted by the count of
     variants attempted in the active campaign.
  3. **Random-walk Monte Carlo**  — sortino must beat the 95th-pct of bar-
     permuted returns under the same backtest structure.
  4. **Parameter parsimony budget**  — each new hyperparameter beyond the
     baseline must improve Sortino by ≥ 0.10 AND clear Bonferroni.
  5. **Sub-period stationarity**  — Sortino on disjoint 18-month sub-periods
     must not vary by more than a factor of (1 / 0.3).

Cost-aware Sortino: the gates assume the Sortino values they receive are
*net of full Dhan delivery costs* (DP charge included). The walk-forward
caller is responsible for computing both gross and net; promotion always
uses net.
"""

from __future__ import annotations

import csv
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    metric: float | None = None
    threshold: float | None = None
    reason: str = ""

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class StrategySummary:
    """Compact stats from a walk-forward run that the gates consume."""

    iter_id: str                       # e.g. 'iter_0042'
    sortino_train_mean: float
    sortino_val_mean: float
    sortino_val_pvalue: float          # vs random reshuffle on val window
    aggregate_dd: float                # absolute, in pct
    n_trades: int
    n_hyperparameters: int             # count of tunable params in strategy.py
    sub_period_sortinos: tuple[float, ...]   # disjoint 18m sub-period Sortinos
    rw_mc_null_pct: float              # percentile of strategy Sortino vs RW null
    # Audit-2026-05-15 #8: every traded ticker was in the point-in-time
    # universe on its entry date (computed in the immutable evaluator from
    # the trade log). False ⇒ the variant ignored the injected universe and
    # silently reintroduced survivorship — a hard structural reject.
    universe_respected: bool = True


# ──────────────────────────────────────────────────────────────────────
# Sealed-test mechanism
# ──────────────────────────────────────────────────────────────────────


SEALED_REVEAL_LOG = Path("iterations/sealed_reveals.csv")
SEALED_FIELDS = ("iter_id", "revealed_at", "sealed_sortino", "decision")


def _ensure_sealed_log(path: Path = SEALED_REVEAL_LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=SEALED_FIELDS).writeheader()


def has_been_revealed(iter_id: str, path: Path = SEALED_REVEAL_LOG) -> bool:
    if not path.exists():
        return False
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["iter_id"] == iter_id:
                return True
    return False


def record_sealed_reveal(
    iter_id: str,
    sealed_sortino: float,
    decision: str,
    path: Path = SEALED_REVEAL_LOG,
) -> None:
    _ensure_sealed_log(path)
    with path.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=SEALED_FIELDS).writerow(
            {
                "iter_id": iter_id,
                "revealed_at": datetime.utcnow().isoformat(timespec="seconds"),
                "sealed_sortino": f"{sealed_sortino:.6f}",
                "decision": decision,
            }
        )


def sealed_test_gate(
    iter_id: str,
    sealed_sortino: float,
    baseline_sortino: float,
    *,
    log_path: Path = SEALED_REVEAL_LOG,
) -> GateResult:
    """Reveal the sealed test ONCE per iter_id; pass if Sortino > baseline AND > 0.

    Calling this function commits the reveal — subsequent calls for the same
    iter_id raise. This enforces the "sealed reveal is final" invariant.
    """
    if has_been_revealed(iter_id, log_path):
        raise RuntimeError(
            f"sealed test for {iter_id} has already been revealed (no retries)"
        )
    passed = sealed_sortino > baseline_sortino and sealed_sortino > 0.0
    record_sealed_reveal(
        iter_id, sealed_sortino, "KEEP" if passed else "REVERT", log_path
    )
    return GateResult(
        name="sealed_test",
        passed=passed,
        metric=sealed_sortino,
        threshold=baseline_sortino,
        reason=(
            "sealed Sortino exceeds baseline AND > 0"
            if passed
            else f"sealed Sortino {sealed_sortino:.3f} <= baseline {baseline_sortino:.3f}"
        ),
    )


# ──────────────────────────────────────────────────────────────────────
# Bonferroni p-value gate
# ──────────────────────────────────────────────────────────────────────


def bonferroni_gate(
    summary: StrategySummary,
    n_active_variants: int,
    *,
    alpha: float = 0.05,
) -> GateResult:
    """Pass if val-Sortino p-value < alpha / N_active_variants."""
    if n_active_variants < 1:
        n_active_variants = 1
    threshold = alpha / n_active_variants
    passed = summary.sortino_val_pvalue < threshold
    return GateResult(
        name="bonferroni",
        passed=passed,
        metric=summary.sortino_val_pvalue,
        threshold=threshold,
        reason=(
            "p < alpha / N"
            if passed
            else f"p={summary.sortino_val_pvalue:.4f} >= alpha/N={threshold:.4f}"
        ),
    )


# ──────────────────────────────────────────────────────────────────────
# Random-walk Monte Carlo gate
# ──────────────────────────────────────────────────────────────────────


def random_walk_mc_gate(summary: StrategySummary) -> GateResult:
    """Pass if strategy Sortino exceeds the 95th pct of RW-null Sortinos.

    The percentile is precomputed by the caller (it requires running the
    strategy against many permutations of universe returns — expensive but
    one-time per variant). The gate here just checks the comparison.
    """
    passed = summary.rw_mc_null_pct >= 0.95
    return GateResult(
        name="random_walk_mc",
        passed=passed,
        metric=summary.rw_mc_null_pct,
        threshold=0.95,
        reason=(
            "strategy beats 95th pct of RW null"
            if passed
            else f"only {summary.rw_mc_null_pct:.2%} percentile vs RW null"
        ),
    )


def compute_rw_mc_null(
    daily_returns: np.ndarray,
    sortino_fn,
    *,
    n_permutations: int = 5000,
    rng: np.random.Generator | None = None,
) -> tuple[float, np.ndarray]:
    """Return (strategy_pct_rank, null_sortinos).

    `daily_returns` is an array of strategy daily returns (after costs).
    `sortino_fn` maps an array of daily returns → scalar Sortino.

    Builds a NO-EDGE Monte-Carlo null: demean the returns (strip the
    strategy's drift) then IID-bootstrap resample. The null preserves the
    strategy's OWN volatility / downside shape but has ~zero edge, so its
    Sortinos scatter around 0. A genuine positive risk-adjusted edge lands
    far in the upper tail (pct → 1, permutation p → tiny); pure noise lands
    mid-distribution and correctly fails the gate. `pct` = fraction of null
    Sortinos ≤ the observed Sortino.

    BUGFIX 2026-05-16: the previous implementation permuted the daily ORDER
    of the returns and recomputed Sortino — but Sortino depends only on the
    multiset of returns (mean / downside-std), so it is exactly
    order-invariant. Every "null" draw equalled the original Sortino to
    within ~1e-12 float-summation round-off, making `pct` and the Bonferroni
    `sortino_val_pvalue` pure tie-noise unrelated to strategy quality. That
    silently failed ~every variant across every experiment (the gate could
    not be passed because it tested nothing). Verified: 2000 order-perms of
    a fixed series → std 0.0, 1 unique Sortino.
    """
    if rng is None:
        rng = np.random.default_rng()
    if daily_returns.size < 2:
        return 0.0, np.zeros(n_permutations)
    orig = float(sortino_fn(daily_returns))
    centered = daily_returns - float(np.mean(daily_returns))
    n = centered.size
    rw = np.empty(n_permutations, dtype=np.float64)
    for i in range(n_permutations):
        sample = rng.choice(centered, size=n, replace=True)
        rw[i] = float(sortino_fn(sample))
    pct = float(np.mean(rw <= orig))
    return pct, rw


# ──────────────────────────────────────────────────────────────────────
# Parsimony budget gate
# ──────────────────────────────────────────────────────────────────────


BASELINE_HYPERPARAMS = 5
DEFAULT_PARSIMONY_DELTA_SORTINO = 0.10


def parsimony_gate(
    summary: StrategySummary,
    baseline_sortino: float,
    *,
    baseline_hyperparams: int = BASELINE_HYPERPARAMS,
    delta_per_param: float = DEFAULT_PARSIMONY_DELTA_SORTINO,
) -> GateResult:
    """Each parameter beyond baseline must pay for itself with ≥ delta_per_param
    Sortino improvement.

    Required improvement = (n_hyperparameters - baseline) * delta_per_param.
    Strategies at baseline param count or fewer always pass (no penalty).
    """
    excess = max(0, summary.n_hyperparameters - baseline_hyperparams)
    required = excess * delta_per_param
    actual_improvement = summary.sortino_val_mean - baseline_sortino
    passed = actual_improvement >= required
    return GateResult(
        name="parsimony",
        passed=passed,
        metric=actual_improvement,
        threshold=required,
        reason=(
            f"baseline params={baseline_hyperparams}, strategy={summary.n_hyperparameters}"
            f"; needs Sortino +{required:.2f}, has +{actual_improvement:.2f}"
        ),
    )


# ──────────────────────────────────────────────────────────────────────
# Sub-period stationarity gate
# ──────────────────────────────────────────────────────────────────────


DEFAULT_MIN_RATIO = 0.30


def sub_period_stationarity_gate(
    summary: StrategySummary,
    *,
    min_ratio: float = DEFAULT_MIN_RATIO,
) -> GateResult:
    """Pass if min(|Sortino_i|) / max(|Sortino_i|) >= min_ratio across sub-periods.

    Detects strategies that work in one regime only. Sortinos near zero are
    floored at 1e-3 to avoid divide-by-zero (a strategy with Sortino ~0
    everywhere will trivially "pass" with ratio 1.0, but the Bonferroni gate
    will already have rejected it).
    """
    sorts = summary.sub_period_sortinos
    if len(sorts) < 2:
        return GateResult(
            name="sub_period_stationarity",
            passed=True,
            metric=None,
            threshold=min_ratio,
            reason="too few sub-periods to evaluate; passing by default",
        )
    abs_sorts = [max(abs(s), 1e-3) for s in sorts]
    ratio = min(abs_sorts) / max(abs_sorts)
    passed = ratio >= min_ratio
    return GateResult(
        name="sub_period_stationarity",
        passed=passed,
        metric=ratio,
        threshold=min_ratio,
        reason=f"min/max ratio of |Sortino| across {len(sorts)} sub-periods = {ratio:.2f}",
    )


# ──────────────────────────────────────────────────────────────────────
# Universe-respect gate (audit 2026-05-15 #8)
# ──────────────────────────────────────────────────────────────────────


def universe_respect_gate(summary: StrategySummary) -> GateResult:
    """Hard structural reject if the variant traded any ticker that was NOT
    in the point-in-time universe on its entry date.

    The loop edits strategy.py freely, including the Fix-B PIT-universe
    guard. This gate enforces the invariant from the IMMUTABLE side using
    the trade log, so a variant that drops the guard and reintroduces
    survivorship is rejected no matter how its code is written."""
    passed = bool(summary.universe_respected)
    return GateResult(
        name="universe_respect",
        passed=passed,
        metric=None,
        threshold=None,
        reason=(
            "all trades within the point-in-time universe"
            if passed
            else "variant traded tickers outside the point-in-time universe "
                 "— survivorship/look-ahead reintroduced (hard reject)"
        ),
    )


# ──────────────────────────────────────────────────────────────────────
# Composite gate runner
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateRun:
    iter_id: str
    results: tuple[GateResult, ...]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_dict(self) -> dict:
        return {
            "iter_id": self.iter_id,
            "passed": self.passed,
            "gates": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "metric": r.metric,
                    "threshold": r.threshold,
                    "reason": r.reason,
                }
                for r in self.results
            ],
        }


def run_all_gates(
    summary: StrategySummary,
    baseline_sortino: float,
    n_active_variants: int,
    *,
    baseline_hyperparams: int = BASELINE_HYPERPARAMS,
    skip_sealed: bool = False,
    sealed_sortino: float | None = None,
    sealed_log_path: Path = SEALED_REVEAL_LOG,
) -> GateRun:
    """Run all non-sealed gates. If `skip_sealed` is False AND
    `sealed_sortino` is provided, run the sealed reveal as the final gate
    (which mutates `sealed_reveals.csv`).

    `baseline_hyperparams` lets the caller pass the param count of the
    CURRENT committed strategy so parsimony penalises only knobs ADDED
    during the campaign (the principled reading of "beyond the baseline"),
    rather than an absolute constant.

    Order: structural integrity first (universe-respect — cheapest, hardest),
    then statistical gates, sealed reveal last (it commits a one-shot record).
    """
    gates = [
        universe_respect_gate(summary),
        bonferroni_gate(summary, n_active_variants),
        random_walk_mc_gate(summary),
        parsimony_gate(
            summary, baseline_sortino,
            baseline_hyperparams=baseline_hyperparams,
        ),
        sub_period_stationarity_gate(summary),
    ]
    if not skip_sealed and sealed_sortino is not None:
        # Only attempt sealed reveal if the cheaper gates passed
        if all(g.passed for g in gates):
            gates.append(
                sealed_test_gate(
                    summary.iter_id,
                    sealed_sortino,
                    baseline_sortino,
                    log_path=sealed_log_path,
                )
            )
        else:
            gates.append(
                GateResult(
                    name="sealed_test",
                    passed=False,
                    reason="cheaper gates failed; sealed reveal not attempted",
                )
            )
    return GateRun(iter_id=summary.iter_id, results=tuple(gates))


__all__ = [
    "GateResult",
    "GateRun",
    "StrategySummary",
    "BASELINE_HYPERPARAMS",
    "DEFAULT_PARSIMONY_DELTA_SORTINO",
    "DEFAULT_MIN_RATIO",
    "SEALED_REVEAL_LOG",
    "has_been_revealed",
    "record_sealed_reveal",
    "sealed_test_gate",
    "bonferroni_gate",
    "random_walk_mc_gate",
    "compute_rw_mc_null",
    "parsimony_gate",
    "sub_period_stationarity_gate",
    "universe_respect_gate",
    "run_all_gates",
]
