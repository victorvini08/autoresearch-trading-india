"""Tests for scripts/realworld_shadow.py (Step 5.e) — the shadow book.

A qualified CHALLENGER does NOT go live. It is activated as SHADOW_ACTIVE and
its targets are scored forward on genuinely-new data, head-to-head against the
incumbent, for >=4 rebalance cycles. That forward comparison — not the
in-sample validation Sortino — is what makes it eligible for a manual
promotion. This is the renewable out-of-sample gate that replaces the spent
sealed test.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

import scripts.realworld_shadow as shadow
import scripts.review_schedule as sched
from storage import realworld_db


CURRENT_STRATEGY = "entry_pct = 0.30\n"      # incumbent marker
CANDIDATE_STRATEGY = "entry_pct = 0.25\n"    # challenger marker


def _insert_version(rw_path, snapshot_path, *, status="SHADOW_ACTIVE",
                    created=datetime(2026, 5, 15), activated=datetime(2026, 5, 15)):
    conn = realworld_db.connect(rw_path)
    realworld_db.insert_strategy_version(
        conn, version_hash="v-1", created_at=created, mode="dhan-paper",
        hypothesis_id="rev-1-h0", parent_version_hash=None, unified_diff="d",
        gate_results_json="{}", scale_robustness_json="{}",
        sealed_status="DEFERRED_TO_SHADOW", sealed_metrics_json=None,
        validator_version="v1", journal_excerpt="x",
        snapshot_path=str(snapshot_path), status="CHALLENGER")
    if status == "SHADOW_ACTIVE":
        realworld_db.update_strategy_version_status(
            conn, "v-1", "SHADOW_ACTIVE", updated_at=activated)
    conn.close()


def _score(challenger_sortino, challenger_dd, inc_sortino, inc_dd):
    def fn(text, start, end):
        if "0.25" in text:  # challenger
            return {"test_sortino": challenger_sortino, "test_max_dd": challenger_dd,
                    "test_calmar": 1.0, "test_trade_count": 20}
        return {"test_sortino": inc_sortino, "test_max_dd": inc_dd,
                "test_calmar": 1.0, "test_trade_count": 20}
    return fn


# ── cycle counting ──────────────────────────────────────────────────────────


def test_count_cycles_matches_schedule_and_excludes_start():
    start, end = date(2026, 5, 15), date(2026, 8, 15)
    expected = sum(
        1 for n in range(1, (end - start).days + 1)
        if sched.is_rebalance_signal_date(start + timedelta(days=n)))
    assert shadow.count_rebalance_cycles(start, end) == expected
    assert shadow.count_rebalance_cycles(end, end) == 0


# ── activation ──────────────────────────────────────────────────────────────


def test_activate_shadow_flips_challenger(tmp_path):
    snap = tmp_path / "v-1.py"
    snap.write_text(CANDIDATE_STRATEGY)
    _insert_version(tmp_path / "rw.duckdb", snap, status="CHALLENGER")
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    assert shadow.activate_shadow(conn, "v-1", now=datetime(2026, 6, 1)) is True
    assert realworld_db.get_strategy_version(conn, "v-1")["status"] == "SHADOW_ACTIVE"
    # second activation is a no-op (already active)
    assert shadow.activate_shadow(conn, "v-1", now=datetime(2026, 6, 2)) is False
    conn.close()


# ── forward evaluation ──────────────────────────────────────────────────────


def _evaluate(tmp_path, score_fn, *, today=date(2026, 8, 15)):
    snap = tmp_path / "v-1.py"
    snap.write_text(CANDIDATE_STRATEGY)
    strat = tmp_path / "strategy.py"
    strat.write_text(CURRENT_STRATEGY)
    _insert_version(tmp_path / "rw.duckdb", snap)
    return shadow.evaluate_shadow(
        "v-1", today=today, realworld_db_path=tmp_path / "rw.duckdb",
        strategy_path=strat, score_fn=score_fn)


def test_evaluate_shadow_eligible_when_cycles_met_and_not_worse(tmp_path):
    cmp = _evaluate(tmp_path, _score(1.0, 0.10, 0.8, 0.12))
    assert cmp.cycles_elapsed >= shadow.MIN_SHADOW_CYCLES
    assert cmp.eligible is True
    assert cmp.challenger["test_sortino"] == 1.0


def test_evaluate_shadow_not_eligible_too_few_cycles(tmp_path):
    cmp = _evaluate(tmp_path, _score(1.0, 0.10, 0.8, 0.12), today=date(2026, 5, 29))
    assert cmp.cycles_elapsed < shadow.MIN_SHADOW_CYCLES
    assert cmp.eligible is False


def test_evaluate_shadow_not_eligible_when_worse(tmp_path):
    cmp = _evaluate(tmp_path, _score(0.6, 0.10, 0.8, 0.12))
    assert cmp.eligible is False


def test_evaluate_shadow_not_eligible_when_dd_worse(tmp_path):
    # equal Sortino but the challenger draws down materially deeper -> not eligible
    cmp = _evaluate(tmp_path, _score(0.8, 0.20, 0.8, 0.12))
    assert cmp.eligible is False


def test_evaluate_shadow_missing_version_returns_none(tmp_path):
    realworld_db.connect(tmp_path / "rw.duckdb").close()
    assert shadow.evaluate_shadow(
        "nope", today=date(2026, 8, 15),
        realworld_db_path=tmp_path / "rw.duckdb",
        strategy_path=tmp_path / "strategy.py",
        score_fn=_score(1.0, 0.1, 0.8, 0.1)) is None
