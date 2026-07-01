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

import json
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
    VALIDITY_IOC,
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

# Sweep-to-fill (rebalance-day robustness). On Dhan a "MARKET" equity order is
# really a protected LIMIT at LTP that can miss on a tick, and IOC cancels the
# unfilled part rather than resting it. So instead of placing once and hoping,
# the executor re-derives the RESIDUAL delta from the live book and re-fires IOC
# until everything is filled or a hard time budget elapses. Residual sizing comes
# from re-running _build_orders against current positions, so repeated passes can
# never over-fill. Bounded by BOTH a wall-clock budget and a sweep cap; the
# settle pause lets each IOC reach terminal + the position read be authoritative
# before the next residual is sized (this is what prevents a double-fill race).
REBALANCE_FILL_BUDGET_SEC = 180.0   # total wall-clock for one execute_day's fills
MAX_FILL_SWEEPS = 90                # backstop on passes; the time budget governs first
SWEEP_SETTLE_SEC = 2.0              # pause between passes (tests set this to 0)

# First-day live bootstrap marker. A freshly-funded dhan-live account is an
# EMPTY book, which signal_today treats as the seeded-flat path: it acts on
# the decision bar alone and only rebalances on an even-week rebalance Friday.
# So a live start on any other weekday would idle (uninvested) for up to two
# weeks until the next scheduled rebalance. This marker lets the executor force
# a single rebalance on the very first live session, then never again — an
# ops-level bootstrap, NOT a change to the gated strategy calendar (same layer
# as the LIQUIDCASE cash floor). The 4-week paper analogue is intentionally not
# bootstrapped: paper runs daily on the mock and has no idle-cash cost.
LIVE_BOOTSTRAP_MARKER = portfolio_db.REPO_ROOT / "state" / "live_bootstrapped.json"


def _live_bootstrap_done() -> bool:
    """True once the first-day live rebalance has been forced (marker exists)."""
    return LIVE_BOOTSTRAP_MARKER.exists()


