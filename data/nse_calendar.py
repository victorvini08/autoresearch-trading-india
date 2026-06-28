"""NSE trading-day calendar — weekend + published-holiday awareness.

Why this exists: the execution guard in ``scripts/run_live.py`` needs to know,
for a given calendar date, whether NSE actually holds a session. Weekends are
mechanical (``weekday() >= 5``), but **holidays are NOT derivable from the price
feed at decision time** — on the morning of a holiday the feed looks identical
to a normal trading morning (both lag exactly one session, because today's bhav
is only published after the close). So the official holiday list MUST be carried
explicitly here.

This was the root cause of the 2026-06-26 incident: Muharram is an NSE holiday,
but the old guard skipped only weekends, so the 10:15 cron ran on the holiday,
keyed its decision to the last available bar (06-25), and the mock "filled" a
real structural MA-exit of TATASTEEL on a closed market. With this calendar the
guard skips the holiday and the signal defers to the next session.

Source: NSE "Market Timings & Holidays" (equity segment), cross-checked against
ClearTax and Zerodha holiday calendars (verified 2026-06).

  >>> MAINTENANCE: this list must be UPDATED ANNUALLY from
  >>> https://www.nseindia.com/resources/exchange-communication-holidays
  >>> Add the new year's dates AND its year to ``_COVERED_YEARS``. Until then,
  >>> ``is_calendar_current()`` lets callers warn that holiday coverage lapsed.
"""
from __future__ import annotations

from datetime import date

# Full-day NSE equity trading holidays. Weekend-coinciding holidays are kept for
# completeness (harmless — the weekday rule already skips them). 2026-11-08 is
# the Diwali "Muhurat" session (a Sunday); we neither trade weekends nor the
# Muhurat session, so it is a non-trading day for us either way.
NSE_HOLIDAYS: frozenset[date] = frozenset({
    date(2026, 1, 15),   # Maharashtra municipal elections
    date(2026, 1, 26),   # Republic Day
    date(2026, 2, 15),   # Maha Shivaratri (Sunday)
    date(2026, 3, 3),    # Holi
    date(2026, 3, 21),   # Id-Ul-Fitr (Saturday)
    date(2026, 3, 26),   # Shri Ram Navami
    date(2026, 3, 31),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 6, 26),   # Muharram  <- the 2026-06-26 incident
    date(2026, 8, 15),   # Independence Day (Saturday)
    date(2026, 9, 14),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 8),   # Diwali Laxmi Pujan / Muhurat (Sunday)
    date(2026, 11, 10),  # Diwali Balipratipada
    date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
    date(2026, 12, 25),  # Christmas
})

# Years for which NSE_HOLIDAYS is authoritative. Outside these the weekend rule
# still holds, but a weekday holiday could slip through — callers should warn.
_COVERED_YEARS: frozenset[int] = frozenset({2026})


def is_nse_holiday(d: date) -> bool:
    """True iff `d` is a published NSE full-day trading holiday."""
    return d in NSE_HOLIDAYS


def is_trading_day(d: date) -> bool:
    """True iff NSE holds a normal session on `d` (a weekday that is not a
    published holiday). This is the single predicate the execution guard uses."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def is_calendar_current(d: date) -> bool:
    """False when `d`'s year is beyond the maintained holiday horizon. The
    weekend rule still applies, but holidays for that year are unknown until the
    calendar is updated — callers can use this to emit a maintenance warning."""
    return d.year in _COVERED_YEARS
