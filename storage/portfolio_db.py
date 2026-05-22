"""Paper-trade and (future) real-trade ledger.

One duckdb file under storage/portfolio.duckdb owns six tables:
    desired_targets   — strategy's intended fractions per (date, ticker, mode)
    submitted_orders  — orders sent to broker (paper: synthetic; real: Playwright)
    actual_fills      — fills received from broker
    broker_positions  — end-of-day snapshot of holdings
    cash_ledger       — every deposit/withdrawal/commission/buy/sell/tax entry
    discrepancies     — any time intent != reality, one row gets logged here

`mode` ('paper' | 'real') is part of every table's row and part of the PK
on the tables where the same logical key can coexist between modes.

This module exposes a thin DAO surface — no ORM, just typed function calls.
The same DAO will back the future scripts/execute.py for real mode."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "storage" / "portfolio.duckdb"
HALT_FILE_PATH = REPO_ROOT / "state" / "halt.json"


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the portfolio duckdb file, ensuring the ledger
    schema exists. Caller closes when done.

    init_schema is idempotent (CREATE TABLE IF NOT EXISTS), so a fresh
    paper ledger self-bootstraps on first use — previously every consumer
    (premarket_scan, run_live, daily_report, dashboard) crashed with
    'Table broker_positions does not exist' because nothing ever called
    init_schema on storage/portfolio.duckdb."""
    conn = duckdb.connect(str(db_path))
    init_schema(conn)
    return conn


_DDL = [
    """
    CREATE TABLE IF NOT EXISTS desired_targets (
        as_of_date       DATE      NOT NULL,
        ticker           VARCHAR   NOT NULL,
        target_fraction  DOUBLE    NOT NULL,
        source           VARCHAR,
        mode             VARCHAR   NOT NULL,
        PRIMARY KEY (as_of_date, ticker, mode)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS submitted_orders (
        order_id      VARCHAR   PRIMARY KEY,
        submitted_at  TIMESTAMP NOT NULL,
        as_of_date    DATE      NOT NULL,
        ticker        VARCHAR   NOT NULL,
        side          VARCHAR   NOT NULL,
        order_type    VARCHAR   NOT NULL,
        quantity      DOUBLE    NOT NULL,
        limit_price   DOUBLE,
        status        VARCHAR   NOT NULL,
        mode          VARCHAR   NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS actual_fills (
        fill_id       VARCHAR   PRIMARY KEY,
        order_id      VARCHAR   NOT NULL,
        filled_at     TIMESTAMP NOT NULL,
        ticker        VARCHAR   NOT NULL,
        side          VARCHAR   NOT NULL,
        quantity      DOUBLE    NOT NULL,
        fill_price    DOUBLE    NOT NULL,
        commission    DOUBLE    NOT NULL,
        slippage_bps  DOUBLE,
        mode          VARCHAR   NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS broker_positions (
        snapshot_date    DATE      NOT NULL,
        ticker           VARCHAR   NOT NULL,
        quantity         DOUBLE    NOT NULL,
        avg_entry_price  DOUBLE,
        mark_price       DOUBLE,
        mark_value       DOUBLE,
        mode             VARCHAR   NOT NULL,
        PRIMARY KEY (snapshot_date, ticker, mode)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS cash_ledger (
        entry_id    VARCHAR   PRIMARY KEY,
        entry_at    TIMESTAMP NOT NULL,
        as_of_date  DATE,
        kind        VARCHAR   NOT NULL,
        amount_usd  DOUBLE    NOT NULL,
        notes       VARCHAR,
        mode        VARCHAR   NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS discrepancies (
        discrepancy_id  VARCHAR   PRIMARY KEY,
        detected_at     TIMESTAMP NOT NULL,
        as_of_date      DATE,
        kind            VARCHAR   NOT NULL,
        ticker          VARCHAR,
        expected        VARCHAR,
        actual          VARCHAR,
        resolution      VARCHAR,
        notes           VARCHAR,
        mode            VARCHAR   NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS position_lots (
        lot_id          VARCHAR   PRIMARY KEY,
        ticker          VARCHAR   NOT NULL,
        buy_fill_id     VARCHAR   NOT NULL,
        buy_date        DATE      NOT NULL,
        buy_price       DOUBLE    NOT NULL,
        qty_open        DOUBLE    NOT NULL,
        qty_total       DOUBLE    NOT NULL,
        mode            VARCHAR   NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS realized_trades (
        trade_id          VARCHAR   PRIMARY KEY,
        sell_fill_id      VARCHAR   NOT NULL,
        buy_lot_id        VARCHAR   NOT NULL,
        ticker            VARCHAR   NOT NULL,
        buy_date          DATE      NOT NULL,
        sell_date         DATE      NOT NULL,
        qty               DOUBLE    NOT NULL,
        buy_price         DOUBLE    NOT NULL,
        sell_price        DOUBLE    NOT NULL,
        realized_pnl_usd  DOUBLE    NOT NULL,
        holding_days      INTEGER   NOT NULL,
        tax_paid_usd      DOUBLE    NOT NULL,
        mode              VARCHAR   NOT NULL
    );
    """,
]


