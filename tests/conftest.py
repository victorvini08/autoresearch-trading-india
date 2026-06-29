"""Shared pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def _no_sweep_settle(monkeypatch):
    """Zero out the executor's sweep-to-fill settle pause in tests. The real
    ~2s pause lets each live IOC reach a terminal state before the next residual
    is sized; under the in-memory mock fills are synchronous, so the pause is
    pure wall-clock waste. Safe no-op if the module isn't imported by a test."""
    try:
        import scripts.executors.dhan as _dhan
        monkeypatch.setattr(_dhan, "SWEEP_SETTLE_SEC", 0.0, raising=False)
    except Exception:
        pass
