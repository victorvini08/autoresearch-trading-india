"""Tests for the corporate-action ledger and reconciliation Q6."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest

from data.corporate_actions import (
    CorporateAction,
    format_action_summary,
    get_actions_for_tickers_on_date,
    get_actions_on_date,
    load_corporate_actions,
    save_corporate_actions,
    upsert_action,
)
from scripts.reconciliation import compute_reconciliation_for_date
from storage import portfolio_db


# === Round-trip + helpers ===================================================

def test_save_then_load_round_trip(tmp_path):
    p = tmp_path / "corporate_actions.json"
    actions = [
        CorporateAction(
            ex_date=date(2026, 5, 8),
            ticker="LAURUSLABS",
            type="dividend",
            value=1.2,
            notes="₹1.20/share",
        ),
        CorporateAction(
            ex_date=date(2026, 5, 15),
            ticker="RELIANCE",
            type="split",
            value=2.0,
            notes="1:2 split",
        ),
    ]
    save_corporate_actions(actions, p)
    out = load_corporate_actions(p)
    assert len(out) == 2
    assert out[0].ticker == "LAURUSLABS"
    assert out[0].value == 1.2
    assert out[1].type == "split"
    assert out[1].value == 2.0


def test_load_missing_file_returns_empty(tmp_path):
    assert load_corporate_actions(tmp_path / "does_not_exist.json") == []


def test_upsert_blocks_duplicates_by_ticker_date_type(tmp_path):
    actions: list[CorporateAction] = []
    a = CorporateAction(date(2026, 1, 1), "X", "dividend", 1.0)
    actions, was_added = upsert_action(actions, a)
    assert was_added and len(actions) == 1

    # Same (ticker, ex_date, type) key — must NOT be re-added even with
    # a different `value` field.
    a2 = CorporateAction(date(2026, 1, 1), "X", "dividend", 99.0)
    actions, was_added = upsert_action(actions, a2)
    assert not was_added and len(actions) == 1

    # Different type — adds.
    a3 = CorporateAction(date(2026, 1, 1), "X", "split", 2.0)
    actions, was_added = upsert_action(actions, a3)
    assert was_added and len(actions) == 2


def test_filter_by_date_and_ticker():
    actions = [
        CorporateAction(date(2026, 1, 1), "A", "dividend", 1.0),
        CorporateAction(date(2026, 1, 1), "B", "split", 2.0),
        CorporateAction(date(2026, 1, 2), "A", "dividend", 1.5),
    ]
    on_jan1 = get_actions_on_date(actions, date(2026, 1, 1))
    assert {ca.ticker for ca in on_jan1} == {"A", "B"}

    held = {"B"}
    just_b = get_actions_for_tickers_on_date(actions, held, date(2026, 1, 1))
    assert len(just_b) == 1 and just_b[0].ticker == "B"


def test_format_action_summary_handles_all_types():
    cases = [
        CorporateAction(date(2026, 1, 1), "X", "dividend", 1.25),
        CorporateAction(date(2026, 1, 1), "Y", "split", 2.0),
        CorporateAction(date(2026, 1, 1), "Z", "bonus", 3.0),
        CorporateAction(date(2026, 1, 1), "W", "rights", 100.0),
        CorporateAction(date(2026, 1, 1), "V", "isin_change", None, new_symbol="V_NEW"),
        CorporateAction(date(2026, 1, 1), "U", "delisting", None),
        CorporateAction(date(2026, 1, 1), "T", "suspension", None),
        CorporateAction(date(2026, 1, 1), "S", "demerger", None),
    ]
    for ca in cases:
        s = format_action_summary(ca)
        assert ca.ticker in s
        assert len(s) > 0


# === Reconciliation Q6 ======================================================

@pytest.fixture
def db_with_holdings(tmp_path):
    """Fresh DB with one held position so Q6 has a 'relevant ticker' set."""
    db = tmp_path / "portfolio.duckdb"
    with portfolio_db.connect(db) as c:
        c.execute(
            "INSERT INTO broker_positions (snapshot_date, ticker, quantity, "
            "avg_entry_price, mark_price, mark_value, mode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [date(2026, 5, 26), "ONGC", 35, 280.0, 285.0, 35 * 285.0, "dhan-paper"],
        )
    return db


def test_q6_no_ledger_file_returns_ok(db_with_holdings, monkeypatch, tmp_path):
    # Point the CA loader at a non-existent path
    monkeypatch.setattr(
        "data.corporate_actions.DEFAULT_CA_PATH",
        tmp_path / "absent.json",
    )
    out = compute_reconciliation_for_date(
        date(2026, 5, 26), "dhan-paper", db_with_holdings,
    )
    q6 = out["corporate_actions"]
    assert q6["status"] == "ok"
    assert "No corporate-action ledger" in q6["detail"]


def test_q6_ledger_with_no_today_hits_returns_ok(
    db_with_holdings, monkeypatch, tmp_path,
):
    ca_path = tmp_path / "ca.json"
    save_corporate_actions(
        [
            # Different date — should NOT fire on 2026-05-26
            CorporateAction(date(2026, 5, 8), "LAURUSLABS", "dividend", 1.2),
            # Right date but not in our holdings — should NOT fire
            CorporateAction(date(2026, 5, 26), "INFY", "dividend", 5.0),
        ],
        ca_path,
    )
    monkeypatch.setattr(
        "data.corporate_actions.DEFAULT_CA_PATH", ca_path,
    )
    out = compute_reconciliation_for_date(
        date(2026, 5, 26), "dhan-paper", db_with_holdings,
    )
    assert out["corporate_actions"]["status"] == "ok"


def test_q6_ca_on_held_ticker_today_warns_and_lists(
    db_with_holdings, monkeypatch, tmp_path,
):
    ca_path = tmp_path / "ca.json"
    save_corporate_actions(
        [
            CorporateAction(
                date(2026, 5, 26), "ONGC", "dividend", 6.25,
                notes="Final dividend",
            ),
        ],
        ca_path,
    )
    monkeypatch.setattr(
        "data.corporate_actions.DEFAULT_CA_PATH", ca_path,
    )
    out = compute_reconciliation_for_date(
        date(2026, 5, 26), "dhan-paper", db_with_holdings,
    )
    q6 = out["corporate_actions"]
    assert q6["status"] == "warn"
    assert len(q6["events"]) == 1
    assert q6["events"][0]["ticker"] == "ONGC"
    assert q6["events"][0]["type"] == "dividend"
    assert "ONGC" in q6["detail"]