# Indian resident tax rate on short-term capital gains for Indian (domestic)
# equities held < 12 months: flat 15%. LTCG (>= 12 months) is 10% on gains
# above a ₹1,00,000 annual exemption per fiscal year. For a swing-trading
# horizon (2-10 days) all sales fall under STCG; the LTCG branch below exists
# for completeness but should rarely fire.
STCG_RATE = 0.15
LTCG_RATE = 0.10
LTCG_HOLDING_DAYS = 365   # 12 calendar months
LTCG_THRESHOLD_INR = 100_000   # ₹1L annual LTCG exemption per FY


def compute_tax(realized_pnl_usd: float, holding_days: int) -> float:
    """Tax owed on a single realized trade.

    Conservative: tax each gain immediately, no loss offset. Real Indian
    tax law lets ST losses offset ST/LT gains within the FY; modelling that
    requires per-FY aggregation. Per-trade gross-tax over-states tax by the
    netting amount, which is acceptable for paper-trade (slightly pessimistic
    reporting beats optimistic).
    """
    if realized_pnl_usd <= 0:
        return 0.0
    rate = STCG_RATE if holding_days < LTCG_HOLDING_DAYS else LTCG_RATE
    return realized_pnl_usd * rate


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the eight tables if they don't exist. Idempotent."""
    for stmt in _DDL:
        conn.execute(stmt)


@dataclass
class LedgerState:
    """Snapshot of paper-mode (or real-mode) state at a given date.

    Loaded via load_state(). Read-only; mutations go through DAO writers."""
    mode: str
    as_of: date
    cash_usd: float
    positions: dict[str, float]
    mark_equity: float
    peak_equity: float
    today_pnl_usd: float
    halted: bool


# --- Writers ---

def upsert_target(
    conn: duckdb.DuckDBPyConnection,
    *,
    as_of_date: date,
    ticker: str,
    target_fraction: float,
    source: str | None,
    mode: str,
) -> None:
    """Insert-or-replace a target row on PK (as_of_date, ticker, mode)."""
    conn.execute(
        "INSERT INTO desired_targets (as_of_date, ticker, target_fraction, source, mode) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (as_of_date, ticker, mode) DO UPDATE SET "
        "  target_fraction = excluded.target_fraction, "
        "  source = excluded.source",
        [as_of_date, ticker, target_fraction, source, mode],
    )


def delete_targets_for_day(
    conn: duckdb.DuckDBPyConnection, *, as_of_date: date, mode: str
) -> None:
    """Delete all desired_targets rows for (as_of_date, mode).

    Used by paper_trade._process_day before upserting the day's fresh signal set
    so that a rerun whose signal set shrank doesn't leave orphan rows behind
    (full daily replacement semantics — I-3).
    """
    conn.execute(
        "DELETE FROM desired_targets WHERE as_of_date = ? AND mode = ?",
        [as_of_date, mode],
    )


