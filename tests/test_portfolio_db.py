"""DAO round-trip and schema tests for the paper-trade ledger.

TWEAKS from US repo:
- STCG_RATE: 0.312 -> 0.15  (India equity STCG)
- LTCG_RATE: 0.20  -> 0.10  (India equity LTCG)
- LTCG_HOLDING_DAYS: 730 -> 365 (Indian Income-Tax Act §111A/112A: 12 months)
- LTCG_THRESHOLD_INR: ₹1L annual exemption (not used in per-trade asserts but
  exposed via storage.portfolio_db for downstream use)
- Test field names (e.g. amount_usd, realized_pnl_usd, cash_usd) are kept
  as-is — those are column / field NAMES in storage.portfolio_db, not
  currency assertions. They denote signed numeric amounts that for India
  carry INR semantics.

Each test creates a fresh in-memory duckdb via :memory: so tests don't leak."""
from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, timedelta

import duckdb
import pytest

from storage import portfolio_db


@pytest.fixture
def conn():
    """Fresh in-memory duckdb with schema initialised."""
    c = duckdb.connect(":memory:")
    portfolio_db.init_schema(c)
    yield c
    c.close()


def test_init_schema_creates_all_tables(conn):
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    names = {r[0] for r in rows}
    assert names == {
        "actual_fills",
        "broker_positions",
        "cash_ledger",
        "desired_targets",
        "discrepancies",
        "position_lots",
        "realized_trades",
        "submitted_orders",
    }


def test_init_schema_is_idempotent(conn):
    portfolio_db.init_schema(conn)
    portfolio_db.init_schema(conn)
    rows = conn.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).fetchone()
    assert rows[0] == 8


def test_schema_includes_mode_in_pks(conn):
    # desired_targets PK = (as_of_date, ticker, mode)
    cols = conn.execute(
        "SELECT column_name FROM information_schema.key_column_usage "
        "WHERE table_name = 'desired_targets' ORDER BY ordinal_position"
    ).fetchall()
    assert [c[0] for c in cols] == ["as_of_date", "ticker", "mode"]

    # broker_positions PK = (snapshot_date, ticker, mode)
    cols = conn.execute(
        "SELECT column_name FROM information_schema.key_column_usage "
        "WHERE table_name = 'broker_positions' ORDER BY ordinal_position"
    ).fetchall()
    assert [c[0] for c in cols] == ["snapshot_date", "ticker", "mode"]


def test_ledger_state_dataclass_fields():
    expected = {
        "mode",
        "as_of",
        "cash_usd",
        "positions",
        "mark_equity",
        "peak_equity",
        "today_pnl_usd",
        "halted",
    }
    assert {f.name for f in fields(portfolio_db.LedgerState)} == expected


def test_india_tax_constants_match_act_111a_112a():
    """India equity tax constants:
       - STCG (§111A): 15% on gains held under 12 months
       - LTCG (§112A): 10% on gains held >= 12 months
       - LTCG exemption: ₹1L per FY (not asserted per-trade)
    """
    assert portfolio_db.STCG_RATE == 0.15
    assert portfolio_db.LTCG_RATE == 0.10
    assert portfolio_db.LTCG_HOLDING_DAYS == 365
    assert portfolio_db.LTCG_THRESHOLD_INR == 100_000


def test_as_of_date_is_nullable_on_cash_ledger_and_discrepancies(conn):
    """AC3: cash_ledger and discrepancies must have a nullable as_of_date so
    deposits/withdrawals (cash) and portfolio-level/manual discrepancies (no
    specific date) can be recorded without a placeholder date."""
    for table in ("cash_ledger", "discrepancies"):
        row = conn.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = ? AND column_name = 'as_of_date'",
            [table],
        ).fetchone()
        assert row is not None, f"{table}.as_of_date column missing"
        assert row[0] == "YES", f"{table}.as_of_date should be nullable"


def test_connect_uses_explicit_path_when_provided(tmp_path):
    """AC5: connect(db_path=...) opens the file at the given path; the default
    path is used otherwise. We verify the explicit-override branch here; the
    default-path branch is exercised implicitly by every Task 2+ test."""
    explicit = tmp_path / "custom_portfolio.duckdb"
    c = portfolio_db.connect(explicit)
    portfolio_db.init_schema(c)
    c.close()
    assert explicit.exists(), f"connect() did not create the file at {explicit}"


