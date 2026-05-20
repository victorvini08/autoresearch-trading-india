"""Pre-market scan. Runs at 09:00 IST (15 min before NSE open).

For each ticker currently held in the dhan-paper / dhan-live ledger,
fetch the latest pre-open quote, compute the gap vs prior close, and
flag anything that crosses GAP_THRESHOLD. Also probe the India VIX
level to detect macro shocks.

Output: state/premarket_<YYYY-MM-DD>.json. This file is purely
advisory — `scripts/run_live.py` reads it and may:

  - skip rebalancing on a ticker that gapped > GAP_THRESHOLD (we don't
    want to blindly market-fill into a violently-moving name)
  - scale down gross exposure if India VIX > VIX_THRESHOLD
  - recommend halt for trading halts / unscheduled events

The scan is READ-ONLY. It does not modify the ledger, does not write
halt.json, does not call risk_check. It just records observations
into a JSON file the orchestrator consumes.

Same infrastructure runs in both dhan-paper (advisory only) and
dhan-live (gates real trades) modes. Exercising it daily during the
paper warmup proves the path before money is at stake.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from storage import portfolio_db

logger = logging.getLogger(__name__)

# Thresholds — match the spec's risk-gate semantics for consistency.
GAP_THRESHOLD = 0.05      # 5% pre-open move on a held name → flag
VIX_THRESHOLD = 35.0      # >35 on India VIX implies acute risk-off regime
LARGE_GAP_HARD_HALT = 0.15  # >15% on a held name → recommend halt, not just skip

IST = ZoneInfo("Asia/Kolkata")
SCAN_DIR = Path("state")


def scan(
    today_ist: date,
    *,
    mode: str = "dhan-paper",
    db_path: Path | None = None,
    quote_fetch=None,
    out_dir: Path | None = None,
) -> dict:
    """Run the scan and write state/premarket_<today_ist>.json.

    `quote_fetch` is injectable for tests — a callable
    `(ticker: str) -> dict | None` returning at least `prior_close` and
    `premarket_price` (None if unavailable). When None, the default
    pre-open backend is used (TODO Phase 6: NSE pre-open + India VIX).

    `mode` selects which ledger snapshot to read positions from.
    Supported: 'dhan-paper' (default) and 'dhan-live'.
    """
    out_dir = out_dir or SCAN_DIR
    db_path = db_path or portfolio_db.DEFAULT_DB_PATH
    fetch = quote_fetch or _default_quote_fetch

    out_dir.mkdir(parents=True, exist_ok=True)
    held = _held_tickers(db_path, mode=mode, as_of=today_ist)

    ticker_results: dict[str, dict] = {}
    halt_recommendations: list[str] = []
    for ticker in held:
        try:
            row = fetch(ticker)
        except Exception as e:  # noqa: BLE001 — best-effort per-ticker
            ticker_results[ticker] = {"error": f"{type(e).__name__}: {e}"}
            continue
        if row is None or row.get("premarket_price") is None or row.get("prior_close") is None:
            ticker_results[ticker] = {"error": "no premarket data"}
            continue
        prior = float(row["prior_close"])
        live = float(row["premarket_price"])
        gap = (live - prior) / prior if prior > 0 else 0.0
        gap_flag = abs(gap) >= GAP_THRESHOLD
        hard_halt = abs(gap) >= LARGE_GAP_HARD_HALT
        if hard_halt:
            halt_recommendations.append(
                f"{ticker}: pre-market move {gap:+.1%} >= "
                f"{LARGE_GAP_HARD_HALT:.0%}"
            )
        ticker_results[ticker] = {
            "prior_close": prior,
            "premarket_price": live,
            "gap_pct": round(gap, 6),
            "gap_flag": gap_flag,
            "hard_halt": hard_halt,
        }

    vix_info = _try_fetch_vix(fetch)
    vix_flag = vix_info.get("level") is not None and vix_info["level"] > VIX_THRESHOLD

    payload = {
        "as_of_date": today_ist.isoformat(),
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode_scanned": mode,
        "vix": {
            **vix_info,
            "threshold": VIX_THRESHOLD,
            "flag": vix_flag,
        },
        "tickers": ticker_results,
        "halt_recommendations": halt_recommendations,
        "gap_threshold": GAP_THRESHOLD,
        "large_gap_hard_halt_threshold": LARGE_GAP_HARD_HALT,
    }

    out_path = out_dir / f"premarket_{today_ist.isoformat()}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    return payload


def load(today_ist: date, *, scan_dir: Path | None = None) -> dict | None:
    """Read today's premarket scan output, if any. Returns None if no
    scan ran today (e.g. weekend, or premarket_scan failed)."""
    scan_dir = scan_dir or SCAN_DIR
    path = scan_dir / f"premarket_{today_ist.isoformat()}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def tickers_to_skip(scan_payload: dict | None) -> set[str]:
    """Helper for run_live.py: tickers the orchestrator should NOT
    rebalance today based on the scan. Empty set if scan unavailable."""
    if not scan_payload:
        return set()
    out: set[str] = set()
    for ticker, info in (scan_payload.get("tickers") or {}).items():
        if isinstance(info, dict) and (info.get("gap_flag") or info.get("hard_halt")):
            out.add(ticker)
    return out


def vix_scale_down(scan_payload: dict | None) -> float:
    """Helper for run_live.py: returns a fraction in [0, 1] to scale
    gross exposure by. 1.0 = no scaling. <1.0 = reduce. 0.5 on VIX>35.
    """
    if not scan_payload:
        return 1.0
    vix = scan_payload.get("vix", {})
    if vix.get("flag"):
        return 0.5
    return 1.0


# ---- internals ----

def _held_tickers(db_path: Path, *, mode: str, as_of: date) -> list[str]:
    """Read tickers with non-zero quantity from the latest snapshot ≤ as_of."""
    with portfolio_db.connect(db_path) as conn:
        state = portfolio_db.load_state(conn, mode=mode, as_of=as_of)
    return sorted([t for t, q in state.positions.items() if q != 0])


def _default_quote_fetch(ticker: str, today: date | None = None) -> dict | None:
    """Yahoo Finance backend. Returns {prior_close, premarket_price} or None.

    yfinance fetches the recent daily candles; we read today's Open (the
    official 09:15 NSE open) as the 'premarket_price' proxy and the
    prior trading day's Close as 'prior_close'. NSE symbols use the
    TICKER.NS form on Yahoo; INDIAVIX uses ^INDIAVIX.

    Yahoo Finance is roughly 15-min delayed for Indian markets — this
    backend is reliable only when the scan fires at or after 10:00 IST.
    The job is scheduled at 10:00 with that delay in mind. If Yahoo
    hasn't published today's row yet (we ran too early, holiday, or
    Yahoo glitch), the fetcher returns None and the scan records
    "no premarket data" for that ticker — downstream (run_live) treats
    missing data as 'no gap signal, proceed normally'.

    Limitations (documented, accepted for Phase A):
      - Yahoo Finance is an unofficial scraped feed; the API can break
        when Yahoo redesigns. The fetcher fails closed (returns None),
        the scan degrades gracefully, run_live still trades.
      - Yahoo's Open != NSE bhav's official Open exactly (small
        adjustment-policy differences). We use Yahoo only for GAP
        DETECTION (defensive monitoring signal); paper fill pricing
        continues to use the authoritative NSE bhav archive.
      - When we go live: Dhan's marketfeed/ltp would be the broker-
        native replacement, but it is part of Dhan's PAID Data API
        (₹500/mo) and explicitly out of scope. yfinance remains.
    """
    import yfinance as yf  # local import — keeps import-time light

    today = today or datetime.now(IST).date()
    yahoo_sym = "^INDIAVIX" if ticker.upper() == "INDIAVIX" else f"{ticker.upper()}.NS"
    try:
        hist = yf.Ticker(yahoo_sym).history(
            period="7d", interval="1d", auto_adjust=False
        )
    except Exception as e:  # noqa: BLE001 — best-effort scrape
        logger.warning("yfinance fetch failed for %s (%s): %s", ticker, yahoo_sym, e)
        return None
    if hist is None or hist.empty:
        return None
    hist = hist.dropna(subset=["Open", "Close"])
    if len(hist) < 2:
        return None
    # Defensive: the LAST row must be today's data. If Yahoo lags so the
    # most recent row is yesterday, we have no premarket for today —
    # return None rather than silently using stale numbers.
    last_idx = hist.index[-1]
    last_date = last_idx.date() if hasattr(last_idx, "date") else None
    if last_date != today:
        return None
    last_open = float(hist["Open"].iloc[-1])
    prior_close = float(hist["Close"].iloc[-2])
    if not (last_open > 0 and prior_close > 0):
        return None
    return {"prior_close": prior_close, "premarket_price": last_open}


def _try_fetch_vix(fetch) -> dict:
    """Returns {'level': float | None, 'source': str, 'error': str|None}.

    TODO Phase 6: India VIX symbol on NSE is 'INDIAVIX'. Wire to
    data.ingest_macro.fetch_india_vix() once that helper lands; until
    then we attempt the injected fetcher (tests use it) and otherwise
    return a no-data placeholder. The orchestrator treats level=None
    as 'no VIX flag' which is the safe default.
    """
    try:
        row = fetch("INDIAVIX")
    except Exception as e:  # noqa: BLE001
        return {"level": None, "source": "nse-pending", "error": f"{type(e).__name__}: {e}"}
    if row is None:
        return {"level": None, "source": "nse-pending", "error": "no data"}
    # Use whichever of premarket_price / prior_close is most current.
    level = row.get("premarket_price") or row.get("prior_close")
    return {"level": level, "source": "nse-pending", "error": None}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", type=date.fromisoformat, default=None,
                   help="Date to label the scan (default: today in IST)")
    p.add_argument("--mode", default="dhan-paper",
                   help="Ledger mode to read positions from (default: dhan-paper)")
    args = p.parse_args(argv)

    today_ist = args.date or datetime.now(IST).date()
    payload = scan(today_ist, mode=args.mode)
    print(f"[premarket] wrote scan for {today_ist}: "
          f"{len(payload['tickers'])} tickers, "
          f"vix_flag={payload['vix']['flag']}, "
          f"halt_recs={len(payload['halt_recommendations'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
