"""Cross-provider cache resume (user decision 2026-05-15): a half-cache
filled by Codex must be CONTINUED by a later Claude run, not recomputed.
Strict per-model isolation remains available via LLM_STRICT_MODEL_CACHE=1
for single-model ablations."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from llm.classify import classify_macro_regime_batch


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "DB_PATH", tmp_path / "llm_cache.sqlite")


@pytest.fixture(autouse=True)
def _stub_snapshot(monkeypatch):
    monkeypatch.setattr(
        "llm.classify._macro_snapshot",
        lambda _d, *a, **k: {"india_vix": 18.0},
    )


def _provider(model_id: str, response: str) -> MagicMock:
    p = MagicMock()
    p.model_id = model_id
    p.classify = MagicMock(return_value=response)
    return p


_RESP = '[{"date": "2024-03-01", "regime": "risk_off", "confidence": 0.8, "reasoning": "x"}]'


def test_claude_continues_from_codex_filled_cache(monkeypatch):
    monkeypatch.delenv("LLM_STRICT_MODEL_CACHE", raising=False)
    codex = _provider("codex-gpt-x", _RESP)
    classify_macro_regime_batch([date(2024, 3, 1)], codex)
    assert codex.classify.call_count == 1

    # Different provider/model — must REUSE the Codex cell, zero LLM calls.
    claude = _provider("claude-sonnet-4-6", _RESP)
    out = classify_macro_regime_batch([date(2024, 3, 1)], claude)
    assert claude.classify.call_count == 0
    assert out[date(2024, 3, 1)]["regime"] == "risk_off"


def test_strict_env_restores_per_model_isolation(monkeypatch):
    monkeypatch.setenv("LLM_STRICT_MODEL_CACHE", "1")
    codex = _provider("codex-gpt-x", _RESP)
    classify_macro_regime_batch([date(2024, 3, 1)], codex)

    claude = _provider("claude-sonnet-4-6", _RESP)
    classify_macro_regime_batch([date(2024, 3, 1)], claude)
    # Strict mode → Claude does NOT see Codex's row → reclassifies.
    assert claude.classify.call_count == 1
