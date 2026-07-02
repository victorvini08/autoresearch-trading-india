"""Cost-model extension point — implement for a new market's fees/taxes.

Returns realised trading cost in the account currency. The reference
implementation is ``autoresearch.backtest.costs.IndiaCostModel`` (Dhan delivery:
₹0 brokerage + exchange/SEBI/GST/STT/stamp + flat DP charge on sells).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CostModel(ABC):
    """Per-trade cost in the account currency."""

    @abstractmethod
    def commission(self, notional: float, side: str) -> float:
        """Total realised cost for one side of a trade. ``side`` in {BUY, SELL}."""

    @abstractmethod
    def round_trip_cost(self, notional: float) -> float:
        """Commission for a buy then sell at the same notional (excludes slippage)."""
