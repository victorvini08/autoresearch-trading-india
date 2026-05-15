"""Audit-2026-05-15 Fix B regression tests: point-in-time universe + the
leak-free-execution invariant.
"""
from datetime import date
from pathlib import Path

import prepare
from strategy import resolve_active_universe

UBD = {
    date(2022, 1, 1): frozenset({"A", "B"}),
    date(2022, 6, 1): frozenset({"B", "C"}),
    date(2023, 1, 1): frozenset({"C", "D"}),
}
SD = sorted(UBD)


def test_resolve_none_when_no_universe_injected():
    assert resolve_active_universe(None, None, date(2022, 7, 1)) is None
    assert resolve_active_universe({}, [], date(2022, 7, 1)) is None


def test_resolve_empty_before_earliest_snapshot():
    # MUST NOT fall forward to a future snapshot (that is the look-ahead bug).
    assert resolve_active_universe(UBD, SD, date(2021, 12, 31)) == set()


def test_resolve_picks_most_recent_on_or_before():
    assert resolve_active_universe(UBD, SD, date(2022, 1, 1)) == {"A", "B"}
    assert resolve_active_universe(UBD, SD, date(2022, 5, 31)) == {"A", "B"}
    assert resolve_active_universe(UBD, SD, date(2022, 6, 1)) == {"B", "C"}
    assert resolve_active_universe(UBD, SD, date(2022, 9, 9)) == {"B", "C"}
    assert resolve_active_universe(UBD, SD, date(2025, 1, 1)) == {"C", "D"}


def test_pit_universe_excludes_future_snapshots(monkeypatch):
    """prepare._pit_universe must use ONLY snapshots dated <= window_end."""
    snaps = [date(2022, 1, 1), date(2022, 6, 1), date(2023, 1, 1)]
    monkeypatch.setattr(prepare, "snapshot_dates", lambda: snaps)
    monkeypatch.setattr(
        prepare, "get_universe_at",
        lambda d: {date(2022, 1, 1): ["A", "B"],
                   date(2022, 6, 1): ["B", "C"],
                   date(2023, 1, 1): ["C", "D"]}[d],
    )
    members, ubd = prepare._pit_universe(date(2022, 6, 1))
    assert set(ubd) == {date(2022, 1, 1), date(2022, 6, 1)}  # no 2023 leak
    assert members == ["A", "B", "C"]


def test_pit_universe_empty_when_window_predates_all(monkeypatch):
    monkeypatch.setattr(prepare, "snapshot_dates", lambda: [date(2023, 1, 1)])
    monkeypatch.setattr(prepare, "get_universe_at", lambda d: ["X"])
    members, ubd = prepare._pit_universe(date(2021, 1, 1))
    assert members == [] and ubd == {}


def test_engine_has_no_cheat_on_close():
    """Leak-free-execution invariant: orders fill at next-bar OPEN. A future
    edit enabling cheat-on-close/open would silently reintroduce price
    look-ahead — this sentinel fails loudly if so."""
    src = Path("backtest/engine.py").read_text()
    assert "set_coc(True)" not in src
    assert "cheat_on_close" not in src
    assert "cheat_on_open=True" not in src
    assert "coc=True" not in src
