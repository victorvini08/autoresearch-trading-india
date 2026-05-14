"""Operational risk-gate tests.

The halt-file side effect is contained via monkeypatching the HALT_FILE
attribute to a per-test tmp_path."""
from __future__ import annotations

import json
from datetime import date

import pytest

from scripts import risk_check
from storage.portfolio_db import LedgerState


def _state(**overrides) -> LedgerState:
    defaults = dict(
        mode="paper",
        as_of=date(2026, 5, 1),
        cash_usd=50_000.0,
        positions={},
        mark_equity=100_000.0,
        peak_equity=100_000.0,
        today_pnl_usd=0.0,
        halted=False,
    )
    defaults.update(overrides)
    return LedgerState(**defaults)


def _targets(*pairs) -> dict:
    """Build a signals dict like signal_today.generate_signals() returns."""
    return {
        "as_of_date": "2026-05-01",
        "targets": [{"ticker": t, "target_fraction": f} for t, f in pairs],
        "exits": [],
    }


@pytest.fixture(autouse=True)
def isolate_halt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(risk_check, "HALT_FILE", tmp_path / "halt.json")


def test_passes_with_clean_state_and_benign_targets():
    ok, reasons = risk_check.check(
        targets=_targets(("AAPL", 0.10), ("MSFT", 0.10)),
        state=_state(),
    )
    assert ok is True
    assert reasons == []


def test_halt_flag_short_circuits():
    ok, reasons = risk_check.check(
        targets=_targets(("AAPL", 0.99)),     # would also trip concentration
        state=_state(halted=True),
    )
    assert ok is False
    assert reasons == ["halt flag set"]


def test_daily_loss_above_limit_fires():
    ok, reasons = risk_check.check(
        targets=_targets(),
        state=_state(today_pnl_usd=-3500.0, mark_equity=100_000.0),
    )
    assert ok is False
    assert any("daily loss" in r for r in reasons)


def test_max_dd_above_threshold_sets_halt(tmp_path):
    state = _state(
        mark_equity=82_000.0,    # 18% below peak (clears the 15% halt threshold)
        peak_equity=100_000.0,
    )
    ok, reasons = risk_check.check(targets=_targets(), state=state)
    assert ok is False
    assert any("max DD" in r for r in reasons)
    # Halt file written
    assert risk_check.HALT_FILE.exists()
    payload = json.loads(risk_check.HALT_FILE.read_text())
    assert payload["reason"] == "max_dd_halt"
    assert payload["set_by"] == "risk_check"


def test_per_position_concentration_cap_fires():
    ok, reasons = risk_check.check(
        targets=_targets(("AAPL", 0.25)),     # 25% > 20% cap
        state=_state(),
    )
    assert ok is False
    assert any("AAPL" in r and "cap" in r.lower() for r in reasons)


def test_gross_exposure_above_100_fires():
    ok, reasons = risk_check.check(
        targets=_targets(("A", 0.10), ("B", 0.10), ("C", 0.10), ("D", 0.10),
                         ("E", 0.10), ("F", 0.10), ("G", 0.10), ("H", 0.10),
                         ("I", 0.10), ("J", 0.10), ("K", 0.10)),       # gross 1.10
        state=_state(),
    )
    assert ok is False
    assert any("gross" in r.lower() for r in reasons)


def test_multiple_violations_enumerate_all():
    ok, reasons = risk_check.check(
        targets=_targets(("X", 0.25)),    # 25% > 20% concentration cap
        state=_state(today_pnl_usd=-3500.0, mark_equity=100_000.0),   # daily loss
    )
    assert ok is False
    assert len(reasons) >= 2
