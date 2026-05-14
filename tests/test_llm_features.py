from datetime import date, datetime

import pytest

from llm.cache import (
    MACRO_TICKER_SENTINEL,
    cache_put,
    events_ticker_key,
    sentiment_ticker_key,
)
from llm.features import (
    EVENTS_DEFAULT,
    events,
    macro_regime,
    news_volume,
    sentiment,
)


@pytest.fixture(autouse=True)
def _isolate_cache_and_news(monkeypatch, tmp_path):
    import data.ingest_news as news_mod
    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "DB_PATH", tmp_path / "llm_cache.sqlite")
    monkeypatch.setattr(news_mod, "DB_PATH", tmp_path / "news.duckdb")


# --- macro_regime ---

def test_macro_regime_returns_none_when_uncached():
    assert macro_regime(date(2024, 1, 15), model_id="any") is None


def test_macro_regime_reads_cache():
    cache_put(
        "2024-01-15", MACRO_TICKER_SENTINEL, "h1", "test-model",
        {"regime": "risk_off", "confidence": 0.8, "reasoning": "x"},
    )
    assert macro_regime(date(2024, 1, 15), model_id="test-model") == "risk_off"


def test_macro_regime_picks_latest_after_prompt_bump():
    cache_put(
        "2024-01-15", MACRO_TICKER_SENTINEL, "v1_hash", "test-model",
        {"regime": "neutral", "confidence": 0.5, "reasoning": "old"},
    )
    cache_put(
        "2024-01-15", MACRO_TICKER_SENTINEL, "v2_hash", "test-model",
        {"regime": "risk_on", "confidence": 0.9, "reasoning": "new"},
    )
    assert macro_regime(date(2024, 1, 15), model_id="test-model") == "risk_on"


def test_macro_regime_default_finds_any_model():
    """A row written by Codex should be readable by a strategy whose default
    accessor (model_id=None) doesn't care which model wrote it."""
    cache_put(
        "2024-01-15", MACRO_TICKER_SENTINEL, "h1", "codex-default",
        {"regime": "risk_off", "confidence": 0.8, "reasoning": "x"},
    )
    # No model_id passed → falls back to DEFAULT_MODEL_ID which is None
    assert macro_regime(date(2024, 1, 15)) == "risk_off"


def test_macro_regime_strict_model_filter_isolates_rows():
    """Passing an explicit model_id restores strict per-model lookup
    (useful for ablation studies)."""
    cache_put(
        "2024-01-15", MACRO_TICKER_SENTINEL, "h1", "codex-default",
        {"regime": "risk_off", "confidence": 0.8, "reasoning": "x"},
    )
    # Strict lookup for a different model finds nothing
    assert macro_regime(date(2024, 1, 15), model_id="claude-code-opus-4-7") is None


# --- sentiment ---

def test_sentiment_returns_none_when_uncached():
    assert sentiment("AAPL", date(2024, 3, 1), model_id="any") is None


def test_sentiment_reads_cache():
    cache_put(
        "2024-03-01", sentiment_ticker_key("AAPL"), "h1", "test-model",
        {"score": -0.6, "confidence": 0.7},
    )
    got = sentiment("AAPL", date(2024, 3, 1), model_id="test-model")
    assert got == {"score": -0.6, "confidence": 0.7}


# --- events ---

def test_events_returns_default_when_uncached():
    got = events("AAPL", date(2024, 3, 1), model_id="any")
    assert got == EVENTS_DEFAULT
    assert got is not EVENTS_DEFAULT  # caller gets a copy


def test_events_reads_cache():
    flags = {
        "earnings": 1, "guidance_change": 0, "m_and_a": 0, "regulatory": 0,
        "executive_change": 0, "layoffs": 0, "product_launch": 1,
    }
    cache_put(
        "2024-03-01", events_ticker_key("META"), "h1", "test-model", flags,
    )
    assert events("META", date(2024, 3, 1), model_id="test-model") == flags


def test_sentiment_and_events_dont_collide():
    """Same (date, ticker) but different feature kinds must not interfere."""
    cache_put(
        "2024-03-01", sentiment_ticker_key("AAPL"), "h1", "m1",
        {"score": 0.5, "confidence": 0.7},
    )
    cache_put(
        "2024-03-01", events_ticker_key("AAPL"), "h2", "m1",
        {**EVENTS_DEFAULT, "earnings": 1},
    )
    assert sentiment("AAPL", date(2024, 3, 1), model_id="m1") == {
        "score": 0.5, "confidence": 0.7,
    }
    assert events("AAPL", date(2024, 3, 1), model_id="m1")["earnings"] == 1


# --- news_volume ---

def _seed_news_rows(rows: list[dict]) -> None:
    """Insert raw rows directly into the news table for test setup."""
    from data.ingest_news import _upsert
    _upsert(rows)


def test_news_volume_zero_when_no_news():
    """No ingested news for the day → 0. Lets strategy distinguish 'no news'
    from sentiment of 0.0 (the empty-news short-circuit default)."""
    assert news_volume("AAPL", date(2024, 3, 1)) == 0


def test_news_volume_counts_articles_for_that_day():
    _seed_news_rows([
        {"ticker": "AAPL", "published_at": datetime(2024, 3, 1, 8, 0),
         "headline": "morning headline", "summary": "x",
         "source_name": "X", "source_id": "test", "url": "http://a"},
        {"ticker": "AAPL", "published_at": datetime(2024, 3, 1, 14, 30),
         "headline": "afternoon headline", "summary": "y",
         "source_name": "X", "source_id": "test", "url": "http://b"},
        {"ticker": "AAPL", "published_at": datetime(2024, 3, 2, 9, 0),
         "headline": "next-day headline", "summary": "z",
         "source_name": "X", "source_id": "test", "url": "http://c"},
    ])
    assert news_volume("AAPL", date(2024, 3, 1)) == 2
    assert news_volume("AAPL", date(2024, 3, 2)) == 1


def test_news_volume_isolates_by_ticker():
    _seed_news_rows([
        {"ticker": "AAPL", "published_at": datetime(2024, 3, 1, 12, 0),
         "headline": "AAPL only", "summary": "x",
         "source_name": "X", "source_id": "test", "url": "http://a"},
    ])
    assert news_volume("AAPL", date(2024, 3, 1)) == 1
    assert news_volume("MSFT", date(2024, 3, 1)) == 0
