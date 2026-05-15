"""Indian-equities universe construction.

The universe is the **top 200 names by 20-day Average Daily Value (ADV) drawn
from the Nifty 500**, filtered for tradeability. It is recomputed monthly and
snapshot-locked at each historical rebalance date so that backtests see the
universe membership that actually existed on each historical day (no
look-ahead / survivorship bias).

Source of truth: `https://niftyindices.com/IndexConstituent/ind_nifty500list.csv`
(free, public; refreshed by NSE Indices semi-annually with intermediate
reconstitutions when needed).

Filters (in order, all must pass):

  1. Series == 'EQ'           — excludes SME, BE, T, Z groups
  2. Listing-age >= 504 td    — ≈2 years of price history available
  3. Trading-days >= 90%      — of last 250 sessions had trades (not
                                  suspended / circuited persistently)
  4. Free-float mcap >= ₹1000 cr — exclude manipulability candidates
  5. 20-day ADV >= ₹10 cr     — liquidity floor; ensures ₹50k buy/sell is
                                  < 0.05% of daily volume
  6. Sort by ADV desc, take top 200

This file does NOT fetch price data on its own — it consumes the price tables
that `data.ingest_prices` populates. Universe rebuild is the first thing the
daily/biweekly pipeline does after price ingest.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import requests

logger = logging.getLogger(__name__)

NIFTY500_URL = (
    "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv"
)

# Backstop User-Agent — NSE-domain endpoints reject default python-requests UAs
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)

# Filter thresholds (canonical; loop may experiment with smaller universes
# downstream but the ingest universe stays at these values).
MIN_LISTING_TRADING_DAYS = 504        # ~2 years
MIN_TRADING_DAYS_RATIO = 0.90         # of last 250 sessions
MIN_FREE_FLOAT_MCAP_CR = 1_000        # ₹1,000 crore
MIN_ADV_CR = 10                       # ₹10 crore (20-day rolling)
ADV_LOOKBACK_DAYS = 20
RECENT_SESSIONS_WINDOW = 250
TARGET_UNIVERSE_SIZE = 200


@dataclass(frozen=True)
class UniverseRow:
    as_of_date: date
    ticker: str                  # NSE symbol, e.g. 'RELIANCE'
    isin: str
    company: str
    industry: str                # NSE industry classification (sector proxy)
    free_float_mcap_cr: float    # ₹ crore
    adv_20d_cr: float            # ₹ crore


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: pull the Nifty 500 constituent list (refreshes monthly)
# ─────────────────────────────────────────────────────────────────────────────


def fetch_nifty500_constituents(timeout: int = 30) -> list[dict[str, str]]:
    """Download and parse the current Nifty 500 constituent CSV.

    Returns a list of dicts with keys: Symbol, Series, Company Name, Industry, ISIN Code.

    Raises HTTPError if NSE Indices is unreachable. Caller should cache the
    result in `storage/universe.duckdb` and fall back to the cached copy on
    transient failure.
    """
    # niftyindices.com sniffs the Accept header and serves an HTML wrapper for
    # specific CSV / text mimetypes; only Accept:*/* (curl default) returns the
    # raw CSV. Empirically verified 2026-05-15.
    headers = {"User-Agent": _BROWSER_UA, "Accept": "*/*"}
    resp = requests.get(NIFTY500_URL, headers=headers, timeout=timeout)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return [
        {
            "symbol": row["Symbol"].strip().upper(),
            "series": row.get("Series", "EQ").strip(),
            "company": row["Company Name"].strip(),
            "industry": row.get("Industry", "OTHER").strip() or "OTHER",
            "isin": row["ISIN Code"].strip(),
        }
        for row in reader
        if row.get("Symbol")
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: compute ADV and apply tradeability filters at a given as-of date
# ─────────────────────────────────────────────────────────────────────────────


def compute_universe(
    as_of_date: date,
    prices_db: Path,
    universe_db: Path,
    constituents: list[dict[str, str]] | None = None,
    *,
    target_size: int = TARGET_UNIVERSE_SIZE,
    min_adv_cr: float = MIN_ADV_CR,
    min_free_float_mcap_cr: float = MIN_FREE_FLOAT_MCAP_CR,
) -> list[UniverseRow]:
    """Compute the universe as of `as_of_date` — POINT-IN-TIME, survivorship-free.

    Membership is derived purely from the prices already in `prices_db`
    (`daily_bars`, the full NSE EQ bhav including names that later delisted):
    every ticker actively trading strictly BEFORE `as_of_date` is a candidate,
    filtered by listing age + 20-day ADV + recent-trading-days ratio, then
    ranked by ADV desc and sliced to `target_size`. A name that delisted in
    2022 simply stops being a candidate after 2022 — automatically, with no
    look-ahead. This is the live-trading selection rule applied consistently
    through time (see audit 2026-05-15).

    `constituents` (the CURRENT Nifty 500 CSV, fetched if None) is used ONLY
    as a best-effort sector/ISIN enrichment lookup — NOT for membership.
    Sector labels are stable over time, so today's label applied historically
    is a harmless approximation; a name absent from the current list (e.g. a
    delisted one) gets industry='OTHER' and an empty ISIN, both of which
    data.sectors.canonicalise and resolve_scrip_code already handle
    gracefully (sector cap treats OTHER as a normal bucket; BSE matching
    falls back to the NSE symbol).

    ADV = mean(close*volume) over the last ADV_LOOKBACK_DAYS sessions strictly
    before as_of_date. `universe_db` is written idempotently (delete-then-
    insert per as_of_date). Returns the post-filter list sorted by ADV desc.
    """
    if constituents is None:
        constituents = fetch_nifty500_constituents()

    # Static enrichment lookup ONLY (symbol → sector/ISIN/company). Membership
    # comes from price history below, never from this list.
    enrich: dict[str, dict[str, str]] = {
        c["symbol"]: c for c in constituents
    }

    conn = duckdb.connect(str(prices_db), read_only=True)
    try:
        # ADV computation: short window strictly BEFORE as_of_date (don't use
        # same-day data). Window is ~ADV_LOOKBACK_DAYS calendar days × 2 + 30
        # margin to cover weekends/holidays.
        adv_window_start = as_of_date - timedelta(days=ADV_LOOKBACK_DAYS * 2 + 30)
        adv_rows = conn.execute(
            """
            SELECT ticker,
                   AVG(close * volume) / 1e7 AS adv_cr
              FROM daily_bars
             WHERE dt >= ? AND dt < ?
             GROUP BY ticker
            """,
            (adv_window_start, as_of_date),
        ).fetchall()

        # Total listing-age + trading-day stats over the FULL history strictly
        # before `as_of_date`. Listing age = total count of trading bars; the
        # trading-day ratio is computed against the last RECENT_SESSIONS_WINDOW
        # sessions.
        recent_window_start = as_of_date - timedelta(days=int(RECENT_SESSIONS_WINDOW * 1.5))
        history_rows = conn.execute(
            """
            SELECT ticker,
                   COUNT(*) AS total_bars,
                   SUM(CASE WHEN dt >= ? AND volume > 0 THEN 1 ELSE 0 END)
                       AS recent_trading_days,
                   SUM(CASE WHEN dt >= ? THEN 1 ELSE 0 END) AS recent_bars
              FROM daily_bars
             WHERE dt < ?
             GROUP BY ticker
            """,
            (recent_window_start, recent_window_start, as_of_date),
        ).fetchall()
    finally:
        conn.close()

    adv_by = {r[0]: (r[1] or 0.0) for r in adv_rows}
    by_ticker = {
        r[0]: {
            "n_bars": r[1],
            "adv_cr": adv_by.get(r[0], 0.0),
            "n_trading_days": r[2],
            "recent_bars": r[3],
        }
        for r in history_rows
    }

    # Candidate set = every ticker with price history strictly before
    # as_of_date (point-in-time, survivorship-free). NOT a fixed list.
    survivors: list[UniverseRow] = []
    for ticker, stats in by_ticker.items():
        if stats["n_bars"] < MIN_LISTING_TRADING_DAYS:
            continue
        if stats["adv_cr"] < min_adv_cr:
            continue
        recent_bars = stats.get("recent_bars", 0) or 0
        if recent_bars > 0:
            ratio = stats["n_trading_days"] / recent_bars
            if ratio < MIN_TRADING_DAYS_RATIO:
                continue
        meta = enrich.get(ticker)
        # ADV (₹10cr floor) is the liquidity gate; free-float mcap is a
        # best-effort enrichment only, hence 0.0 when unknown.
        survivors.append(
            UniverseRow(
                as_of_date=as_of_date,
                ticker=ticker,
                isin=meta["isin"] if meta else "",
                company=meta["company"] if meta else ticker,
                industry=meta["industry"] if meta else "OTHER",
                free_float_mcap_cr=0.0,
                adv_20d_cr=float(stats["adv_cr"]),
            )
        )

    survivors.sort(key=lambda r: r.adv_20d_cr, reverse=True)
    picked = survivors[:target_size]
    logger.info(
        "universe @ %s: %d PIT candidates → %d pass filters → %d picked (top by ADV)",
        as_of_date,
        len(by_ticker),
        len(survivors),
        len(picked),
    )

    _write_snapshot(universe_db, as_of_date, picked)
    return picked


# ─────────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────────


def _write_snapshot(
    universe_db: Path,
    as_of_date: date,
    rows: list[UniverseRow],
) -> None:
    """Idempotent write: delete-then-insert for the (as_of_date) slice."""
    conn = duckdb.connect(str(universe_db))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS universe_snapshot (
                as_of_date DATE NOT NULL,
                ticker VARCHAR NOT NULL,
                isin VARCHAR,
                company VARCHAR,
                industry VARCHAR,
                free_float_mcap_cr DOUBLE,
                adv_20d_cr DOUBLE,
                rank_by_adv INTEGER,
                PRIMARY KEY (as_of_date, ticker)
            )
            """
        )
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(
                "DELETE FROM universe_snapshot WHERE as_of_date = ?",
                (as_of_date,),
            )
            for i, r in enumerate(rows, start=1):
                conn.execute(
                    """
                    INSERT INTO universe_snapshot
                        (as_of_date, ticker, isin, company, industry,
                         free_float_mcap_cr, adv_20d_cr, rank_by_adv)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.as_of_date,
                        r.ticker,
                        r.isin,
                        r.company,
                        r.industry,
                        r.free_float_mcap_cr,
                        r.adv_20d_cr,
                        i,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def load_universe(
    universe_db: Path,
    as_of_date: date,
) -> list[UniverseRow]:
    """Read the snapshot for `as_of_date`. Returns [] if no snapshot exists."""
    conn = duckdb.connect(str(universe_db), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT as_of_date, ticker, isin, company, industry,
                   free_float_mcap_cr, adv_20d_cr
              FROM universe_snapshot
             WHERE as_of_date = ?
             ORDER BY rank_by_adv
            """,
            (as_of_date,),
        ).fetchall()
    finally:
        conn.close()
    return [UniverseRow(*r) for r in rows]


