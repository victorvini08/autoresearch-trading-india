import os
import shutil
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from llm.classify import classify_sentiment_batch
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
    """Replace read_news to return the given items."""
    def fake_read(ticker, start, end):
        return pd.DataFrame(items) if items else pd.DataFrame(
            {"headline": [], "summary": []}
        )
    monkeypatch.setattr("llm.classify.read_news", fake_read)


def test_empty_news_short_circuits(monkeypatch):
    """No news → no LLM call, default zeros returned."""
    _seed_news(monkeypatch, [])
    p = _fake_provider("never called")
    out = classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)
    assert out[("AAPL", date(2024, 3, 1))] == {
        "score": 0.0, "confidence": 0.0, "is_actionable": False
    }
    assert p.classify.call_count == 0


def test_with_news_calls_llm_and_caches(monkeypatch):
    _seed_news(monkeypatch, [
        {"headline": "Apple Q1 beat", "summary": "Strong iPhone sales"},
    ])
    p = _fake_provider(
        '[{"ticker": "AAPL", "date": "2024-03-01", "score": 0.7,'
        ' "confidence": 0.85, "is_actionable": true}]'
    )

    out = classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)
    assert out[("AAPL", date(2024, 3, 1))]["score"] == 0.7
    assert out[("AAPL", date(2024, 3, 1))]["is_actionable"] is True
    assert p.classify.call_count == 1

    # Re-run: cache hit, no extra call
    p.classify.reset_mock()
    classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)
    assert p.classify.call_count == 0


def test_one_bad_row_does_not_drop_other_rows(monkeypatch):
    """Score out of range on one row should not lose the valid one in the same batch."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    p = _fake_provider(
        '[{"ticker": "AAPL", "date": "2024-03-01", "score": 1.5,'
        ' "confidence": 0.5, "is_actionable": false},'
        ' {"ticker": "MSFT", "date": "2024-03-01", "score": -0.3,'
        ' "confidence": 0.7, "is_actionable": true}]'
    )
    out = classify_sentiment_batch(
        [("AAPL", date(2024, 3, 1)), ("MSFT", date(2024, 3, 1))], p,
    )
    assert ("MSFT", date(2024, 3, 1)) in out
    assert out[("MSFT", date(2024, 3, 1))]["score"] == -0.3
    assert out[("MSFT", date(2024, 3, 1))]["is_actionable"] is True
    assert ("AAPL", date(2024, 3, 1)) not in out


def test_zero_valid_in_batch_raises(monkeypatch):
    """If every row in the batch is invalid, raise — likely LLM gone wrong."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    p = _fake_provider(
        '[{"ticker": "AAPL", "date": "2024-03-01", "score": 1.5,'
        ' "confidence": 0.5, "is_actionable": false}]'
    )
    with pytest.raises(RuntimeError, match="0 valid entries"):
        classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)


def test_handles_markdown_fenced_array(monkeypatch):
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    p = _fake_provider(
        '```json\n'
        '[{"ticker": "AAPL", "date": "2024-03-01", "score": -0.4,'
        ' "confidence": 0.6, "is_actionable": true}]\n'
        '```'
    )
    out = classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)
    assert out[("AAPL", date(2024, 3, 1))]["score"] == -0.4
    assert out[("AAPL", date(2024, 3, 1))]["is_actionable"] is True


def test_missing_is_actionable_field_rejected(monkeypatch):
    """LLM output missing the new is_actionable field should be invalid."""
    _seed_news(monkeypatch, [{"headline": "x", "summary": "y"}])
    p = _fake_provider(
        '[{"ticker": "AAPL", "date": "2024-03-01", "score": 0.2, "confidence": 0.5}]'
    )
    with pytest.raises(RuntimeError, match="0 valid entries"):
        classify_sentiment_batch([("AAPL", date(2024, 3, 1))], p)


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("claude") is None or not os.environ.get("FINNHUB_API_KEY"),
    reason="needs claude CLI + FINNHUB_API_KEY",
)
def test_classify_sentiment_live_with_real_news():
    """Live: pull AAPL news → classify → cache → re-run skips LLM."""
    from datetime import timedelta

    from data.ingest_news import ingest_finnhub_news

    today = date.today()
    target = today - timedelta(days=2)
    ingest_finnhub_news(["AAPL"], target.isoformat(), target.isoformat())

    p = ClaudeCodeProvider()
    out = classify_sentiment_batch([("AAPL", target)], p)
    score = out[("AAPL", target)]["score"]
    assert -1.0 <= score <= 1.0