def get_most_recent_target_date_before(
    conn: duckdb.DuckDBPyConnection, as_of_date: date, mode: str
) -> date | None:
    """Most recent `desired_targets.as_of_date` strictly less than `as_of_date`.

    Used by paper_trade's fraction-change filter to compare today's intent
    against the LAST KNOWN intent. Returns None on first ever day or when
    no prior targets exist for this mode."""
    row = conn.execute(
        "SELECT MAX(as_of_date) FROM desired_targets "
        "WHERE mode = ? AND as_of_date < ?",
        [mode, as_of_date],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def get_target_fractions_for_date(
    conn: duckdb.DuckDBPyConnection, as_of_date: date, mode: str
) -> dict[str, float]:
    """All target_fractions on a given (date, mode) keyed by ticker.

    Used to compare today's strategy intent against yesterday's so paper_trade
    can suppress micro-rebalances when the fraction is unchanged. Tickers not
    present in the result are implicitly 0 (the strategy didn't address them)."""
    rows = conn.execute(
        "SELECT ticker, target_fraction FROM desired_targets "
        "WHERE as_of_date = ? AND mode = ?",
        [as_of_date, mode],
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def insert_order(
    conn: duckdb.DuckDBPyConnection,
    *,
    order_id: str,
    submitted_at: datetime,
    as_of_date: date,
    ticker: str,
    side: str,
    order_type: str,
    quantity: float,
    limit_price: float | None,
    status: str,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO submitted_orders "
        "(order_id, submitted_at, as_of_date, ticker, side, order_type, "
        " quantity, limit_price, status, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [order_id, submitted_at, as_of_date, ticker, side, order_type,
         quantity, limit_price, status, mode],
    )


def update_order_status(
    conn: duckdb.DuckDBPyConnection, order_id: str, status: str
) -> None:
    conn.execute(
        "UPDATE submitted_orders SET status = ? WHERE order_id = ?",
        [status, order_id],
    )


def insert_fill(
    conn: duckdb.DuckDBPyConnection,
    *,
    fill_id: str,
    order_id: str,
    filled_at: datetime,
    ticker: str,
    side: str,
    quantity: float,
    fill_price: float,
    commission: float,
    slippage_bps: float | None,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO actual_fills "
        "(fill_id, order_id, filled_at, ticker, side, quantity, "
        " fill_price, commission, slippage_bps, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [fill_id, order_id, filled_at, ticker, side, quantity,
         fill_price, commission, slippage_bps, mode],
    )


def upsert_position(
    conn: duckdb.DuckDBPyConnection,
    *,
    snapshot_date: date,
    ticker: str,
    quantity: float,
    avg_entry_price: float | None,
    mark_price: float | None,
    mark_value: float | None,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO broker_positions "
        "(snapshot_date, ticker, quantity, avg_entry_price, mark_price, "
        " mark_value, mode) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (snapshot_date, ticker, mode) DO UPDATE SET "
        "  quantity = excluded.quantity, "
        "  avg_entry_price = excluded.avg_entry_price, "
        "  mark_price = excluded.mark_price, "
        "  mark_value = excluded.mark_value",
        [snapshot_date, ticker, quantity, avg_entry_price,
         mark_price, mark_value, mode],
    )


def insert_cash_entry(
    conn: duckdb.DuckDBPyConnection,
    *,
    entry_id: str,
    entry_at: datetime,
    as_of_date: date | None,
    kind: str,
    amount_usd: float,
    notes: str | None,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO cash_ledger "
        "(entry_id, entry_at, as_of_date, kind, amount_usd, notes, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [entry_id, entry_at, as_of_date, kind, amount_usd, notes, mode],
    )


def insert_discrepancy(
    conn: duckdb.DuckDBPyConnection,
    *,
    discrepancy_id: str,
    detected_at: datetime,
    as_of_date: date | None,
    kind: str,
    ticker: str | None,
    expected: str | None,
    actual: str | None,
    resolution: str | None,
    notes: str | None,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO discrepancies "
        "(discrepancy_id, detected_at, as_of_date, kind, ticker, expected, "
        " actual, resolution, notes, mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [discrepancy_id, detected_at, as_of_date, kind, ticker, expected,
         actual, resolution, notes, mode],
    )


# --- Rerun scaffolding ---

