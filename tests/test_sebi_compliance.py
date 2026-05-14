"""Unit tests for `scripts.sebi_compliance`."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.sebi_compliance import (
    OPS_THRESHOLD,
    ComplianceRecord,
    load_recent,
    log_today,
    write_compliance_record,
)


def test_record_idempotent_per_date_and_mode(tmp_path: Path) -> None:
    db = tmp_path / "sebi.duckdb"
    r1 = ComplianceRecord(
        as_of_date=date(2026, 5, 14),
        algo_id="ALGO_001",
        source_ip="203.0.113.5",
        orders_placed=4,
        max_burst_ops=0.001,
        mode="dhan-paper",
    )
    write_compliance_record(r1, db)
    # Overwrite same (date, mode)
    r2 = ComplianceRecord(
        as_of_date=date(2026, 5, 14),
        algo_id="ALGO_001",
        source_ip="203.0.113.5",
        orders_placed=6,        # updated
        max_burst_ops=0.002,
        mode="dhan-paper",
    )
    write_compliance_record(r2, db)
    rows = load_recent(days=10, db_path=db)
    assert len(rows) == 1
    assert rows[0].orders_placed == 6


def test_threshold_warning_in_notes(tmp_path: Path) -> None:
    db = tmp_path / "sebi.duckdb"
    with patch("scripts.sebi_compliance.detect_source_ip", return_value="127.0.0.1"):
        rec = log_today(
            mode="dhan-live",
            orders_placed=200,
            max_burst_ops=OPS_THRESHOLD + 1.0,
            db_path=db,
        )
    assert "empanelment" in rec.notes


def test_no_threshold_warning_below_limit(tmp_path: Path) -> None:
    db = tmp_path / "sebi.duckdb"
    with patch("scripts.sebi_compliance.detect_source_ip", return_value="127.0.0.1"):
        rec = log_today(
            mode="dhan-paper",
            orders_placed=6,
            max_burst_ops=0.001,
            db_path=db,
        )
    assert rec.notes == ""


def test_algo_id_unset_marked_as_UNSET(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SEBI_ALGO_ID", raising=False)
    db = tmp_path / "sebi.duckdb"
    with patch("scripts.sebi_compliance.detect_source_ip", return_value="127.0.0.1"):
        rec = log_today(
            mode="dhan-paper", orders_placed=0, max_burst_ops=0.0, db_path=db,
        )
    assert rec.algo_id == "UNSET"


def test_load_recent_empty_when_no_db(tmp_path: Path) -> None:
    assert load_recent(days=30, db_path=tmp_path / "missing.duckdb") == []
