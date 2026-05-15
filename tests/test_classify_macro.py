import os
import shutil
from datetime import date
from unittest.mock import MagicMock

import pytest

from llm.classify import classify_macro_regime_batch
from llm.provider import ClaudeCodeProvider


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "DB_PATH", tmp_path / "llm_cache.sqlite")


@pytest.fixture
def _stub_fred(monkeypatch):
    """Stub the Indian macro snapshot; avoid a real DuckDB read."""
    monkeypatch.setattr(
        "llm.classify._macro_snapshot",
        lambda _d, *a, **k: {
            "india_vix": 18.5,
            "india_vix_pct_252d": 0.62,
            "nifty50_pct_vs_200dma": 3.4,
        },
    )


def _fake_provider(response: str) -> MagicMock:
    p = MagicMock()
    p.model_id = "test-model"
    p.classify = MagicMock(return_value=response)
    return p


def test_classify_writes_cache_and_returns_parsed(_stub_fred):
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "risk_off", "confidence": 0.8, '
        '"reasoning": "vol up"}]'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1)], p)
    assert out[date(2024, 3, 1)]["regime"] == "risk_off"
    assert p.classify.call_count == 1


def test_classify_two_dates_uses_one_batched_call(_stub_fred):
    """The whole point of the refactor: 2 dates → 1 batched LLM call."""
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "risk_off", "confidence": 0.8, "reasoning": "x"},'
        ' {"date": "2024-03-02", "regime": "neutral", "confidence": 0.5, "reasoning": "y"}]'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1), date(2024, 3, 2)], p)
    assert p.classify.call_count == 1
    assert out[date(2024, 3, 1)]["regime"] == "risk_off"
    assert out[date(2024, 3, 2)]["regime"] == "neutral"


def test_classify_is_idempotent_on_rerun(_stub_fred):
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "neutral", "confidence": 0.6, "reasoning": "ok"},'
        ' {"date": "2024-03-02", "regime": "neutral", "confidence": 0.6, "reasoning": "ok"}]'
    )
    classify_macro_regime_batch([date(2024, 3, 1), date(2024, 3, 2)], p)
    assert p.classify.call_count == 1  # one batched call

    # Second pass with same dates → cache hit, 0 new LLM calls
    p.classify.reset_mock()
    classify_macro_regime_batch([date(2024, 3, 1), date(2024, 3, 2)], p)
    assert p.classify.call_count == 0


def test_classify_chunks_respect_chunk_size(_stub_fred):
    """3 dates with chunk_size=2 → 2 batched calls (2 + 1)."""
    responses = [
        '[{"date": "2024-03-01", "regime": "neutral", "confidence": 0.5, "reasoning": "a"},'
        ' {"date": "2024-03-02", "regime": "neutral", "confidence": 0.5, "reasoning": "b"}]',
        '[{"date": "2024-03-03", "regime": "neutral", "confidence": 0.5, "reasoning": "c"}]',
    ]
    p = MagicMock()
    p.model_id = "test-model"
    p.classify = MagicMock(side_effect=responses)

    classify_macro_regime_batch(
        [date(2024, 3, 1), date(2024, 3, 2), date(2024, 3, 3)],
        p, chunk_size=2,
    )
    assert p.classify.call_count == 2


def test_classify_skips_one_bad_row_caches_others(_stub_fred):
    """A malformed row in a multi-row batch must not nuke the valid rows."""
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "moon_cycle", "confidence": 0.8, "reasoning": "bad"},'
        ' {"date": "2024-03-02", "regime": "neutral", "confidence": 0.6, "reasoning": "good"}]'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1), date(2024, 3, 2)], p)
    assert date(2024, 3, 2) in out
    assert out[date(2024, 3, 2)]["regime"] == "neutral"
    assert date(2024, 3, 1) not in out  # bad row was skipped, not cached


def test_classify_raises_when_zero_valid_in_batch(_stub_fred):
    """If every row in a batch is invalid, raise — suspicious LLM output."""
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "moon_cycle", "confidence": 0.8, "reasoning": "x"}]'
    )
    with pytest.raises(RuntimeError, match="0 valid entries"):
        classify_macro_regime_batch([date(2024, 3, 1)], p)


def test_classify_raises_when_unparseable(_stub_fred):
    p = _fake_provider("not json at all")
    with pytest.raises(RuntimeError, match="could not be parsed"):
        classify_macro_regime_batch([date(2024, 3, 1)], p)


def test_macro_accepts_response_without_confidence(_stub_fred):
    """Regression for the 2026-05-15 'every row invalid' bug: the prompt
    schema was {regime, reasoning} but the validator REQUIRED confidence,
    so 100% of rows were rejected. confidence is now requested AND optional
    (defaulted) so a stray omission can't nuke an unattended run."""
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "risk_off", "reasoning": "vol up"}]'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1)], p)
    assert out[date(2024, 3, 1)]["regime"] == "risk_off"
    assert out[date(2024, 3, 1)]["confidence"] == 0.5  # defaulted


def test_macro_defaults_bad_confidence_value(_stub_fred):
    p = _fake_provider(
        '[{"date": "2024-03-01", "regime": "neutral", '
        '"confidence": "high", "reasoning": "mixed"}]'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1)], p)
    assert out[date(2024, 3, 1)]["regime"] == "neutral"
    assert out[date(2024, 3, 1)]["confidence"] == 0.5  # non-numeric → default


def test_classify_handles_markdown_fenced_json(_stub_fred):
    p = _fake_provider(
        'Here is my analysis:\n```json\n'
        '[{"date": "2024-03-01", "regime": "risk_on", "confidence": 0.7, "reasoning": "low vol"}]\n'
        '```\n'
    )
    out = classify_macro_regime_batch([date(2024, 3, 1)], p)
    assert out[date(2024, 3, 1)]["regime"] == "risk_on"


def test_classify_uses_recent_news_in_cache_key(_stub_fred):
    """Different news → different per-cell prompt_hash → different cache row."""
    r1 = '[{"date": "2024-03-01", "regime": "risk_on", "confidence": 0.8, "reasoning": "x"}]'
    p1 = _fake_provider(r1)
    classify_macro_regime_batch(
        [date(2024, 3, 1)], p1, {date(2024, 3, 1): ["bull news"]},
    )

    r2 = '[{"date": "2024-03-01", "regime": "risk_off", "confidence": 0.8, "reasoning": "y"}]'
    p2 = _fake_provider(r2)
    classify_macro_regime_batch(
        [date(2024, 3, 1)], p2, {date(2024, 3, 1): ["bear news"]},
    )

    # Both calls hit provider — distinct cache rows because per-cell hash differs
    assert p1.classify.call_count == 1
    assert p2.classify.call_count == 1


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("claude") is None or not os.environ.get("FRED_API_KEY"),
    reason="needs claude CLI + FRED_API_KEY",
)
def test_classify_macro_regime_live():
    """Live: classify two specific dates against real FRED + claude. Slow."""
    p = ClaudeCodeProvider()
    out = classify_macro_regime_batch(
        [date(2020, 3, 16), date(2021, 6, 30)], p,
    )
    for d, result in out.items():
        assert result["regime"] in {"risk_on", "risk_off", "neutral", "shock"}
        assert 0 <= result["confidence"] <= 1
