"""Single source of truth for which book (paper vs live) an entrypoint acts on.

`run_live` read EXECUTION_MODE; `daily_report` and `safety_evaluator` did not,
so the 15:35 cron scored a frozen paper book while real money traded live —
the safety circuit-breaker never saw the live drawdown. Every entrypoint now
resolves through here so the modes cannot drift apart again.
"""
from __future__ import annotations

import os

DEFAULT_MODE = "dhan-paper"


def resolve_execution_mode(explicit: str | None = None) -> str:
    """An explicit `--mode` wins; otherwise EXECUTION_MODE; otherwise paper.

    Defaulting to paper keeps the safe mode the fallback: a missing env var
    can never silently promote an entrypoint onto the live book.
    """
    return explicit or os.environ.get("EXECUTION_MODE") or DEFAULT_MODE
