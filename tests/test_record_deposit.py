"""Live cash-accounting: the ₹0-anchor bug for dhan-live and its deposit fix."""
from datetime import date, datetime, timezone

from storage.portfolio_db import (
    connect, get_cash_balance, insert_cash_entry, record_deposit,
)
import scripts.record_deposit as rd


def test_live_cash_negative_without_deposit_then_correct_with(tmp_path):
    """dhan-live anchors cash at ₹0, so a buy with no opening deposit drives
    get_cash_balance NEGATIVE (the dashboard/P&L bug). Recording the opening
    capital as a deposit makes it match the real broker."""
    db = tmp_path / "pf.duckdb"
    with connect(db) as conn:
        insert_cash_entry(conn, entry_id="buy1", entry_at=datetime.now(timezone.utc),
                          as_of_date=date(2026, 7, 1), kind="buy", amount_usd=-30000.0,
                          notes="buy 30k stock", mode="dhan-live")
        # BUG: ledger says -₹30k (real account would show ₹20k cash + ₹30k stock)
        assert get_cash_balance(conn, mode="dhan-live") == -30000.0
        # FIX: record the ₹50k opening deposit
        eid = record_deposit(conn, amount_inr=50000.0, mode="dhan-live",
                             as_of_date=date(2026, 7, 1))
        assert eid.startswith("deposit-dhan-live-")
        assert get_cash_balance(conn, mode="dhan-live") == 20000.0  # 50000 - 30000


def test_record_deposit_and_withdrawal(tmp_path):
    db = tmp_path / "pf.duckdb"
    with connect(db) as conn:
        assert get_cash_balance(conn, mode="dhan-live") == 0.0
        record_deposit(conn, amount_inr=50000.0, mode="dhan-live")
        assert get_cash_balance(conn, mode="dhan-live") == 50000.0
        record_deposit(conn, amount_inr=-10000.0, mode="dhan-live")  # withdrawal
        assert get_cash_balance(conn, mode="dhan-live") == 40000.0


def test_cli_check_detects_mismatch_then_seed_matches(tmp_path, monkeypatch):
    """`check` flags a broker-vs-ledger gap (exit 2); `seed-to-broker` records it;
    `check` then passes (exit 0)."""
    db = tmp_path / "pf.duckdb"
    monkeypatch.setattr(rd, "_broker_cash", lambda: 50000.0)

    # empty ledger (₹0) vs broker ₹50k -> mismatch
    assert rd.main(["check", "--db", str(db), "--mode", "dhan-live"]) == 2
    # seed records the ₹50k difference
    assert rd.main(["seed-to-broker", "--db", str(db), "--mode", "dhan-live"]) == 0
    with connect(db) as conn:
        assert get_cash_balance(conn, mode="dhan-live") == 50000.0
    # now matched
    assert rd.main(["check", "--db", str(db), "--mode", "dhan-live"]) == 0


def test_cli_record_explicit_amount(tmp_path):
    db = tmp_path / "pf.duckdb"
    assert rd.main(["record", "--amount", "50000", "--db", str(db), "--mode", "dhan-live"]) == 0
    with connect(db) as conn:
        assert get_cash_balance(conn, mode="dhan-live") == 50000.0