def test_connect_auto_initialises_schema(tmp_path):
    """Regression (2026-05-19): connect() must self-bootstrap the schema.

    premarket_scan / run_live / daily_report / dashboard all do
    `portfolio_db.connect(path)` then immediately read the ledger WITHOUT
    calling init_schema — a fresh storage/portfolio.duckdb therefore
    crashed every morning with 'Table broker_positions does not exist',
    so paper trading never actually executed. connect() now runs the
    idempotent init_schema itself."""
    fresh = tmp_path / "fresh_ledger.duckdb"
    c = portfolio_db.connect(fresh)  # NO explicit init_schema
    try:
        names = {
            r[0] for r in c.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        assert names == {
            "actual_fills", "broker_positions", "cash_ledger",
            "desired_targets", "discrepancies", "position_lots",
            "realized_trades", "submitted_orders",
        }
        # The exact query that was crashing premarket_scan must now work.
        c.execute(
            "SELECT MAX(snapshot_date) FROM broker_positions "
            "WHERE mode = ? AND snapshot_date <= ?",
            ("dhan-paper", date(2026, 5, 19)),
        )
    finally:
        c.close()


def test_upsert_target_round_trip(conn):
    portfolio_db.upsert_target(
        conn,
        as_of_date=date(2026, 5, 1),
        ticker="AAPL",
        target_fraction=0.095,
        source="signal_today.py@abc123",
        mode="paper",
    )
    row = conn.execute(
        "SELECT target_fraction, source FROM desired_targets "
        "WHERE as_of_date = ? AND ticker = ? AND mode = ?",
        [date(2026, 5, 1), "AAPL", "paper"],
    ).fetchone()
    assert row == (0.095, "signal_today.py@abc123")


def test_upsert_target_overwrites_on_pk(conn):
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 1), ticker="AAPL",
        target_fraction=0.05, source="v1", mode="paper",
    )
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 1), ticker="AAPL",
        target_fraction=0.10, source="v2", mode="paper",
    )
    row = conn.execute(
        "SELECT target_fraction, source FROM desired_targets WHERE ticker = 'AAPL'"
    ).fetchone()
    assert row == (0.10, "v2")


def test_insert_order_and_fill_round_trip(conn):
    portfolio_db.insert_order(
        conn,
        order_id="paper-2026-05-01-AAPL-buy-1",
        submitted_at=datetime(2026, 5, 1, 16, 5),
        as_of_date=date(2026, 5, 1),
        ticker="AAPL",
        side="buy",
        order_type="market",
        quantity=50,
        limit_price=None,
        status="pending",
        mode="paper",
    )
    portfolio_db.insert_fill(
        conn,
        fill_id="paper-2026-05-01-AAPL-buy-1-fill-1",
        order_id="paper-2026-05-01-AAPL-buy-1",
        filled_at=datetime(2026, 5, 2, 9, 30),
        ticker="AAPL",
        side="buy",
        quantity=50,
        fill_price=200.10,
        commission=29.5,
        slippage_bps=5.0,
        mode="paper",
    )
    portfolio_db.update_order_status(conn, "paper-2026-05-01-AAPL-buy-1", "filled")

    order = conn.execute(
        "SELECT status, quantity FROM submitted_orders WHERE order_id = ?",
        ["paper-2026-05-01-AAPL-buy-1"],
    ).fetchone()
    assert order == ("filled", 50)

    fill = conn.execute(
        "SELECT fill_price, commission FROM actual_fills "
        "WHERE order_id = ?",
        ["paper-2026-05-01-AAPL-buy-1"],
    ).fetchone()
    assert fill == (200.10, 29.5)


