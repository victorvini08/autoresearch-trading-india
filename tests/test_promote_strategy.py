"""Tests for scripts/promote_strategy.py (Step 5.f) — the manual promote.

This is the ONLY operation that writes the live strategy.py, and it is
human-only: it refuses unless the version has actually run a shadow trial
(SHADOW_ACTIVE), validates the snapshot through the loop's AST/import sandbox
before swapping, backs up the incumbent for rollback, swaps atomically, and
records PROMOTED / RETIRED / VALIDATOR_KEPT. It never git-commits — the human
reviews and commits.
"""
from __future__ import annotations

from datetime import datetime

import pytest

import scripts.promote_strategy as promote
from storage import realworld_db


INCUMBENT = '''import backtrader as bt


class MomentumStrategy(bt.Strategy):
    params = (("entry_pct", 0.30),)

    def __init__(self):
        self.x = 1

    def next(self):
        pass
'''

CHALLENGER = INCUMBENT.replace("0.30", "0.25")

# Missing `next` -> fails the sandbox -> promote must refuse to swap.
BROKEN = '''import backtrader as bt


class Broken(bt.Strategy):
    def __init__(self):
        pass
'''


def _setup(tmp_path, *, snapshot_text=CHALLENGER, status="SHADOW_ACTIVE", hid="rev-1-h0"):
    strat = tmp_path / "strategy.py"
    strat.write_text(INCUMBENT)
    snap_dir = tmp_path / "versions"
    snap_dir.mkdir()
    snap = snap_dir / "v-1.py"
    snap.write_text(snapshot_text)

    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    if hid is not None:
        realworld_db.insert_hypothesis(
            conn, hypothesis_id=hid, review_id="rev-1",
            created_at=datetime(2026, 6, 1), mode="dhan-paper",
            category="hyperparameter", confidence="high", text="x",
            causal_story="y", predeclared_test="z",
            supporting_evidence_json="[]", text_lexical_hash="hh")
    realworld_db.insert_strategy_version(
        conn, version_hash="v-1", created_at=datetime(2026, 6, 5),
        mode="dhan-paper", hypothesis_id=hid, parent_version_hash=None,
        unified_diff="d", gate_results_json="{}", scale_robustness_json="{}",
        sealed_status="DEFERRED_TO_SHADOW", sealed_metrics_json=None,
        validator_version="v1", journal_excerpt="x", snapshot_path=str(snap),
        status="CHALLENGER")
    if status == "SHADOW_ACTIVE":
        realworld_db.update_strategy_version_status(
            conn, "v-1", "SHADOW_ACTIVE", updated_at=datetime(2026, 6, 6))
    conn.close()
    return strat, snap_dir


def _promote(tmp_path, strat, snap_dir, **over):
    kw = dict(
        version_hash="v-1", mode="dhan-paper",
        realworld_db_path=tmp_path / "rw.duckdb", strategy_path=strat,
        snapshot_dir=snap_dir, journal_path=tmp_path / "j.md",
        now=datetime(2026, 8, 20, 12, 0, 0))
    kw.update(over)
    return promote.promote_challenger(**kw)


def test_promote_swaps_strategy_and_updates_db(tmp_path):
    strat, snap_dir = _setup(tmp_path)
    res = _promote(tmp_path, strat, snap_dir)
    assert res.ok is True
    # the live file now holds the challenger
    assert strat.read_text() == CHALLENGER
    # incumbent backed up for rollback
    assert res.backup_path is not None
    from pathlib import Path
    assert Path(res.backup_path).read_text() == INCUMBENT
    # DB lifecycle
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_strategy_version(conn, "v-1")["status"] == "PROMOTED"
    assert realworld_db.get_hypothesis(conn, "rev-1-h0")["state"] == "VALIDATOR_KEPT"
    conn.close()
    assert (tmp_path / "j.md").exists()


def test_promote_refuses_when_not_shadow_active(tmp_path):
    strat, snap_dir = _setup(tmp_path, status="CHALLENGER")
    res = _promote(tmp_path, strat, snap_dir)
    assert res.ok is False
    assert "SHADOW_ACTIVE" in res.message
    assert strat.read_text() == INCUMBENT          # live file untouched
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_strategy_version(conn, "v-1")["status"] == "CHALLENGER"
    conn.close()


def test_promote_refuses_invalid_snapshot(tmp_path):
    strat, snap_dir = _setup(tmp_path, snapshot_text=BROKEN)
    res = _promote(tmp_path, strat, snap_dir)
    assert res.ok is False
    assert strat.read_text() == INCUMBENT          # never swapped a broken file
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_strategy_version(conn, "v-1")["status"] == "SHADOW_ACTIVE"
    conn.close()


def test_promote_missing_version(tmp_path):
    strat, snap_dir = _setup(tmp_path)
    res = _promote(tmp_path, strat, snap_dir, version_hash="nope")
    assert res.ok is False
    assert strat.read_text() == INCUMBENT


def test_promote_retires_prior_promoted(tmp_path):
    strat, snap_dir = _setup(tmp_path)
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    realworld_db.insert_strategy_version(
        conn, version_hash="v-old", created_at=datetime(2026, 5, 1),
        mode="dhan-paper", hypothesis_id=None, parent_version_hash=None,
        unified_diff="d", gate_results_json="{}", scale_robustness_json="{}",
        sealed_status="DEFERRED_TO_SHADOW", sealed_metrics_json=None,
        validator_version="v1", journal_excerpt="x", snapshot_path="old.py",
        status="PROMOTED")
    conn.close()
    res = _promote(tmp_path, strat, snap_dir)
    assert res.ok is True
    conn = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_strategy_version(conn, "v-old")["status"] == "RETIRED"
    conn.close()


def test_promote_force_bypasses_shadow_requirement(tmp_path):
    strat, snap_dir = _setup(tmp_path, status="CHALLENGER")
    res = _promote(tmp_path, strat, snap_dir, require_shadow=False)
    assert res.ok is True
    assert strat.read_text() == CHALLENGER
