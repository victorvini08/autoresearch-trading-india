"""llm.features macro-signal accessors (added 2026-05-15).

Contract: only signals with REAL data coverage are exposed — policy/repo
rate and FII/DII must be filtered out even if the underlying snapshot
emits them — and the point-in-time source is the audited _macro_snapshot.
"""
from datetime import date

from llm import features


def test_macro_signals_whitelists_only_real_coverage(monkeypatch):
    fake = {
        "india_vix": 14.2,
        "india_vix_pct_252d": 0.61,
        "nifty50_pct_vs_200dma": 3.1,
        "usd_inr": 83.4,
        "usd_inr_1w_change_pct": 0.4,
        "gdelt_tone_mean": -0.8,
        "gdelt_epu_policy": 1.0,
        # These MUST be filtered out (insufficient/stale data):
        "repo_rate_pct": 6.5,
        "fii_net_20d_cr": -12000.0,
        "dii_net_20d_cr": 9000.0,
    }
    monkeypatch.setattr("llm.classify._macro_snapshot", lambda _d: fake)
    out = features.macro_signals(date(2024, 1, 15))
    assert "repo_rate_pct" not in out
    assert "fii_net_20d_cr" not in out
    assert "dii_net_20d_cr" not in out
    assert out["india_vix_pct_252d"] == 0.61
    assert out["gdelt_tone_mean"] == -0.8
    assert set(out) <= features._MACRO_SIGNAL_KEYS


def test_scalar_accessors(monkeypatch):
    monkeypatch.setattr(
        "llm.classify._macro_snapshot",
        lambda _d: {"india_vix_pct_252d": 0.95, "nifty50_pct_vs_200dma": -4.2},
    )
    d = date(2024, 6, 1)
    assert features.india_vix_percentile(d) == 0.95
    assert features.nifty_vs_200dma_pct(d) == -4.2


def test_scalar_accessors_none_when_absent(monkeypatch):
    monkeypatch.setattr("llm.classify._macro_snapshot", lambda _d: {})
    d = date(2024, 6, 1)
    assert features.india_vix_percentile(d) is None
    assert features.nifty_vs_200dma_pct(d) is None
    assert features.macro_signals(d) == {}


def test_macro_signals_real_db_pit_sanity():
    """Against the real macro.duckdb: a mid-2024 date has the
    fully-backfilled GDELT + VIX signals and never the excluded repo rate."""
    out = features.macro_signals(date(2024, 1, 15))
    assert "gdelt_tone_mean" in out
    assert "india_vix_pct_252d" in out
    assert "repo_rate_pct" not in out
    assert "fii_net_20d_cr" not in out