def test_cash_ledger_balance_sums_signed_amounts(conn):
    portfolio_db.insert_cash_entry(
        conn, entry_id="e1", entry_at=datetime(2026, 5, 1, 9),
        as_of_date=None, kind="deposit", amount_usd=100_000.0,
        notes="initial", mode="paper",
    )
    portfolio_db.insert_cash_entry(
        conn, entry_id="e2", entry_at=datetime(2026, 5, 2, 10),
        as_of_date=date(2026, 5, 1), kind="buy", amount_usd=-9_500.0,
        notes=None, mode="paper",
    )
    portfolio_db.insert_cash_entry(
        conn, entry_id="e3", entry_at=datetime(2026, 5, 2, 10),
        as_of_date=date(2026, 5, 1), kind="commission", amount_usd=-29.5,
        notes=None, mode="paper",
    )
    assert portfolio_db.get_cash_balance(conn, mode="paper") == pytest.approx(90_470.5)


def test_position_upsert_and_read(conn):
    portfolio_db.upsert_position(
        conn, snapshot_date=date(2026, 5, 2), ticker="AAPL", quantity=50,
        avg_entry_price=200.10, mark_price=201.50, mark_value=10075.0, mode="paper",
    )
    positions = portfolio_db.get_positions_as_of(conn, date(2026, 5, 2), mode="paper")
    assert positions["AAPL"].quantity == 50
    assert positions["AAPL"].mark_value == pytest.approx(10075.0)


def test_peak_equity_returns_max_over_snapshots(conn):
    # Seed deposit
    portfolio_db.insert_cash_entry(
        conn, entry_id="d1", entry_at=datetime(2026, 5, 1, 9),
        as_of_date=None, kind="deposit", amount_usd=100_000.0,
        notes="initial", mode="paper",
    )
    # Three snapshots, equity peak should be the highest
    for d, qty, mark in [
        (date(2026, 5, 2), 100, 1100.0),   # equity = cash 90_500 + 100*1100 = 200_500
        (date(2026, 5, 3), 100, 1200.0),   # equity = ... + 100*1200 = 210_500 (peak)
        (date(2026, 5, 4), 100, 1050.0),   # equity = ... + 100*1050 = 195_500
    ]:
        portfolio_db.upsert_position(
            conn, snapshot_date=d, ticker="X", quantity=qty,
            avg_entry_price=1000.0, mark_price=mark, mark_value=qty * mark, mode="paper",
        )
    # Buy entry to consume cash: 100 * 1000 + 100 commission = 100_100 outflow
    portfolio_db.insert_cash_entry(
        conn, entry_id="b1", entry_at=datetime(2026, 5, 1, 9, 30),
        as_of_date=date(2026, 5, 1), kind="buy", amount_usd=-100_000.0,
        notes=None, mode="paper",
    )
    portfolio_db.insert_cash_entry(
        conn, entry_id="b2", entry_at=datetime(2026, 5, 1, 9, 30),
        as_of_date=date(2026, 5, 1), kind="commission", amount_usd=-100.0,
        notes=None, mode="paper",
    )
    peak = portfolio_db.get_peak_equity(conn, mode="paper")
    # Cash after buy = -100, positions peak at 100*1200 = 120_000, total peak = 119_900
    assert peak == pytest.approx(119_900.0)


def test_delete_day_scopes_to_one_date(conn):
    # Set up two days of activity
    for d in [date(2026, 5, 1), date(2026, 5, 2)]:
        portfolio_db.insert_order(
            conn, order_id=f"paper-{d}-X-buy-1", submitted_at=datetime.combine(d, datetime.min.time()),
            as_of_date=d, ticker="X", side="buy", order_type="market",
            quantity=10, limit_price=None, status="filled", mode="paper",
        )
        portfolio_db.insert_cash_entry(
            conn, entry_id=f"c-{d}", entry_at=datetime.combine(d, datetime.min.time()),
            as_of_date=d, kind="buy", amount_usd=-100.0, notes=None, mode="paper",
        )
        portfolio_db.upsert_target(
            conn, as_of_date=d, ticker="X", target_fraction=0.1, source="t", mode="paper",
        )

    portfolio_db.delete_day(conn, as_of_date=date(2026, 5, 1), mode="paper")

    # May-1 rows in dependent tables gone
    orders = conn.execute(
        "SELECT count(*) FROM submitted_orders WHERE as_of_date = ?",
        [date(2026, 5, 1)],
    ).fetchone()
    assert orders[0] == 0
    cash = conn.execute(
        "SELECT count(*) FROM cash_ledger WHERE as_of_date = ?",
        [date(2026, 5, 1)],
    ).fetchone()
    assert cash[0] == 0

    # May-2 untouched
    orders2 = conn.execute(
        "SELECT count(*) FROM submitted_orders WHERE as_of_date = ?",
        [date(2026, 5, 2)],
    ).fetchone()
    assert orders2[0] == 1

    # desired_targets preserved on May-1 (UPSERT-overwritten on rewrite)
    targets = conn.execute(
        "SELECT count(*) FROM desired_targets WHERE as_of_date = ?",
        [date(2026, 5, 1)],
    ).fetchone()
    assert targets[0] == 1