def delete_day(
    conn: duckdb.DuckDBPyConnection, *, as_of_date: date, mode: str
) -> None:
    """Wipe everything paper_trade produced for one (as_of_date, mode).

    Restores lot-consumption state for D's sells so a rerun re-allocates
    realized PnL from scratch. Then cleans 7 dependent tables. Order matters:
    each step's JOINs depend on tables not yet deleted.
    desired_targets is NOT touched — UPSERT will overwrite on rewrite."""
    # First: restore qty consumed by D's sells back to the source lots,
    # so a re-run starts from the lot state we had BEFORE this day's processing.
    # Uses JOIN through actual_fills + submitted_orders — both must be present.
    restorations = conn.execute(
        "SELECT buy_lot_id, qty FROM realized_trades WHERE mode = ? AND sell_fill_id IN ("
        "  SELECT af.fill_id FROM actual_fills af "
        "  JOIN submitted_orders so ON af.order_id = so.order_id "
        "  WHERE so.as_of_date = ? AND so.mode = ?"
        ")",
        [mode, as_of_date, mode],
    ).fetchall()
    for lot_id, qty in restorations:
        conn.execute(
            "UPDATE position_lots SET qty_open = qty_open + ? WHERE lot_id = ?",
            [qty, lot_id],
        )
    # Now delete the realized_trades rows for D — same JOIN dependency, must
    # happen before submitted_orders/actual_fills are deleted.
    conn.execute(
        "DELETE FROM realized_trades WHERE mode = ? AND sell_fill_id IN ("
        "  SELECT af.fill_id FROM actual_fills af "
        "  JOIN submitted_orders so ON af.order_id = so.order_id "
        "  WHERE so.as_of_date = ? AND so.mode = ?"
        ")",
        [mode, as_of_date, mode],
    )
    # Delete lots opened by D's BUY fills — same JOIN dependency.
    conn.execute(
        "DELETE FROM position_lots WHERE mode = ? AND buy_fill_id IN ("
        "  SELECT af.fill_id FROM actual_fills af "
        "  JOIN submitted_orders so ON af.order_id = so.order_id "
        "  WHERE so.as_of_date = ? AND so.mode = ?"
        ")",
        [mode, as_of_date, mode],
    )
    # broker_positions: JOINs through actual_fills + submitted_orders.
    conn.execute(
        "DELETE FROM broker_positions WHERE mode = ? AND snapshot_date IN ("
        "  SELECT DISTINCT CAST(filled_at AS DATE) FROM actual_fills af "
        "  JOIN submitted_orders so ON af.order_id = so.order_id "
        "  WHERE so.as_of_date = ? AND so.mode = ?"
        ")",
        [mode, as_of_date, mode],
    )
    # actual_fills: JOINs through submitted_orders.
    conn.execute(
        "DELETE FROM actual_fills WHERE order_id IN ("
        "  SELECT order_id FROM submitted_orders "
        "  WHERE as_of_date = ? AND mode = ?"
        ")",
        [as_of_date, mode],
    )
    # submitted_orders last among linked tables — no JOIN dependencies remain.
    conn.execute(
        "DELETE FROM submitted_orders WHERE as_of_date = ? AND mode = ?",
        [as_of_date, mode],
    )
    conn.execute(
        "DELETE FROM cash_ledger WHERE as_of_date = ? AND mode = ?",
        [as_of_date, mode],
    )
    conn.execute(
        "DELETE FROM discrepancies WHERE as_of_date = ? AND mode = ?",
        [as_of_date, mode],
    )


def wipe_mode(conn: duckdb.DuckDBPyConnection, mode: str) -> None:
    """Delete every row for a mode across all 8 tables."""
    for table in (
        "desired_targets", "realized_trades", "position_lots",
        "actual_fills", "broker_positions",
        "submitted_orders", "cash_ledger", "discrepancies",
    ):
        conn.execute(f"DELETE FROM {table} WHERE mode = ?", [mode])


# --- Lot tracking & realized trades (tax accounting) ---

def open_lot(
    conn: duckdb.DuckDBPyConnection,
    *,
    lot_id: str,
    ticker: str,
    buy_fill_id: str,
    buy_date: date,
    buy_price: float,
    qty: float,
    mode: str,
) -> None:
    """Record a new long lot from a buy fill. qty_open starts at qty_total."""
    conn.execute(
        "INSERT INTO position_lots "
        "(lot_id, ticker, buy_fill_id, buy_date, buy_price, qty_open, qty_total, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [lot_id, ticker, buy_fill_id, buy_date, buy_price, qty, qty, mode],
    )


