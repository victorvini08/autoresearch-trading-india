"""In-memory mock of `brokers.dhan.DhanBroker` for v1 paper-only operation.

The mock implements the same public interface as `DhanBroker` so callers can
swap between live and mock by flipping the `DHAN_MOCK=1` env var. Fills are
simulated at the *current* price from `storage/prices.duckdb` with a small
configurable slippage (5 bps by default). Cash and positions are tracked in
memory; the executor reconciles its 8-table ledger from the mock the same
way it would from the real Dhan.

What we deliberately DON'T mock:
- Order-rejection edge cases (circuit hits, halted stocks, margin violation)
  — those manifest in `dhan-live` only; mock always accepts. The risk_check
  step at the executor layer is what defends against them in paper.
- Slippage models tied to volume — biweekly rebalance at our size is well
  below 0.1% of ADV; constant slippage is a fine approximation.

Fundamental constraint: this mock is for *pipeline* validation, not for
strategy alpha validation. Real-money fills can and do behave differently
from this simulator. Real-money launch requires the 4-week paper-validation
gate (vs backtest) plus a positive sealed-test reveal.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb

from brokers.dhan import (
    EXCHANGE_NSE_EQ,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    PRODUCT_CNC,
    STATUS_REJECTED,
    STATUS_TRADED,
    VALIDITY_DAY,
    Fill,
    OrderRequest,
    OrderResponse,
    Position,
)

logger = logging.getLogger(__name__)

DEFAULT_SLIPPAGE_BPS = 5.0       # 0.05% per side


@dataclass
class _MockOrder:
    order_id: str
    request: OrderRequest
    status: str
    fill_price: float | None
    fill_time: datetime | None


@dataclass
class DhanMock:
    """In-memory simulator. Pass the prices DuckDB path so fills can be priced
    from the most-recent close.
    """

    prices_db: Path | None = None
    initial_cash_inr: float = 50_000.0
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS
    mode: str = "dhan-paper"

    _cash: float = field(init=False, default=0.0)
    _positions: dict[str, list] = field(init=False, default_factory=dict)
    # _positions[ticker] = list of [qty, avg_price] lots (FIFO when selling)
    _orders: dict[str, _MockOrder] = field(init=False, default_factory=dict)
    _trades: list[Fill] = field(init=False, default_factory=list)
    _next_order_id: int = field(init=False, default=1)

    def __post_init__(self) -> None:
        self._cash = self.initial_cash_inr

    # ── lifecycle ──
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    # ── instrument resolution (mock accepts any ticker; logs unknowns) ──
    def security_id_for(self, ticker: str) -> str:
        return f"MOCK_{ticker.upper()}"

    # ── price lookup ──
    def _latest_close(self, ticker: str, on_or_before: date | None = None) -> float | None:
        if self.prices_db is None or not Path(self.prices_db).exists():
            return None
        conn = duckdb.connect(str(self.prices_db), read_only=True)
        try:
            if on_or_before:
                row = conn.execute(
                    "SELECT close FROM daily_bars WHERE ticker=? AND dt<=? "
                    "ORDER BY dt DESC LIMIT 1",
                    (ticker.upper(), on_or_before),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT close FROM daily_bars WHERE ticker=? ORDER BY dt DESC LIMIT 1",
                    (ticker.upper(),),
                ).fetchone()
        finally:
            conn.close()
        return float(row[0]) if row and row[0] else None

    # ── cash + positions ──
    def get_cash(self) -> dict:
        return {
            "availableBalance": self._cash,
            "sodLimit": self._cash,
            "collateralAmount": 0.0,
            "utilizedAmount": 0.0,
        }

    def get_positions(self) -> list[Position]:
        out: list[Position] = []
        for ticker, lots in self._positions.items():
            qty = sum(q for q, _ in lots)
            if qty == 0:
                continue
            avg = sum(q * p for q, p in lots) / qty
            close = self._latest_close(ticker) or avg
            out.append(
                Position(
                    ticker=ticker,
                    quantity=qty,
                    average_price=avg,
                    realized_pnl=0.0,
                    unrealized_pnl=(close - avg) * qty,
                )
            )
        return out

    def get_holdings(self) -> list[Position]:
        # Mock treats all positions as settled (no T+1 distinction)
        return self.get_positions()

    # ── orders ──
    def place_order(
        self,
        req: OrderRequest,
        *,
        as_of_date: date | None = None,
    ) -> OrderResponse:
        order_id = f"MOCK_{self._next_order_id:08d}"
        self._next_order_id += 1

        ref_price: float | None = req.price
        if req.order_type == ORDER_TYPE_MARKET:
            ref_price = self._latest_close(req.ticker, on_or_before=as_of_date)
        if ref_price is None:
            # No price data → reject. This is how live would behave if the
            # exchange couldn't price the order.
            order = _MockOrder(
                order_id=order_id,
                request=req,
                status=STATUS_REJECTED,
                fill_price=None,
                fill_time=None,
            )
            self._orders[order_id] = order
            logger.warning(
                "DhanMock REJECT %s %s %s: no reference price",
                req.transaction_type,
                req.quantity,
                req.ticker,
            )
            return OrderResponse(order_id=order_id, status=STATUS_REJECTED)

        slip = ref_price * (self.slippage_bps / 10_000.0)
        if req.transaction_type.upper() == "BUY":
            fill_price = ref_price + slip
        else:
            fill_price = max(0.01, ref_price - slip)

        # Cash + lot mutation
        notional = fill_price * req.quantity
        if req.transaction_type.upper() == "BUY":
            if self._cash < notional:
                order = _MockOrder(
                    order_id=order_id,
                    request=req,
                    status=STATUS_REJECTED,
                    fill_price=None,
                    fill_time=None,
                )
                self._orders[order_id] = order
                logger.warning(
                    "DhanMock REJECT BUY %s %s: insufficient cash (need %.2f, have %.2f)",
                    req.quantity,
                    req.ticker,
                    notional,
                    self._cash,
                )
                return OrderResponse(order_id=order_id, status=STATUS_REJECTED)
            self._cash -= notional
            self._positions.setdefault(req.ticker.upper(), []).append(
                [req.quantity, fill_price]
            )
        else:  # SELL
            lots = self._positions.get(req.ticker.upper(), [])
            held = sum(q for q, _ in lots)
            if held < req.quantity:
                order = _MockOrder(
                    order_id=order_id,
                    request=req,
                    status=STATUS_REJECTED,
                    fill_price=None,
                    fill_time=None,
                )
                self._orders[order_id] = order
                logger.warning(
                    "DhanMock REJECT SELL %s %s: insufficient holdings (need %s, have %s)",
                    req.quantity,
                    req.ticker,
                    req.quantity,
                    held,
                )
                return OrderResponse(order_id=order_id, status=STATUS_REJECTED)
            # FIFO consume
            remaining = req.quantity
            new_lots: list[list] = []
            for q, p in lots:
                if remaining <= 0:
                    new_lots.append([q, p])
                    continue
                if q <= remaining:
                    remaining -= q
                else:
                    new_lots.append([q - remaining, p])
                    remaining = 0
            self._positions[req.ticker.upper()] = new_lots
            self._cash += notional

        fill_time = datetime.utcnow()
        order = _MockOrder(
            order_id=order_id,
            request=req,
            status=STATUS_TRADED,
            fill_price=fill_price,
            fill_time=fill_time,
        )
        self._orders[order_id] = order
        self._trades.append(
            Fill(
                order_id=order_id,
                ticker=req.ticker.upper(),
                side=req.transaction_type.upper(),
                quantity=req.quantity,
                price=fill_price,
                fill_time=fill_time,
                commission=0.0,  # Dhan brokerage = 0 on delivery; STT/DP applied in ledger writer
                raw={"mock": True},
            )
        )
        return OrderResponse(order_id=order_id, status=STATUS_TRADED)

    def get_order(self, order_id: str) -> OrderResponse:
        o = self._orders.get(order_id)
        if not o:
            return OrderResponse(order_id=order_id, status="UNKNOWN")
        return OrderResponse(order_id=o.order_id, status=o.status)

    def cancel_order(self, order_id: str) -> bool:
        # Mock fills synchronously; cancel is a no-op (already in terminal state)
        return False

    def list_today_orders(self) -> list[OrderResponse]:
        return [
            OrderResponse(order_id=o.order_id, status=o.status)
            for o in self._orders.values()
        ]

    def get_fills(self) -> list[Fill]:
        return list(self._trades)

    def wait_for_done(self, order_id: str, **_kw) -> OrderResponse:
        # Mock fills synchronously; never has to actually wait
        time.sleep(0.0)
        return self.get_order(order_id)


__all__ = ["DhanMock", "DEFAULT_SLIPPAGE_BPS"]
