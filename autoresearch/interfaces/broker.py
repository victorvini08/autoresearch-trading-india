"""Broker extension point — implement to trade a new venue.

A Broker is the order/position/cash gateway between the executor and a real
(or simulated) brokerage account. The reference implementations are
``DhanBroker`` (live Dhan HQ Trading API) and ``DhanMock`` (in-memory paper).

The method set below is the common surface both reference classes already
expose, so the executor can swap between live and paper by construction.
Concrete brokers may accept extra keyword arguments (e.g. ``place_order``'s
``as_of_date``); the abstract signatures use ``*`` / ``**kwargs`` to stay
compatible with both.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Broker(ABC):
    """Order/position/cash gateway. Reference: DhanBroker, DhanMock."""

    @abstractmethod
    def connect(self) -> None:
        """Establish/verify the broker session (no-op for the mock)."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the broker session."""

    @abstractmethod
    def security_id_for(self, ticker: str) -> str:
        """Map a ticker to the broker's internal security identifier."""

    @abstractmethod
    def get_cash(self) -> dict:
        """Return available cash / fund limits."""

    @abstractmethod
    def get_positions(self) -> list:
        """Return currently open (intraday/unsettled) positions."""

    @abstractmethod
    def get_holdings(self) -> list:
        """Return settled long-term holdings."""

    @abstractmethod
    def place_order(self, req, *, as_of_date=None):
        """Place an order described by ``req``; return the broker's response."""

    @abstractmethod
    def get_order(self, order_id: str):
        """Return the current status of a single order."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order; return True on success."""

    @abstractmethod
    def list_today_orders(self) -> list:
        """Return today's orders."""

    @abstractmethod
    def get_fills(self) -> list:
        """Return today's executions (with commission where available)."""

    @abstractmethod
    def wait_for_done(self, order_id: str, **kwargs):
        """Block until the order reaches a terminal state; return it."""
