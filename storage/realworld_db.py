"""Durable store for the monthly LLM review (Step 4).

Deliberately SEPARATE from storage/portfolio.duckdb. The portfolio ledger is
broker-truth (orders, fills, lots, realized trades); this file is the
research-meta layer. Almost everything the review reasons over (reconciliation
Q1-Q7, held/closed trade attribution, safety state, the realized-trade count)
is recomputed on-render from the ledger and price history — so it needs no
storage here. Only two facts genuinely cannot be recomputed and therefore live
here:

    hypotheses  — every hypothesis the review has ever emitted, with its state.
                  The validator's duplicate gate checks new hypotheses against
                  the lexical hashes of all *burned* ones (rejected/obsolete/
                  withdrawn/expired) so a killed idea is never re-litigated.
    audit       — one row per review run (pass OR fail). Provenance: input
                  snapshot hash, prompt/model/validator versions, the full LLM
                  output, and the validator's verdict. Guarantees every run is
                  reproducible and attributable.

Thin DAO surface — no ORM, mirroring storage/portfolio_db.py.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "storage" / "realworld.duckdb"

# Hypothesis lifecycle. PENDING = passed the review validator, awaiting the
# on-demand Step 5 validator. VALIDATOR_KEPT = promoted into strategy.py.
# The rest are terminal "burned" states the duplicate gate guards against.
HYPOTHESIS_STATES = frozenset(
    {"PENDING", "VALIDATOR_KEPT", "VALIDATOR_REJECTED", "OBSOLETE", "WITHDRAWN", "EXPIRED"}
)
# A KEPT hypothesis is *live strategy*, not a dead end — it must NOT block
# re-proposal. Only genuinely-dead states burn a lexical hash.
BURNED_STATES = frozenset({"VALIDATOR_REJECTED", "OBSOLETE", "WITHDRAWN", "EXPIRED"})

# Allowed enum values, mirrored by the validator's schema gate.
HYPOTHESIS_CATEGORIES = frozenset(
    {"risk_off", "signal", "hyperparameter", "cost", "execution", "data_bug"}
)
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the realworld duckdb file, ensuring the schema exists.
    init_schema is idempotent. Caller closes when done."""
    conn = duckdb.connect(str(db_path))
    init_schema(conn)
    return conn


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hypotheses (
            hypothesis_id           VARCHAR   PRIMARY KEY,
            review_id               VARCHAR   NOT NULL,
            created_at              TIMESTAMP NOT NULL,
            mode                    VARCHAR   NOT NULL,
            category                VARCHAR   NOT NULL,
            confidence              VARCHAR   NOT NULL,
            text                    VARCHAR   NOT NULL,
            causal_story            VARCHAR   NOT NULL,
            predeclared_test        VARCHAR   NOT NULL,
            supporting_evidence_json VARCHAR  NOT NULL,
            text_lexical_hash       VARCHAR   NOT NULL,
            state                   VARCHAR   NOT NULL DEFAULT 'PENDING',
            state_updated_at        TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit (
            review_id               VARCHAR   PRIMARY KEY,
            run_at                  TIMESTAMP NOT NULL,
            mode                    VARCHAR   NOT NULL,
            trigger                 VARCHAR   NOT NULL,
            input_snapshot_hash     VARCHAR   NOT NULL,
            prompt_version          VARCHAR   NOT NULL,
            model_id                VARCHAR   NOT NULL,
            output_json             VARCHAR   NOT NULL,
            validator_version       VARCHAR   NOT NULL,
            validator_result        VARCHAR   NOT NULL,
            validator_failures_json VARCHAR   NOT NULL,
            n_realized_trades       INTEGER   NOT NULL,
            safety_state            VARCHAR   NOT NULL,
            cold_start              BOOLEAN   NOT NULL
        )
        """
    )


def insert_audit(
    conn: duckdb.DuckDBPyConnection,
    *,
    review_id: str,
    run_at: datetime,
    mode: str,
    trigger: str,
    input_snapshot_hash: str,
    prompt_version: str,
    model_id: str,
    output_json: str,
    validator_version: str,
    validator_result: str,
    validator_failures_json: str,
    n_realized_trades: int,
    safety_state: str,
    cold_start: bool,
) -> None:
    conn.execute(
        "INSERT INTO audit (review_id, run_at, mode, trigger, input_snapshot_hash, "
        " prompt_version, model_id, output_json, validator_version, validator_result, "
        " validator_failures_json, n_realized_trades, safety_state, cold_start) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [review_id, run_at, mode, trigger, input_snapshot_hash, prompt_version,
         model_id, output_json, validator_version, validator_result,
         validator_failures_json, n_realized_trades, safety_state, cold_start],
    )


def get_audit(conn: duckdb.DuckDBPyConnection, review_id: str) -> dict | None:
    cur = conn.execute("SELECT * FROM audit WHERE review_id = ?", [review_id])
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def insert_hypothesis(
    conn: duckdb.DuckDBPyConnection,
    *,
    hypothesis_id: str,
    review_id: str,
    created_at: datetime,
    mode: str,
    category: str,
    confidence: str,
    text: str,
    causal_story: str,
    predeclared_test: str,
    supporting_evidence_json: str,
    text_lexical_hash: str,
    state: str = "PENDING",
) -> None:
    conn.execute(
        "INSERT INTO hypotheses (hypothesis_id, review_id, created_at, mode, category, "
        " confidence, text, causal_story, predeclared_test, supporting_evidence_json, "
        " text_lexical_hash, state, state_updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [hypothesis_id, review_id, created_at, mode, category, confidence, text,
         causal_story, predeclared_test, supporting_evidence_json,
         text_lexical_hash, state, created_at],
    )


def update_hypothesis_state(
    conn: duckdb.DuckDBPyConnection,
    hypothesis_id: str,
    new_state: str,
    *,
    updated_at: datetime,
) -> None:
    conn.execute(
        "UPDATE hypotheses SET state = ?, state_updated_at = ? WHERE hypothesis_id = ?",
        [new_state, updated_at, hypothesis_id],
    )


def get_hypotheses(
    conn: duckdb.DuckDBPyConnection, mode: str, state: str | None = None
) -> list[dict]:
    if state is None:
        cur = conn.execute(
            "SELECT * FROM hypotheses WHERE mode = ? ORDER BY created_at", [mode])
    else:
        cur = conn.execute(
            "SELECT * FROM hypotheses WHERE mode = ? AND state = ? ORDER BY created_at",
            [mode, state])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_burned_hypothesis_hashes(conn: duckdb.DuckDBPyConnection, mode: str) -> set[str]:
    """Lexical hashes of all hypotheses in a burned (terminally-dead) state for
    this mode. The validator's duplicate gate rejects any new hypothesis whose
    hash is in this set."""
    placeholders = ", ".join("?" for _ in BURNED_STATES)
    cur = conn.execute(
        f"SELECT text_lexical_hash FROM hypotheses WHERE mode = ? "
        f"AND state IN ({placeholders})",
        [mode, *sorted(BURNED_STATES)],
    )
    return {r[0] for r in cur.fetchall()}