def get_open_lots_fifo(
    conn: duckdb.DuckDBPyConnection, *, ticker: str, mode: str
) -> list[tuple]:
    """Open lots for `ticker`, oldest first. Returns (lot_id, buy_date, buy_price, qty_open)."""
    return conn.execute(
        "SELECT lot_id, buy_date, buy_price, qty_open "
        "FROM position_lots "
        "WHERE ticker = ? AND mode = ? AND qty_open > 1e-9 "
        "ORDER BY buy_date ASC, lot_id ASC",
        [ticker, mode],
    ).fetchall()


def consume_lot(
    conn: duckdb.DuckDBPyConnection, *, lot_id: str, qty_consumed: float
) -> None:
    """Reduce qty_open for `lot_id` by `qty_consumed`. Used during sell FIFO matching."""
    conn.execute(
        "UPDATE position_lots SET qty_open = qty_open - ? WHERE lot_id = ?",
        [qty_consumed, lot_id],
    )


def adjust_lots_for_split(
    conn: duckdb.DuckDBPyConnection,
    *,
    ticker: str,
    ratio: float,
    before_date: date,
    mode: str,
) -> int:
    """Apply a stock split to lots opened BEFORE the split date. Multiplies
    qty_open / qty_total by ratio and divides buy_price by ratio so that
    notional dollar exposure of each lot is unchanged. Returns count of
    affected lots.
    """
    if ratio == 1.0:
        return 0
    rows = conn.execute(
        "UPDATE position_lots SET "
        "  qty_open = qty_open * ?, "
        "  qty_total = qty_total * ?, "
        "  buy_price = buy_price / ? "
        "WHERE ticker = ? AND mode = ? AND buy_date < ? "
        "RETURNING lot_id",
        [ratio, ratio, ratio, ticker, mode, before_date],
    ).fetchall()
    return len(rows)


def insert_realized_trade(
    conn: duckdb.DuckDBPyConnection,
    *,
    trade_id: str,
    sell_fill_id: str,
    buy_lot_id: str,
    ticker: str,
    buy_date: date,
    sell_date: date,
    qty: float,
    buy_price: float,
    sell_price: float,
    realized_pnl_usd: float,
    holding_days: int,
    tax_paid_usd: float,
    mode: str,
) -> None:
    conn.execute(
        "INSERT INTO realized_trades "
        "(trade_id, sell_fill_id, buy_lot_id, ticker, buy_date, sell_date, qty, "
        " buy_price, sell_price, realized_pnl_usd, holding_days, tax_paid_usd, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [trade_id, sell_fill_id, buy_lot_id, ticker, buy_date, sell_date, qty,
         buy_price, sell_price, realized_pnl_usd, holding_days,
         tax_paid_usd, mode],
    )


def _fy_start_for(as_of: date) -> date:
    """Indian fiscal year starts on April 1. For a date in Jan-Mar, FY started
    the previous calendar year's April 1; for Apr-Dec, this year's April 1."""
    if as_of.month >= 4:
        return date(as_of.year, 4, 1)
    return date(as_of.year - 1, 4, 1)


def get_ytd_tax_estimate(
    conn: duckdb.DuckDBPyConnection,
    mode: str,
    as_of: date,
) -> dict:
    """Estimated tax owed on net realized PnL in the fiscal year containing
    `as_of` (April 1 → March 31 Indian FY). Real Indian tax allows ST losses
    to offset ST gains within the FY before the rate is applied.

    Returns a dict:
        fy_start         start of the fiscal year
        as_of            evaluation date (FY-to-date cutoff)
        gross_gains      sum of realized_pnl_usd > 0 in the window
        gross_losses     sum of realized_pnl_usd < 0 in the window (negative)
        net_pnl          gross_gains + gross_losses
        tax_owed         max(0, net_pnl) × STCG_RATE
        n_trades         count of realized_trades rows in the window

    Caveats:
    - Treats ALL realized trades as short-term (24-month threshold not
      enforced here; we'd need a holding-days filter). For a swing
      strategy with avg holding < 14 days, no trade ever crosses the
      LTCG line so this is effectively correct.
    - LTCG trades (if any) would still be priced at STCG_RATE under
      this estimate — slightly over-states for those rare cases.
    - Does NOT account for surcharges (10-37% above ₹50L taxable
      income). The STCG_RATE constant is the slab+cess for a 30%
      bracket without surcharge.
    """
    fy_start = _fy_start_for(as_of)
    row = conn.execute(
        "SELECT "
        "  COALESCE(SUM(CASE WHEN realized_pnl_usd > 0 THEN realized_pnl_usd ELSE 0 END), 0) AS gains, "
        "  COALESCE(SUM(CASE WHEN realized_pnl_usd < 0 THEN realized_pnl_usd ELSE 0 END), 0) AS losses, "
        "  COUNT(*) AS n "
        "FROM realized_trades WHERE mode = ? AND sell_date >= ? AND sell_date <= ?",
        [mode, fy_start, as_of],
    ).fetchone()
    gross_gains = float(row[0])
    gross_losses = float(row[1])
    n_trades = int(row[2])
    net_pnl = gross_gains + gross_losses
    tax_owed = max(0.0, net_pnl) * STCG_RATE
    return {
        "fy_start": fy_start,
        "as_of": as_of,
        "gross_gains": gross_gains,
        "gross_losses": gross_losses,
        "net_pnl": net_pnl,
        "tax_owed": tax_owed,
        "n_trades": n_trades,
    }