def test_delete_day_clears_broker_positions_via_fill_join(conn):
    """Regression: delete_day's broker_positions DELETE uses a JOIN through
    actual_fills, which must NOT be deleted yet when the broker_positions
    DELETE runs. This test exercises the correct order."""
    portfolio_db.insert_order(
        conn,
        order_id="paper-2026-05-01-AAPL-buy-1",
        submitted_at=datetime(2026, 5, 1, 16, 5),
        as_of_date=date(2026, 5, 1),
        ticker="AAPL",
        side="buy",
        order_type="market",
        quantity=50,
        limit_price=None,
        status="filled",
        mode="paper",
    )
    portfolio_db.insert_fill(
        conn,
        fill_id="paper-2026-05-01-AAPL-buy-1-fill-1",
        order_id="paper-2026-05-01-AAPL-buy-1",
        filled_at=datetime(2026, 5, 2, 9, 30),
        ticker="AAPL",
        side="buy",
        quantity=50,
        fill_price=200.10,
        commission=29.5,
        slippage_bps=5.0,
        mode="paper",
    )
    portfolio_db.upsert_position(
        conn,
        snapshot_date=date(2026, 5, 2),
        ticker="AAPL",
        quantity=50,
        avg_entry_price=200.10,
        mark_price=201.50,
        mark_value=10075.0,
        mode="paper",
    )

    # Sanity: position is present before delete_day
    before = conn.execute(
        "SELECT count(*) FROM broker_positions WHERE snapshot_date = ? AND mode = 'paper'",
        [date(2026, 5, 2)],
    ).fetchone()[0]
    assert before == 1

    portfolio_db.delete_day(conn, as_of_date=date(2026, 5, 1), mode="paper")

    # The position derived from a fill of a 2026-05-01 order must be gone
    after = conn.execute(
        "SELECT count(*) FROM broker_positions WHERE snapshot_date = ? AND mode = 'paper'",
        [date(2026, 5, 2)],
    ).fetchone()[0]
    assert after == 0


def test_wipe_mode_clears_paper_only(conn):
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 1), ticker="X",
        target_fraction=0.1, source="p", mode="paper",
    )
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 1), ticker="X",
        target_fraction=0.2, source="r", mode="real",
    )
    portfolio_db.wipe_mode(conn, "paper")

    paper = conn.execute(
        "SELECT count(*) FROM desired_targets WHERE mode = 'paper'"
    ).fetchone()[0]
    real = conn.execute(
        "SELECT count(*) FROM desired_targets WHERE mode = 'real'"
    ).fetchone()[0]
    assert paper == 0 and real == 1


