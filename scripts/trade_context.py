"""Trade context — per-trade attribution + held-position drift.

Pure read-only computation. No new database, no stored tables, no capture
hooks — same shape as scripts/reconciliation.py. Everything here is either
immutable ledger data or point-in-time-recomputable from prices, so we
recompute on demand (≈5-6 closed trades + ≈10 held names per call is free).

Two questions, per (date, mode):

  HELD-POSITION DRIFT  — "are the names I still hold actually still good picks?"
      For each currently-held name: its momentum-quality rank/decile the day
      we bought it (recomputed PIT) vs its rank/decile today. A name that
      entered top-decile and has since fallen out of the universe or below
      the top-N is flagged so it can be reasoned about BEFORE it closes.

  CLOSED-TRADE ATTRIBUTION — "did that trade make alpha, or just ride beta —
      and did cost eat it?"  For each trade closed in the lookback window:
        - Signal:    entry rank / decile (PIT at buy date)
        - Benchmark: return vs Nifty-50 over the exact holding window → excess
        - Cost:      modeled round-trip DP + STT + fees, in bps
        - a single dominant_cause tag

The signal layer is reconstructable because strategy.momentum_quality_scores()
is a pure function of price history + ADV — no need to capture anything at
trade time, no touching the locked strategy.

Per-trade *execution* and *construction* attribution are intentionally NOT
duplicated here: those are book-level rebalance concepts already covered by
reconciliation Q2 (slippage) and Q3 (construction drag). Event-study /
classifier context is omitted because the locked strategy doesn't consume
macro_regime/sentiment and they aren't computed live.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from data.universe import DEFAULT_UNIVERSE_DB, get_universe_at
from storage.portfolio_db import DEFAULT_DB_PATH, connect

# Must match strategy.py params (IndiaMomentumQuality defaults).
BETA_WINDOW = 252        # lookback_days
FORMATION_DAYS = 21      # skip_days
N_POSITIONS = 25         # "top pick" cutoff for the rank-decay flag
ADV_WINDOW = 20          # ADV averaging window (strategy._ADV_WINDOW)

DEFAULT_PRICES_DB = Path("storage/prices.duckdb")
DEFAULT_MACRO_DB = Path("storage/macro.duckdb")
NIFTY_SERIES_ID = "index_nifty_50"

# How far back closed-trade attribution looks (calendar days).
DEFAULT_CLOSED_LOOKBACK_DAYS = 30

# Held-name drift: decile drop (out of 10) that trips the ⚠ rank-decay flag.
DECILE_DECAY_FLAG = 3


# === Top-level ==============================================================

def compute_trade_context_for_date(
    d: date,
    mode: str = "dhan-paper",
    db_path: Path | str = DEFAULT_DB_PATH,
    prices_db: Path | str = DEFAULT_PRICES_DB,
    universe_db: Path | str = DEFAULT_UNIVERSE_DB,
    macro_db: Path | str = DEFAULT_MACRO_DB,
    closed_lookback_days: int = DEFAULT_CLOSED_LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Compute held-drift + closed-trade attribution for (date, mode)."""
    conn = connect(db_path)
    # A per-call PIT-score cache keyed by score_date — held names share
    # "today", closed trades reuse any shared entry dates.
    score_cache: dict[date, tuple[dict[str, dict[str, Any]], int]] = {}
    try:
        held = _held_position_drift(
            conn, d, mode, Path(prices_db), Path(universe_db), score_cache,
        )
        closed = _closed_trade_attribution(
            conn, d, mode, closed_lookback_days,
            Path(prices_db), Path(universe_db), Path(macro_db), score_cache,
        )
        return {
            "date": d.isoformat(),
            "mode": mode,
            "held": held,
            "closed": closed,
        }
    finally:
        conn.close()


# === PIT momentum-quality scoring ==========================================

