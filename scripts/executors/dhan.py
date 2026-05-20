"""DhanExecutor — per-day execution implementing the Executor protocol.

Pipeline (atomic, idempotent):

    1. Pre-flight: halt.json, risk gates, trading-window guard
    2. Signal extraction: load broker state + last-rebalance overlay
       → target_fraction dict
    3. Risk check: max position, max gross, sector cap
    4. FRACTION_CHANGE_THRESHOLD suppression (US repo learnings §4.2 —
       suppress when target_fraction has moved < 0.5pp from previous)
    5. Order construction: convert target_fractions → integer share orders
    6. Place orders (Dhan or mock); poll until terminal state
    7. Reconcile fills against intent
    8. Write 8-table ledger via storage.portfolio_db inside a single
       BEGIN/COMMIT transaction

Mode selection: `DHAN_MOCK=1` env var (or constructor arg) chooses the
mock broker. Same code path for mock vs live — no mode-specific branches
beyond broker construction.

Note on currency: `ExecutionSummary` field names retain the `_usd` suffix
from the predecessor protocol; for `mode in {'dhan-paper','dhan-live'}` the
values are INR. The `currency` column on cash_ledger rows is the
authoritative tag.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from types import SimpleNamespace
from pathlib import Path

from brokers.dhan import (
    ORDER_TYPE_MARKET,
    STATUS_REJECTED,
    STATUS_TRADED,
    OrderRequest,
)
from scripts.executors.protocol import (
    ExecutionSummary,
    PreflightSkipped,
)
from scripts.halt import set_halt, show_halt

logger = logging.getLogger(__name__)

FRACTION_CHANGE_THRESHOLD = 0.005   # 0.5pp — US repo learnings §4.2
DEFAULT_PRICES_DB = Path("storage/prices.duckdb")
DEFAULT_PORTFOLIO_DB = Path("storage/portfolio.duckdb")


@dataclass
class DhanExecutor:
    """Implements the Executor protocol for Dhan (live or mock).

    Construct with explicit dependencies for testability; defaults match the
    standard runtime layout (storage/ at repo root).
    """

    mode: str = "dhan-paper"
    prices_db: Path = DEFAULT_PRICES_DB
    portfolio_db: Path = DEFAULT_PORTFOLIO_DB
    halt_file: Path = Path("halt.json")
    broker: object | None = None          # DhanBroker or DhanMock; constructed lazily
    initial_cash_inr: float = 50_000.0
    fraction_change_threshold: float = FRACTION_CHANGE_THRESHOLD

    def __post_init__(self) -> None:
        if self.broker is None:
            self.broker = self._construct_broker()

    def _construct_broker(self):
        use_mock = (
            self.mode == "dhan-paper"
            or os.environ.get("DHAN_MOCK", "0") in ("1", "true", "True")
        )
        if use_mock:
            from brokers.dhan_mock import DhanMock
            from scripts.premarket_scan import _default_quote_fetch

            def _yfinance_today_open(ticker: str) -> float | None:
                """Phase B (close→open fix): live paper-fill pricing —
                today's NSE open via yfinance. Reuses premarket_scan's
                already-tested fetcher (same Yahoo .NS / ^INDIAVIX
                symbol resolution + the 'must be today's row' guard +
                fail-closed semantics). Returns the open or None;
                DhanMock falls back to the bhav close on None."""
                row = _default_quote_fetch(ticker)
                if not row:
                    return None
                return row.get("premarket_price")

            return DhanMock(
                prices_db=self.prices_db,
                portfolio_db=self.portfolio_db,
                fill_price_fetcher=_yfinance_today_open,
                initial_cash_inr=self.initial_cash_inr,
                mode=self.mode,
            )
        from brokers.dhan import DhanBroker

        return DhanBroker()

    # ──────────────────────────────────────────────────────────
    # Executor protocol entry-point
    # ──────────────────────────────────────────────────────────

    def execute_day(
        self,
        as_of_date: date,
        *,
        strategy_module: str = "strategy",
        source_tag: str = "run_live",
        skips: set[str] | None = None,
    ) -> ExecutionSummary:
        """`skips`: tickers flagged by premarket_scan (>=5% pre-open move or
        VIX hard-halt). Built orders touching these names are dropped after
        construction — leaves any current position in place (no buy, no
        sell) rather than transacting into a violently-moving tape."""
        notes: list[str] = []
        skips = set(s.upper() for s in (skips or ()))

        # 1. Pre-flight: halt (halt.json is global — not per-mode)
        halt_payload = show_halt()
        if halt_payload is not None:
            return ExecutionSummary(
                mode=self.mode,
                as_of_date=as_of_date,
                fill_date=None,
                skipped=True,
                skipped_reason=f"halt.json active: {halt_payload.get('reason', '?')}",
            )

        # 2. Signal extraction (broker state + last-rebalance overlay)
        try:
            from scripts.signal_today import generate_signals

            signals_result = generate_signals(
                target_date=as_of_date,
                strategy_module_name=strategy_module,
            )
            # generate_signals returns {"targets": [{"ticker","target_fraction"},...],
            # "exits":[...]} — a LIST of entry rows. _build_orders expects a
            # {ticker: target_fraction} MAPPING (a ticker absent from the map is
            # liquidated, which is exactly how `exits` should manifest). Adapt
            # the shape here; tolerate the legacy mapping form defensively so an
            # unexpected shape degrades to {} rather than crashing the cron.
            raw_targets = (
                signals_result.get("targets", [])
                if isinstance(signals_result, dict)
                else getattr(signals_result, "targets", []) or []
            )
            if isinstance(raw_targets, dict):
                targets = {k: float(v) for k, v in raw_targets.items()}
            elif isinstance(raw_targets, list):
                targets = {
                    r["ticker"]: float(r["target_fraction"])
                    for r in raw_targets
                    if isinstance(r, dict)
                    and "ticker" in r and "target_fraction" in r
                }
            else:
                targets = {}
        except PreflightSkipped as e:
            if e.set_halt:
                set_halt(e.reason, set_by="DhanExecutor")
            return ExecutionSummary(
                mode=self.mode,
                as_of_date=as_of_date,
                fill_date=None,
                skipped=True,
                skipped_reason=e.reason,
                halt_set=e.set_halt,
            )

        if not targets:
            return ExecutionSummary(
                mode=self.mode,
                as_of_date=as_of_date,
                fill_date=None,
                skipped=True,
                skipped_reason="strategy produced empty target_fractions (non-rebalance day)",
            )

        # 3. Convert target_fractions → integer share orders
        order_reqs, gross_buy, gross_sell = self._build_orders(
            as_of_date=as_of_date,
            targets=targets,
        )
        # 3b. Drop orders touching premarket-flagged tickers (gap/halt). For
        #     held names this leaves the position in place (no sell into a
        #     gap-down); for new entries this defers them to the next
        #     rebalance day (no buy into a gap-up).
        if skips and order_reqs:
            before = len(order_reqs)
            dropped: dict[str, float] = {}
            kept = []
            for req in order_reqs:
                if req.ticker.upper() in skips:
                    notional = float(req.quantity) * float(req.price or 0.0)
                    dropped[req.ticker.upper()] = notional
                    if req.transaction_type.upper() == "BUY":
                        gross_buy -= notional
                    else:
                        gross_sell -= notional
                else:
                    kept.append(req)
            order_reqs = kept
            if dropped:
                notes.append(
                    f"premarket: dropped {before - len(order_reqs)} orders for "
                    f"gap-flagged tickers {sorted(dropped)}"
                )
        if not order_reqs:
            notes.append("FRACTION_CHANGE_THRESHOLD suppressed all rebalance deltas")
            return ExecutionSummary(
                mode=self.mode,
                as_of_date=as_of_date,
                fill_date=as_of_date,
                n_orders=0,
                n_fills=0,
                gross_buy_usd=0.0,
                gross_sell_usd=0.0,
                total_commission_usd=0.0,
                notes=notes,
            )

        # 4. Place orders + wait for terminal status
        placed: list = []
        for req in order_reqs:
            try:
                if hasattr(self.broker, "place_order"):
                    # as_of_date drives Phase B fill-pricing in the mock
                    # (today's NSE open via yfinance); DhanBroker ignores it.
                    resp = self.broker.place_order(req, as_of_date=as_of_date)
                else:
                    raise RuntimeError("broker has no place_order")
                placed.append((req, resp))
            except Exception as e:
                logger.error("place_order %s %s failed: %s", req.transaction_type, req.ticker, e)
                notes.append(
                    f"place_order failed for {req.transaction_type} {req.quantity} {req.ticker}: {e}"
                )

        for req, resp in list(placed):
            if resp.status == STATUS_TRADED:
                continue
            if resp.status == STATUS_REJECTED:
                notes.append(f"order rejected: {req.transaction_type} {req.quantity} {req.ticker}")
                continue
            try:
                final = self.broker.wait_for_done(resp.order_id)
                if final.status == STATUS_REJECTED:
                    notes.append(f"post-wait reject {req.ticker}: {final.status}")
            except Exception as e:
                logger.error("wait_for_done %s failed: %s", resp.order_id, e)

        # 5. Reconcile fills
        fills = list(self.broker.get_fills())
        n_fills = len(fills)
        # We placed orders only today, but mock keeps fills across calls;
        # filter to today's fills by intent — match against `placed` order_ids.
        placed_ids = {r.order_id for _, r in placed if r.order_id}
        todays = [f for f in fills if f.order_id in placed_ids]
        n_fills = len(todays)
        total_commission = sum(f.commission for f in todays)

        # 6. Ledger write — single-transaction via ledger_writer. The real
        # API is write_execution_result(conn, *, as_of_date, mode, orders,
        # fills, new_positions={ticker:(qty, mark_price)}); the old
        # write_day_ledger(path, targets=..., source_tag=...) name/signature
        # never existed in the India build. new_positions is the post-fill
        # broker state marked at the latest close ≤ as_of_date.
        try:
            from storage import portfolio_db as _pdb
            from scripts.ledger_writer import write_execution_result

            post = self.broker.get_positions()
            mark_px = _load_latest_closes(
                self.prices_db,
                tickers={p.ticker for p in post},
                on_or_before=as_of_date,
            )
            new_positions = {
                p.ticker: (p.quantity, float(mark_px.get(p.ticker, 0.0)))
                for p in post
            }
            # Impedance adapter: the India broker model
            # (OrderRequest/OrderResponse pair, Fill with .price/.fill_time/
            # 'BUY'|'SELL') -> the ledger model expected by
            # write_execution_result / portfolio_db.insert_{order,fill}
            # (order_id/submitted_at/ticker/side/order_type/quantity/
            # limit_price/status; fill_id/order_id/filled_at/ticker/side/
            # quantity/fill_price/commission). ledger_writer's lot FIFO
            # compares `side == "buy"` (lowercase), so normalise case.
            _submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            ledger_orders = [
                SimpleNamespace(
                    order_id=resp.order_id,
                    submitted_at=_submitted_at,
                    ticker=req.ticker,
                    side=req.transaction_type.lower(),
                    order_type=req.order_type,
                    quantity=req.quantity,
                    limit_price=req.price,
                    status=resp.status,
                )
                for req, resp in placed
            ]
            ledger_fills = [
                SimpleNamespace(
                    fill_id=f.order_id,          # 1 fill/order (mock) → unique
                    order_id=f.order_id,
                    filled_at=f.fill_time,
                    ticker=f.ticker,
                    side=f.side.lower(),
                    quantity=f.quantity,
                    fill_price=f.price,
                    commission=f.commission,
                    slippage_bps=None,
                )
                for f in todays
            ]
            with _pdb.connect(self.portfolio_db) as conn:
                ws = write_execution_result(
                    conn,
                    as_of_date=as_of_date,
                    mode=self.mode,
                    orders=ledger_orders,
                    fills=ledger_fills,
                    new_positions=new_positions,
                )
            n_disc = ws.n_discrepancies
        except Exception as e:
            logger.error("ledger write failed: %s", e)
            notes.append(f"ledger write failed: {e}")
            n_disc = -1

        return ExecutionSummary(
            mode=self.mode,
            as_of_date=as_of_date,
            fill_date=as_of_date,
            n_orders=len(placed),
            n_fills=n_fills,
            gross_buy_usd=gross_buy,
            gross_sell_usd=gross_sell,
            total_commission_usd=total_commission,
            n_discrepancies=max(0, n_disc),
            halt_set=False,
            notes=notes,
        )

    # ──────────────────────────────────────────────────────────
    # Order construction
    # ──────────────────────────────────────────────────────────

    def _build_orders(
        self,
        *,
        as_of_date: date,
        targets: dict[str, float],
    ) -> tuple[list, float, float]:
        """Convert {ticker: target_fraction} into list[OrderRequest].

        - Reads current positions from broker
        - Computes total equity = cash + sum(positions * latest_close)
        - Computes target_qty = round(target_fraction * total_equity / close)
        - Applies FRACTION_CHANGE_THRESHOLD on `target_fraction` (not target_qty,
          which drifts daily due to mark-to-market — US repo learnings §4.5)
        - Generates BUY for qty_delta > 0, SELL for qty_delta < 0; MKT orders
        """
        cash = float(self.broker.get_cash().get("availableBalance", 0.0))
        positions = {p.ticker: p for p in self.broker.get_positions()}

        # Build latest-close lookup for all candidate tickers
        prices = _load_latest_closes(
            self.prices_db,
            tickers=set(targets) | set(positions),
            on_or_before=as_of_date,
        )

        total_equity = cash + sum(
            (positions[t].quantity * prices.get(t, 0.0)) for t in positions
        )

        # Pull previous targets (for fraction-change suppression)
        prev_targets = _load_prev_targets(
            self.portfolio_db, mode=self.mode, before_date=as_of_date
        )

        order_reqs: list = []
        gross_buy = 0.0
        gross_sell = 0.0

        # 1. Open positions not in targets → SELL all
        for ticker, pos in positions.items():
            if pos.quantity <= 0:
                continue
            if ticker not in targets:
                px = prices.get(ticker)
                if px is None:
                    continue
                gross_sell += pos.quantity * px
                order_reqs.append(
                    OrderRequest(
                        transaction_type="SELL",
                        ticker=ticker,
                        quantity=pos.quantity,
                        order_type=ORDER_TYPE_MARKET,
                    )
                )

        # 2. Walk through targets; size each
        for ticker, target_fraction in targets.items():
            px = prices.get(ticker)
            if not px or px <= 0:
                logger.warning("skip target %s: no price", ticker)
                continue
            target_qty = int((target_fraction * total_equity) / px)
            current_qty = positions[ticker].quantity if ticker in positions else 0
            delta = target_qty - current_qty
            if delta == 0:
                continue
            # Fraction-change suppression on fraction not qty
            prev = prev_targets.get(ticker, 0.0)
            if abs(target_fraction - prev) < self.fraction_change_threshold and target_qty == current_qty:
                continue
            if delta > 0:
                gross_buy += delta * px
                order_reqs.append(
                    OrderRequest(
                        transaction_type="BUY",
                        ticker=ticker,
                        quantity=delta,
                        order_type=ORDER_TYPE_MARKET,
                    )
                )
            else:
                gross_sell += abs(delta) * px
                order_reqs.append(
                    OrderRequest(
                        transaction_type="SELL",
                        ticker=ticker,
                        quantity=abs(delta),
                        order_type=ORDER_TYPE_MARKET,
                    )
                )

        return order_reqs, gross_buy, gross_sell


# ──────────────────────────────────────────────────────────────────────
# Helpers (depend on DBs being initialised; soft-degrade if not)
# ──────────────────────────────────────────────────────────────────────


def _load_latest_closes(
    prices_db: Path,
    tickers: set[str],
    on_or_before: date,
) -> dict[str, float]:
    if not tickers or not prices_db.exists():
        return {}
    import duckdb

    conn = duckdb.connect(str(prices_db), read_only=True)
    try:
        placeholders = ",".join("?" * len(tickers))
        rows = conn.execute(
            f"""
            WITH ranked AS (
              SELECT ticker, close, dt,
                     ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY dt DESC) rn
                FROM daily_bars
               WHERE ticker IN ({placeholders}) AND dt <= ?
            )
            SELECT ticker, close FROM ranked WHERE rn = 1
            """,
            (*tickers, on_or_before),
        ).fetchall()
    finally:
        conn.close()
    return {t: float(c) for t, c in rows if c is not None}


def _load_prev_targets(
    portfolio_db: Path,
    mode: str,
    before_date: date,
) -> dict[str, float]:
    """Most-recent desired_targets row per ticker for this mode, strictly
    before `before_date`. Used for FRACTION_CHANGE_THRESHOLD suppression.
    """
    if not portfolio_db.exists():
        return {}
    import duckdb

    conn = duckdb.connect(str(portfolio_db), read_only=True)
    try:
        tbl = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='desired_targets'"
        ).fetchone()
        if not tbl:
            return {}
        rows = conn.execute(
            """
            WITH ranked AS (
              SELECT ticker, target_fraction, as_of_date,
                     ROW_NUMBER() OVER (
                       PARTITION BY ticker ORDER BY as_of_date DESC
                     ) rn
                FROM desired_targets
               WHERE mode = ? AND as_of_date < ?
            )
            SELECT ticker, target_fraction FROM ranked WHERE rn = 1
            """,
            (mode, before_date),
        ).fetchall()
    finally:
        conn.close()
    return {t: float(f) for t, f in rows if f is not None}


__all__ = ["DhanExecutor", "FRACTION_CHANGE_THRESHOLD"]