def test_load_state_assembles_correctly(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", tmp_path / "halt.json")

    portfolio_db.insert_cash_entry(
        conn, entry_id="d1", entry_at=datetime(2026, 5, 1, 9),
        as_of_date=None, kind="deposit", amount_usd=100_000.0,
        notes="initial", mode="paper",
    )
    portfolio_db.upsert_position(
        conn, snapshot_date=date(2026, 5, 2), ticker="X", quantity=10,
        avg_entry_price=100.0, mark_price=110.0, mark_value=1100.0, mode="paper",
    )
    portfolio_db.upsert_position(
        conn, snapshot_date=date(2026, 5, 3), ticker="X", quantity=10,
        avg_entry_price=100.0, mark_price=120.0, mark_value=1200.0, mode="paper",
    )

    state = portfolio_db.load_state(conn, mode="paper", as_of=date(2026, 5, 3))

    assert state.mode == "paper"
    assert state.as_of == date(2026, 5, 3)
    assert state.cash_usd == pytest.approx(100_000.0)
    assert state.positions == {"X": 10}
    assert state.mark_equity == pytest.approx(101_200.0)
    assert state.peak_equity == pytest.approx(101_200.0)
    assert state.today_pnl_usd == pytest.approx(100.0)   # 101_200 - 101_100
    assert state.halted is False


# ---------------------------------------------------------------------------
# I-3: delete_targets_for_day scopes to one (date, mode) pair
# ---------------------------------------------------------------------------

def test_delete_targets_for_day_clears_only_that_day(conn):
    """Insert targets for D1 and D2 for the same mode. Call
    delete_targets_for_day(D1). Assert D1 targets gone, D2 targets intact.
    """
    d1 = date(2026, 5, 1)
    d2 = date(2026, 5, 2)

    for d, tk in [(d1, "AAPL"), (d1, "MSFT"), (d2, "GOOG")]:
        portfolio_db.upsert_target(
            conn,
            as_of_date=d,
            ticker=tk,
            target_fraction=0.1,
            source="test",
            mode="paper",
        )

    portfolio_db.delete_targets_for_day(conn, as_of_date=d1, mode="paper")

    d1_count = conn.execute(
        "SELECT count(*) FROM desired_targets WHERE as_of_date = ? AND mode = 'paper'",
        [d1],
    ).fetchone()[0]
    d2_count = conn.execute(
        "SELECT count(*) FROM desired_targets WHERE as_of_date = ? AND mode = 'paper'",
        [d2],
    ).fetchone()[0]

    assert d1_count == 0, f"Expected D1 targets cleared, got {d1_count}"
    assert d2_count == 1, f"Expected D2 targets intact, got {d2_count}"


# ---------------------------------------------------------------------------
# Tax accounting: position_lots + realized_trades
# ---------------------------------------------------------------------------

def _open_buy_fill(conn, *, order_id, fill_id, ticker, fill_date, fill_price, qty):
    """Helper: insert a buy order + fill so tests can attach lots properly."""
    portfolio_db.insert_order(
        conn,
        order_id=order_id,
        submitted_at=datetime.combine(fill_date - timedelta(days=1), datetime.min.time()),
        as_of_date=fill_date - timedelta(days=1),
        ticker=ticker,
        side="buy",
        order_type="market",
        quantity=qty,
        limit_price=None,
        status="filled",
        mode="paper",
    )
    portfolio_db.insert_fill(
        conn,
        fill_id=fill_id,
        order_id=order_id,
        filled_at=datetime.combine(fill_date, datetime.min.time()),
        ticker=ticker,
        side="buy",
        quantity=qty,
        fill_price=fill_price,
        commission=10.0,
        slippage_bps=5.0,
        mode="paper",
    )


def test_compute_tax_short_term_gain():
    """TWEAK: India STCG = 15% on gains held under 365 days (12 months).
    Was 31.2% under 730 days in the US repo."""
    assert portfolio_db.compute_tax(1000.0, 30) == pytest.approx(150.0)


def test_compute_tax_loss_no_tax():
    """Losses produce no tax — naive per-trade model has no offset."""
    assert portfolio_db.compute_tax(-500.0, 30) == 0.0
    assert portfolio_db.compute_tax(0.0, 30) == 0.0


def test_compute_tax_long_term_gain():
    """TWEAK: India LTCG = 10% on gains held >= 365 days (12 months).
    Was 20% on >= 730 days in the US repo."""
    assert portfolio_db.compute_tax(1000.0, 365) == pytest.approx(100.0)


def test_open_lot_round_trip(conn):
    portfolio_db.open_lot(
        conn,
        lot_id="lot-1",
        ticker="AAPL",
        buy_fill_id="fill-1",
        buy_date=date(2026, 5, 1),
        buy_price=200.0,
        qty=10.0,
        mode="paper",
    )
    lots = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert len(lots) == 1
    lot_id, buy_date, buy_price, qty_open = lots[0]
    assert lot_id == "lot-1"
    assert buy_date == date(2026, 5, 1)
    assert buy_price == 200.0
    assert qty_open == 10.0


def test_get_open_lots_fifo_oldest_first(conn):
    """Multiple lots for the same ticker — oldest buy_date first."""
    for i, d in enumerate([date(2026, 5, 5), date(2026, 5, 1), date(2026, 5, 3)]):
        portfolio_db.open_lot(
            conn,
            lot_id=f"lot-{i}",
            ticker="AAPL",
            buy_fill_id=f"fill-{i}",
            buy_date=d,
            buy_price=200.0 + i,
            qty=10.0,
            mode="paper",
        )
    lots = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert [lot[1] for lot in lots] == [
        date(2026, 5, 1), date(2026, 5, 3), date(2026, 5, 5),
    ]


def test_consume_lot_reduces_qty(conn):
    portfolio_db.open_lot(
        conn, lot_id="lot-1", ticker="AAPL", buy_fill_id="f1",
        buy_date=date(2026, 5, 1), buy_price=200.0, qty=10.0, mode="paper",
    )
    portfolio_db.consume_lot(conn, lot_id="lot-1", qty_consumed=3.0)
    lots = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert lots[0][3] == pytest.approx(7.0)


def test_get_open_lots_filters_fully_consumed(conn):
    portfolio_db.open_lot(
        conn, lot_id="lot-1", ticker="AAPL", buy_fill_id="f1",
        buy_date=date(2026, 5, 1), buy_price=200.0, qty=10.0, mode="paper",
    )
    portfolio_db.consume_lot(conn, lot_id="lot-1", qty_consumed=10.0)
    lots = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert lots == []


def test_adjust_lots_for_split(conn):
    """10-for-1 split should multiply qty by 10 and divide buy_price by 10."""
    portfolio_db.open_lot(
        conn, lot_id="lot-pre", ticker="NVDA", buy_fill_id="f1",
        buy_date=date(2024, 6, 5), buy_price=1200.0, qty=10.0, mode="paper",
    )
    # Lot opened AFTER the split — shouldn't be adjusted
    portfolio_db.open_lot(
        conn, lot_id="lot-post", ticker="NVDA", buy_fill_id="f2",
        buy_date=date(2024, 6, 11), buy_price=120.0, qty=100.0, mode="paper",
    )
    n = portfolio_db.adjust_lots_for_split(
        conn, ticker="NVDA", ratio=10.0,
        before_date=date(2024, 6, 10), mode="paper",
    )
    assert n == 1, "Only pre-split lot should adjust"
    lots = {lot[0]: lot for lot in portfolio_db.get_open_lots_fifo(
        conn, ticker="NVDA", mode="paper",
    )}
    # Pre-split lot: qty 10 → 100, buy_price 1200 → 120
    pre = lots["lot-pre"]
    assert pre[2] == pytest.approx(120.0)
    assert pre[3] == pytest.approx(100.0)
    # Post-split lot: unchanged
    post = lots["lot-post"]
    assert post[2] == pytest.approx(120.0)
    assert post[3] == pytest.approx(100.0)


def test_realized_trades_round_trip_with_tax(conn):
    """TWEAK: 7-day holding × ₹100 gain @ 15% STCG → ₹15 tax (was ₹31.20 @ 31.2%)."""
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="trade-1",
        sell_fill_id="sf-1",
        buy_lot_id="lot-1",
        ticker="AAPL",
        buy_date=date(2026, 5, 1),
        sell_date=date(2026, 5, 8),
        qty=10.0,
        buy_price=200.0,
        sell_price=210.0,
        realized_pnl_usd=100.0,
        holding_days=7,
        tax_paid_usd=15.0,
        mode="paper",
    )
    assert portfolio_db.get_cumulative_tax_paid(conn, mode="paper") == pytest.approx(15.0)
    assert portfolio_db.get_total_realized_pnl(conn, mode="paper") == pytest.approx(100.0)


