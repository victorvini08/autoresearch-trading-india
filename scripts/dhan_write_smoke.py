"""Real-money WRITE smoke for the live Dhan order path.

`scripts.dhan_smoke` is READ-ONLY (cash/positions/holdings). This script proves
the WRITE chain that the executor relies on — order placement, status polling,
and fill capture — against the REAL Dhan API, using a tiny capped round-trip:

    BUY 1 share (MARKET, CNC) -> wait_for_done -> read the fill
    SELL 1 share (marketable LIMIT, CNC) -> wait_for_done -> read the fill

It goes through the exact `brokers.dhan.DhanBroker` methods the executor calls,
so a clean run means "real orders place and fill through our code." The net
position returns to flat; the only real cost is any DP charge plus a few rupees
of spread on one share — the price of certainty before funding to deployment
size.

ROOT-CAUSE LEARNING (2026-06-29): order placement returns `DH-905 Invalid IP`
until BOTH (a) the egress IP is whitelisted in the Dhan portal AND (b) the
access-token is (re)generated AFTER that whitelist — the token binds the IP
state at generation time. `GET /v2/ip/getIP` can show ipMatchStatus=PRIMARY_MATCH
/ ordersAllowed=true while orders still 905 if the live token predates the
whitelist. Fix: renew the token (scripts.dhan_token_refresh), then place orders.
This preflight prints getIP so the mismatch is visible up front.

SELL pricing: Dhan converts an equity MARKET order to a protected LIMIT at LTP,
which can rest unfilled if the bid slips below it (observed: a MARKET sell stuck
as LIMIT@buy-price). So the SELL here is a LIMIT anchored just below the BUY fill
(marketable -> fills at the bid), with escalation and a hard cancel so the smoke
never strands a share.

SAFETY (all enforced before any order is sent):
  * DRY-RUN by default. Nothing is placed unless `--confirm` is passed.
  * NSE market-hours guard (09:15-15:30 IST).
  * Per-order notional cap (`--max-notional`, default Rs.900) vs latest local close.
  * Available-balance check.
  * BUY non-fill -> cancelled, no SELL. SELL non-fill -> escalated then cancelled,
    with a loud manual-exit warning; never leaves a resting order.

  One-off operational tool; does NOT touch the strategy, ledger, bootstrap
  marker, or any cron.

Usage (on the VM, where the live token lives):
    DHAN_MOCK=0 uv run python -m scripts.dhan_write_smoke --ticker IOC            # dry run
    DHAN_MOCK=0 uv run python -m scripts.dhan_write_smoke --ticker IOC --confirm  # real round-trip
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

from brokers.dhan import (
    ORDER_TYPE_LIMIT,
    STATUS_TRADED,
    DhanBroker,
    OrderRequest,
)

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)
DEFAULT_PRICES_DB = Path("storage/prices.duckdb")
# SELL is a LIMIT below the BUY fill so it crosses the spread and fills at the
# bid; escalate if a tick moves against us, then hard-cancel.
_SELL_ESCALATION = (0.99, 0.97, 0.95)


def _latest_local_close(ticker: str, prices_db: Path) -> float | None:
    """Latest NSE bhav close for `ticker` from the local prices DB (sanity
    bound for the notional cap). Returns None if unavailable."""
    try:
        import duckdb

        conn = duckdb.connect(str(prices_db), read_only=True)
        try:
            row = conn.execute(
                "SELECT close FROM daily_bars WHERE ticker = ? "
                "ORDER BY dt DESC LIMIT 1",
                [ticker.upper()],
            ).fetchone()
        finally:
            conn.close()
        return float(row[0]) if row and row[0] else None
    except Exception as e:  # noqa: BLE001 — sanity bound only; never fatal here
        print(f"[warn] local close lookup failed ({type(e).__name__}: {e})")
        return None


def _within_market_hours(now_ist: datetime) -> bool:
    if now_ist.weekday() >= 5:  # Sat/Sun
        return False
    return MARKET_OPEN <= now_ist.time() <= MARKET_CLOSE


def _print_ip_status(broker: DhanBroker) -> None:
    """Print Dhan's view of the IP whitelist (getIP). A PRIMARY_MATCH with
    ordersAllowed=true but a subsequent DH-905 means the token predates the
    whitelist — renew it (scripts.dhan_token_refresh) and retry."""
    try:
        r = broker._sess.get(broker._base + "/v2/ip/getIP", timeout=15)
        g = r.json() if r.text.strip() else {}
        print(f"IP check: detected={g.get('detectedIP')} primary={g.get('primaryIP')} "
              f"match={g.get('ipMatchStatus')} ordersAllowed={g.get('ordersAllowed')}")
        if not g.get("ordersAllowed"):
            print("  [warn] ordersAllowed=false — whitelist this IP in the Dhan "
                  "portal (Static IP Setting), then RENEW the token.")
    except Exception as e:  # noqa: BLE001 — diagnostic only
        print(f"[warn] getIP failed ({type(e).__name__}: {e})")


def _fill_price(broker: DhanBroker, order_id: str) -> float | None:
    fills = [f for f in broker.get_fills() if f.order_id == order_id]
    return fills[0].price if fills else None


def _buy_market(broker: DhanBroker, ticker: str) -> float | None:
    """BUY 1 share MARKET CNC; return the fill price, or None (and cancel any
    residual) if it did not trade."""
    print(f"\n--- BUY 1 {ticker} (MARKET, CNC) ---")
    resp = broker.place_order(OrderRequest(transaction_type="BUY", ticker=ticker, quantity=1))
    print(f"  placed: order_id={resp.order_id} status={resp.status}")
    final = broker.wait_for_done(resp.order_id)
    print(f"  terminal: {final.status}")
    if final.status != STATUS_TRADED:
        broker.cancel_order(resp.order_id)  # never leave it resting
        print(f"  [!] BUY did not trade (status={final.status}); cancelled. No position.")
        return None
    time.sleep(1.0)
    px = _fill_price(broker, resp.order_id)
    print(f"  FILL: BUY 1 {ticker} @ Rs.{px}")
    return px


def _sell_to_flat(broker: DhanBroker, ticker: str, anchor_px: float) -> bool:
    """SELL 1 share via a marketable LIMIT anchored below `anchor_px` (the buy
    fill). Escalate through _SELL_ESCALATION, hard-cancelling each non-fill, so
    the smoke never strands a share. Returns True iff sold."""
    for mult in _SELL_ESCALATION:
        limit = round(anchor_px * mult, 1)
        print(f"\n--- SELL 1 {ticker} (LIMIT Rs.{limit}, CNC) ---")
        resp = broker.place_order(
            OrderRequest(transaction_type="SELL", ticker=ticker, quantity=1,
                         order_type=ORDER_TYPE_LIMIT, price=limit)
        )
        print(f"  placed: order_id={resp.order_id} status={resp.status}")
        final = broker.wait_for_done(resp.order_id, timeout_sec=30)
        if final.status == STATUS_TRADED:
            time.sleep(1.0)
            print(f"  FILL: SELL 1 {ticker} @ Rs.{_fill_price(broker, resp.order_id)}")
            return True
        print(f"  not filled (status={final.status}); cancelling and escalating")
        broker.cancel_order(resp.order_id)
        time.sleep(1.0)
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Real-money WRITE smoke (1-share round-trip).")
    ap.add_argument("--ticker", default="IOC", help="NSE symbol (default: IOC)")
    ap.add_argument("--confirm", action="store_true",
                    help="actually place orders (default: dry-run)")
    ap.add_argument("--max-notional", type=float, default=900.0,
                    help="refuse if 1 share costs more than this (Rs., default 900)")
    ap.add_argument("--prices-db", default=str(DEFAULT_PRICES_DB))
    args = ap.parse_args(argv)

    ticker = args.ticker.upper()
    now_ist = datetime.now(IST)
    print(f"== Dhan WRITE smoke — {ticker} — {now_ist:%Y-%m-%d %H:%M:%S %Z} ==")

    broker = DhanBroker()  # raises if token/client id absent

    # IP / token preflight (the DH-905 root cause is visible here).
    _print_ip_status(broker)

    # 1. Resolve the instrument (proves the scrip master is loaded).
    try:
        sec_id = broker.security_id_for(ticker)
    except Exception as e:  # noqa: BLE001
        print(f"[abort] cannot resolve {ticker} to a securityId: {e}")
        return 1
    print(f"securityId({ticker}) = {sec_id}")

    # 2. Price / notional cap (local bhav close as the bound).
    px = _latest_local_close(ticker, Path(args.prices_db))
    if px is None:
        print(f"[abort] no local close for {ticker}; pass a ticker present in the bhav DB.")
        return 1
    print(f"latest local close ~ Rs.{px:.2f}  (cap Rs.{args.max_notional:.0f})")
    if px > args.max_notional:
        print(f"[abort] 1 share (~Rs.{px:.0f}) exceeds the Rs.{args.max_notional:.0f} cap. "
              f"Pick a cheaper liquid name with --ticker.")
        return 1

    # 3. Cash check.
    cash = float(broker.get_cash().get("availableBalance", 0.0))
    print(f"availableBalance = Rs.{cash:.2f}")
    if cash < px:
        print(f"[abort] balance Rs.{cash:.0f} < 1 share (~Rs.{px:.0f}). Fund the account.")
        return 1

    # 4. Market-hours guard.
    if not _within_market_hours(now_ist):
        print(f"[abort] market closed (now {now_ist:%H:%M} IST; window "
              f"{MARKET_OPEN:%H:%M}-{MARKET_CLOSE:%H:%M}). Re-run during market hours.")
        return 1

    if not args.confirm:
        print("\n[DRY-RUN] all pre-flight checks PASSED. Would place: "
              f"BUY 1 {ticker} (MARKET) -> SELL 1 {ticker} (marketable LIMIT) -> flat.")
        print("Re-run with --confirm to place the real round-trip.")
        return 0

    # 5. Live round-trip.
    print("\n*** PLACING REAL ORDERS (--confirm) ***")
    buy_px = _buy_market(broker, ticker)
    if buy_px is None:
        print("\n[STOP] BUY did not trade — no position to unwind.")
        return 1
    if not _sell_to_flat(broker, ticker, buy_px):
        print(f"\n[!!] SELL could not fill after escalation — you may still hold 1 "
              f"{ticker}. No order is resting; exit manually in the Dhan app.")
        return 1

    # 6. Confirm flat.
    pos = [p for p in broker.get_positions() if p.ticker.upper() == ticker and p.quantity]
    print("\n=== round-trip complete ===")
    print(f"residual {ticker} position: {pos if pos else 'FLAT (0 shares)'}")
    print("WRITE path verified: place -> poll -> fill works against the real API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
