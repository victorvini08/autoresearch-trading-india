"""Regression: ingest_prices is the carried-over compatibility shim.

daily_update / precompute_macro_cache call it with ISO-date STRINGS;
ingest_range iterates dates and does d.weekday(), so the wrapper MUST
normalise str/None → date before calling ingest_range. A regression here
breaks the entire daily paper-trading cadence (observed 2026-05-18:
"'str' object has no attribute 'weekday'").
"""
from __future__ import annotations

from datetime import date

import data.ingest_prices as ip


def _capture(monkeypatch):
    seen: dict = {}

    def fake_ingest_range(db, start, end, *, tickers=None):
        seen["start"], seen["end"] = start, end
        return {"rows_written": 0, "days_skipped": 0}

    monkeypatch.setattr(ip, "ingest_range", fake_ingest_range)
    return seen


def test_string_args_are_coerced_to_date(monkeypatch):
    seen = _capture(monkeypatch)
    ip.ingest_prices({"RELIANCE"}, "2026-05-15", "2026-05-18")
    assert seen["start"] == date(2026, 5, 15)
    assert seen["end"] == date(2026, 5, 18)
    assert isinstance(seen["start"], date) and isinstance(seen["end"], date)


def test_date_args_pass_through(monkeypatch):
    seen = _capture(monkeypatch)
    ip.ingest_prices(None, date(2026, 5, 1), date(2026, 5, 3))
    assert seen["start"] == date(2026, 5, 1)
    assert seen["end"] == date(2026, 5, 3)


def test_none_defaults_are_dates(monkeypatch):
    seen = _capture(monkeypatch)
    ip.ingest_prices()
    assert isinstance(seen["start"], date) and isinstance(seen["end"], date)
    assert seen["start"] <= seen["end"]