def test_delete_day_restores_consumed_lot_qty(conn):
    """When a sell on day D is rolled back via delete_day, the consumed lot's
    qty_open must be restored so rerunning that day recomputes realized PnL
    from a clean state.
    """
    # Pre-existing buy from a previous day (its order is NOT for the day we'll delete)
    _open_buy_fill(
        conn,
        order_id="paper-2026-04-30-AAPL-buy-1",
        fill_id="paper-2026-04-30-AAPL-buy-1-fill-1",
        ticker="AAPL",
        fill_date=date(2026, 5, 1),
        fill_price=200.0,
        qty=10.0,
    )
    portfolio_db.open_lot(
        conn, lot_id="lot-1", ticker="AAPL",
        buy_fill_id="paper-2026-04-30-AAPL-buy-1-fill-1",
        buy_date=date(2026, 5, 1), buy_price=200.0, qty=10.0, mode="paper",
    )

    # Sell on day D=2026-05-08, filled 2026-05-09
    portfolio_db.insert_order(
        conn,
        order_id="paper-2026-05-08-AAPL-sell-1",
        submitted_at=datetime(2026, 5, 8, 16, 5),
        as_of_date=date(2026, 5, 8),
        ticker="AAPL", side="sell", order_type="market",
        quantity=6.0, limit_price=None, status="filled", mode="paper",
    )
    portfolio_db.insert_fill(
        conn,
        fill_id="paper-2026-05-08-AAPL-sell-1-fill-1",
        order_id="paper-2026-05-08-AAPL-sell-1",
        filled_at=datetime(2026, 5, 9, 9, 30),
        ticker="AAPL", side="sell", quantity=6.0,
        fill_price=210.0, commission=10.0, slippage_bps=5.0, mode="paper",
    )
    portfolio_db.consume_lot(conn, lot_id="lot-1", qty_consumed=6.0)
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-1",
        sell_fill_id="paper-2026-05-08-AAPL-sell-1-fill-1",
        buy_lot_id="lot-1",
        ticker="AAPL",
        buy_date=date(2026, 5, 1),
        sell_date=date(2026, 5, 9),
        qty=6.0, buy_price=200.0, sell_price=210.0,
        realized_pnl_usd=60.0, holding_days=8, tax_paid_usd=9.0,  # 60 × 0.15
        mode="paper",
    )

    # Pre-delete state: lot qty_open should be 4, realized_trade exists
    lots_before = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert lots_before[0][3] == pytest.approx(4.0)
    rt_before = conn.execute("SELECT count(*) FROM realized_trades").fetchone()[0]
    assert rt_before == 1

    # Delete day 2026-05-08 (the sell). Should restore lot qty to 10 and
    # remove the realized_trade row.
    portfolio_db.delete_day(conn, as_of_date=date(2026, 5, 8), mode="paper")

    lots_after = portfolio_db.get_open_lots_fifo(conn, ticker="AAPL", mode="paper")
    assert lots_after[0][3] == pytest.approx(10.0), \
        "Consumed qty should be restored after delete_day"
    rt_after = conn.execute("SELECT count(*) FROM realized_trades").fetchone()[0]
    assert rt_after == 0


