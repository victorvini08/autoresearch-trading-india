"""Tests for storage/realworld_db.py — the durable store for the monthly
LLM review's hypotheses + audit trail (Step 4.a).

This DB is deliberately SEPARATE from portfolio.duckdb: the ledger is
broker-truth; this is the research-meta layer (LLM hypotheses + provenance).
Only two facts here genuinely can't be recomputed on-render and therefore
need durable storage: (1) the burned-hypothesis hashes the validator's
duplicate gate checks against, and (2) the per-run audit trail.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from storage import realworld_db


@pytest.fixture
def conn(tmp_path):
    c = realworld_db.connect(tmp_path / "realworld.duckdb")
    yield c
    c.close()


def test_connect_creates_tables(conn):
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    assert {"hypotheses", "audit"} <= tables


def test_connect_is_idempotent(tmp_path):
    # Opening twice must not error (CREATE TABLE IF NOT EXISTS).
    p = tmp_path / "realworld.duckdb"
    realworld_db.connect(p).close()
    realworld_db.connect(p).close()


def test_insert_and_read_audit(conn):
    realworld_db.insert_audit(
        conn,
        review_id="rev-1",
        run_at=datetime(2026, 6, 30, 16, 0, 0),
        mode="dhan-paper",
        trigger="monthly",
        input_snapshot_hash="abc123",
        prompt_version="v1",
        model_id="claude-code-claude-opus-4-7",
        output_json="{}",
        validator_version="v1",
        validator_result="passed",
        validator_failures_json="[]",
        n_realized_trades=0,
        safety_state="NORMAL",
        cold_start=True,
    )
    row = realworld_db.get_audit(conn, "rev-1")
    assert row["mode"] == "dhan-paper"
    assert row["trigger"] == "monthly"
    assert row["cold_start"] is True
    assert row["n_realized_trades"] == 0
    assert row["validator_result"] == "passed"


def test_get_audit_missing_returns_none(conn):
    assert realworld_db.get_audit(conn, "does-not-exist") is None


def test_insert_hypothesis_defaults_pending(conn):
    realworld_db.insert_hypothesis(
        conn,
        hypothesis_id="h-1",
        review_id="rev-1",
        created_at=datetime(2026, 6, 30, 16, 0, 0),
        mode="dhan-paper",
        category="cost",
        confidence="low",
        text="DP charge drag exceeds the modeled flat fee on sub-2k sells.",
        causal_story="Small odd-lot sells pay the same flat DP charge.",
        predeclared_test="Realized sells < ₹2k net trail modeled cost by >X bps.",
        supporting_evidence_json='["t-1"]',
        text_lexical_hash="hash-1",
    )
    rows = realworld_db.get_hypotheses(conn, mode="dhan-paper")
    assert len(rows) == 1
    assert rows[0]["state"] == "PENDING"
    assert rows[0]["category"] == "cost"
    assert rows[0]["hypothesis_id"] == "h-1"


def test_get_hypotheses_filter_by_state(conn):
    realworld_db.insert_hypothesis(
        conn, hypothesis_id="h-1", review_id="rev-1",
        created_at=datetime(2026, 6, 30), mode="dhan-paper",
        category="signal", confidence="high", text="x",
        causal_story="y", predeclared_test="z",
        supporting_evidence_json="[]", text_lexical_hash="hash-1",
    )
    assert len(realworld_db.get_hypotheses(conn, "dhan-paper", state="PENDING")) == 1
    assert len(realworld_db.get_hypotheses(conn, "dhan-paper", state="VALIDATOR_KEPT")) == 0


def test_burned_hashes_excludes_pending(conn):
    realworld_db.insert_hypothesis(
        conn, hypothesis_id="h-1", review_id="rev-1",
        created_at=datetime(2026, 6, 30), mode="dhan-paper",
        category="signal", confidence="high", text="x",
        causal_story="y", predeclared_test="z",
        supporting_evidence_json="[]", text_lexical_hash="hash-pending",
    )
    # PENDING is not burned — re-proposal is allowed while still live.
    assert realworld_db.get_burned_hypothesis_hashes(conn, "dhan-paper") == set()


def test_burned_hashes_includes_rejected(conn):
    realworld_db.insert_hypothesis(
        conn, hypothesis_id="h-1", review_id="rev-1",
        created_at=datetime(2026, 6, 30), mode="dhan-paper",
        category="signal", confidence="high", text="x",
        causal_story="y", predeclared_test="z",
        supporting_evidence_json="[]", text_lexical_hash="hash-burned",
    )
    realworld_db.update_hypothesis_state(
        conn, "h-1", "VALIDATOR_REJECTED", updated_at=datetime(2026, 7, 1))
    assert realworld_db.get_burned_hypothesis_hashes(conn, "dhan-paper") == {"hash-burned"}


def test_burned_hashes_kept_is_not_burned(conn):
    # A KEPT hypothesis is live strategy, not a burned idea — must NOT block
    # re-proposal via the duplicate gate.
    realworld_db.insert_hypothesis(
        conn, hypothesis_id="h-1", review_id="rev-1",
        created_at=datetime(2026, 6, 30), mode="dhan-paper",
        category="signal", confidence="high", text="x",
        causal_story="y", predeclared_test="z",
        supporting_evidence_json="[]", text_lexical_hash="hash-kept",
    )
    realworld_db.update_hypothesis_state(
        conn, "h-1", "VALIDATOR_KEPT", updated_at=datetime(2026, 7, 1))
    assert realworld_db.get_burned_hypothesis_hashes(conn, "dhan-paper") == set()


def test_burned_hashes_scoped_by_mode(conn):
    realworld_db.insert_hypothesis(
        conn, hypothesis_id="h-1", review_id="rev-1",
        created_at=datetime(2026, 6, 30), mode="dhan-paper",
        category="signal", confidence="high", text="x",
        causal_story="y", predeclared_test="z",
        supporting_evidence_json="[]", text_lexical_hash="hash-1",
    )
    realworld_db.update_hypothesis_state(
        conn, "h-1", "OBSOLETE", updated_at=datetime(2026, 7, 1))
    assert realworld_db.get_burned_hypothesis_hashes(conn, "dhan-live") == set()
    assert realworld_db.get_burned_hypothesis_hashes(conn, "dhan-paper") == {"hash-1"}


# ── strategy_versions: challenger lineage (Step 5.a) ──────────────────────
#
# Every candidate the Step 5 validator vets becomes a CHALLENGER snapshot here
# — NOT a live strategy.py swap. The promotion chain is a status lifecycle:
#   CHALLENGER -> SHADOW_ACTIVE (running on the shadow paper book)
#             -> PROMOTED (manually swapped into live strategy.py)
#             -> RETIRED (superseded or failed shadow).
# The row is the SEBI "material-change" defensibility artifact: it stores the
# unified diff, the atomic-gate results, the ₹5L scale re-run, and the sealed
# status (DEFERRED_TO_SHADOW when no fresh out-of-sample window exists yet).


def _insert_version(conn, **over):
    kw = dict(
        version_hash="v-abc123",
        created_at=datetime(2026, 7, 1, 12, 0, 0),
        mode="dhan-paper",
        hypothesis_id="rev-1-h0",
        parent_version_hash="v-incumbent",
        unified_diff="--- a/strategy.py\n+++ b/strategy.py\n@@ ...",
        gate_results_json='{"passed": true, "gates": []}',
        scale_robustness_json='{"capital": 500000, "robust": true}',
        sealed_status="DEFERRED_TO_SHADOW",
        sealed_metrics_json=None,
        validator_version="v1",
        journal_excerpt="Implements late-decile entry filter.",
        snapshot_path="state/strategy_versions/v-abc123.py",
    )
    kw.update(over)
    realworld_db.insert_strategy_version(conn, **kw)


def test_connect_creates_strategy_versions_table(conn):
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    assert "strategy_versions" in tables


def test_insert_and_read_strategy_version_defaults_challenger(conn):
    _insert_version(conn)
    row = realworld_db.get_strategy_version(conn, "v-abc123")
    assert row is not None
    assert row["status"] == "CHALLENGER"
    assert row["hypothesis_id"] == "rev-1-h0"
    assert row["parent_version_hash"] == "v-incumbent"
    assert row["sealed_status"] == "DEFERRED_TO_SHADOW"
    assert row["sealed_metrics_json"] is None
    assert row["snapshot_path"] == "state/strategy_versions/v-abc123.py"


def test_get_strategy_version_missing_returns_none(conn):
    assert realworld_db.get_strategy_version(conn, "nope") is None


def test_update_strategy_version_status(conn):
    _insert_version(conn)
    realworld_db.update_strategy_version_status(
        conn, "v-abc123", "SHADOW_ACTIVE", updated_at=datetime(2026, 7, 2))
    row = realworld_db.get_strategy_version(conn, "v-abc123")
    assert row["status"] == "SHADOW_ACTIVE"
    assert row["status_updated_at"] == datetime(2026, 7, 2)


def test_get_strategy_versions_filter_by_status(conn):
    _insert_version(conn, version_hash="v-1")
    _insert_version(conn, version_hash="v-2")
    realworld_db.update_strategy_version_status(
        conn, "v-2", "PROMOTED", updated_at=datetime(2026, 7, 3))
    challengers = realworld_db.get_strategy_versions(
        conn, "dhan-paper", status="CHALLENGER")
    promoted = realworld_db.get_strategy_versions(
        conn, "dhan-paper", status="PROMOTED")
    assert [r["version_hash"] for r in challengers] == ["v-1"]
    assert [r["version_hash"] for r in promoted] == ["v-2"]


def test_get_strategy_versions_scoped_by_mode(conn):
    _insert_version(conn, version_hash="v-paper", mode="dhan-paper")
    _insert_version(conn, version_hash="v-live", mode="dhan-live")
    rows = realworld_db.get_strategy_versions(conn, "dhan-paper")
    assert [r["version_hash"] for r in rows] == ["v-paper"]


def test_strategy_version_states_constant():
    assert realworld_db.STRATEGY_VERSION_STATES == frozenset(
        {"CHALLENGER", "SHADOW_ACTIVE", "PROMOTED", "RETIRED"})
