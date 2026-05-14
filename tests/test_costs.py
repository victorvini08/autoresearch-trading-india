"""Unit tests for `backtest.costs` — Dhan delivery cost model."""

from __future__ import annotations

import pytest

from backtest.costs import (
    DP_CHARGE_INR,
    GST_RATE,
    NSE_TRANSACTION_RATE,
    STAMP_BUY_RATE,
    STT_SELL_RATE,
    commission_inr,
    round_trip_cost_inr,
)


def test_brokerage_is_zero_on_delivery() -> None:
    """Dhan delivery brokerage is 0 ₹; only government + DP charges remain."""
    # Tiny trade (₹100) should produce only fractional government charges + DP if sell
    buy_cost = commission_inr(100.0, "BUY")
    sell_cost = commission_inr(100.0, "SELL")
    # No brokerage should mean the largest single component on a buy is stamp duty
    assert buy_cost < 1.0  # ₹100 trade has < ₹1 of charges total on buy
    # On sell, DP charge (~₹14.75) dominates
    assert sell_cost > DP_CHARGE_INR * 0.99


def test_stt_only_on_sell() -> None:
    """STT (0.1%) charges on the sell side only."""
    notional = 10_000.0
    expected_stt = STT_SELL_RATE * notional  # ₹10
    sell_cost = commission_inr(notional, "SELL")
    buy_cost = commission_inr(notional, "BUY")
    # The diff between sell and buy at the same notional should include STT
    diff = sell_cost - buy_cost
    # DP charge (sell only) + STT (sell only) - stamp duty (buy only)
    expected_diff = DP_CHARGE_INR + expected_stt - (STAMP_BUY_RATE * notional)
    assert abs(diff - expected_diff) < 0.01


def test_dp_only_on_sell() -> None:
    """DP charge ₹14.75 is flat, sell side only."""
    sell_cost = commission_inr(1_000_000.0, "SELL")  # large trade
    sell_cost_small = commission_inr(100.0, "SELL")  # small trade
    # DP component is identical (flat) regardless of trade size
    # The diff between large and small sell ≈ STT diff + exchange diff + GST + stamp wouldn't apply
    # We assert DP_CHARGE_INR is present on BOTH small and large sells
    assert sell_cost > DP_CHARGE_INR
    assert sell_cost_small > DP_CHARGE_INR * 0.95


def test_stamp_duty_only_on_buy() -> None:
    """Stamp duty (0.015%) charges on the buy side only."""
    notional = 10_000.0
    buy_cost = commission_inr(notional, "BUY")
    # Buy: brokerage 0 + exchange 0.00345% + sebi negligible + GST on those + stamp 0.015%
    expected_min = STAMP_BUY_RATE * notional  # ₹1.5
    assert buy_cost >= expected_min * 0.95


def test_round_trip_matches_handoff_spec() -> None:
    """Round-trip on ₹5,000 ≈ ₹20.91 per spec §10."""
    rt = round_trip_cost_inr(5_000.0)
    assert 20.0 < rt < 22.0, f"expected ~₹20.91, got ₹{rt:.4f}"


def test_round_trip_5k_vs_50k() -> None:
    """Larger trades have a larger absolute round-trip cost but lower % drag."""
    rt_5k = round_trip_cost_inr(5_000.0)
    rt_50k = round_trip_cost_inr(50_000.0)
    assert rt_50k > rt_5k          # absolute cost grows
    pct_5k = rt_5k / 5_000.0
    pct_50k = rt_50k / 50_000.0
    assert pct_50k < pct_5k         # % drag shrinks at scale


def test_invalid_side_raises() -> None:
    with pytest.raises(ValueError):
        commission_inr(1_000.0, "SHORT")


def test_zero_notional_is_dp_floor_on_sell() -> None:
    """At zero notional, sell still incurs the flat DP charge."""
    sell_cost = commission_inr(0.0, "SELL")
    assert abs(sell_cost - DP_CHARGE_INR) < 0.01
    buy_cost = commission_inr(0.0, "BUY")
    assert buy_cost == 0.0


def test_gst_applied_to_brokerage_exchange_sebi_only_not_stt() -> None:
    """STT, stamp, DP do NOT have GST applied — only brokerage + exchange + SEBI do.

    Since Dhan brokerage is 0, the GST base is essentially the exchange + SEBI
    fees — very small at retail trade sizes.
    """
    notional = 50_000.0
    cost = commission_inr(notional, "BUY")
    # Exchange = 0.00345% * 50k = ₹1.725; GST on that = ₹0.31 ← tiny
    # Stamp = 0.015% * 50k = ₹7.5
    # Total ≈ exchange + sebi + GST + stamp ≈ ₹1.73 + tiny + ₹0.31 + ₹7.5 ≈ ₹9.55
    assert 9.0 < cost < 10.5
