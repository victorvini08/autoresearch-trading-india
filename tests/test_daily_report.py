"""daily_report renders a deterministic markdown file from a summary + DB.

TWEAKS from US repo:
- Currency rendering: '$' -> '₹' (India daily_report uses _fmt_inr / _fmt_inr_px)
- Mode names: 'paper' -> 'dhan-paper' (seeded ledger + ExecutionSummary)
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from scripts import daily_report
from scripts.executors.protocol import ExecutionSummary
from storage import portfolio_db


@pytest.fixture
def seeded_ledger(tmp_path, monkeypatch):
    """A minimal portfolio.duckdb with one day's worth of orders, fills,
    positions, cash, discrepancies. Mode = 'dhan-paper'."""
    db_path = tmp_path / "portfolio.duckdb"
    halt_file = tmp_path / "halt.json"
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)

    conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(conn)

    AS_OF = date(2026, 5, 12)
    FILL_AT = datetime(2026, 5, 13, 14, 30)

    # Targets
    conn.execute(
        "INSERT INTO desired_targets VALUES (?, ?, ?, ?, ?)",
        [AS_OF, "NVDA", 0.10, "run_live", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO desired_targets VALUES (?, ?, ?, ?, ?)",
        [AS_OF, "META", 0.05, "run_live", "dhan-paper"],
    )

    # Submitted orders
    conn.execute(
        "INSERT INTO submitted_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["o1", datetime(2026, 5, 12, 16, 0), AS_OF, "NVDA", "buy", "limit", 10.0, 105.50, "filled", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO submitted_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["o2", datetime(2026, 5, 12, 16, 0), AS_OF, "META", "sell", "limit", 2.0, 700.00, "filled", "dhan-paper"],
    )

    # Fills
    conn.execute(
        "INSERT INTO actual_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["f1", "o1", FILL_AT, "NVDA", "buy", 10.0, 105.45, 1.20, 5.0, "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO actual_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["f2", "o2", FILL_AT, "META", "sell", 2.0, 700.10, 1.20, 5.0, "dhan-paper"],
    )

    # Positions snapshot for the fill date
    conn.execute(
        "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2026, 5, 13), "NVDA", 10.0, None, 106.00, 1060.00, "dhan-paper"],
    )

    # Cash entries — one deposit + one trade
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c1", datetime(2026, 5, 1), None, "deposit", 5000.0, "initial", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c2", FILL_AT, AS_OF, "buy", -1054.50, "NVDA buy", "dhan-paper"],
    )

    # One discrepancy
    conn.execute(
        "INSERT INTO discrepancies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["d1", datetime(2026, 5, 12, 16, 5), AS_OF, "large_overnight_gap", "NVDA",
         "open within 5pct", "open=110", "filled_anyway", "audit suggested", "dhan-paper"],
    )

    conn.close()
    return {"db_path": db_path, "as_of": AS_OF}


def _summary(seeded_ledger, **overrides) -> ExecutionSummary:
    defaults = dict(
        mode="dhan-paper",
        as_of_date=seeded_ledger["as_of"],
        fill_date=date(2026, 5, 13),
        n_orders=2,
        n_fills=2,
        gross_buy_usd=1054.50,
        gross_sell_usd=1400.00,
        total_commission_usd=2.40,
        n_discrepancies=1,
    )
    defaults.update(overrides)
    return ExecutionSummary(**defaults)


def test_generates_file_at_expected_path(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    assert out.exists()
    assert out.name == "2026-05-12.md"


def test_header_includes_status_ok(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "# 2026-05-12 — dhan-paper run [OK]" in body
    assert "**Fill date:** `2026-05-13`" in body


def test_skipped_status_in_header(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger, n_orders=0, n_fills=0, skipped=True,
                 skipped_reason="halt.json set", halt_set=True, halt_reason="manual"),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "[SKIPPED]" in body
    assert "halt.json set" in body
    assert "manual" in body


def test_targets_section_lists_rows(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "## Targets" in body
    assert "NVDA" in body
    assert "META" in body
    assert "+10.00%" in body
    assert "+5.00%" in body


def test_orders_fills_table(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "## Orders & fills" in body
    assert "Orders submitted: **2**" in body
    # TWEAK: currency symbol changed from $ to ₹
    assert "₹105.4500" in body  # NVDA fill price
    assert "₹700.1000" in body  # META fill price


def test_positions_section(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "## Positions (snapshot 2026-05-13)" in body
    # TWEAK: currency symbol changed from $ to ₹
    assert "₹1,060.00" in body  # NVDA mark value


def test_discrepancies_section_lists_rows(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "## Discrepancies (1)" in body
    assert "large_overnight_gap" in body
    assert "filled_anyway" in body


def test_discrepancies_section_renders_none_when_empty(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger, n_discrepancies=0),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "## Discrepancies" in body
    assert "_(none)_" in body


def test_premarket_section_when_payload_given(seeded_ledger, tmp_path):
    pm = {
        "vix": {"level": 18.0, "flag": False},
        "tickers": {"NVDA": {"gap_flag": True}},
        "halt_recommendations": [],
    }
    out = daily_report.generate(
        _summary(seeded_ledger),
        context=daily_report.ReportContext(premarket_payload=pm),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "1 held tickers scanned, 1 gap-flagged" in body or "1 gap-flagged" in body


def test_premarket_section_absent_when_no_payload(seeded_ledger, tmp_path):
    out = daily_report.generate(
        _summary(seeded_ledger),
        db_path=seeded_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    assert "Premarket scan: **not run**" in body
