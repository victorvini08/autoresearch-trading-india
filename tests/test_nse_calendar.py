"""Unit tests for data.nse_calendar — the trading-day guard's source of truth."""
from __future__ import annotations

from datetime import date

from data import nse_calendar as cal


def test_muharram_2026_is_a_holiday():
    """The 2026-06-26 incident date must be a recognised NSE holiday."""
    assert cal.is_nse_holiday(date(2026, 6, 26)) is True
    assert cal.is_trading_day(date(2026, 6, 26)) is False


def test_normal_weekday_is_a_trading_day():
    # 2026-06-25 (Thursday) — a normal session, the day TATASTEEL broke its MA.
    assert cal.is_trading_day(date(2026, 6, 25)) is True
    # 2026-06-29 (Monday) — the session the deferred exit should land on.
    assert cal.is_trading_day(date(2026, 6, 29)) is True


def test_weekend_is_not_a_trading_day():
    assert cal.is_trading_day(date(2026, 6, 27)) is False  # Saturday
    assert cal.is_trading_day(date(2026, 6, 28)) is False  # Sunday


def test_a_spread_of_known_2026_holidays():
    for d in (
        date(2026, 1, 26),   # Republic Day
        date(2026, 3, 3),    # Holi
        date(2026, 10, 2),   # Gandhi Jayanti
        date(2026, 12, 25),  # Christmas
    ):
        assert cal.is_nse_holiday(d) is True
        assert cal.is_trading_day(d) is False


def test_calendar_currency_horizon():
    assert cal.is_calendar_current(date(2026, 6, 26)) is True
    # Beyond the maintained horizon → must report itself stale so callers warn.
    assert cal.is_calendar_current(date(2099, 1, 4)) is False
