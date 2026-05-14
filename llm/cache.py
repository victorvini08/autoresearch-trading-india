"""Deterministic sqlite cache for LLM outputs.

Key: (date, ticker, prompt_hash, model_id). Same inputs always map to the
same row. For per-date features (e.g. macro_regime) that have no ticker,
the convention is `ticker = "_macro_"` (a sentinel string that can't be a
real exchange ticker).

Backstop guarantee: cache hits make backtest iterations deterministic. The
agent's reproducibility argument across iterations depends on the cache, not
on calling the same model multiple times — different LLM calls return slightly
different outputs even at temperature=0.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "storage" / "llm_cache.sqlite"

# Ticker-key conventions: macro features have no ticker, so we use a sentinel.
# Sentiment and events share (date, ticker), so we prefix the ticker key with
# the feature kind to keep them in distinct cache rows.
MACRO_TICKER_SENTINEL = "_macro_"


def sentiment_ticker_key(ticker: str) -> str:
    return f"_sent_{ticker}"


def events_ticker_key(ticker: str) -> str:
    return f"_evt_{ticker}"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
    date         TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    prompt_hash  TEXT NOT NULL,
    model_id     TEXT NOT NULL,
    output_json  TEXT NOT NULL,
    written_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, ticker, prompt_hash, model_id)
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute(_SCHEMA)
    return con


def cache_get(
    date: str, ticker: str, prompt_hash: str, model_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the cached output dict for this key, or None if no row matches.

    `model_id` is optional — when None (the default), any model that wrote a
    row for this (date, ticker, prompt_hash) counts as a hit. Use this when
    you don't care which model produced the classification (the common case
    once the cache has been filled). Pass an explicit `model_id` for strict
    isolation (ablation studies comparing two models on the same prompts).
    """
    con = _connect()
    try:
        if model_id is None:
            row = con.execute(
                "SELECT output_json FROM llm_cache "
                "WHERE date = ? AND ticker = ? AND prompt_hash = ? "
                "ORDER BY written_at DESC, rowid DESC LIMIT 1",
                [date, ticker, prompt_hash],
            ).fetchone()
        else:
            row = con.execute(
                "SELECT output_json FROM llm_cache "
                "WHERE date = ? AND ticker = ? AND prompt_hash = ? "
                "AND model_id = ?",
                [date, ticker, prompt_hash, model_id],
            ).fetchone()
    finally:
        con.close()
    return json.loads(row[0]) if row else None


def cache_put(
    date: str, ticker: str, prompt_hash: str, model_id: str,
    output: dict[str, Any],
) -> None:
    """Insert-or-replace a cache row."""
    con = _connect()
    try:
        con.execute(
            "INSERT OR REPLACE INTO llm_cache "
            "(date, ticker, prompt_hash, model_id, output_json) "
            "VALUES (?, ?, ?, ?, ?)",
            [date, ticker, prompt_hash, model_id, json.dumps(output)],
        )
        con.commit()
    finally:
        con.close()


def cache_get_latest(
    date: str, ticker: str, model_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the most-recently-written cache row for (date, ticker), regardless
    of prompt_hash. Used at strategy-read time: 'whatever's there is fine.'

    `model_id` defaults to None which matches any model — so a cache filled by
    Codex is readable by strategy code running with Claude (and vice versa).
    Pass an explicit `model_id` to restrict to one model's outputs.
    """
    con = _connect()
    try:
        if model_id is None:
            row = con.execute(
                "SELECT output_json FROM llm_cache "
                "WHERE date = ? AND ticker = ? "
                "ORDER BY written_at DESC, rowid DESC LIMIT 1",
                [date, ticker],
            ).fetchone()
        else:
            row = con.execute(
                "SELECT output_json FROM llm_cache "
                "WHERE date = ? AND ticker = ? AND model_id = ? "
                "ORDER BY written_at DESC, rowid DESC LIMIT 1",
                [date, ticker, model_id],
            ).fetchone()
    finally:
        con.close()
    return json.loads(row[0]) if row else None


def cache_size() -> int:
    """Total rows in the cache (useful for tests + ops sanity)."""
    con = _connect()
    try:
        return int(con.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0])
    finally:
        con.close()
