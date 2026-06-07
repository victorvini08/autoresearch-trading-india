"""Tests for backtest/sealed_budget.py (Step 5.d).

The sealed test is a CONSUMABLE: its validity comes from being untouched by any
selection decision, and the 2025-01..2026-05 window was already spent selecting
the locked strategy. So a fresh reveal is only legitimate on genuinely-new
forward data that has accrued AFTER that frozen boundary — never on the burned
window — and only sparingly (one per quarter). Until enough fresh data exists,
every candidate is routed to the shadow book.
"""
from __future__ import annotations

from datetime import date

import backtest.sealed_budget as B


def test_frozen_boundary_matches_prepare_sealed_end():
    # The initial frozen boundary IS the end of the burned sealed window.
    import prepare
    assert B.INITIAL_FROZEN_BOUNDARY == prepare.BACKTEST_END


def test_defers_when_insufficient_fresh_data():
    # Today is weeks after the lock — nowhere near MIN_FRESH_SEALED_MONTHS.
    d = B.assess_sealed_budget(date(2026, 6, 7))
    assert d.available is False
    assert d.status == "DEFERRED_TO_SHADOW"
    assert "shadow" in d.reason.lower()


def test_available_once_enough_fresh_data_accrues():
    d = B.assess_sealed_budget(date(2027, 1, 1))
    assert d.available is True
    assert d.status == "AVAILABLE"
    assert d.window_end == date(2027, 1, 1)


def test_fresh_window_never_touches_the_burned_window():
    d = B.assess_sealed_budget(date(2027, 1, 1))
    # The window can only start strictly AFTER the burned boundary.
    assert d.window_start > B.INITIAL_FROZEN_BOUNDARY
    assert d.window_start == date(2026, 5, 15)


def test_quarterly_budget_blocks_a_second_reveal_same_quarter():
    d = B.assess_sealed_budget(
        date(2027, 1, 15), last_reveal_at=date(2027, 1, 2))
    assert d.available is False
    assert "quarter" in d.reason.lower()


def test_quarterly_budget_allows_next_quarter():
    # Last reveal in Q4-2026; today in Q1-2027 with enough data -> allowed.
    d = B.assess_sealed_budget(
        date(2027, 1, 20), last_reveal_at=date(2026, 12, 20))
    assert d.available is True


def test_custom_frozen_boundary_advances_window():
    # After a prior reveal advanced the boundary, the next fresh window starts
    # after the new boundary.
    d = B.assess_sealed_budget(
        date(2027, 8, 1), frozen_boundary=date(2027, 1, 1))
    assert d.available is True
    assert d.window_start == date(2027, 1, 2)
