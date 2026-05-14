import os
import shutil
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from llm.classify import classify_events_batch
from llm.provider import ClaudeCodeProvider


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    import data.ingest_news as news_mod
    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "DB_PATH", tmp_path / "llm_cache.sqlite")
    monkeypatch.setattr(news_mod, "DB_PATH", tmp_path / "news.duckdb")


def _fake_provider(response: str) -> MagicMock:
    p = MagicMock()
    p.model_id = "test-model"
    p.classify = MagicMock(return_value=response)
    return p


def _seed_news(monkeypatch, items: list[dict]) -> None:
    def fake_read(ticker, start, end):
        return pd.DataFrame(items) if items else pd.DataFrame(
            {"headline": [], "summary": []}
        )
    monkeypatch.setattr("llm.classify.read_news", fake_read)


_ALL_FLAGS = (
    "earnings", "guidance_change", "m_and_a", "regulatory",
    "executive_change", "layoffs", "product_launch",
)

# Two valid event objects we can reuse — earnings+product_launch fired, others not.
_VALID_FIELDS = (
    '"earnings": {"fired": true, "severity": 0.7}, '
    '"guidance_change": {"fired": false, "severity": 0.0}, '
    '"m_and_a": {"fired": false, "severity": 0.0}, '
    '"regulatory": {"fired": false, "severity": 0.0}, '
    '"executive_change": {"fired": false, "severity": 0.0}, '
    '"layoffs": {"fired": false, "severity": 0.0}, '
    '"product_launch": {"fired": true, "severity": 0.4}'
)


def test_empty_news_short_circuits(monkeypatch):
    _seed_news(monkeypatch, [])
    p = _fake_provider("never called")
    out = classify_events_batch([("AAPL", date(2024, 3, 1))], p)
    assert out[("AAPL", date(2024, 3, 1))] == {
        k: {"fired": False, "severity": 0.0} for k in _ALL_FLAGS
    }
    assert p.classify.call_count == 0


def test_with_news_extracts_flags(monkeypatch):
    _seed_news(monkeypatch, [
        {"headline": "Apple earnings + new iPhone", "summary": "Q1 beat, new product"},
    ])
    p = _fake_provider(
        f'[{{"ticker": "AAPL", "date": "2024-03-01", {_VALID_FIELDS}}}]'
    )
    out = classify_events_batch([("AAPL", date(2024, 3, 1))], p)
    flags = out[("AAPL", date(2024, 3, 1))]
    assert flags["earnings"]["fired"] is True
    assert flags["earnings"]["severity"] == 0.7
    assert flags["product_launch"]["fired"] is True
    assert flags["product_launch"]["severity"] == 0.4
    assert flags["m_and_a"]["fired"] is False
    assert flags["m_and_a"]["severity"] == 0.0


def test_idempotent_rerun_skips_llm(monkeypatch):
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    p = _fake_provider(
        f'[{{"ticker": "AAPL", "date": "2024-03-01", {_VALID_FIELDS}}}]'
    )
    classify_events_batch([("AAPL", date(2024, 3, 1))], p)
    p.classify.reset_mock()
    classify_events_batch([("AAPL", date(2024, 3, 1))], p)
    assert p.classify.call_count == 0


def test_one_bad_row_does_not_drop_others(monkeypatch):
    """Missing event-category on one row should not nuke valid rows in same batch."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    bad_fields = (
        '"earnings": {"fired": true, "severity": 0.7}, '
        '"guidance_change": {"fired": false, "severity": 0.0}, '
        '"m_and_a": {"fired": false, "severity": 0.0}, '
        '"regulatory": {"fired": false, "severity": 0.0}, '
        '"executive_change": {"fired": false, "severity": 0.0}, '
        '"layoffs": {"fired": false, "severity": 0.0}'  # missing product_launch
    )
    p = _fake_provider(
        f'[{{"ticker": "AAPL", "date": "2024-03-01", {bad_fields}}},'
        f' {{"ticker": "MSFT", "date": "2024-03-01", {_VALID_FIELDS}}}]'
    )
    out = classify_events_batch(
        [("AAPL", date(2024, 3, 1)), ("MSFT", date(2024, 3, 1))], p,
    )
    assert ("MSFT", date(2024, 3, 1)) in out
    assert ("AAPL", date(2024, 3, 1)) not in out


def test_zero_valid_in_batch_raises(monkeypatch):
    """severity > 1.0 invalidates the row; all-invalid batch raises."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    bad_fields = (
        '"earnings": {"fired": true, "severity": 2.5}, '
        '"guidance_change": {"fired": false, "severity": 0.0}, '
        '"m_and_a": {"fired": false, "severity": 0.0}, '
        '"regulatory": {"fired": false, "severity": 0.0}, '
        '"executive_change": {"fired": false, "severity": 0.0}, '
        '"layoffs": {"fired": false, "severity": 0.0}, '
        '"product_launch": {"fired": false, "severity": 0.0}'
    )
    p = _fake_provider(
        f'[{{"ticker": "AAPL", "date": "2024-03-01", {bad_fields}}}]'
    )
    with pytest.raises(RuntimeError, match="0 valid entries"):
        classify_events_batch([("AAPL", date(2024, 3, 1))], p)


def test_not_fired_with_nonzero_severity_rejected(monkeypatch):
    """Internal consistency: fired=false must have severity=0.0."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    inconsistent_fields = (
        '"earnings": {"fired": false, "severity": 0.5}, '  # contradictory
        '"guidance_change": {"fired": false, "severity": 0.0}, '
        '"m_and_a": {"fired": false, "severity": 0.0}, '
        '"regulatory": {"fired": false, "severity": 0.0}, '
        '"executive_change": {"fired": false, "severity": 0.0}, '
        '"layoffs": {"fired": false, "severity": 0.0}, '
        '"product_launch": {"fired": false, "severity": 0.0}'
    )
    p = _fake_provider(
        f'[{{"ticker": "AAPL", "date": "2024-03-01", {inconsistent_fields}}}]'
    )
    with pytest.raises(RuntimeError, match="0 valid entries"):
        classify_events_batch([("AAPL", date(2024, 3, 1))], p)


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("claude") is None or not os.environ.get("FINNHUB_API_KEY"),
    reason="needs claude CLI + FINNHUB_API_KEY",
)
def test_classify_events_live_with_real_news():
    from datetime import timedelta

    from data.ingest_news import ingest_finnhub_news

    today = date.today()
    target = today - timedelta(days=2)
    ingest_finnhub_news(["AAPL"], target.isoformat(), target.isoformat())

    p = ClaudeCodeProvider()
    out = classify_events_batch([("AAPL", target)], p)
    flags = out[("AAPL", target)]
    for k in _ALL_FLAGS:
        assert k in flags
        assert isinstance(flags[k], dict)
        assert isinstance(flags[k]["fired"], bool)
        assert 0.0 <= flags[k]["severity"] <= 1.0
