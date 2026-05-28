"""Dashboard build — JSON payload + HTML rendering against a seeded ledger.

Dashboard has two tabs (paper / real). Tests cover both populated
and empty buckets.

TWEAKS from US repo:
- Mode names: 'paper' -> 'dhan-paper' (PAPER_MODES bucket)
- Mode names: 'ibkr-paper'/'ibkr-live'/'real' -> 'dhan-live' (REAL_MODES bucket)
- modes_included assertions updated to reflect the India bucket membership
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

import pytest

from scripts import dashboard
from storage import portfolio_db


def _extract_payload(html: str) -> dict:
    m = re.search(r"const DATA = (\{.*?\});", html, flags=re.DOTALL)
    assert m is not None, "DATA payload not found in HTML"
    return json.loads(m.group(1))


def _seed_paper_day(conn, *, day_a: date, day_b: date):
    """TWEAK: seeded mode is 'dhan-paper' (was 'paper' in US)."""
    fill_a = datetime(2026, 5, 13, 14, 30)
    fill_b = datetime(2026, 5, 14, 14, 30)
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c_p_deposit", datetime(2026, 5, 1), None, "deposit", 5000.0, "seed", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO desired_targets VALUES (?, ?, ?, ?, ?)",
        [day_a, "NVDA", 0.20, "run_live", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO submitted_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["o_p1", datetime(2026, 5, 12, 16, 0), day_a, "NVDA", "buy", "limit",
         5.0, 200.0, "filled", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO actual_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["f_p1", "o_p1", fill_a, "NVDA", "buy", 5.0, 200.10, 0.35, 5.0, "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c_p1", fill_a, day_a, "buy", -1000.50, "NVDA buy", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [day_b, "NVDA", 5.0, 200.10, 205.0, 1025.0, "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO submitted_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["o_p2", datetime(2026, 5, 13, 16, 0), day_b, "NVDA", "sell", "limit",
         5.0, 205.0, "filled", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO actual_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["f_p2", "o_p2", fill_b, "NVDA", "sell", 5.0, 205.05, 0.35, 5.0, "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c_p2", fill_b, day_b, "sell", 1025.25, "NVDA sell", "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO discrepancies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["d_p1", datetime(2026, 5, 13, 16, 5), day_b, "large_overnight_gap",
         "NVDA", "open within 5%", "open=215", "filled_anyway", "audit", "dhan-paper"],
    )


def _seed_real_day(conn, *, day: date, mode: str = "dhan-live"):
    """One day of activity in the real bucket.

    TWEAK: default real mode is 'dhan-live' (was 'ibkr-paper'/'ibkr-live'
    in US). REAL_MODES is currently ('dhan-live',).
    """
    conn.execute(
        "INSERT INTO cash_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["c_r_deposit", datetime(2026, 5, 1), None, "deposit", 10000.0, "seed", mode],
    )
    conn.execute(
        "INSERT INTO submitted_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["o_r1", datetime(2026, 5, 14, 14, 30), day, "AAPL", "buy", "limit",
         3.0, 220.0, "filled", mode],
    )
    conn.execute(
        "INSERT INTO actual_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["f_r1", "o_r1", datetime(2026, 5, 14, 14, 31),
         "AAPL", "buy", 3.0, 219.95, 0.35, 5.0, mode],
    )
    conn.execute(
        "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [day, "AAPL", 3.0, 219.95, 221.0, 663.0, mode],
    )


@pytest.fixture
def seeded_both_buckets(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.duckdb"
    halt_file = tmp_path / "halt.json"
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)

    conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(conn)
    DAY_A = date(2026, 5, 12)
    DAY_B = date(2026, 5, 13)
    DAY_REAL = date(2026, 5, 14)
    _seed_paper_day(conn, day_a=DAY_A, day_b=DAY_B)
    _seed_real_day(conn, day=DAY_REAL, mode="dhan-live")
    conn.close()
    return {
        "db_path": db_path,
        "paper_dates": [DAY_A.isoformat(), DAY_B.isoformat()],
        "real_dates": [DAY_REAL.isoformat()],
    }


@pytest.fixture
def paper_only_ledger(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.duckdb"
    halt_file = tmp_path / "halt.json"
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)
    conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(conn)
    _seed_paper_day(conn, day_a=date(2026, 5, 12), day_b=date(2026, 5, 13))
    conn.close()
    return {"db_path": db_path}


# --------- build + structure ---------

def test_build_writes_dashboard_html(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    assert out.exists()
    assert out.name == "dashboard.html"
    body = out.read_text()
    assert body.startswith("<!doctype html>")
    assert "<title>Trading Dashboard</title>" in body


def test_payload_has_paper_and_real_keys(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    assert "paper" in payload
    assert "real" in payload
    assert "generated_at" in payload
    # TWEAK: India PAPER_MODES = ('dhan-paper',), REAL_MODES = ('dhan-live',)
    assert payload["paper"]["modes_included"] == ["dhan-paper"]
    assert set(payload["real"]["modes_included"]) == {"dhan-live"}


def test_paper_bucket_has_two_dates(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    assert payload["paper"]["dates"] == seeded_both_buckets["paper_dates"]


def test_real_bucket_has_dhan_live_day(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    assert payload["real"]["dates"] == seeded_both_buckets["real_dates"]
    day = payload["real"]["by_date"]["2026-05-14"]
    assert day["orders"][0]["ticker"] == "AAPL"
    # TWEAK: mode tag is dhan-live in the real bucket
    assert day["orders"][0]["mode"] == "dhan-live"


def test_real_bucket_empty_when_no_real_activity(paper_only_ledger, tmp_path):
    out = dashboard.build(
        db_path=paper_only_ledger["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    assert payload["paper"]["dates"] != []
    assert payload["real"]["dates"] == []
    assert payload["real"]["by_date"] == {}
    assert payload["real"]["equity_curve"] == []


def test_paper_day_a_shows_submitted_buy(seeded_both_buckets, tmp_path):
    """Day A (2026-05-12) submitted a buy whose fill landed the NEXT day
    in our seed data. So:
    - n_orders=1 (submitted today)
    - n_fills=0 (won't land until tomorrow)
    - gross_buy_usd=0 (money moves on fill date, not signal date)
    Orders list includes the submitted-but-not-yet-filled buy.

    Note: In production India dhan-paper / dhan-live are intraday so signal
    and fill land same day. This test exercises the dashboard's join logic
    against next-day fills (which Dhan does support for AMO orders) — the
    SQL UNION (`as_of_date = D OR filled_at = D`) covers both patterns.
    """
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    day_a = payload["paper"]["by_date"]["2026-05-12"]
    assert day_a["n_orders"] == 1
    assert day_a["n_fills"] == 0  # buy fills on 2026-05-13, not today
    assert day_a["gross_buy_usd"] == 0.0
    assert day_a["total_commission_usd"] == 0.0
    # The buy order is still in the orders list (submitted today)
    assert any(o["side"] == "buy" and o["as_of_date"] == "2026-05-12"
               for o in day_a["orders"])


def test_paper_day_b_shows_filled_buy_and_submitted_sell(seeded_both_buckets, tmp_path):
    """Day B (2026-05-13): Day-A's buy LANDS here, and a new sell is submitted.
    - n_orders=1 (one new sell submitted)
    - n_fills=1 (the buy from yesterday landed)
    - The orders list includes BOTH (signal+fill activity for today).
    """
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    day_b = payload["paper"]["by_date"]["2026-05-13"]
    assert day_b["n_orders"] == 1   # the sell submitted today
    assert day_b["n_fills"] == 1    # the buy filled today
    # Orders list has 2 entries — both relevant to today
    assert len(day_b["orders"]) == 2
    buys = [o for o in day_b["orders"] if o["side"] == "buy"]
    sells = [o for o in day_b["orders"] if o["side"] == "sell"]
    assert len(buys) == 1 and buys[0]["filled_at"][:10] == "2026-05-13"
    assert len(sells) == 1 and sells[0]["as_of_date"] == "2026-05-13"
    # Dollar metrics: only the buy that filled today counts toward gross_buy
    assert abs(day_b["gross_buy_usd"] - 5.0 * 200.10) < 1e-6
    assert day_b["gross_sell_usd"] == 0.0  # sell fills tomorrow
    assert len(day_b["discrepancies"]) == 1


def test_orders_include_signal_date_field(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    for d in ("2026-05-12", "2026-05-13"):
        for o in payload["paper"]["by_date"][d]["orders"]:
            assert "as_of_date" in o, f"as_of_date missing on day {d}"
            assert o["as_of_date"] is not None


def test_equity_curve_monotonic_in_each_bucket(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    payload = _extract_payload(out.read_text())
    for bucket in ("paper", "real"):
        dates = [p["date"] for p in payload[bucket]["equity_curve"]]
        assert dates == sorted(dates)


def test_empty_db_renders_both_tabs_empty(tmp_path):
    db_path = tmp_path / "empty.duckdb"
    conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(conn)
    conn.close()
    out = dashboard.build(db_path=db_path, reports_dir=tmp_path / "reports")
    payload = _extract_payload(out.read_text())
    assert payload["paper"]["dates"] == []
    assert payload["real"]["dates"] == []


def test_renders_tab_strip_and_critical_elements(seeded_both_buckets, tmp_path):
    out = dashboard.build(
        db_path=seeded_both_buckets["db_path"],
        reports_dir=tmp_path / "reports",
    )
    body = out.read_text()
    # Tab strip
    assert 'data-bucket="paper"' in body
    assert 'data-bucket="real"' in body
    assert 'id="count-paper"' in body
    assert 'id="count-real"' in body
    # Templates that get cloned per-tab
    assert 'id="tab-template"' in body
    assert 'id="empty-template"' in body
    # Per-tab fragments
    assert "date-slider" in body
    assert "equity-chart" in body
    assert "orders-section" in body
    assert "positions-section" in body
    # Discrepancies card removed in Step 1.b — superseded by Reconciliation.
    assert "reconciliation-section" in body
    assert "chart.umd.min.js" in body
    # Step 2.d: safety state card.
    assert "safety-card" in body
    assert "safety-section" in body
    assert "safety-badge" in body


def test_cli_main_runs(seeded_both_buckets, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(portfolio_db, "DEFAULT_DB_PATH", seeded_both_buckets["db_path"])
    rc = dashboard.main(["--out-dir", str(tmp_path / "reports")])
    assert rc == 0
    assert "dashboard" in capsys.readouterr().out.lower()
    assert (tmp_path / "reports" / "dashboard.html").exists()
