"""Context assembly for the monthly LLM review (Step 4.c).

Builds the review's input from the Step 1-3 compute layer — no new derivations,
no new storage. Two outputs:

  ReviewContext  — the ground truth the validator checks against (trade count,
                   safety state, valid evidence ids, burned hashes).
  payload        — the human-readable dict the LLM reasons over (reconciliation,
                   held drift, closed attribution, safety, past hypotheses,
                   journal tail).

Split into a PURE assembler (`assemble_review_input`, fully unit-tested) and a
thin IO wrapper (`gather_review_input`) that calls the DBs and hands the
results to the assembler. The pure/IO split keeps the assembly logic decoupled
from DuckDB so it is testable without seeding five databases.

Evidence-id convention (what the LLM may cite): a held name is cited by its
ticker ("RELIANCE"); a closed trade by "{ticker}@{sell_date}" ("ONGC@2026-05-26").
The same ids appear in the payload the LLM sees and in valid_evidence_ids, so
the causal-citation gate is grounded in exactly what was shown.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from data import realworld_review_validator as V

REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_PATH = REPO_ROOT / "state" / "realworld_journal.md"
JOURNAL_TAIL_CHARS = 4000


@dataclass(frozen=True)
class ReviewInput:
    context: V.ReviewContext
    payload: dict
    input_snapshot_hash: str
    cold_start: bool
    n_realized_trades: int
    safety_state: str


def count_closed_round_trips(conn: duckdb.DuckDBPyConnection, mode: str) -> int:
    """Distinct closed round-trips for `mode` — counted as distinct
    (ticker, sell_date), NOT raw realized_trades rows. One position sold from
    several FIFO lots on the same day is ONE economic bet but several lot-rows;
    statistics care about independent bets, so we collapse them. This is the N
    the cold-start gate reads."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT (ticker, sell_date)) FROM realized_trades "
        "WHERE mode = ?",
        [mode],
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def valid_evidence_ids(trade_context: dict) -> frozenset:
    """The set of ids the LLM is permitted to cite: every held ticker + every
    closed trade as '{ticker}@{sell_date}'."""
    ids: set[str] = set()
    for h in trade_context.get("held", []):
        t = h.get("ticker")
        if t:
            ids.add(str(t))
    for c in trade_context.get("closed", []):
        t = c.get("ticker")
        sd = c.get("sell_date")
        if t and sd:
            ids.add(f"{t}@{sd}")
    return frozenset(ids)


def input_snapshot_hash(payload: dict) -> str:
    """Deterministic hash of the LLM input, for audit provenance. Canonical
    JSON (sorted keys) so logically-identical payloads hash identically."""
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cold_start_banner(n: int) -> str:
    return (
        f"Cold-start mode (N={n} closed round-trips): hypothesis generation "
        f"suppressed until N>={V.COLD_START_MIN_TRADES}. Live PnL commentary is "
        f"diagnostic, not inferential."
    )


def assemble_review_input(
    *,
    d: date,
    mode: str,
    reconciliation: dict,
    trade_context: dict,
    safety_state: str,
    n_realized_trades: int,
    burned_hashes: frozenset,
    past_hypotheses: list,
    journal_tail: str,
) -> ReviewInput:
    """Pure assembly: given already-computed pieces, build the payload +
    ReviewContext + snapshot hash. No IO."""
    cold_start = n_realized_trades < V.COLD_START_MIN_TRADES
    ev_ids = valid_evidence_ids(trade_context)

    payload = {
        "as_of": d.isoformat(),
        "mode": mode,
        "cold_start": cold_start,
        "cold_start_banner": _cold_start_banner(n_realized_trades) if cold_start else None,
        "n_realized_trades": n_realized_trades,
        "safety_state": safety_state,
        "reconciliation": reconciliation,
        "held_positions": trade_context.get("held", []),
        "closed_trades": trade_context.get("closed", []),
        "valid_evidence_ids": sorted(ev_ids),
        "past_hypotheses": past_hypotheses,
        "journal_tail": journal_tail,
    }

    context = V.ReviewContext(
        n_realized_trades=n_realized_trades,
        safety_state=safety_state,
        valid_evidence_ids=ev_ids,
        burned_hashes=burned_hashes,
    )

    return ReviewInput(
        context=context,
        payload=payload,
        input_snapshot_hash=input_snapshot_hash(payload),
        cold_start=cold_start,
        n_realized_trades=n_realized_trades,
        safety_state=safety_state,
    )


def _read_journal_tail(path: Path = JOURNAL_PATH, chars: int = JOURNAL_TAIL_CHARS) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[-chars:]


def gather_review_input(
    d: date,
    mode: str = "dhan-paper",
    *,
    safety_state: str | None = None,
    journal_path: Path = JOURNAL_PATH,
) -> ReviewInput:
    """IO wrapper: call the Step 1-3 compute layer + the realworld store, then
    hand everything to the pure assembler. Imports are local so the pure path
    (assemble_review_input) has no DuckDB import cost."""
    from scripts.reconciliation import compute_reconciliation_for_date
    from scripts.trade_context import compute_trade_context_for_date
    from storage import portfolio_db, realworld_db

    reconciliation = compute_reconciliation_for_date(d, mode)
    trade_context = compute_trade_context_for_date(d, mode)

    conn = portfolio_db.connect()
    try:
        n = count_closed_round_trips(conn, mode)
    finally:
        conn.close()

    rw = realworld_db.connect()
    try:
        burned = frozenset(realworld_db.get_burned_hypothesis_hashes(rw, mode))
        past = [
            {"text": h["text"], "state": h["state"], "category": h["category"]}
            for h in realworld_db.get_hypotheses(rw, mode)
        ]
    finally:
        rw.close()

    if safety_state is None:
        from scripts.safety_evaluator import load_prior_state
        prior = load_prior_state()
        safety_state = prior.state if prior is not None else "NORMAL"

    return assemble_review_input(
        d=d,
        mode=mode,
        reconciliation=reconciliation,
        trade_context=trade_context,
        safety_state=safety_state,
        n_realized_trades=n,
        burned_hashes=burned,
        past_hypotheses=past,
        journal_tail=_read_journal_tail(journal_path),
    )
