import pytest

from llm.cache import cache_get, cache_put, cache_size


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    import llm.cache as mod
    monkeypatch.setattr(mod, "DB_PATH", tmp_path / "llm_cache.sqlite")


def test_get_returns_none_on_miss():
    assert cache_get("2024-01-15", "AAPL", "abc123", "claude-code-opus-4-7") is None


def test_put_then_get_roundtrips():
    out = {"regime": "risk_off", "confidence": 0.8, "reasoning": "vol spike"}
    cache_put("2024-01-15", "_macro_", "abc123", "claude-code-opus-4-7", out)
    got = cache_get("2024-01-15", "_macro_", "abc123", "claude-code-opus-4-7")
    assert got == out


def test_put_replaces_on_same_key():
    cache_put("2024-01-15", "AAPL", "h1", "m1", {"score": 0.5})
    cache_put("2024-01-15", "AAPL", "h1", "m1", {"score": -0.2})
    assert cache_get("2024-01-15", "AAPL", "h1", "m1") == {"score": -0.2}


def test_different_prompt_hash_is_different_row():
    cache_put("2024-01-15", "AAPL", "h1", "m1", {"score": 0.5})
    cache_put("2024-01-15", "AAPL", "h2", "m1", {"score": -0.2})
    assert cache_get("2024-01-15", "AAPL", "h1", "m1") == {"score": 0.5}
    assert cache_get("2024-01-15", "AAPL", "h2", "m1") == {"score": -0.2}
    assert cache_size() == 2


def test_different_model_is_different_row():
    cache_put("2024-01-15", "AAPL", "h1", "claude", {"score": 0.5})
    cache_put("2024-01-15", "AAPL", "h1", "qwen3", {"score": -0.2})
    assert cache_get("2024-01-15", "AAPL", "h1", "claude") == {"score": 0.5}
    assert cache_get("2024-01-15", "AAPL", "h1", "qwen3") == {"score": -0.2}
    assert cache_size() == 2


def test_complex_nested_dict_roundtrips():
    out = {
        "events": {"earnings": 1, "m_and_a": 0, "regulatory": 1},
        "raw_response": "...",
        "tokens": [12, 34, 56],
    }
    cache_put("2024-01-15", "MSFT", "h1", "m1", out)
    assert cache_get("2024-01-15", "MSFT", "h1", "m1") == out
