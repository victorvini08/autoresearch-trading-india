"""Cost model for Dhan delivery (CNC) trading on Indian equities.

All charges captured below are LIVE as of 2026-05-14 and traceable to public
NSE / SEBI / NSDL schedules. Dhan-specific component is just the brokerage
(which is ₹0 for delivery); everything else is broker-agnostic and would
apply identically with any other broker.

Per executed order (one side):

  - **Brokerage**          ₹0  (Dhan delivery is free)
  - **Exchange transaction** 0.00345% of notional   (NSE)
  - **SEBI charges**       ₹10 per crore (i.e. notional / 1e7 × 0.10)  — negligible
  - **GST**                18% on (brokerage + exchange + SEBI)
  - **STT**                0.1% of notional, **SELL ONLY**
  - **Stamp duty**         0.015% of notional, **BUY ONLY**
  - **DP charge**          ₹14.75 flat per scrip, **SELL ONLY**
                           (= ₹12.50 NSDL/CDSL + 18% GST)

A round-trip on a ₹5,000 position is ≈ ₹20.91 (0.42% drag); on a ₹50,000
position ≈ ₹72.17 (0.14%). DP charge dominates at small trade sizes — the
strategy's position-count cap is the lever for managing DP drag.
"""

from __future__ import annotations

DEFAULT_SLIPPAGE_BPS = 5.0

# Schedule constants (Indian regulation as of 2026-05; review when SEBI updates)
NSE_TRANSACTION_RATE = 0.0000345        # 0.00345% per side
SEBI_PER_CRORE_INR = 0.10               # ₹0.10 per ₹1 cr notional
GST_RATE = 0.18                         # 18%
STT_SELL_RATE = 0.001                   # 0.1% (sell side only)
STAMP_BUY_RATE = 0.00015                # 0.015% (buy side only)
DP_CHARGE_INR = 14.75                   # flat per scrip per sell (₹12.50 × 1.18 GST)


def commission_inr(notional_inr: float, side: str) -> float:
    """Total realised cost in ₹ for one side of a delivery trade on Dhan.

    `side` ∈ {'BUY', 'SELL'} (case-insensitive). Order-side flows that don't
    match this set raise ValueError — the cost model must not silently treat
    'shrt' or 'cover' as buy.
    """
    s = side.upper().strip()
    if s not in ("BUY", "SELL"):
        raise ValueError(f"unknown side: {side!r}")
    brokerage = 0.0
    exchange = NSE_TRANSACTION_RATE * notional_inr
    sebi = (notional_inr / 1e7) * SEBI_PER_CRORE_INR
    stt = STT_SELL_RATE * notional_inr if s == "SELL" else 0.0
    stamp = STAMP_BUY_RATE * notional_inr if s == "BUY" else 0.0
    dp = DP_CHARGE_INR if s == "SELL" else 0.0
    gst_base = brokerage + exchange + sebi
    gst = GST_RATE * gst_base
    return brokerage + exchange + sebi + stt + stamp + dp + gst


def round_trip_cost_inr(notional_inr: float) -> float:
    """Commission + government charges for buy then sell at the same notional.

    Convenience for sizing and reporting. Does NOT account for slippage —
    slippage is modeled separately by the backtest engine and the
    broker-mock layer.
    """
    return commission_inr(notional_inr, "BUY") + commission_inr(notional_inr, "SELL")


# Backwards-compat alias — the predecessor engine.py imported `commission_usd`
# and `DEFAULT_SLIPPAGE_BPS` from this module. We re-export an alias so the
# engine keeps working unchanged until Phase 5/6 sweeps engine.py too. The
# alias does NOT convert currencies; the value is INR when the executor mode
# is dhan-*. Callers must rely on the mode tag for the currency.
def commission_usd(notional: float, side: str) -> float:  # noqa: N802 — back-compat
    """Back-compat alias for `commission_inr`. Returns ₹ for dhan-* modes.

    Deprecated; prefer `commission_inr`. The name is preserved so the engine
    import doesn't break during the carry-over phase.
    """
    return commission_inr(notional, side)


__all__ = [
    "DEFAULT_SLIPPAGE_BPS",
    "NSE_TRANSACTION_RATE",
    "SEBI_PER_CRORE_INR",
    "GST_RATE",
    "STT_SELL_RATE",
    "STAMP_BUY_RATE",
    "DP_CHARGE_INR",
    "commission_inr",
    "round_trip_cost_inr",
    "commission_usd",
]