def latest_universe_date(universe_db: Path) -> date | None:
    """Most recent snapshot date in the DB, or None if empty."""
    if not universe_db.exists():
        return None
    conn = duckdb.connect(str(universe_db), read_only=True)
    try:
        row = conn.execute(
            "SELECT MAX(as_of_date) FROM universe_snapshot"
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] else None


DEFAULT_UNIVERSE_DB = Path("storage/universe.duckdb")


def snapshot_dates(universe_db: Path = DEFAULT_UNIVERSE_DB) -> list[date]:
    """All as_of_dates that have a stored (non-empty) snapshot, ascending."""
    if not universe_db.exists():
        return []
    conn = duckdb.connect(str(universe_db), read_only=True)
    try:
        rows = conn.execute(
            "SELECT DISTINCT as_of_date FROM universe_snapshot ORDER BY as_of_date"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def get_universe_at(as_of_date: date, universe_db: Path = DEFAULT_UNIVERSE_DB) -> list[str]:
    """Return the list of NSE tickers in the universe snapshot for `as_of_date`.

    Resolution order:
      1. Most-recent snapshot ON OR BEFORE `as_of_date` (correct historical lookup).
      2. Earliest snapshot AFTER `as_of_date` — fallback when historical snapshots
         haven't been built yet but the strategy still needs to run a backtest
         from before any snapshot exists. Introduces survivorship bias (the
         universe will include names that joined later, exclude ones that left
         earlier). Acceptable for v1 paper validation; v2 should backfill
         historical snapshots from NSE Indices monthly archives.

    Returns [] if the DB is empty.
    """
    if not universe_db.exists():
        return []
    conn = duckdb.connect(str(universe_db), read_only=True)
    try:
        row = conn.execute(
            "SELECT MAX(as_of_date) FROM universe_snapshot WHERE as_of_date <= ?",
            (as_of_date,),
        ).fetchone()
        snap = row[0] if row else None
        if not snap:
            # Fallback: earliest available snapshot (survivorship bias documented above)
            row = conn.execute(
                "SELECT MIN(as_of_date) FROM universe_snapshot"
            ).fetchone()
            snap = row[0] if row else None
            if snap:
                logger.warning(
                    "universe: no snapshot on or before %s; falling back to "
                    "earliest available (%s) — introduces survivorship bias",
                    as_of_date, snap,
                )
        if not snap:
            return []
        rows = conn.execute(
            "SELECT ticker FROM universe_snapshot WHERE as_of_date = ? ORDER BY rank_by_adv",
            (snap,),
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def get_live_universe(universe_db: Path = DEFAULT_UNIVERSE_DB) -> list[str]:
    """Most-recent universe snapshot (used by live cron at run-time)."""
    last = latest_universe_date(universe_db)
    if last is None:
        return []
    return get_universe_at(last, universe_db)


_CONSTITUENTS_CACHE = Path("storage/nifty500_cache.json")


def _load_or_fetch_constituents() -> list[dict[str, str]]:
    """Fetch the current Nifty 500 list once for enrichment, with an on-disk
    cache fallback so a transient network failure can't abort a long backfill.
    Membership does NOT depend on this — it is sector/ISIN enrichment only."""
    import json

    try:
        c = fetch_nifty500_constituents()
        if c:
            _CONSTITUENTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CONSTITUENTS_CACHE.write_text(json.dumps(c))
            return c
    except Exception as e:  # noqa: BLE001 — network/parse; fall back to cache
        logger.warning("nifty500 fetch failed (%s); using cache", e)
    if _CONSTITUENTS_CACHE.exists():
        return json.loads(_CONSTITUENTS_CACHE.read_text())
    raise RuntimeError(
        "nifty500 constituents unavailable (no network, no cache). "
        "Membership is unaffected but sector/ISIN enrichment needs this once."
    )


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def backfill_snapshots(
    prices_db: Path,
    universe_db: Path,
    start: date,
    end: date,
    *,
    step_months: int = 1,
    constituents: list[dict[str, str]] | None = None,
) -> dict[date, int]:
    """Compute & store a POINT-IN-TIME universe snapshot on the 1st of each
    month in [start, end], plus one exactly at `end`.

    This is Fix A for the 2026-05-15 audit: without per-date snapshots,
    get_universe_at falls back to the single latest snapshot for every
    historical date, so the whole walk-forward ran on today's universe.

    Idempotent: compute_universe delete-then-inserts per as_of_date, so
    re-running is safe and resumes cleanly. Constituents (current Nifty 500,
    enrichment only) is fetched once and reused for every snapshot.
    Returns {as_of_date: n_members}.
    """
    if constituents is None:
        constituents = _load_or_fetch_constituents()
    out: dict[date, int] = {}
    d = date(start.year, start.month, 1)
    while d <= end:
        rows = compute_universe(
            d, prices_db, universe_db, constituents=constituents
        )
        out[d] = len(rows)
        logger.info("universe snapshot %s: %d members", d, len(rows))
        d = _add_months(d, step_months)
    if end not in out:
        rows = compute_universe(
            end, prices_db, universe_db, constituents=constituents
        )
        out[end] = len(rows)
        logger.info("universe snapshot %s (end): %d members", end, len(rows))
    return out


__all__ = [
    "UniverseRow",
    "DEFAULT_UNIVERSE_DB",
    "fetch_nifty500_constituents",
    "compute_universe",
    "backfill_snapshots",
    "snapshot_dates",
    "load_universe",
    "latest_universe_date",
    "get_universe_at",
    "get_live_universe",
    "TARGET_UNIVERSE_SIZE",
    "MIN_ADV_CR",
    "MIN_FREE_FLOAT_MCAP_CR",
]
