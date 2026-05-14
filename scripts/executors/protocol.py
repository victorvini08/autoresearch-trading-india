"""Executor protocol — broker-agnostic interface for one day's execution.

Each implementation owns the full per-day flow: pre-flight checks, signal
generation, order construction, fill observation/modeling, and ledger
writes. The orchestrator (`scripts/run_live.py`) only chooses which
executor to instantiate based on EXECUTION_MODE.

ExecutionSummary is the single return type. `daily_report.py` consumes it
without caring whether fills came from yfinance or IBKR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class ExecutionSummary:
    """One day's execution result, broker-agnostic.

    `as_of_date` is the SIGNAL date — when the strategy decided what to do.
    `fill_date` is when those fills actually landed — same day for IBKR,
    next trading day for paper-mode (modeled at the OPEN price).

    `skipped` is set when pre-flight blocked execution. `halt_set` is true
    if max-DD or another gate wrote halt.json during or after this run.
    """

    mode: str  # 'paper' | 'ibkr-paper' | 'ibkr-live'
    as_of_date: date
    fill_date: date | None
    n_orders: int = 0
    n_fills: int = 0
    gross_buy_usd: float = 0.0
    gross_sell_usd: float = 0.0
    total_commission_usd: float = 0.0
    n_discrepancies: int = 0
    halt_set: bool = False
    halt_reason: str | None = None
    skipped: bool = False
    skipped_reason: str | None = None
    # Optional human-readable notes for the daily report — e.g. "applied
    # premarket gap-skip on FER", "VIX>35 scale-down". Free-form.
    notes: list[str] = field(default_factory=list)

    @property
    def gross_turnover_usd(self) -> float:
        return self.gross_buy_usd + self.gross_sell_usd


class PreflightSkipped(Exception):
    """Raised by an executor when pre-flight refuses to trade today.

    `reason` is the user-facing explanation; `set_halt` indicates that
    halt.json was written and the operator must manually unset to resume.
    The orchestrator catches this, returns a skipped ExecutionSummary,
    and emits a daily report explaining why the day was a no-op.
    """

    def __init__(self, reason: str, *, set_halt: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.set_halt = set_halt


class Executor(Protocol):
    """Per-day execution contract.

    Implementations should be safe to instantiate cheaply (no network
    calls in __init__) and `execute_day` must be idempotent: re-running
    with the same `as_of_date` must produce the same ledger state
    (delete-then-write semantics — see paper_trade.py for the pattern).
    """

    mode: str

    def execute_day(
        self,
        as_of_date: date,
        *,
        strategy_module: str = "strategy",
        source_tag: str = "run_live",
    ) -> ExecutionSummary:
        ...
