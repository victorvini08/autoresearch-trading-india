"""Tests for scripts/precompute_macro_cache.py.

TWEAK from US repo:
- The India macro precompute reads NSE trading days from the NIFTY index
  (was QQQ in US). All test seed rows now use ticker='NIFTY'.

Strategy: don't hit the LLM at all. We monkeypatch:
  - shutil.which → make ClaudeCodeProvider think `claude` exists
  - classify_macro_regime_batch → record calls, skip the real provider work
  - PRICES_DB → temp duckdb seeded with NIFTY rows

This keeps tests offline + deterministic. We only test logic that lives in
this script (NIFTY-only filter, per-day iteration, error accumulation, exit
codes) — not DuckDB or argparse.
"""
from datetime import date

import duckdb
import pytest

from scripts.precompute_macro_cache import main, trading_days


def _seed_prices_db(path, rows: list[tuple[str, str]]) -> None:
    """rows is [(date_iso, ticker), ...]."""
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE prices (date DATE, ticker VARCHAR, "
        "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)"
    )
    for d, t in rows:
        con.execute(
            "INSERT INTO prices VALUES (?, ?, 1.0, 1.0, 1.0, 1.0, 1)",
            [d, t],
        )
    con.close()


def test_trading_days_filters_to_nifty(monkeypatch, tmp_path):
    """Without the NIFTY filter, this would return RELIANCE/TCS dates too."""
    db = tmp_path / "prices.duckdb"
    _seed_prices_db(db, [
        ("2024-03-01", "NIFTY"),
        ("2024-03-04", "NIFTY"),
        ("2024-03-05", "NIFTY"),
        ("2024-03-01", "RELIANCE"),
        ("2024-03-04", "TCS"),
    ])
    monkeypatch.setattr("scripts.precompute_macro_cache.PRICES_DB", db)

    days = trading_days(date(2024, 3, 1), date(2024, 3, 5))
    assert days == [date(2024, 3, 1), date(2024, 3, 4), date(2024, 3, 5)]


@pytest.fixture
def _fake_claude_on_path(monkeypatch):
    """ClaudeCodeProvider construction requires `claude` on PATH; provider is
    never actually called because we patch classify_macro_regime_batch."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/fake-claude")


def test_main_processes_all_days_via_chunked_calls(
    monkeypatch, tmp_path, _fake_claude_on_path,
):
    """Three days with chunk_size=2 → script calls classify twice (2 + 1)
    and every day is covered."""
    db = tmp_path / "prices.duckdb"
    _seed_prices_db(db, [
        ("2024-03-01", "NIFTY"),
        ("2024-03-04", "NIFTY"),
        ("2024-03-05", "NIFTY"),
    ])
    monkeypatch.setattr("scripts.precompute_macro_cache.PRICES_DB", db)

    chunks_seen: list[list[date]] = []

    def fake_classify(dates, provider, recent_news_by_date=None, *, chunk_size):
        chunks_seen.append(list(dates))
        return {d: {"regime": "neutral", "confidence": 0.5, "reasoning": "x"}
                for d in dates}

    monkeypatch.setattr(
        "scripts.precompute_macro_cache.classify_macro_regime_batch",
        fake_classify,
    )

    rc = main([
        "--start", "2024-03-01", "--end", "2024-03-05", "--chunk-size", "2",
    ])
    assert rc == 0
    assert len(chunks_seen) == 2
    flat = [d for chunk in chunks_seen for d in chunk]
    assert flat == [date(2024, 3, 1), date(2024, 3, 4), date(2024, 3, 5)]


def test_main_continues_on_per_chunk_failure_and_returns_2(
    monkeypatch, tmp_path, _fake_claude_on_path,
):
    """A failed chunk must not halt the run; exit code is 2 to signal
    failures occurred."""
    db = tmp_path / "prices.duckdb"
    _seed_prices_db(db, [
        ("2024-03-01", "NIFTY"),
        ("2024-03-04", "NIFTY"),
        ("2024-03-05", "NIFTY"),
    ])
    monkeypatch.setattr("scripts.precompute_macro_cache.PRICES_DB", db)

    call_count = 0

    def fake_classify(dates, provider, recent_news_by_date=None, *, chunk_size):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("simulated LLM parse failure")

    monkeypatch.setattr(
        "scripts.precompute_macro_cache.classify_macro_regime_batch",
        fake_classify,
    )

    rc = main([
        "--start", "2024-03-01", "--end", "2024-03-05", "--chunk-size", "2",
    ])
    assert rc == 2
    assert call_count == 2  # 2 chunks attempted (3 days / chunk_size 2 = 2 chunks)


def test_main_exits_1_when_no_trading_days_found(
    monkeypatch, tmp_path, _fake_claude_on_path,
):
    """Distinct from a failure exit (2): exit 1 means the precondition (NIFTY
    data present) wasn't met — caller should run prices ingest first."""
    db = tmp_path / "prices.duckdb"
    _seed_prices_db(db, [])
    monkeypatch.setattr("scripts.precompute_macro_cache.PRICES_DB", db)

    rc = main(["--start", "2024-03-01", "--end", "2024-03-05"])
    assert rc == 1