def get_cumulative_tax_paid(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date | None = None
) -> float:
    """Sum of tax_paid_usd from realized_trades up to and including as_of."""
    if as_of is None:
        row = conn.execute(
            "SELECT COALESCE(SUM(tax_paid_usd), 0.0) FROM realized_trades WHERE mode = ?",
            [mode],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(tax_paid_usd), 0.0) FROM realized_trades "
            "WHERE mode = ? AND sell_date <= ?",
            [mode, as_of],
        ).fetchone()
    return float(row[0])


def get_total_realized_pnl(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date | None = None
) -> float:
    """Sum of realized_pnl_usd (gross, pre-tax) from realized_trades up to as_of."""
    if as_of is None:
        row = conn.execute(
            "SELECT COALESCE(SUM(realized_pnl_usd), 0.0) FROM realized_trades WHERE mode = ?",
            [mode],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(realized_pnl_usd), 0.0) FROM realized_trades "
            "WHERE mode = ? AND sell_date <= ?",
            [mode, as_of],
        ).fetchone()
    return float(row[0])


# --- Readers ---

@dataclass
class PositionRow:
    ticker: str
    quantity: float
    avg_entry_price: float | None
    mark_price: float | None
    mark_value: float | None


@dataclass
class DiscrepancyRow:
    discrepancy_id: str
    detected_at: datetime
    as_of_date: date | None
    kind: str
    ticker: str | None
    notes: str | None


def get_positions_as_of(
    conn: duckdb.DuckDBPyConnection, snapshot_date: date, mode: str
) -> dict[str, PositionRow]:
    """All non-zero positions for `mode` on the requested snapshot date."""
    rows = conn.execute(
        "SELECT ticker, quantity, avg_entry_price, mark_price, mark_value "
        "FROM broker_positions WHERE snapshot_date = ? AND mode = ? AND quantity != 0",
        [snapshot_date, mode],
    ).fetchall()
    return {
        r[0]: PositionRow(
            ticker=r[0], quantity=float(r[1]),
            avg_entry_price=r[2], mark_price=r[3], mark_value=r[4],
        )
        for r in rows
    }


_INITIAL_DEPOSIT_BY_MODE: dict[str, float] = {
    # cash_ledger does NOT store an "initial deposit" row by convention,
    # so the raw SUM is the DELTA from the bootstrap cash, not the
    # balance. Every caller of get_cash_balance treated the return value
    # as the actual balance and displayed it as such — including the
    # dashboard, which surfaced negative cash to the user. Anchor here so
    # the ledger has a single source of truth for "real cash." Paper boots
    # with ₹1,00,000 (DhanExecutor / DhanMock default); dhan-live's real
    # cash comes from the broker and is not seeded from the ledger.
    "dhan-paper": 100_000.0,
    "dhan-live": 0.0,
}


def get_cash_balance(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date | None = None
) -> float:
    """Actual cash balance = mode's initial deposit + signed cash_ledger sum
    through `as_of` (inclusive on entry_at::DATE)."""
    if as_of is None:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0.0) FROM cash_ledger WHERE mode = ?",
            [mode],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0.0) FROM cash_ledger "
            "WHERE mode = ? AND CAST(entry_at AS DATE) <= ?",
            [mode, as_of],
        ).fetchone()
    return _INITIAL_DEPOSIT_BY_MODE.get(mode, 0.0) + float(row[0])


