"""Regression tests for audit-2026-05-15 #1 (anti-overfit gates actually
enforced) + #8 (universe-respect hard gate). Before this, run_all_gates was
dead code never called by the loop."""
from datetime import date

import pandas as pd
import pytest

import prepare
from backtest.anti_overfit import (
    StrategySummary,
    run_all_gates,
    universe_respect_gate,
)
from scripts.loop import evaluate_anti_overfit_gates
from strategy import IndiaMomentumQualityRegime


def _summary(**kw) -> StrategySummary:
    base = dict(
        iter_id="iter_test",
        sortino_train_mean=1.2,
        sortino_val_mean=1.2,
        sortino_val_pvalue=0.001,
        aggregate_dd=0.15,
        n_trades=120,
        n_hyperparameters=8,
        sub_period_sortinos=(1.1, 1.0, 1.2),
        rw_mc_null_pct=0.99,
        universe_respected=True,
    )
    base.update(kw)
    return StrategySummary(**base)


# ── #8 universe-respect gate ────────────────────────────────────────────
def test_universe_respect_gate_pass_fail():
    assert universe_respect_gate(_summary(universe_respected=True)).passed
    g = universe_respect_gate(_summary(universe_respected=False))
    assert not g.passed and "survivorship" in g.reason


def test_run_all_gates_hard_rejects_universe_violation():
    gr = run_all_gates(
        _summary(universe_respected=False), baseline_sortino=0.0,
        n_active_variants=1, baseline_hyperparams=8, skip_sealed=True,
    )
    assert not gr.passed
    assert any(
        r.name == "universe_respect" and not r.passed for r in gr.results
    )


def test_run_all_gates_passes_clean_variant():
    gr = run_all_gates(
        _summary(), baseline_sortino=0.0, n_active_variants=1,
        baseline_hyperparams=8, skip_sealed=True,
    )
    assert gr.passed, [(_.name, _.reason) for _ in gr.results if not _.passed]
    # Sealed reveal must NOT run in the loop path.
    assert all(r.name != "sealed_test" for r in gr.results)


def test_bonferroni_tightens_with_more_variants():
    # Same p-value, many variants → Bonferroni should fail.
    gr = run_all_gates(
        _summary(sortino_val_pvalue=0.02), baseline_sortino=0.0,
        n_active_variants=50, baseline_hyperparams=8, skip_sealed=True,
    )
    assert not gr.passed


# ── prepare.py pure helpers feeding the gates ───────────────────────────
def test_count_hyperparameters_excludes_plumbing():
    n = prepare.count_hyperparameters(IndiaMomentumQualityRegime)
    # Signal knobs after quality_pct removal (2026-05-15): lookback, skip,
    # retention, regime_pct, fii_threshold_cr, n_positions, sector_cap = 7.
    # Excludes db paths / weekday / parity / enforce_sector_cap /
    # universe_by_date.
    assert n == 7


def test_universe_respected_tolerates_decision_vs_fill_lag(monkeypatch):
    """A name in the universe at the DECISION bar but rotated out of the
    snapshot active at the FILL date (entry_date) must NOT be flagged — the
    order was legitimately decided when the name was a member (observed:
    FACT decided 2023-09-29, filled 2023-10-03). A name absent from BOTH
    the fill and decision snapshots IS a real violation."""
    snaps = [date(2023, 9, 1), date(2023, 10, 1)]
    monkeypatch.setattr(prepare, "snapshot_dates", lambda: snaps)
    monkeypatch.setattr(
        prepare, "get_universe_at",
        lambda d: ["FACT", "AAA"] if d == date(2023, 9, 1) else ["AAA"],
    )
    # Decided 2023-09-29 (Sep snapshot, FACT in), filled 2023-10-03.
    lagged = pd.DataFrame(
        {"ticker": ["FACT"], "entry_date": [date(2023, 10, 3)]}
    )
    assert prepare._universe_respected(lagged) is True
    # Genuinely off-universe: not in Sep or Oct snapshot.
    bogus = pd.DataFrame(
        {"ticker": ["ZZZ"], "entry_date": [date(2023, 10, 3)]}
    )
    assert prepare._universe_respected(bogus) is False


def test_universe_respected_detects_off_universe_trade(monkeypatch):
    monkeypatch.setattr(prepare, "snapshot_dates",
                        lambda: [date(2023, 1, 1)])
    monkeypatch.setattr(prepare, "get_universe_at",
                        lambda d: ["AAA", "BBB"])
    ok = pd.DataFrame({"ticker": ["AAA"], "entry_date": [date(2023, 6, 1)]})
    bad = pd.DataFrame({"ticker": ["ZZZ"], "entry_date": [date(2023, 6, 1)]})
    before = pd.DataFrame({"ticker": ["AAA"], "entry_date": [date(2022, 1, 1)]})
    assert prepare._universe_respected(ok) is True
    assert prepare._universe_respected(bad) is False
    assert prepare._universe_respected(before) is False  # pre-any-snapshot
    assert prepare._universe_respected(pd.DataFrame()) is True


def test_sub_period_sortinos_buckets_by_18m():
    vs = [date(2022, 1, 1), date(2022, 6, 1), date(2023, 9, 1), date(2024, 1, 1)]
    sorts = [1.0, 2.0, 4.0, None]
    out = prepare._sub_period_sortinos(vs, sorts, months=18)
    # bucket0 = Jan+Jun 2022 → mean(1,2)=1.5 ; bucket1 = Sep-2023 → 4.0
    assert out == (1.5, 4.0)


# ── loop integration: gates actually gate KEEP ──────────────────────────
def _metrics(**ao):
    base = dict(
        sortino_val_mean=1.2, sortino_val_pvalue=0.001, rw_mc_null_pct=0.99,
        sub_period_sortinos=[1.0, 1.1], n_hyperparameters=8, n_trades=100,
        aggregate_dd=0.15, universe_respected=True,
    )
    base.update(ao)
    return {"anti_overfit": base}


def test_loop_gate_helper_blocks_overfit_variant():
    gr, reason = evaluate_anti_overfit_gates(
        _metrics(sortino_val_pvalue=0.9, rw_mc_null_pct=0.10),
        iter_id="i1", baseline_sortino=0.0, n_active_variants=1,
        baseline_hyperparams=8,
    )
    assert not gr.passed
    assert "anti-overfit FAILED" in reason


def test_loop_gate_helper_passes_clean_variant():
    gr, reason = evaluate_anti_overfit_gates(
        _metrics(), iter_id="i2", baseline_sortino=0.0,
        n_active_variants=1, baseline_hyperparams=8,
    )
    assert gr.passed and reason == "anti-overfit gates passed"


def test_loop_gate_helper_blocks_universe_violation():
    gr, reason = evaluate_anti_overfit_gates(
        _metrics(universe_respected=False),
        iter_id="i3", baseline_sortino=0.0, n_active_variants=1,
        baseline_hyperparams=8,
    )
    assert not gr.passed and "universe_respect" in reason