def test_delete_day_removes_lots_from_buys(conn):
    """Lots opened by D's buys should be deleted when delete_day(D) runs."""
    _open_buy_fill(
        conn,
        order_id="paper-2026-05-08-XYZ-buy-1",
        fill_id="paper-2026-05-08-XYZ-buy-1-fill-1",
        ticker="XYZ",
        fill_date=date(2026, 5, 9),
        fill_price=50.0,
        qty=20.0,
    )
    # The buy order's as_of_date is fill_date - 1 = 2026-05-08
    portfolio_db.open_lot(
        conn, lot_id="lot-x", ticker="XYZ",
        buy_fill_id="paper-2026-05-08-XYZ-buy-1-fill-1",
        buy_date=date(2026, 5, 9), buy_price=50.0, qty=20.0, mode="paper",
    )

    portfolio_db.delete_day(conn, as_of_date=date(2026, 5, 8), mode="paper")

    lots = portfolio_db.get_open_lots_fifo(conn, ticker="XYZ", mode="paper")
    assert lots == [], "Lot from D's buy should be deleted"


def test_ytd_tax_estimate_nets_gains_against_losses(conn):
    """FY netting: ST gains and losses offset within the same fiscal year
    before STCG_RATE is applied. A strategy with ₹1000 of gains and ₹400 of
    losses in the FY owes 15% × ₹600 (net), not 15% × ₹1000 (gross).

    TWEAK: STCG_RATE 0.312 -> 0.15 (India §111A).
    """
    # Two trades in FY 2023-24 (Apr 2023 - Mar 2024)
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-1", sell_fill_id="sf-1", buy_lot_id="lot-1",
        ticker="AAPL", buy_date=date(2023, 5, 1), sell_date=date(2023, 6, 1),
        qty=10.0, buy_price=100.0, sell_price=200.0,
        realized_pnl_usd=1000.0, holding_days=31,
        tax_paid_usd=150.0,    # per-trade gross-tax indicator (not the truth)
        mode="paper",
    )
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-2", sell_fill_id="sf-2", buy_lot_id="lot-2",
        ticker="MSFT", buy_date=date(2023, 8, 1), sell_date=date(2023, 9, 1),
        qty=4.0, buy_price=300.0, sell_price=200.0,
        realized_pnl_usd=-400.0, holding_days=31,
        tax_paid_usd=0.0,
        mode="paper",
    )
    # One trade in FY 2024-25 (should be excluded)
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-3", sell_fill_id="sf-3", buy_lot_id="lot-3",
        ticker="GOOG", buy_date=date(2024, 5, 1), sell_date=date(2024, 6, 1),
        qty=5.0, buy_price=100.0, sell_price=120.0,
        realized_pnl_usd=100.0, holding_days=31,
        tax_paid_usd=15.0,
        mode="paper",
    )

    # Estimate at end of FY 2023-24
    est = portfolio_db.get_ytd_tax_estimate(
        conn, mode="paper", as_of=date(2024, 3, 31),
    )
    assert est["fy_start"] == date(2023, 4, 1)
    assert est["gross_gains"] == pytest.approx(1000.0)
    assert est["gross_losses"] == pytest.approx(-400.0)
    assert est["net_pnl"] == pytest.approx(600.0)
    assert est["tax_owed"] == pytest.approx(600.0 * 0.15)   # NET × STCG_RATE (India)
    assert est["n_trades"] == 2     # only FY 2023-24 trades


