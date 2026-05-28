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
from storage import portfolio_db

logger = logging.getLogger(__name__)

FRACTION_CHANGE_THRESHOLD = 0.005   # 0.5pp — US repo learnings §4.2
# Minimum order notional (₹). Trades below this are SUPPRESSED in
# _build_orders so the strategy stops churning ₹14.75/scrip DP charges
# on 1-share tick-overs caused by mark-drift integer rounding. Sized
# so the DP friction stays under ~1% of trade notional (14.75/1500 ≈
# 1%). Applies ONLY to the resize / rebalance path; full liquidations
# (a name dropped from the strategy) are NOT filtered — those must
# execute regardless of size, otherwise orphan positions could persist.
# Drift below this floor is left to the next biweekly rebalance.
MIN_ORDER_INR = 1500.0
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
    initial_cash_inr: float = 100_000.0
    fraction_change_threshold: float = FRACTION_CHANGE_THRESHOLD

    def __post_init__(self) -> None:
        if self.broker is None:
            self.broker = self._construct_broker()

    def _construct_broker(self):
        use_mock = (
            self.mode == "dhan-paper"
            or os.environ.get("DHAN_MOCK", "0") in ("1", "true", "True")
        )
        # NOTE: earlier this method hard-failed on missing SEBI_ALGO_ID for
        # live mode. Relaxed 2026-05-28 — Dhan's API treats `correlationId`
        # as optional (per /docs/v2/orders), and the user confirmed no
        # Personal-Algo registration form exists in the Dhan portal. The
        # DhanBroker constructor logs a warning if SEBI_ALGO_ID is unset.
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

        # 1b. EOD-style broker_positions snapshot for today (idempotent
        #     via upsert). Ensures broker_positions has a row for EVERY
        #     trading day, not only days where the executor placed orders
        #     via write_execution_result. Without this, non-rebalance
        #     days had no snapshot → equity curve missing data points →
        #     today_pnl had no prior snapshot to diff against → 1D
        #     returns stuck at ₹0. write_execution_result later in this
        #     method will upsert again on rebalance days with the same
        #     mark values; the upsert makes both paths safe.
        self._write_eod_snapshot(as_of_date)

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
            # Exits are surfaced separately by signal_today (target_fraction=0
            # rows split off the positives). They MUST flow into _build_orders
            # so liquidations actually fire — without this merge, an
            # all-to-cash signal returned `targets=[]` and the executor
            # short-circuited as "non-rebalance day", leaving real money
            # invested when the strategy wanted zero exposure.
            raw_exits = (
                signals_result.get("exits", [])
                if isinstance(signals_result, dict)
                else getattr(signals_result, "exits", []) or []
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
            if isinstance(raw_exits, list):
                for r in raw_exits:
                    if (
                        isinstance(r, dict)
                        and "ticker" in r
                        and "target_fraction" in r
                    ):
                        # Exits always carry target_fraction=0; preserve that
                        # explicitly so _build_orders sizes to zero (= sell all).
                        targets.setdefault(r["ticker"], float(r["target_fraction"]))
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
                skipped_reason="strategy produced no targets or exits (non-rebalance day)",
            )

        # Step 2.c: apply the safety-state risk multiplier to every target
        # fraction BEFORE we persist desired_targets or build orders. Without
        # this read, the deterministic safety state machine (Step 2) would
        # be decorative — the spec calls this out explicitly. Fail-open on
        # a missing risk_multiplier.json (default=1.0) so a fresh
        # installation behaves identically to NORMAL.
        try:
            from scripts.safety_evaluator import read_risk_multiplier
            multiplier = read_risk_multiplier()
        except Exception as e:  # noqa: BLE001 — read must never raise
            logger.warning(
                "risk_multiplier read failed: %s: %s; defaulting to 1.0",
                type(e).__name__, e,
            )
            multiplier = 1.0
        if multiplier != 1.0:
            logger.info(
                "applying safety risk_multiplier=%.2f to all %d targets",
                multiplier, len(targets),
            )
            targets = {t: float(v) * multiplier for t, v in targets.items()}

        # Persist desired_targets — strategy's recorded intent for this date.
        # Without this, reconciliation/attribution can't compare "what we said"
        # vs "what we did". Full-replacement semantics: clear and re-upsert so
        # a rerun with a shrunk signal set doesn't leave orphan rows behind.
        try:
            from storage import portfolio_db as _pdb_t

            with _pdb_t.connect(self.portfolio_db) as _t_conn:
                _pdb_t.delete_targets_for_day(
                    _t_conn, as_of_date=as_of_date, mode=self.mode,
                )
                for _t_ticker, _t_frac in targets.items():
                    _pdb_t.upsert_target(
                        _t_conn,
                        as_of_date=as_of_date,
                        ticker=_t_ticker,
                        target_fraction=float(_t_frac),
                        source="strategy",
                        mode=self.mode,
                    )
        except Exception as e:  # noqa: BLE001 — never block trading on a target-log failure
            logger.warning(
                "desired_targets persistence failed: %s: %s",
                type(e).__name__, e,
            )

        # 2b. Operational risk gates (scripts.risk_check) — daily loss,
        #     max-DD halt, per-position cap, gross exposure. Runs against
        #     the most-recent snapshot's mark equity. Bypassing these would
        #     let a loop-mutated strategy push a 50%-single-name target
        #     straight through; the halt-only check above does NOT catch that.
        try:
            from scripts import risk_check as _risk_check
            from storage import portfolio_db as _pdb

            with _pdb.connect(self.portfolio_db) as _conn:
                state = _pdb.load_state(_conn, self.mode, as_of_date)
            rc_targets = {
                "targets": [
                    {"ticker": t, "target_fraction": float(v)}
                    for t, v in targets.items()
                    if v > 0
                ],
            }
            risk_passed, risk_reasons = _risk_check.check(rc_targets, state)
        except Exception as e:  # noqa: BLE001 — risk check must never raise into the loop
            logger.error("risk_check raised %s: %s", type(e).__name__, e)
            risk_passed, risk_reasons = False, [f"risk_check raised {type(e).__name__}: {e}"]
        if not risk_passed:
            return ExecutionSummary(
                mode=self.mode,
                as_of_date=as_of_date,
                fill_date=None,
                skipped=True,
                skipped_reason="risk_check rejected: " + "; ".join(risk_reasons),
                halt_set=any("halt" in r.lower() for r in risk_reasons),
                halt_reason=next(
                    (r for r in risk_reasons if "halt" in r.lower()),
                    None,
                ),
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
            # Use the Dhan trade-leg ID for fill_id, not the order_id —
            # /v2/trades may return N fills for one order (partial fills,
            # iceberg legs); the order_id repeats across them and collided
            # on `actual_fills.fill_id` PK, rolling back the ledger
            # transaction (live data changed, local state unwritten).
            # DhanMock sets trade_id == order_id (1-to-1), so the mock path
            # is unchanged; live path now uses Dhan's leg-unique ID.
            ledger_fills = [
                SimpleNamespace(
                    fill_id=(getattr(f, "trade_id", "") or f.order_id),
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

        # Re-stamp today's broker_positions snapshot from CURRENT (post-trade)
        # broker state, so names that were fully sold this run no longer
        # leave stale rows from the morning's _write_eod_snapshot. This is
        # the second half of the 2026-05-26 double-count fix.
        self._write_eod_snapshot(as_of_date)

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
    # Quiet-day snapshot
    # ──────────────────────────────────────────────────────────

    def _write_eod_snapshot(self, as_of_date: date) -> None:
        """Upsert broker_positions for `as_of_date` using current holdings
        × latest available close. Called at the top of every execute_day
        (after the halt check) so the equity-curve / today_pnl pipeline
        has a snapshot for EVERY trading day, not only rebalance days.
        Idempotent — re-running upserts existing rows."""
        try:
            positions = self.broker.get_positions()
        except Exception as e:  # noqa: BLE001 — best-effort
            logger.warning("EOD snapshot skipped (broker.get_positions failed): %s", e)
            return
        held = [p for p in positions if p.quantity and p.quantity > 0]
        closes = _load_latest_closes(
            self.prices_db,
            tickers={p.ticker for p in held},
            on_or_before=as_of_date,
        ) if held else {}
        # DELETE-then-INSERT semantics: today's snapshot is ALWAYS a clean
        # rewrite of the current broker state. Critical because this method
        # gets called BOTH before signal extraction AND after trades fire —
        # without the delete, a name that was held in the morning but fully
        # sold by trades-end leaves a stale row in today's snapshot, causing
        # the dashboard to double-count positions (sold-name's morning value
        # + post-trade names' values). Bug discovered 2026-05-26 when the
        # dashboard showed equity = ₹142k from a ₹100k base after a 5-name
        # rebalance turnover.
        with portfolio_db.connect(self.portfolio_db) as conn:
            conn.execute(
                "DELETE FROM broker_positions "
                "WHERE snapshot_date = ? AND mode = ?",
                [as_of_date, self.mode],
            )
            for p in held:
                mark = closes.get(p.ticker)
                if mark is None or mark <= 0:
                    continue
                portfolio_db.upsert_position(
                    conn,
                    snapshot_date=as_of_date,
                    ticker=p.ticker,
                    quantity=float(p.quantity),
                    avg_entry_price=float(p.average_price)
                    if p.average_price is not None else None,
                    mark_price=float(mark),
                    mark_value=float(p.quantity) * float(mark),
                    mode=self.mode,
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
            # Minimum-order-size filter: a tiny trade can't justify the
            # ₹14.75/scrip DP charge — skip and let the small qty delta
            # resolve at the next biweekly rebalance. Primary defense
            # against daily 1-share-tick-over churn from mark-drift
            # integer rounding (which the broken FRACTION_CHANGE_THRESHOLD
            # below failed to suppress).
            trade_notional = abs(delta) * px
            if trade_notional < MIN_ORDER_INR:
                logger.info(
                    "skip small order %s qty_delta=%d notional=₹%.2f < min ₹%.0f",
                    ticker, delta, trade_notional, MIN_ORDER_INR,
                )
                continue
            # Fraction-change suppression on fraction not qty (US repo
            # learnings §4.5). The old form gated this on
            # `target_qty == current_qty`, but that branch is unreachable —
            # `delta == 0` was already filtered above, so the qty equality
            # could never be true here, making the entire suppressor dead
            # code (Codex finding B5). Drop the qty clause so the
            # fraction-change guard actually fires on small fraction deltas
            # that round to a 1-share change from mark drift.
            #
            # Liquidations (target_fraction == 0 with a held position) MUST
            # bypass this guard — exits always fire. Without the bypass, an
            # exit with no prior captured target_fraction (e.g., a name we
            # hold from a stale rebalance whose row was pruned, or a manually
            # seeded position) would be suppressed by the no-change math
            # (prev=0, target=0).
            if target_fraction > 0:
                prev = prev_targets.get(ticker, 0.0)
                if abs(target_fraction - prev) < self.fraction_change_threshold:
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