def _latest_snapshot_date_on_or_before(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date | None
) -> date | None:
    if as_of is None:
        row = conn.execute(
            "SELECT MAX(snapshot_date) FROM broker_positions WHERE mode = ?",
            [mode],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(snapshot_date) FROM broker_positions "
            "WHERE mode = ? AND snapshot_date <= ?",
            [mode, as_of],
        ).fetchone()
    return row[0]


def get_equity_curve(
    conn: duckdb.DuckDBPyConnection, mode: str,
):
    """date -> mark_equity. Equity at date D = cash_balance_through(D) + sum(mark_value(D)).

    Returns a pandas DataFrame with columns ['snapshot_date', 'mark_equity'].
    """
    import pandas as pd  # local import to keep module import-time light
    rows = conn.execute(
        "SELECT snapshot_date, SUM(mark_value) FROM broker_positions "
        "WHERE mode = ? GROUP BY snapshot_date ORDER BY snapshot_date",
        [mode],
    ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["snapshot_date", "mark_equity"])
    out = []
    for snap_date, positions_mark in rows:
        cash = get_cash_balance(conn, mode=mode, as_of=snap_date)
        out.append((snap_date, cash + float(positions_mark or 0.0)))
    return pd.DataFrame(out, columns=["snapshot_date", "mark_equity"])


def get_peak_equity(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date | None = None
) -> float:
    """Max of mark_equity over snapshots <= as_of. Returns 0.0 when empty."""
    curve = get_equity_curve(conn, mode=mode)
    if curve.empty:
        return 0.0
    if as_of is not None:
        curve = curve[curve["snapshot_date"] <= as_of]
    if curve.empty:
        return 0.0
    return float(curve["mark_equity"].max())


def get_today_pnl(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date
) -> float:
    """mark_equity(as_of) - mark_equity(most recent prior snapshot).

    Returns 0.0 if there's no prior snapshot (first day of activity)."""
    curve = get_equity_curve(conn, mode=mode)
    curve = curve[curve["snapshot_date"] <= as_of]
    if len(curve) < 2:
        return 0.0
    return float(curve.iloc[-1]["mark_equity"] - curve.iloc[-2]["mark_equity"])


def get_recent_discrepancies(
    conn: duckdb.DuckDBPyConnection, mode: str, since: datetime | None = None
) -> list[DiscrepancyRow]:
    sql = (
        "SELECT discrepancy_id, detected_at, as_of_date, kind, ticker, notes "
        "FROM discrepancies WHERE mode = ?"
    )
    params: list = [mode]
    if since is not None:
        sql += " AND detected_at >= ?"
        params.append(since)
    sql += " ORDER BY detected_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [
        DiscrepancyRow(
            discrepancy_id=r[0], detected_at=r[1], as_of_date=r[2],
            kind=r[3], ticker=r[4], notes=r[5],
        )
        for r in rows
    ]


def load_state(
    conn: duckdb.DuckDBPyConnection, mode: str, as_of: date
) -> LedgerState:
    """Assemble a LedgerState snapshot as-of the requested date.

    Uses the most recent snapshot_date <= as_of for positions. Cash is summed
    through `as_of`. PnL is mark_equity_today - mark_equity_prior_snapshot.
    Halt flag is the existence of the configured halt file."""
    snap_date = _latest_snapshot_date_on_or_before(conn, mode, as_of)
    if snap_date is not None:
        positions = {
            t: p.quantity
            for t, p in get_positions_as_of(conn, snap_date, mode).items()
        }
        positions_mark = sum(
            (p.mark_value or 0.0)
            for p in get_positions_as_of(conn, snap_date, mode).values()
        )
    else:
        positions = {}
        positions_mark = 0.0

    cash = get_cash_balance(conn, mode=mode, as_of=as_of)
    mark_equity = cash + positions_mark
    peak_equity = get_peak_equity(conn, mode=mode, as_of=as_of)
    today_pnl = get_today_pnl(conn, mode=mode, as_of=as_of)
    halted = HALT_FILE_PATH.exists()

    return LedgerState(
        mode=mode,
        as_of=as_of,
        cash_usd=cash,
        positions=positions,
        mark_equity=mark_equity,
        peak_equity=peak_equity,
        today_pnl_usd=today_pnl,
        halted=halted,
    )