def test_ytd_tax_estimate_zero_when_net_loss(conn):
    """No tax owed when net realized PnL is negative."""
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-1", sell_fill_id="sf-1", buy_lot_id="lot-1",
        ticker="AAPL", buy_date=date(2023, 5, 1), sell_date=date(2023, 6, 1),
        qty=10.0, buy_price=100.0, sell_price=80.0,
        realized_pnl_usd=-200.0, holding_days=31, tax_paid_usd=0.0,
        mode="paper",
    )
    est = portfolio_db.get_ytd_tax_estimate(
        conn, mode="paper", as_of=date(2024, 3, 31),
    )
    assert est["net_pnl"] == pytest.approx(-200.0)
    assert est["tax_owed"] == 0.0


def test_ytd_fy_start_jan_mar_uses_previous_year_april(conn):
    """A January date is in the FY that started the previous calendar year."""
    from storage.portfolio_db import _fy_start_for
    assert _fy_start_for(date(2024, 1, 15)) == date(2023, 4, 1)
    assert _fy_start_for(date(2024, 3, 31)) == date(2023, 4, 1)
    assert _fy_start_for(date(2024, 4, 1)) == date(2024, 4, 1)
    assert _fy_start_for(date(2024, 12, 31)) == date(2024, 4, 1)


def test_wipe_mode_clears_lots_and_trades(conn):
    portfolio_db.open_lot(
        conn, lot_id="lot-1", ticker="AAPL", buy_fill_id="f1",
        buy_date=date(2026, 5, 1), buy_price=200.0, qty=10.0, mode="paper",
    )
    portfolio_db.insert_realized_trade(
        conn,
        trade_id="rt-1", sell_fill_id="sf-1", buy_lot_id="lot-1",
        ticker="AAPL", buy_date=date(2026, 5, 1), sell_date=date(2026, 5, 5),
        qty=5.0, buy_price=200.0, sell_price=210.0,
        realized_pnl_usd=50.0, holding_days=4, tax_paid_usd=7.5,  # 50 × 0.15
        mode="paper",
    )
    portfolio_db.wipe_mode(conn, "paper")
    assert conn.execute("SELECT count(*) FROM position_lots").fetchone()[0] == 0
