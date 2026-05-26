"""Tests for the dhan-live promotion gate (`scripts.promote_live`).

The gate's contract:
  - No consent file → live is BLOCKED (default-safe).
  - Consent expired → BLOCKED.
  - strategy.py hash drift since grant → BLOCKED.
  - Force-granted consent works (manual override for explicit operator review).
  - Refusal when insufficient paper days OR unresolved discrepancies in window.

Tests use an isolated tmp consent path + tmp portfolio DB so they never
touch real state.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

from scripts import promote_live


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch) -> dict:
    """Re-point CONSENT_PATH + PORTFOLIO_DB + STRATEGY_PY at tmp files."""
    consent = tmp_path / "live_consent.json"
    portfolio = tmp_path / "portfolio.duckdb"
    strategy_py = tmp_path / "strategy.py"
    strategy_py.write_text("# fake strategy\nclass S: pass\n")
    monkeypatch.setattr(promote_live, "CONSENT_PATH", consent)
    monkeypatch.setattr(promote_live, "PORTFOLIO_DB", portfolio)
    monkeypatch.setattr(promote_live, "STRATEGY_PY", strategy_py)
    return {"consent": consent, "portfolio": portfolio, "strategy_py": strategy_py}


def _seed_portfolio(p: Path, n_paper_days: int, n_unresolved: int = 0) -> None:
    """Create a portfolio DB with N paper days + N unresolved discrepancies."""
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            """
            CREATE TABLE broker_positions (
                snapshot_date DATE, ticker VARCHAR, quantity DOUBLE,
                avg_entry_price DOUBLE, mark_price DOUBLE, mark_value DOUBLE,
                mode VARCHAR
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE discrepancies (
                discrepancy_id VARCHAR, detected_at TIMESTAMP, as_of_date DATE,
                kind VARCHAR, ticker VARCHAR, expected VARCHAR, actual VARCHAR,
                resolution VARCHAR, notes VARCHAR, mode VARCHAR
            )
            """
        )
        today = date.today()
        for i in range(n_paper_days):
            d = today - timedelta(days=i)
            conn.execute(
                "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d, "RELIANCE", 1.0, 1000.0, 1000.0, 1000.0, "dhan-paper"),
            )
        for i in range(n_unresolved):
            conn.execute(
                "INSERT INTO discrepancies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"D{i}",
                    datetime.now(),
                    today - timedelta(days=1),
                    "qty_mismatch",
                    "RELIANCE",
                    "10",
                    "9",
                    None,  # unresolved
                    "note",
                    "dhan-paper",
                ),
            )
    finally:
        conn.close()


def test_no_consent_blocks_live(isolated):
    allowed, reason = promote_live.check_consent_for_live()
    assert not allowed
    assert "no state/live_consent.json" in reason


def test_grant_refuses_insufficient_paper_days(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=5)  # < required 20
    with pytest.raises(RuntimeError, match="only 5 clean paper days"):
        promote_live.grant_consent()


def test_grant_refuses_unresolved_discrepancies(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=25, n_unresolved=3)
    with pytest.raises(RuntimeError, match="3 unresolved discrepancies"):
        promote_live.grant_consent()


def test_grant_succeeds_with_clean_paper(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=25)
    payload = promote_live.grant_consent()
    assert payload["paper_days_validated"] >= 20
    assert payload["discrepancies_in_window"] == 0
    assert payload["consent_token"]
    assert payload["strategy_hash"] == promote_live._strategy_hash()
    assert not payload["forced"]
    # The consent file is on disk
    assert isolated["consent"].exists()
    # And the live gate now allows
    allowed, _reason = promote_live.check_consent_for_live()
    assert allowed


def test_grant_force_bypasses_gates(isolated):
    # No paper days at all — but --force lets us through anyway
    _seed_portfolio(isolated["portfolio"], n_paper_days=0)
    payload = promote_live.grant_consent(force=True)
    assert payload["forced"] is True


def test_strategy_hash_drift_blocks_live(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=25)
    promote_live.grant_consent()
    # Operator edits strategy.py after granting consent
    isolated["strategy_py"].write_text("# CHANGED\nclass S: pass\n")
    allowed, reason = promote_live.check_consent_for_live()
    assert not allowed
    assert "strategy.py changed" in reason


def test_consent_expiry_blocks_live(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=25)
    promote_live.grant_consent()
    # Backdate valid_until_utc to yesterday
    consent = json.loads(isolated["consent"].read_text())
    consent["valid_until_utc"] = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat(timespec="seconds")
    isolated["consent"].write_text(json.dumps(consent))
    allowed, reason = promote_live.check_consent_for_live()
    assert not allowed
    assert "consent expired" in reason


def test_revoke_blocks_subsequent_live(isolated):
    _seed_portfolio(isolated["portfolio"], n_paper_days=25)
    promote_live.grant_consent()
    assert promote_live.check_consent_for_live()[0] is True
    assert promote_live.revoke_consent() is True
    assert promote_live.check_consent_for_live()[0] is False


def test_show_returns_none_when_no_consent(isolated):
    assert promote_live.show_consent() is None