def _pit_scores(
    score_date: date,
    prices_db: Path,
    universe_db: Path,
    cache: dict[date, tuple[dict[str, dict[str, Any]], int]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Recompute the strategy's momentum-quality ranking as of `score_date`.

    Returns ({ticker: {"rank": 1-based, "score": float, "decile": 1-10}},
             universe_size). A ticker absent from the dict either fell out of
             the PIT universe or failed the strategy's momentum gate that day.
    """
    if score_date in cache:
        return cache[score_date]

    universe = get_universe_at(score_date, universe_db)
    if not universe:
        cache[score_date] = ({}, 0)
        return cache[score_date]

    close_by_ticker, adv_by_ticker = _load_closes_adv(
        prices_db, universe, score_date,
    )
    if len(close_by_ticker) < 3:
        cache[score_date] = ({}, 0)
        return cache[score_date]

    # Lazy import: pulls backtrader; keep it out of module-import cost.
    from strategy import momentum_quality_scores

    raw = momentum_quality_scores(
        close_by_ticker, adv_by_ticker, BETA_WINDOW, FORMATION_DAYS,
    )
    ranked = sorted(raw.items(), key=lambda kv: kv[1], reverse=True)
    size = len(ranked)
    out: dict[str, dict[str, Any]] = {}
    for i, (t, score) in enumerate(ranked):
        rank = i + 1
        decile = max(1, min(10, 10 - int((rank - 1) * 10 / size)))
        out[t] = {"rank": rank, "score": float(score), "decile": decile}
    cache[score_date] = (out, size)
    return cache[score_date]


def _load_closes_adv(
    prices_db: Path, tickers: list[str], score_date: date,
) -> tuple[dict[str, list[float]], dict[str, float]]:
    """Pull trailing closes + ADV for the universe up to `score_date`.

    Mirrors strategy._close_and_adv: needs >= BETA_WINDOW+1 closes; ADV is the
    mean of close*volume over the last ADV_WINDOW bars. A ~420-calendar-day
    window comfortably covers the 253 trading days required.
    """
    if not tickers:
        return {}, {}
    lower = score_date - timedelta(days=420)
    conn = duckdb.connect(str(prices_db), read_only=True)
    try:
        placeholders = ",".join(["?"] * len(tickers))
        rows = conn.execute(
            f"SELECT ticker, dt, close, volume FROM daily_bars "
            f"WHERE ticker IN ({placeholders}) AND dt <= ? AND dt >= ? "
            f"ORDER BY ticker, dt",
            [*tickers, score_date, lower],
        ).fetchall()
    finally:
        conn.close()

    by_ticker: dict[str, list[tuple[float, float]]] = {}
    for t, _dt, close, vol in rows:
        by_ticker.setdefault(t, []).append((float(close or 0.0), float(vol or 0.0)))

    need = max(BETA_WINDOW + 1, ADV_WINDOW)
    close_by_ticker: dict[str, list[float]] = {}
    adv_by_ticker: dict[str, float] = {}
    for t, series in by_ticker.items():
        if len(series) < need:
            continue
        closes = [c for c, _ in series[-(BETA_WINDOW + 1):]]
        if any(c <= 0.0 for c in closes):
            continue
        last_adv_bars = series[-ADV_WINDOW:]
        adv = sum(c * v for c, v in last_adv_bars) / len(last_adv_bars)
        if adv <= 0.0:
            continue
        close_by_ticker[t] = closes
        adv_by_ticker[t] = adv
    return close_by_ticker, adv_by_ticker


# === Held-position drift ===================================================

def _held_position_drift(
    conn: duckdb.DuckDBPyConnection,
    d: date,
    mode: str,
    prices_db: Path,
    universe_db: Path,
    score_cache: dict,
) -> list[dict[str, Any]]:
    """One row per currently-held name with entry-vs-now rank/decile drift."""
    # Latest broker snapshot on or before d.
    snap_row = conn.execute(
        "SELECT MAX(snapshot_date) FROM broker_positions "
        "WHERE mode = ? AND snapshot_date <= ?",
        [mode, d],
    ).fetchone()
    snap = snap_row[0] if snap_row else None
    if snap is None:
        return []

    positions = conn.execute(
        "SELECT ticker, quantity, mark_price, mark_value FROM broker_positions "
        "WHERE mode = ? AND snapshot_date = ? AND quantity > 0 "
        "ORDER BY mark_value DESC",
        [mode, snap],
    ).fetchall()
    if not positions:
        return []

    current_scores, current_size = _pit_scores(
        d, prices_db, universe_db, score_cache,
    )

    rows: list[dict[str, Any]] = []
    for ticker, qty, mark_price, mark_value in positions:
        # Entry = earliest still-open lot for this ticker; weighted avg buy.
        lots = conn.execute(
            "SELECT buy_date, buy_price, qty_open FROM position_lots "
            "WHERE mode = ? AND ticker = ? AND qty_open > 0 "
            "ORDER BY buy_date",
            [mode, ticker],
        ).fetchall()
        if lots:
            entry_date = lots[0][0]
            tot_qty = sum(q for _, _, q in lots) or 1.0
            wavg_buy = sum(p * q for _, p, q in lots) / tot_qty
        else:
            entry_date, wavg_buy = None, None

        entry_rank = entry_decile = entry_size = None
        if entry_date is not None:
            entry_scores, entry_size = _pit_scores(
                entry_date, prices_db, universe_db, score_cache,
            )
            if ticker in entry_scores:
                entry_rank = entry_scores[ticker]["rank"]
                entry_decile = entry_scores[ticker]["decile"]

        cur = current_scores.get(ticker)
        current_rank = cur["rank"] if cur else None
        current_decile = cur["decile"] if cur else None

        mark_price = float(mark_price or 0.0)
        unrealized_pct = (
            (mark_price / wavg_buy - 1.0) * 100.0
            if wavg_buy not in (None, 0.0) else None
        )
        holding_days = (d - entry_date).days if entry_date else None

        flag, flag_label = _drift_flag(
            entry_decile, current_rank, current_decile,
        )

        rows.append({
            "ticker": ticker,
            "qty": float(qty),
            "mark_value": float(mark_value or 0.0),
            "entry_date": entry_date.isoformat() if entry_date else None,
            "holding_days": holding_days,
            "avg_buy_price": (float(wavg_buy) if wavg_buy is not None else None),
            "mark_price": mark_price,
            "unrealized_pct": unrealized_pct,
            "entry_rank": entry_rank,
            "entry_decile": entry_decile,
            "entry_universe_size": entry_size,
            "current_rank": current_rank,
            "current_decile": current_decile,
            "current_universe_size": current_size,
            "flag": flag,            # ok | warn | flag
            "flag_label": flag_label,
        })
    return rows


def _drift_flag(
    entry_decile: int | None,
    current_rank: int | None,
    current_decile: int | None,
) -> tuple[str, str]:
    """Map entry-vs-now into a dashboard status + label.

    ✗ collapsed   — no current score (fell out of universe / failed momentum gate)
    ⚠ rank-decay  — still scored but out of the top-N, or decile dropped a lot
    ✓ on-track    — still a strong pick
    """
    if current_rank is None or current_decile is None:
        return "flag", "momentum collapsed (out of universe / gate)"
    if current_rank > N_POSITIONS:
        return "warn", f"rank decayed to #{current_rank} (out of top {N_POSITIONS})"
    if (
        entry_decile is not None
        and (entry_decile - current_decile) >= DECILE_DECAY_FLAG
    ):
        return "warn", (
            f"decile {entry_decile}→{current_decile} (weakening)"
        )
    return "ok", f"still top-{N_POSITIONS} (#{current_rank})"


# === Closed-trade attribution ==============================================

def _closed_trade_attribution(
    conn: duckdb.DuckDBPyConnection,
    d: date,
    mode: str,
    lookback_days: int,
    prices_db: Path,
    universe_db: Path,
    macro_db: Path,
    score_cache: dict,
) -> list[dict[str, Any]]:
    """One row per trade closed in [d - lookback_days, d]."""
    start = d - timedelta(days=lookback_days)
    trades = conn.execute(
        "SELECT ticker, buy_date, sell_date, qty, buy_price, sell_price, "
        "       realized_pnl_usd, holding_days, tax_paid_usd "
        "FROM realized_trades "
        "WHERE mode = ? AND sell_date >= ? AND sell_date <= ? "
        "ORDER BY sell_date DESC, ticker",
        [mode, start, d],
    ).fetchall()
    if not trades:
        return []

    from backtest.costs import commission_usd

    nifty = _NiftyReader(macro_db)
    rows: list[dict[str, Any]] = []
    for (ticker, buy_date, sell_date, qty, buy_price, sell_price,
         realized_pnl, holding_days, tax_paid) in trades:
        qty = float(qty)
        buy_price = float(buy_price)
        sell_price = float(sell_price)
        return_pct = (sell_price / buy_price - 1.0) * 100.0 if buy_price else 0.0

        # Signal layer: entry rank/decile (PIT at buy date).
        entry_scores, entry_size = _pit_scores(
            buy_date, prices_db, universe_db, score_cache,
        )
        es = entry_scores.get(ticker)
        entry_rank = es["rank"] if es else None
        entry_decile = es["decile"] if es else None

        # Benchmark layer: Nifty-50 return over the exact holding window.
        nifty_pct = nifty.return_pct(buy_date, sell_date)
        excess_pct = (
            return_pct - nifty_pct if nifty_pct is not None else None
        )

        # Cost layer: modeled round-trip DP + STT + fees, in bps of sell notional.
        sell_notional = sell_price * qty
        cost_inr = (
            commission_usd(buy_price * qty, "BUY")
            + commission_usd(sell_notional, "SELL")
        )
        cost_bps = (cost_inr / sell_notional * 10000.0) if sell_notional else 0.0

        cause = _dominant_cause(
            return_pct, excess_pct, entry_decile, cost_bps,
        )

        rows.append({
            "ticker": ticker,
            "buy_date": buy_date.isoformat(),
            "sell_date": sell_date.isoformat(),
            "holding_days": int(holding_days),
            "qty": qty,
            "return_pct": return_pct,
            "realized_pnl_inr": float(realized_pnl),
            "tax_inr": float(tax_paid),
            "nifty_pct": nifty_pct,
            "excess_pct": excess_pct,
            "entry_rank": entry_rank,
            "entry_decile": entry_decile,
            "entry_universe_size": entry_size,
            "cost_inr": float(cost_inr),
            "cost_bps": float(cost_bps),
            "dominant_cause": cause,
        })
    return rows


def _dominant_cause(
    return_pct: float,
    excess_pct: float | None,
    entry_decile: int | None,
    cost_bps: float,
) -> str:
    """Single tag for why a closed trade landed where it did.

    clean-alpha    — made money AND beat Nifty
    beta-only      — made money but lagged Nifty (rode the market)
    market-drag    — lost money but matched/beat Nifty (the market fell more)
    signal-was-weak— lost & lagged, and it was a low-decile pick at entry
    cost-heavy     — lost & lagged, and cost was a big share of the loss
    signal-failure — lost & lagged despite a strong-decile entry
    """
    won = return_pct > 0
    # If we can't benchmark, fall back to raw sign.
    beat = (excess_pct is None and won) or (
        excess_pct is not None and excess_pct >= 0
    )
    if won and beat:
        return "clean-alpha"
    if won and not beat:
        return "beta-only"
    if (not won) and beat:
        return "market-drag"
    # lost AND lagged
    if entry_decile is not None and entry_decile <= 3:
        return "signal-was-weak"
    loss_bps = abs(return_pct) * 100.0  # %→bps
    if loss_bps > 0 and cost_bps > 0.5 * loss_bps:
        return "cost-heavy"
    return "signal-failure"


class _NiftyReader:
    """Nifty-50 index level lookups from macro.duckdb, cached per instance."""

    def __init__(self, macro_db: Path):
        self._db = macro_db
        self._cache: dict[date, float | None] = {}

    def _level_on_or_before(self, conn, d: date) -> float | None:
        if d in self._cache:
            return self._cache[d]
        row = conn.execute(
            "SELECT value FROM macro_daily "
            "WHERE series_id = ? AND dt <= ? ORDER BY dt DESC LIMIT 1",
            [NIFTY_SERIES_ID, d],
        ).fetchone()
        val = float(row[0]) if row and row[0] is not None else None
        self._cache[d] = val
        return val

    def return_pct(self, start: date, end: date) -> float | None:
        if not self._db.exists():
            return None
        conn = duckdb.connect(str(self._db), read_only=True)
        try:
            lo = self._level_on_or_before(conn, start)
            hi = self._level_on_or_before(conn, end)
        finally:
            conn.close()
        if lo in (None, 0.0) or hi is None:
            return None
        return (hi / lo - 1.0) * 100.0
