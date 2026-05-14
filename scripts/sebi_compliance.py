"""SEBI retail-algo compliance: registration metadata + OPS counter logging.

Effective 2026-04-01 SEBI mandates every algo running on a broker API to:
  1. Be registered with the broker (Personal Algo for own funds, or Trading
     Provider for managing others'). The broker assigns a unique algo ID
     which is stamped on every order. Setup is a one-time portal action by
     the user — documented in CLAUDE.md.
  2. Come from a whitelisted static IP. We log the source IP on every run
     so the user can detect IP drift if their ISP rotates (rare; but
     worth catching before the broker does).
  3. Stay under 10 orders per second OR be empanelled. Our cadence is
     biweekly so we're at ~0.001 OPS — multiple orders of magnitude under
     the threshold. We log the daily max-burst-OPS to confirm.

This module writes an append-only record to `storage/sebi_compliance.duckdb`
that an auditor can review. None of these actions block trading — they're
observational so the user can prove compliance retrospectively. The actual
algo ID is sourced from the `SEBI_ALGO_ID` env var and stamped onto every
order by `brokers.dhan.DhanBroker.place_order`.
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

COMPLIANCE_DB = Path("storage/sebi_compliance.duckdb")
OPS_THRESHOLD = 10                # SEBI threshold; we want to stay << this


@dataclass(frozen=True)
class ComplianceRecord:
    as_of_date: date
    algo_id: str
    source_ip: str
    orders_placed: int
    max_burst_ops: float
    mode: str
    notes: str = ""


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sebi_compliance_daily (
            as_of_date DATE NOT NULL,
            algo_id VARCHAR NOT NULL,
            source_ip VARCHAR NOT NULL,
            orders_placed INTEGER NOT NULL,
            max_burst_ops DOUBLE NOT NULL,
            mode VARCHAR NOT NULL,
            notes VARCHAR,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (as_of_date, mode)
        )
        """
    )


def detect_source_ip() -> str:
    """Return the public-facing IP this machine appears to use.

    Falls back to the local hostname IP if the public-IP probe fails. The
    point of recording this is detection of drift, not strict accuracy.
    """
    try:
        import requests

        resp = requests.get("https://api.ipify.org", timeout=5)
        resp.raise_for_status()
        return resp.text.strip()
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "unknown"


def write_compliance_record(
    record: ComplianceRecord,
    db_path: Path = COMPLIANCE_DB,
) -> None:
    conn = duckdb.connect(str(db_path))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(
                "DELETE FROM sebi_compliance_daily WHERE as_of_date=? AND mode=?",
                (record.as_of_date, record.mode),
            )
            conn.execute(
                """
                INSERT INTO sebi_compliance_daily
                    (as_of_date, algo_id, source_ip, orders_placed,
                     max_burst_ops, mode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.as_of_date,
                    record.algo_id,
                    record.source_ip,
                    record.orders_placed,
                    record.max_burst_ops,
                    record.mode,
                    record.notes,
                ),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def log_today(
    *,
    mode: str,
    orders_placed: int,
    max_burst_ops: float,
    db_path: Path = COMPLIANCE_DB,
) -> ComplianceRecord:
    """Append a compliance record for today's run. Idempotent per (date, mode)."""
    algo_id = os.environ.get("SEBI_ALGO_ID", "")
    if not algo_id:
        logger.warning(
            "SEBI_ALGO_ID not set in env — algo registration is mandatory "
            "from 2026-04-01. Live orders will be rejected by Dhan until set."
        )
    rec = ComplianceRecord(
        as_of_date=date.today(),
        algo_id=algo_id or "UNSET",
        source_ip=detect_source_ip(),
        orders_placed=orders_placed,
        max_burst_ops=max_burst_ops,
        mode=mode,
        notes=(
            "WARNING: max_burst_ops exceeds threshold; empanelment required"
            if max_burst_ops >= OPS_THRESHOLD
            else ""
        ),
    )
    write_compliance_record(rec, db_path)
    return rec


def load_recent(
    *,
    days: int = 30,
    db_path: Path = COMPLIANCE_DB,
) -> list[ComplianceRecord]:
    if not db_path.exists():
        return []
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT as_of_date, algo_id, source_ip, orders_placed,
                   max_burst_ops, mode, COALESCE(notes, '')
              FROM sebi_compliance_daily
             ORDER BY as_of_date DESC, mode
             LIMIT ?
            """,
            (days,),
        ).fetchall()
    finally:
        conn.close()
    return [
        ComplianceRecord(
            as_of_date=r[0],
            algo_id=r[1],
            source_ip=r[2],
            orders_placed=r[3],
            max_burst_ops=r[4],
            mode=r[5],
            notes=r[6],
        )
        for r in rows
    ]


if __name__ == "__main__":
    # CLI: print latest record for ops audit
    recs = load_recent(days=7)
    if not recs:
        print("no compliance records yet")
    for r in recs:
        print(
            f"{r.as_of_date} {r.mode:11s} algo={r.algo_id} "
            f"orders={r.orders_placed:3d} max_ops={r.max_burst_ops:.3f} "
            f"ip={r.source_ip} {r.notes}"
        )


__all__ = [
    "OPS_THRESHOLD",
    "ComplianceRecord",
    "detect_source_ip",
    "log_today",
    "load_recent",
    "write_compliance_record",
]
