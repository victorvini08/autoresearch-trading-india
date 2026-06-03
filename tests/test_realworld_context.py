"""Tests for scripts/realworld_context.py (Step 4.c).

Context assembly reuses the Step 1-3 compute functions (reconciliation,
trade_context, safety_state) to build two things: the validator's ReviewContext
(ground truth) and the LLM-facing payload. The genuinely-new logic — the
closed-round-trip count, evidence-id derivation, snapshot hashing, and the
pure assembler — is TDD'd here; the thin IO `gather` wrapper is glue covered
by the 4.d runner.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from storage import portfolio_db
from data import realworld_review_validator as V
import scripts.realworld_context as ctx


def _seed_realized(conn, rows):
    for i, (ticker, buy_d, sell_d) in enumerate(rows):
        portfolio_db.insert_realized_trade(
            conn,
            trade_id=f"t-{i}",
            sell_fill_id=f"sf-{ticker}-{sell_d}",
            buy_lot_id=f"lot-{i}",
            ticker=ticker,
            buy_date=buy_d,
            sell_date=sell_d,
            qty=10.0,
            buy_price=100.0,
            sell_price=110.0,
            realized_pnl_usd=100.0,
            holding_days=(sell_d - buy_d).days,
            tax_paid_usd=15.0,
            mode="dhan-paper",
        )


def test_count_closed_round_trips_is_distinct_not_lot_rows(tmp_path):
    conn = portfolio_db.connect(tmp_path / "p.duckdb")
    # ONGC sold on the same day from TWO lots -> 2 realized_trades rows but
    # ONE economic round-trip. RELIANCE is a third distinct close.
    _seed_realized(conn, [
        ("ONGC", date(2026, 1, 10), date(2026, 5, 26)),
        ("ONGC", date(2026, 2, 10), date(2026, 5, 26)),
        ("RELIANCE", date(2026, 3, 1), date(2026, 5, 29)),
    ])
    assert ctx.count_closed_round_trips(conn, "dhan-paper") == 2
    conn.close()


def test_count_closed_round_trips_scoped_by_mode(tmp_path):
    conn = portfolio_db.connect(tmp_path / "p.duckdb")
    _seed_realized(conn, [("ONGC", date(2026, 1, 10), date(2026, 5, 26))])
    assert ctx.count_closed_round_trips(conn, "dhan-live") == 0
    conn.close()


def test_valid_evidence_ids_from_held_and_closed():
    trade_context = {
        "held": [{"ticker": "RELIANCE"}, {"ticker": "TCS"}],
        "closed": [
            {"ticker": "ONGC", "sell_date": "2026-05-26"},
            {"ticker": "INFY", "sell_date": "2026-05-29"},
        ],
    }
    ids = ctx.valid_evidence_ids(trade_context)
    assert ids == frozenset({"RELIANCE", "TCS", "ONGC@2026-05-26", "INFY@2026-05-29"})


def test_input_snapshot_hash_deterministic():
    payload = {"a": 1, "b": [3, 2, 1]}
    assert ctx.input_snapshot_hash(payload) == ctx.input_snapshot_hash(dict(payload))


def test_input_snapshot_hash_changes_with_content():
    assert ctx.input_snapshot_hash({"a": 1}) != ctx.input_snapshot_hash({"a": 2})


def _assemble(**overrides):
    base = dict(
        d=date(2026, 5, 29),
        mode="dhan-paper",
        reconciliation={"date": "2026-05-29", "drawdown_threshold": {"status": "ok"}},
        trade_context={
            "held": [{"ticker": "RELIANCE", "flag": "warn"}],
            "closed": [{"ticker": "ONGC", "sell_date": "2026-05-26"}],
        },
        safety_state="NORMAL",
        n_realized_trades=20,
        burned_hashes=frozenset({"deadbeef"}),
        past_hypotheses=[{"text": "x", "state": "VALIDATOR_REJECTED", "category": "signal"}],
        journal_tail="previous month entry...",
    )
    base.update(overrides)
    return ctx.assemble_review_input(**base)


def test_assemble_builds_review_context():
    ri = _assemble()
    assert isinstance(ri.context, V.ReviewContext)
    assert ri.context.n_realized_trades == 20
    assert ri.context.safety_state == "NORMAL"
    assert ri.context.burned_hashes == frozenset({"deadbeef"})
    # evidence ids derived from the trade_context
    assert ri.context.valid_evidence_ids == frozenset({"RELIANCE", "ONGC@2026-05-26"})


def test_assemble_payload_has_all_sections():
    ri = _assemble()
    for key in ("reconciliation", "held_positions", "closed_trades",
                "safety_state", "past_hypotheses", "journal_tail",
                "valid_evidence_ids", "n_realized_trades"):
        assert key in ri.payload


def test_assemble_cold_start_below_threshold():
    ri = _assemble(n_realized_trades=5)
    assert ri.cold_start is True
    assert ri.payload["cold_start"] is True
    assert ri.payload["cold_start_banner"]  # non-empty banner present
    assert "5" in ri.payload["cold_start_banner"]


def test_assemble_not_cold_start_at_threshold():
    ri = _assemble(n_realized_trades=V.COLD_START_MIN_TRADES)
    assert ri.cold_start is False
    assert ri.payload["cold_start_banner"] is None


def test_assemble_hash_matches_payload():
    ri = _assemble()
    assert ri.input_snapshot_hash == ctx.input_snapshot_hash(ri.payload)
