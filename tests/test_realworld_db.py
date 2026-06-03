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
