"""Write an ExecutionResult into storage/portfolio.duckdb.

This is the shared writer the spec §4.5 calls for. It is called by:
  - scripts/run_live.py via scripts/executors/dhan.DhanExecutor
    (Phase 4) in both dhan-paper and dhan-live modes

The function is intentionally tight: it accepts already-observed orders
and fills (the executor produced them), and never tries to model or
infer them. All sourcing of fill prices, qty, and timing happens upstream
in scripts/executors/dhan.py (against brokers.dhan_mock for dhan-paper
or brokers.dhan for dhan-live).

Write order matters:
  1. submitted_orders  (status='pending' or final, depending)
  2. actual_fills      (only for orders that filled)
  3. cash_ledger       (buy/sell + commission entries, signed)
  4. position_lots     (open on buy; consume FIFO on sell)
  5. realized_trades   (one row per consumed lot)
  6. broker_positions  (EOD snapshot)
  7. discrepancies     (anything unusual — captured by caller, written here)

All wrapped in a single transaction. All currency values are INR (see
the CURRENCY constant below; Phase 5 wires the `currency` column on
portfolio_db tables).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

import duckdb

from backtest.costs import commission_usd, DEFAULT_SLIPPAGE_BPS
from storage import portfolio_db


# All rows written by this writer are denominated in INR (Indian mode is
# dhan-paper / dhan-live; no cross-currency mode exists in v1). The actual
# `currency` column on portfolio_db tables is added by Phase 5 (handoff §3,
# storage/portfolio_db.py tweaks). Until that lands, this constant documents
# the invariant; once the column exists the insert_* calls below should be
# updated to pass `currency=CURRENCY`.
CURRENCY = "INR"


@dataclass(frozen=True)
class DiscrepancyRow:
    kind: str
    ticker: str | None
    expected: str | None
    actual: str | None
    resolution: str | None
    notes: str | None


@dataclass(frozen=True)
class WriteSummary:
    """What got written. Returned so risk_check.post_execution_check()
    and daily_report.py can summarize without re-querying the DB."""

    as_of_date: date
    mode: str
    n_orders: int
    n_fills: int
    n_discrepancies: int
    gross_buy_usd: float
    gross_sell_usd: float
    total_commission_usd: float


def write_execution_result(
    conn: duckdb.DuckDBPyConnection,
    *,
    as_of_date: date,
    mode: Literal["dhan-paper", "dhan-live"],
    orders,  # list of submitted orders from the Dhan executor (Phase 4)
    fills,  # list of fills from the Dhan executor (Phase 4)
    new_positions: dict[str, tuple[float, float]],  # {ticker: (qty, mark_price)}
    discrepancies: list[DiscrepancyRow] | None = None,
) -> WriteSummary:
    """Single-transaction write of a browser-executed (or simulated) trade day.

    new_positions is supplied by the caller — for real-mode it comes from
    re-reading the portfolio page after fills land; for paper it's
    computed from prior positions + filled orders.

    Returns a WriteSummary the orchestrator forwards to daily_report.
    """
    discrepancies = discrepancies or []
    n_orders = 0
    n_fills = 0
    gross_buy = 0.0
    gross_sell = 0.0
    total_commission = 0.0

    # Aggregate filled qty per order_id so the final status_order_id ->
    # submitted_orders.status update reflects the actual terminal state:
    # TRADED (full fill), PART_TRADED (some fills, less than requested),
    # or whatever the broker reported originally (REJECTED / CANCELLED /
    # EXPIRED / PENDING for orders that never filled).
    filled_qty_by_order: dict[str, float] = {}
    requested_qty_by_order: dict[str, float] = {o.order_id: o.quantity for o in orders}

    conn.execute("BEGIN TRANSACTION")
    try:
        # 1. submitted_orders
        for o in orders:
            portfolio_db.insert_order(
                conn,
                order_id=o.order_id,
                submitted_at=_to_naive_utc(o.submitted_at),
                as_of_date=as_of_date,
                ticker=o.ticker,
                side=o.side,
                order_type=o.order_type,
                quantity=o.quantity,
                limit_price=o.limit_price,
                status=o.status,
                mode=mode,
            )
            n_orders += 1

        # 2. actual_fills + 3. cash_ledger + 4. position_lots + 5. realized_trades
        for f in fills:
            # India cost model is side-aware (DP charge ₹14.75 on SELL
            # only, STT sell-side, stamp buy-side); commission_usd requires
            # `side`. Carried-over call predated the side-aware model.
            commission = commission_usd(f.fill_price * f.quantity, f.side)
            portfolio_db.insert_fill(
                conn,
                fill_id=f.fill_id,
                order_id=f.order_id,
                filled_at=_to_naive_utc(f.filled_at),
                ticker=f.ticker,
                side=f.side,
                quantity=f.quantity,
                fill_price=f.fill_price,
                commission=commission,
                slippage_bps=DEFAULT_SLIPPAGE_BPS,
                mode=mode,
            )
            filled_qty_by_order[f.order_id] = (
                filled_qty_by_order.get(f.order_id, 0.0) + f.quantity
            )
            # CLAUDE.md hard constraint #5: cash-ledger entries are anchored
            # to the FILL date, not the signal date. For signal-on-T fills-on-T
            # (our Indian intraday flow) they coincide. They diverge whenever
            # a fill arrives outside the signal-day boundary (delayed Dhan
            # acknowledgement near the 15:30 close, GTT, etc.); pinning to
            # the signal date in that case would mis-date cash and tax lots.
            fill_date = f.filled_at.date()
            portfolio_db.insert_cash_entry(
                conn,
                entry_id=uuid.uuid4().hex,
                entry_at=_to_naive_utc(f.filled_at),
                as_of_date=fill_date,
                kind=f.side,
                amount_usd=(-f.fill_price * f.quantity) if f.side == "buy" else (f.fill_price * f.quantity),
                notes=f"{f.ticker} {f.side} {f.quantity} @ {f.fill_price:.4f}",
                mode=mode,
            )
            portfolio_db.insert_cash_entry(
                conn,
                entry_id=uuid.uuid4().hex,
                entry_at=_to_naive_utc(f.filled_at),
                as_of_date=fill_date,
                kind="commission",
                amount_usd=-commission,
                notes=f"{f.ticker} {f.side} {f.quantity} commission",
                mode=mode,
            )
            n_fills += 1
            total_commission += commission
            if f.side == "buy":
                gross_buy += f.fill_price * f.quantity
                portfolio_db.open_lot(
                    conn,
                    lot_id=uuid.uuid4().hex,
                    ticker=f.ticker,
                    buy_fill_id=f.fill_id,
                    buy_date=f.filled_at.date(),
                    buy_price=f.fill_price,
                    qty=f.quantity,
                    mode=mode,
                )
            else:
                gross_sell += f.fill_price * f.quantity
                _consume_lots_fifo(
                    conn,
                    ticker=f.ticker,
                    sell_qty=f.quantity,
                    sell_price=f.fill_price,
                    sell_fill_id=f.fill_id,
                    sell_date=f.filled_at.date(),
                    mode=mode,
                    discrepancy_log=discrepancies,
                    as_of_date=as_of_date,
                )

        # Resolve final submitted_orders.status per order from realised fills.
        # The original status came from place_order (PENDING / TRANSIT / TRADED /
        # REJECTED / PART_TRADED), but the truth at end-of-day is the sum of
        # actual_fills vs requested qty:
        #   filled == requested  →  TRADED       (clean fill)
        #   0 < filled < req     →  PART_TRADED  (broker filled some, dropped rest)
        # Orders with zero fills keep whatever status place_order recorded —
        # so REJECTED / CANCELLED / EXPIRED / TIMEOUT survive unchanged.
        # No more lowercase synthetic "filled" string that masks partials.
        for order_id, filled in filled_qty_by_order.items():
            requested = requested_qty_by_order.get(order_id, 0.0)
            if requested <= 0:
                continue
            if abs(filled - requested) < 1e-6:
                final_status = "TRADED"
            elif filled > 0:
                final_status = "PART_TRADED"
            else:
                continue  # zero-fill order — leave broker-reported status
            portfolio_db.update_order_status(conn, order_id, final_status)

        # 6. broker_positions EOD snapshot
        for ticker, (qty, mark_price) in new_positions.items():
            if qty == 0:
                conn.execute(
                    "DELETE FROM broker_positions "
                    "WHERE snapshot_date = ? AND ticker = ? AND mode = ?",
                    [as_of_date, ticker, mode],
                )
                continue
            portfolio_db.upsert_position(
                conn,
                snapshot_date=as_of_date,
                ticker=ticker,
                quantity=qty,
                avg_entry_price=None,
                mark_price=mark_price,
                mark_value=qty * mark_price,
                mode=mode,
            )

        # 7. discrepancies
        for dr in discrepancies:
            portfolio_db.insert_discrepancy(
                conn,
                discrepancy_id=uuid.uuid4().hex,
                detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                as_of_date=as_of_date,
                kind=dr.kind,
                ticker=dr.ticker,
                expected=dr.expected,
                actual=dr.actual,
                resolution=dr.resolution,
                notes=dr.notes,
                mode=mode,
            )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return WriteSummary(
        as_of_date=as_of_date,
        mode=mode,
        n_orders=n_orders,
        n_fills=n_fills,
        n_discrepancies=len(discrepancies),
        gross_buy_usd=gross_buy,
        gross_sell_usd=gross_sell,
        total_commission_usd=total_commission,
    )


def _consume_lots_fifo(
    conn: duckdb.DuckDBPyConnection,
    *,
    ticker: str,
    sell_qty: float,
    sell_price: float,
    sell_fill_id: str,
    sell_date: date,
    mode: str,
    discrepancy_log: list[DiscrepancyRow],
    as_of_date: date,
) -> None:
    """FIFO consumption + realized_trades + gross tax computation.

    Mirrors paper_trade.py L698-L752. Tax is recorded per-trade for audit
    (Schedule FA) but NOT withheld from cash — real STCG is FY-netted at
    report time via portfolio_db.get_ytd_tax_estimate.
    """
    remaining = sell_qty
    open_lots = portfolio_db.get_open_lots_fifo(conn, ticker=ticker, mode=mode)
    for lot_id, buy_date, buy_price, qty_open in open_lots:
        if remaining <= 1e-9:
            break
        take = min(qty_open, remaining)
        pnl = (sell_price - buy_price) * take
        holding_days = (sell_date - buy_date).days
        tax_paid = portfolio_db.compute_tax(pnl, holding_days)
        portfolio_db.consume_lot(conn, lot_id=lot_id, qty_consumed=take)
        portfolio_db.insert_realized_trade(
            conn,
            trade_id=uuid.uuid4().hex,
            sell_fill_id=sell_fill_id,
            buy_lot_id=lot_id,
            ticker=ticker,
            buy_date=buy_date,
            sell_date=sell_date,
            qty=take,
            buy_price=buy_price,
            sell_price=sell_price,
            realized_pnl_usd=pnl,
            holding_days=holding_days,
            tax_paid_usd=tax_paid,
            mode=mode,
        )
        remaining -= take

    if remaining > 1e-6:
        discrepancy_log.append(
            DiscrepancyRow(
                kind="sell_without_lot",
                ticker=ticker,
                expected=f"open_qty>={sell_qty:.6f}",
                actual=f"unmatched={remaining:.6f}",
                resolution="auto_skipped",
                notes="sell exceeded open lot qty; tax accounting partial",
            )
        )


def _to_naive_utc(dt: datetime) -> datetime:
    """duckdb's TIMESTAMP column doesn't carry tz — strip after converting."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