def _mark_live_bootstrap_done(as_of_date: date) -> None:
    """Record that the one-time first-day live rebalance has been performed."""
    LIVE_BOOTSTRAP_MARKER.parent.mkdir(parents=True, exist_ok=True)
    LIVE_BOOTSTRAP_MARKER.write_text(
        json.dumps(
            {
                "bootstrapped_on": as_of_date.isoformat(),
                "set_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "note": "first-day live rebalance forced; normal calendar resumes",
            },
            indent=2,
        )
    )


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
    initial_cash_inr: float = 50_000.0   # user-confirmed deployment capital 2026-06-11
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

            # Seed the signal from the LIVE account's actual current holdings
            # so the strategy's held/retention logic runs against reality, not
            # a from-scratch re-simulation. Without this seed the re-derived
            # imaginary book drifts from the live account and every rebalance
            # churns to reconcile the two (the sim-vs-live divergence bug:
            # on 2026-06-01 it phantom-rotated FEDERALBNK/BHARATFORG →
            # TITAN/SHRIRAMFIN despite the live book already holding qualifying
            # names). Fail-soft: a broker read failure falls back to None
            # (legacy from-scratch replay) rather than blocking the cron.
            try:
                live_positions: dict[str, float] | None = {
                    p.ticker: float(p.quantity)
                    for p in self.broker.get_positions()
                    if getattr(p, "quantity", 0) and p.quantity > 0
                }
                live_cash: float | None = float(
                    self.broker.get_cash().get("availableBalance", 0.0)
                )
            except Exception as e:  # noqa: BLE001 — never block trading on a read
                logger.warning(
                    "live-position seed read failed (%s: %s); falling back "
                    "to from-scratch signal", type(e).__name__, e,
                )
                live_positions, live_cash = None, None

            # Cash-floor seed handling (2026-06-10): the floor ETF is an
            # EXECUTOR-level policy holding — the strategy must never see it.
            # If it leaked into the seed, the strategy would treat it as an
            # off-universe held name and liquidate it every rebalance. Strip
            # it from the seeded positions and fold its market value into
            # seeded cash so gross is sized on true deployable equity.
            from scripts.cash_floor import (
                CASH_FLOOR_ENABLED,
                CASH_FLOOR_TICKER,
            )
            if (
                CASH_FLOOR_ENABLED
                and live_positions
                and CASH_FLOOR_TICKER in live_positions
            ):
                _floor_qty = live_positions.pop(CASH_FLOOR_TICKER)
                _floor_px = _load_latest_closes(
                    self.prices_db,
                    tickers={CASH_FLOOR_TICKER},
                    on_or_before=as_of_date,
                ).get(CASH_FLOOR_TICKER)
                if _floor_px and live_cash is not None:
                    live_cash += _floor_qty * _floor_px

            # First-day live bootstrap: force a single rebalance when a
            # freshly-funded live account starts EMPTY (no equity positions;
            # a floor-only book has already been stripped to {} above) and the
            # bootstrap has never run. Scoped to dhan-live — paper runs daily
            # on the mock and has no idle-cash cost. signal_today honours the
            # flag on the seeded decision bar alone, so exactly one rebalance
            # fires; the marker (written below) prevents it recurring.
            force_rebalance = (
                self.mode == "dhan-live"
                and live_positions == {}
                and not _live_bootstrap_done()
            )
            if force_rebalance:
                logger.info(
                    "first-day live bootstrap: empty live book on %s — forcing "
                    "an initial rebalance so capital deploys immediately instead "
                    "of idling to the next rebalance Friday", as_of_date,
                )

            signals_result = generate_signals(
                target_date=as_of_date,
                strategy_module_name=strategy_module,
                current_positions=live_positions,
                current_cash=live_cash,
                force_rebalance=force_rebalance,
            )
            # NB: the one-time bootstrap marker is written LATER — only once
            # the forced rebalance has produced a real equity order to place
            # (see "first-day live bootstrap: consume marker" below). Marking
            # it here would burn the one-shot on a run that computes target
            # FRACTIONS but builds no whole-share orders — e.g. a low-capital
            # ₹1k API shakedown — leaving the real funded start un-bootstrapped.
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

        # 2d. Cash-floor injection (2026-06-10): park idle capital in the
        #     liquid floor ETF. Runs AFTER risk_check (the floor is policy
        #     cash, not an equity position — a ~40% floor holding must not
        #     trip per-name/gross gates) and only on rebalance days (empty
        #     targets short-circuit above, so the floor is never churned
        #     between rebalances). The floor ALWAYS appears in `targets`
        #     when enabled — _build_orders liquidates any held name absent
        #     from targets, so omission would dump the floor. The banded
        #     target returns the CURRENT fraction inside the band → ~zero
        #     delta → no order → the ₹14.75 DP charge fires only a few
        #     times a year. Ordering: floor-first when shrinking (the SELL
        #     frees cash before equity BUYS), floor-last when growing
        #     (park the residual after equity is funded).
        try:
            from scripts.cash_floor import (
                CASH_FLOOR_ENABLED as _CF_ON,
                CASH_FLOOR_TICKER as _CF_TKR,
                banded_floor_target,
            )
            if _CF_ON:
                _eq_sum = sum(v for v in targets.values() if v > 0)
                _cur_frac = 0.0
                try:
                    _pos = {
                        p.ticker: float(p.quantity)
                        for p in self.broker.get_positions()
                        if getattr(p, "quantity", 0) and p.quantity > 0
                    }
                    _cash = float(
                        self.broker.get_cash().get("availableBalance", 0.0)
                    )
                    _pxm = _load_latest_closes(
                        self.prices_db,
                        tickers={_CF_TKR} | set(_pos),
                        on_or_before=as_of_date,
                    )
                    _eqty = _cash + sum(
                        q * _pxm.get(t, 0.0) for t, q in _pos.items()
                    )
                    if _eqty > 0:
                        _cur_frac = (
                            _pos.get(_CF_TKR, 0.0) * _pxm.get(_CF_TKR, 0.0)
                        ) / _eqty
                except Exception as e:  # noqa: BLE001 — fall back to 0 (fresh park)
                    logger.warning(
                        "cash-floor current-fraction read failed: %s: %s",
                        type(e).__name__, e,
                    )
                _f_target = banded_floor_target(_eq_sum, _cur_frac)
                if _f_target < _cur_frac:
                    targets = {_CF_TKR: _f_target, **targets}
                else:
                    targets = {**targets, _CF_TKR: _f_target}
                notes.append(
                    f"cash_floor[{_CF_TKR}]: equity={_eq_sum:.3f} "
                    f"cur={_cur_frac:.3f} target={_f_target:.3f}"
                )
                try:
                    from storage import portfolio_db as _pdb_cf

                    with _pdb_cf.connect(self.portfolio_db) as _cf_conn:
                        _pdb_cf.upsert_target(
                            _cf_conn,
                            as_of_date=as_of_date,
                            ticker=_CF_TKR,
                            target_fraction=float(_f_target),
                            source="cash_floor",
                            mode=self.mode,
                        )
                except Exception as e:  # noqa: BLE001 — log-only
                    logger.warning(
                        "cash-floor target persistence failed: %s: %s",
                        type(e).__name__, e,
                    )
        except Exception as e:  # noqa: BLE001 — the floor must never block equity
            logger.warning(
                "cash-floor injection failed: %s: %s — proceeding without",
                type(e).__name__, e,
            )

        # 3-4. SWEEP-TO-FILL. On Dhan a "MARKET" equity order is really a
        # protected LIMIT at LTP that can miss on a tick, and IOC cancels the
        # unfilled part instead of resting it. So rather than place-once-and-hope,
        # we re-derive the RESIDUAL delta from the live book each pass and re-fire
        # IOC until everything is filled or a hard time budget elapses. Residual
        # sizing comes from re-running _build_orders against current positions, so
        # repeated passes converge to target and can NEVER over-fill.
        import time as _sweep_time

        def _drop_premarket_skips(reqs, gb, gs):
            """Drop premarket-flagged (gap/halt) tickers from this pass's orders.
            Returns (kept, gross_buy, gross_sell)."""
            if not (skips and reqs):
                return reqs, gb, gs
            kept, dropped = [], {}
            for req in reqs:
                if req.ticker.upper() in skips:
                    notional = float(req.quantity) * float(req.price or 0.0)
                    dropped[req.ticker.upper()] = notional
                    if req.transaction_type.upper() == "BUY":
                        gb -= notional
                    else:
                        gs -= notional
                else:
                    kept.append(req)
            return kept, gb, gs

        placed: list = []          # (req, resp) across ALL passes, for reconcile
        gross_buy = gross_sell = 0.0
        last_reqs: list = []       # residual still outstanding when the loop exits
        seen_premarket_drop = False
        bootstrap_marked = False
        deadline = _sweep_time.monotonic() + REBALANCE_FILL_BUDGET_SEC

        for sweep in range(MAX_FILL_SWEEPS):
            reqs, gb, gs = self._build_orders(as_of_date=as_of_date, targets=targets)
            n_before = len(reqs)
            reqs, gb, gs = _drop_premarket_skips(reqs, gb, gs)
            if skips and n_before > len(reqs) and not seen_premarket_drop:
                notes.append(
                    f"premarket: dropped {n_before - len(reqs)} orders for "
                    f"gap-flagged tickers {sorted(skips)}"
                )
                seen_premarket_drop = True
            last_reqs = reqs
            if not reqs:
                break  # fully converged: all filled, or remaining deltas suppressed
            if sweep == 0:
                gross_buy, gross_sell = gb, gs  # report the round-0 intended gross

            # First-day live bootstrap: consume the one-time marker ONLY once the
            # forced rebalance has a real EQUITY order to place (not the cash
            # floor) — a low-capital run that builds no whole-share equity order
            # never reaches here, so the bootstrap stays ARMED. See the marker
            # helpers near the top of this module.
            if force_rebalance and not bootstrap_marked:
                from scripts.cash_floor import CASH_FLOOR_TICKER as _BOOT_FLOOR_TKR

                if any(r.ticker.upper() != _BOOT_FLOOR_TKR for r in reqs):
                    _mark_live_bootstrap_done(as_of_date)
                    notes.append("first-day live bootstrap: forced initial rebalance")
                    bootstrap_marked = True

            for req in reqs:
                try:
                    if not hasattr(self.broker, "place_order"):
                        raise RuntimeError("broker has no place_order")
                    # as_of_date drives Phase B fill-pricing in the mock; the
                    # live broker ignores it (exchange supplies the fill price).
                    resp = self.broker.place_order(req, as_of_date=as_of_date)
                    placed.append((req, resp))
                    if resp.status == STATUS_REJECTED:
                        notes.append(
                            f"order rejected: {req.transaction_type} {req.quantity} {req.ticker}")
                except Exception as e:
                    logger.error("place_order %s %s failed: %s",
                                 req.transaction_type, req.ticker, e)
                    notes.append(
                        f"place_order failed for {req.transaction_type} "
                        f"{req.quantity} {req.ticker}: {e}")

            if _sweep_time.monotonic() >= deadline:
                break
            _sweep_time.sleep(SWEEP_SETTLE_SEC)  # settle: IOC reaches terminal +
            #                                      position read becomes authoritative

        # Nothing was placeable at all → non-rebalance day or every delta
        # suppressed (FRACTION_CHANGE_THRESHOLD / MIN_ORDER_INR).
        if not placed:
            notes.append("no fillable orders (non-rebalance day or all deltas suppressed)")
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

        # Loud alert if the budget/cap was exhausted with residual deltas still
        # open — the rebalance did NOT fully complete (rare: an all-session
        # halt/illiquid name). The book is closer to target than before; the
        # shortfall is logged and self-heals at the next rebalance.
        if last_reqs:
            shortfall = sorted(
                f"{r.transaction_type} {r.quantity} {r.ticker}" for r in last_reqs)
            logger.error(
                "sweep-to-fill INCOMPLETE after budget/cap — residual legs: %s", shortfall)
            notes.append(f"INCOMPLETE: {len(last_reqs)} unfilled residual leg(s): {shortfall}")
        else:
            notes.append(f"sweep-to-fill complete in <= {MAX_FILL_SWEEPS} passes")

        # 4b. FLOOR-SWEEP: park ACTUAL residual idle cash into the cash-floor ETF.
        # The main sweep sizes the floor from equity TARGETS, so when equities
        # under-fill — whole-share rounding, or a name too expensive to fit the
        # per-name cap at small capital (e.g. a ₹5,660 stock vs a ₹5,000 10% cap
        # at ₹50k) — that shortfall stayed as cash earning 0%. Here we read the
        # REAL post-fill broker cash and top the floor up with (cash - buffer),
        # so idle capital earns the ~6.5% liquid-ETF yield instead of nothing.
        # BUY-only, whole shares, IOC, residual recomputed each pass (can't
        # over-buy). Reached only after a real rebalance placed orders (past the
        # `if not placed` guard), so it never churns the floor on a quiet day.
        if CASH_FLOOR_ENABLED:
            try:
                import time as _fs_time

                from scripts.cash_floor import (
                    CASH_FLOOR_BUFFER as _FS_BUFFER,
                    CASH_FLOOR_TICKER as _FS_TKR,
                )
                _fs_px = _load_latest_closes(
                    self.prices_db, tickers={_FS_TKR}, on_or_before=as_of_date,
                ).get(_FS_TKR)
                _fs_added = 0
                for _ in range(5):  # bounded; residual-recomputed each pass
                    _fs_cash = float(self.broker.get_cash().get("availableBalance", 0.0))
                    _post = [p for p in self.broker.get_positions() if p.quantity]
                    _pxm = _load_latest_closes(
                        self.prices_db,
                        tickers={p.ticker for p in _post} | {_FS_TKR},
                        on_or_before=as_of_date,
                    )
                    _equity = _fs_cash + sum(
                        float(p.quantity) * float(_pxm.get(p.ticker, 0.0)) for p in _post)
                    _deployable = _fs_cash - _FS_BUFFER * _equity   # keep the buffer
                    if not _fs_px or _fs_px <= 0 or _deployable < _fs_px:
                        break  # nothing left to park (< one share past the buffer)
                    _fs_qty = int(_deployable / _fs_px)
                    if _fs_qty < 1:
                        break
                    _fs_req = OrderRequest(transaction_type="BUY", ticker=_FS_TKR,
                                           quantity=_fs_qty, validity=VALIDITY_IOC)
                    _fs_resp = self.broker.place_order(_fs_req, as_of_date=as_of_date)
                    placed.append((_fs_req, _fs_resp))
                    _fs_added += _fs_qty
                    _fs_time.sleep(SWEEP_SETTLE_SEC)
                if _fs_added:
                    notes.append(f"floor-sweep: parked residual cash → +{_fs_added} {_FS_TKR}")
            except Exception as e:  # noqa: BLE001 — best-effort; never blocks the run
                logger.warning("floor-sweep failed: %s: %s", type(e).__name__, e)

        # 5. Reconcile fills
        fills = list(self.broker.get_fills())
        n_fills = len(fills)
        # We placed orders only today, but the broker keeps fills across calls;
        # filter to today's fills by intent — match against `placed` order_ids.
        # IOC cancels produce NO fill, so get_fills already holds only what
        # executed; `filled_ids` lets us drop the cancelled retry orders from the
        # ledger — recording them would bloat n_orders and flag false unfilled
        # discrepancies in write_execution_result.
        placed_ids = {r.order_id for _, r in placed if r.order_id}
        todays = [f for f in fills if f.order_id in placed_ids]
        filled_ids = {f.order_id for f in todays}
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
                if resp.order_id in filled_ids  # only orders that actually filled
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
            n_orders=len(filled_ids),  # distinct orders that filled (not retry attempts)
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
        - Computes target_qty = floor(target_fraction * total_equity / close),
          with a whole-share hold-band: a name we already hold whose raw target
          rounds (to nearest) back to the held qty is held, not shed — stops
          sub-share rounding drift from manufacturing a phantom 1-share trade
          (the expensive-name complement to the MIN_ORDER_INR floor)
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
                        validity=VALIDITY_IOC,
                    )
                )

        # 2. Walk through targets; size each
        for ticker, target_fraction in targets.items():
            px = prices.get(ticker)
            if not px or px <= 0:
                logger.warning("skip target %s: no price", ticker)
                continue
            current_qty = positions[ticker].quantity if ticker in positions else 0
            raw_qty = (target_fraction * total_equity) / px
            target_qty = int(raw_qty)
            # Whole-share hold-band (integer analogue of FRACTION_CHANGE_THRESHOLD).
            # floor() sheds a share from a name we ALREADY hold when its
            # carry-forward target projects to e.g. 0.99999 shares: the round-trip
            #   fraction = qty*px/equity  ->  qty = fraction*equity/px
            # is the identity in exact arithmetic, but 6-dp fraction rounding plus a
            # price/equity snapshot mismatch (signal-time projection vs
            # execution-time _load_latest_closes) lands raw_qty a hair below the
            # held integer, and floor() truncates it to held-1 — a phantom sell the
            # MIN_ORDER_INR floor can't catch for an expensive name (one TITAN share
            # ~₹4,078 >> ₹1,500). Reproduced 2026-06-03: TITAN raw_qty=0.99999 ->
            # int()=0 -> sold the last share, having bled 2->1->0 over three
            # non-rebalance days. If the NEAREST integer to raw_qty equals what we
            # already hold, hold it. Guarded on current_qty > 0 so it only ever
            # RETAINS a position — it never rounds a new name up, so it cannot
            # create an unaffordable buy or disturb rebalance-day sizing.
            if current_qty > 0 and int(raw_qty + 0.5) == current_qty:
                target_qty = current_qty
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
                        validity=VALIDITY_IOC,
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
                        validity=VALIDITY_IOC,
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
