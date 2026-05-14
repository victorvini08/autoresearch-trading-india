"""Operational risk gates. Called before any order placement, paper or real.

These are OPERATIONAL gates (live execution guardrails). Distinct from
backtest/risk.py which is the CATASTROPHE validator on aggregate fold results.
Same project, different layer.

Importable: scripts.risk_check.check(targets, state) -> (passed, reasons).

HALT STATE — MODE AWARENESS (I-5):
    The halt flag (state/halt.json) is intentionally GLOBAL across modes for v1.
    A paper-mode max-DD halt will also block real-mode execution if both run
    against the same halt file.

    Rationale: an operator who hits max-DD in paper-mode almost certainly wants
    both modes paused until they review the situation. Silently continuing in
    real-mode after a paper-mode halt would defeat the purpose of the gate.

    If future operational policy requires mode-scoped halts (e.g., paper can halt
    independently of real), the path forward is to move halt-state ownership into
    a small state/ module with per-mode files (halt-paper.json, halt-real.json)
    and update load_state + _set_halt to key on the mode argument. No refactor
    is done here — this note records the design choice for v1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from storage.portfolio_db import LedgerState, HALT_FILE_PATH as HALT_FILE


@dataclass(frozen=True)
class RiskParams:
    max_daily_loss_frac:    float = 0.03      # 3% of mark equity in a day
    max_drawdown_halt_frac: float = 0.15      # 15% from peak equity
    max_position_frac:      float = 0.20      # per-position concentration cap (allows conviction sizing)
    max_gross_exposure:     float = 1.00      # 100% — cash account, no leverage


DEFAULT_PARAMS = RiskParams()


def check(
    targets: dict,
    state: LedgerState,
    params: RiskParams = DEFAULT_PARAMS,
) -> tuple[bool, list[str]]:
    """Run all 5 gates. Returns (passed, reasons).

    Gate 1 (halt flag) short-circuits — no other gates evaluated when halted.
    Gate 3 (max-DD) is the only gate with a side effect: it WRITES state/halt.json
    when it trips. Manual reset = delete the halt file.
    """
    reasons: list[str] = []

    # Gate 1: halt-flag short-circuit
    if state.halted:
        return (False, ["halt flag set"])

    # Gate 2: daily loss limit
    if state.mark_equity > 0:
        daily_loss_frac = state.today_pnl_usd / state.mark_equity
        if daily_loss_frac < -params.max_daily_loss_frac:
            reasons.append(
                f"daily loss {daily_loss_frac:.2%} exceeds limit "
                f"-{params.max_daily_loss_frac:.0%}"
            )

    # Gate 3: max-DD halt (has side effect)
    if state.peak_equity > 0:
        dd_frac = (state.mark_equity - state.peak_equity) / state.peak_equity
        if dd_frac < -params.max_drawdown_halt_frac:
            _set_halt({
                "reason": "max_dd_halt",
                "dd": dd_frac,
                "set_at": datetime.now(timezone.utc).isoformat(),
                "set_by": "risk_check",
            })
            reasons.append(
                f"max DD {dd_frac:.2%} exceeds halt threshold "
                f"-{params.max_drawdown_halt_frac:.0%}; halt flag set"
            )

    # Gate 4: per-position concentration
    for t in targets.get("targets", []):
        if t["target_fraction"] > params.max_position_frac:
            reasons.append(
                f"{t['ticker']} target {t['target_fraction']:.1%} "
                f"exceeds per-position cap {params.max_position_frac:.0%}"
            )

    # Gate 5: gross exposure
    gross = sum(abs(t["target_fraction"]) for t in targets.get("targets", []))
    if gross > params.max_gross_exposure:
        reasons.append(
            f"gross exposure {gross:.1%} exceeds cap "
            f"{params.max_gross_exposure:.0%}"
        )

    return (len(reasons) == 0, reasons)


def _set_halt(payload: dict) -> None:
    HALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    HALT_FILE.write_text(json.dumps(payload, indent=2))
