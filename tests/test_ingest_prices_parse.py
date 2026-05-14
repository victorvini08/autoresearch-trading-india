"""Parse-only tests for `data.ingest_prices.parse_bhav_csv`. No network."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from data.ingest_prices import (
    DailyBar,
    parse_bhav_csv,
    write_bars,
)

# Realistic NSE bhav header (post-2021 schema)
_BHAV_CSV = """\
SYMBOL,SERIES,DATE1,PREV_CLOSE,OPEN_PRICE,HIGH_PRICE,LOW_PRICE,LAST_PRICE,CLOSE_PRICE,AVG_PRICE,TTL_TRD_QNTY,TURNOVER_LACS,NO_OF_TRADES,DELIV_QTY,DELIV_PER
RELIANCE,EQ,13-May-2026,1200.00,1200.00,1215.00,1195.00,1205.00,1205.50,1205.00,1100000,13255.55,45000,650000,59.09
INFY,EQ,13-May-2026,1500.00,1500.00,1525.00,1500.00,1520.00,1520.00,1512.50,900000,13612.50,35000,520000,57.78
SOMESME,SM,13-May-2026,100.00,100.00,102.00,99.00,101.00,101.00,100.00,1000,1.00,5,0,0
"""


def test_parse_bhav_csv_basic() -> None:
    bars = parse_bhav_csv(_BHAV_CSV.encode("utf-8"))
    tickers = {b.ticker for b in bars}
    assert "RELIANCE" in tickers
    assert "INFY" in tickers
    # SM series is filtered out by default (EQ-only)
    assert "SOMESME" not in tickers


def test_parse_bhav_csv_universe_filter() -> None:
    bars = parse_bhav_csv(_BHAV_CSV.encode("utf-8"), tickers={"RELIANCE"})
    assert len(bars) == 1
    assert bars[0].ticker == "RELIANCE"
    assert bars[0].close == 1205.50
    assert bars[0].volume == 1100000


def test_parse_bhav_csv_value_in_crore() -> None:
    bars = parse_bhav_csv(_BHAV_CSV.encode("utf-8"), tickers={"RELIANCE"})
    # 13255.55 lacs = 132.5555 crores
    assert abs(bars[0].value_inr_crores - 132.5555) < 0.001


def test_write_bars_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "prices.duckdb"
    bars = parse_bhav_csv(_BHAV_CSV.encode("utf-8"))
    n1 = write_bars(db, bars)
    n2 = write_bars(db, bars)  # rewrite same slice — should not duplicate
    assert n1 == n2 == 2
    # Confirm only 2 rows present
    conn = duckdb.connect(str(db), read_only=True)
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    finally:
        conn.close()
    assert cnt == 2


def test_parse_bhav_csv_missing_columns_raises() -> None:
    csv_text = "SYMBOL,SERIES\nRELIANCE,EQ\n"
    with pytest.raises(ValueError):
        parse_bhav_csv(csv_text.encode("utf-8"))


def test_dailybar_dataclass_fields() -> None:
    b = DailyBar(
        ticker="X", dt=date(2026, 5, 13),
        open=1.0, high=2.0, low=0.5, close=1.5,
        volume=100, value_inr_crores=0.015,
    )
    assert b.ticker == "X"
    assert b.close == 1.5
