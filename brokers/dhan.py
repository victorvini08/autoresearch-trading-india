"""Dhan HQ Trading API client — hand-rolled REST (no `dhanhq` SDK dependency).

Only TRADING endpoints are wired here. **Dhan's Data API (`/v2/charts/*`) is a
paid product (₹500/mo) and we do NOT call it.** Price data comes from
`data.ingest_prices` (NSE bhav archive — free).

Endpoints used:
  POST   /v2/orders                  — place an order
  GET    /v2/orders                  — today's orders
  GET    /v2/orders/{order-id}       — single order status
  DELETE /v2/orders/{order-id}       — cancel
  GET    /v2/trades                  — today's executions with commission
  GET    /v2/positions               — currently open positions
  GET    /v2/holdings                — long-term (T+1 settled) holdings
  GET    /v2/fundlimit               — cash + margin available

Auth: `access-token: <DHAN_ACCESS_TOKEN>` header + `dhanClientId` in body.

Order tag: every order carries `correlationId` populated with `SEBI_ALGO_ID`
when set (used for traceability). `correlationId` is OPTIONAL per Dhan's API
contract — orders are accepted without it. Earlier versions of this file
asserted otherwise based on a stricter reading of the 2026-04-01 retail-algo
framework; relaxed 2026-05-28 after the user found no Personal-Algo
registration form in the Dhan portal.

Rate-limit: Dhan publishes 20 req/sec; we cap at 10 to leave headroom. Calls
are pipelined through a simple token-bucket guard.

Scrip master: downloaded once a week from
`https://images.dhan.co/api-data/api-scrip-master.csv` and cached locally. This
gives us the `securityId` for every NSE_EQ name.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

DHAN_BASE = "https://api.dhan.co"
SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Order-type constants (Dhan's vocabulary)
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_SL = "STOP_LOSS"
ORDER_TYPE_SLM = "STOP_LOSS_MARKET"

# productType: CNC = Cash & Carry (delivery), MIS = intraday (we never use it)
PRODUCT_CNC = "CNC"
EXCHANGE_NSE_EQ = "NSE_EQ"
VALIDITY_DAY = "DAY"

# Status constants Dhan returns
STATUS_PENDING = "PENDING"
STATUS_TRANSIT = "TRANSIT"
STATUS_TRADED = "TRADED"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"
STATUS_EXPIRED = "EXPIRED"

_TERMINAL_STATES = {STATUS_TRADED, STATUS_REJECTED, STATUS_CANCELLED, STATUS_EXPIRED}


@dataclass
class OrderRequest:
    transaction_type: str            # 'BUY' | 'SELL'
    ticker: str                      # NSE symbol — we resolve to securityId
    quantity: int
    order_type: str = ORDER_TYPE_MARKET
    price: float | None = None       # required for LIMIT
    trigger_price: float | None = None  # required for SL / SLM


@dataclass
class OrderResponse:
    order_id: str
    status: str
    raw: dict = field(default_factory=dict)


@dataclass
class Fill:
    order_id: str
    ticker: str
    side: str                  # 'BUY' | 'SELL'
    quantity: int
    price: float
    fill_time: datetime
    commission: float          # ₹ (sum of broker fees only; STT/DP captured separately)
    trade_id: str = ""         # Dhan trade leg ID; unique even when one order produces N fills
    raw: dict = field(default_factory=dict)


@dataclass
class Position:
    ticker: str
    quantity: int               # net quantity (long positive)
    average_price: float
    realized_pnl: float
    unrealized_pnl: float


# ──────────────────────────────────────────────────────────────────────
# Rate-limit guard (simple token bucket)
# ──────────────────────────────────────────────────────────────────────


class _RateLimiter:
    def __init__(self, max_per_sec: float = 10.0):
        self._min_interval = 1.0 / max_per_sec
        self._last_call = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()


# ──────────────────────────────────────────────────────────────────────
# Scrip master
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.0, min=1, max=30),
    reraise=True,
)
def fetch_scrip_master() -> str:
    """Download the Dhan scrip-master CSV (no auth needed). Returns raw text."""
    resp = requests.get(SCRIP_MASTER_URL, timeout=60)
    resp.raise_for_status()
    return resp.text


def parse_scrip_master(text: str) -> dict[str, dict[str, str]]:
    """Parse the scrip-master CSV into {symbol: row_dict} for NSE_EQ only.

    The CSV columns of interest include:
        SEM_SMST_SECURITY_ID, SEM_TRADING_SYMBOL, SEM_EXM_EXCH_ID,
        SEM_INSTRUMENT_NAME, SEM_LOT_UNITS, SEM_TICK_SIZE, ISIN
    """
    reader = csv.DictReader(io.StringIO(text))
    out: dict[str, dict[str, str]] = {}
    for row in reader:
        exch = (row.get("SEM_EXM_EXCH_ID") or "").strip().upper()
        instrument = (row.get("SEM_INSTRUMENT_NAME") or row.get("SEM_INSTRUMENT") or "").strip().upper()
        symbol = (row.get("SEM_TRADING_SYMBOL") or "").strip().upper()
        if exch != "NSE":
            continue
        if instrument not in ("EQUITY", "EQ"):
            continue
        if not symbol:
            continue
        out[symbol] = row
    return out


def cache_scrip_master(cache_path: Path) -> dict[str, dict[str, str]]:
    """Refresh the local scrip-master if older than a week; otherwise read cache."""
    needs_refresh = True
    if cache_path.exists():
        age_days = (
            time.time() - cache_path.stat().st_mtime
        ) / 86400.0
        if age_days < 7:
            needs_refresh = False
    if needs_refresh:
        text = fetch_scrip_master()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text)
    return parse_scrip_master(cache_path.read_text())


# ──────────────────────────────────────────────────────────────────────
# Broker client
# ──────────────────────────────────────────────────────────────────────


class DhanBroker:
    """REST client for Dhan HQ Trading API. Trading endpoints only."""

    mode: str = "dhan-live"   # callers may override (dhan-paper uses DhanMock)

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        algo_id: str | None = None,
        scrip_master_cache: Path | None = None,
        base_url: str = DHAN_BASE,
        rate_limit_per_sec: float = 10.0,
        timeout_sec: int = 30,
    ) -> None:
        self.access_token = access_token or os.environ.get("DHAN_ACCESS_TOKEN", "")
        self.client_id = client_id or os.environ.get("DHAN_CLIENT_ID", "")
        self.algo_id = algo_id or os.environ.get("SEBI_ALGO_ID", "")
        if not self.access_token or not self.client_id:
            raise RuntimeError(
                "DhanBroker requires DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID "
                "(set in env or pass to constructor). For paper testing, use "
                "DhanMock instead."
            )
        if not self.algo_id:
            # `correlationId` is OPTIONAL per Dhan's POST /v2/orders contract
            # (see https://dhanhq.co/docs/v2/orders/). The SEBI 2026-04-01
            # retail-algo framework asks for algo registration with the broker
            # at the portal level, but Dhan's API does NOT enforce a per-order
            # algo-id field — orders submitted with correlationId="" are
            # accepted. Earlier versions of this code hard-failed here based
            # on a stricter reading; relaxed 2026-05-28 after the user
            # confirmed no Personal-Algo registration form exists in their
            # Dhan portal. Warn so you know you're trading unstamped, but
            # don't block construction.
            logger.warning(
                "SEBI_ALGO_ID is unset — orders will be sent with "
                "correlationId='' (Dhan accepts this; algo registration at "
                "the broker portal is currently a separate concern). To stamp "
                "orders for traceability, set SEBI_ALGO_ID in .env."
            )
        self._base = base_url.rstrip("/")
        self._timeout = timeout_sec
        self._sess = requests.Session()
        self._sess.headers.update(
            {
                "access-token": self.access_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self._rate = _RateLimiter(rate_limit_per_sec)
        cache = scrip_master_cache or Path("storage/dhan_scrip_master.csv")
        try:
            self._scrip = cache_scrip_master(cache)
        except Exception as e:
            logger.warning(
                "scrip master refresh failed (%s); proceeding without — order "
                "placement will fail until scrip master is available",
                e,
            )
            self._scrip = {}

    # ── lifecycle (no-ops for REST; we keep the interface for parity with TWS) ──

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        self._sess.close()

    # ── core REST helper ──

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.0, min=1, max=15),
        reraise=True,
    )
    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        self._rate.wait()
        url = f"{self._base}{path}"
        resp = self._sess.request(method, url, json=body, timeout=self._timeout)
        if resp.status_code >= 400:
            logger.error(
                "Dhan %s %s -> %d: %s", method, path, resp.status_code, resp.text[:500]
            )
        resp.raise_for_status()
        if resp.text.strip() == "":
            return {}
        return resp.json()

    # ── instrument resolution ──

    def security_id_for(self, ticker: str) -> str:
        row = self._scrip.get(ticker.upper())
        if not row:
            raise KeyError(f"ticker {ticker} not found in NSE_EQ scrip master")
        return str(row.get("SEM_SMST_SECURITY_ID") or row.get("SEM_SMST_SECURITY_ID"))

    # ── cash + positions ──

    def get_cash(self) -> dict:
        """Return Dhan's fund-limit snapshot. Caller picks the field they want
        (`availableBalance`, `sodLimit`, `collateralAmount`, etc.).
        """
        return self._request("GET", "/v2/fundlimit") or {}

    def get_positions(self) -> list[Position]:
        """Return everything we own — intraday positions UNION settled holdings.

        Dhan splits the account view across two endpoints:
          - `/v2/positions` — today's intraday + unsettled CNC.
          - `/v2/holdings`  — long-term (T+1 settled) demat holdings.

        Biweekly CNC names settle within T+1 and migrate from /v2/positions
        into /v2/holdings. Querying only the former misses every name held
        more than ~1 trading day and would make the executor think the
        account is flat — sizing buys against cash-only and never selling
        existing holdings. Merge both, dedup by ticker, sum the quantities
        (Dhan can in principle surface the same ticker on both sides
        mid-settlement; treat that as one logical position).
        """
        merged: dict[str, Position] = {}
        for r in self._request("GET", "/v2/positions") or []:
            if not isinstance(r, dict):
                continue
            t = (r.get("tradingSymbol") or "").upper()
            qty = int(r.get("netQty") or 0)
            if not t or qty == 0:
                continue
            merged[t] = Position(
                ticker=t,
                quantity=qty,
                average_price=float(r.get("buyAvg") or 0.0),
                realized_pnl=float(r.get("realizedProfit") or 0.0),
                unrealized_pnl=float(r.get("unrealizedProfit") or 0.0),
            )
        for r in self._request("GET", "/v2/holdings") or []:
            if not isinstance(r, dict):
                continue
            t = (r.get("tradingSymbol") or "").upper()
            qty = int(r.get("totalQty") or 0)
            if not t or qty == 0:
                continue
            existing = merged.get(t)
            if existing is None:
                merged[t] = Position(
                    ticker=t,
                    quantity=qty,
                    average_price=float(r.get("avgCostPrice") or 0.0),
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                )
            else:
                # Mid-settlement: same ticker on both endpoints. Sum the
                # quantities; keep the weighted-avg cost. Realised/unrealised
                # P&L comes from the positions side only (holdings doesn't
                # expose either).
                new_qty = existing.quantity + qty
                if new_qty == 0:
                    merged.pop(t, None)
                    continue
                avg_h = float(r.get("avgCostPrice") or 0.0)
                blended_avg = (
                    (existing.average_price * existing.quantity + avg_h * qty)
                    / new_qty
                ) if new_qty else 0.0
                merged[t] = Position(
                    ticker=t,
                    quantity=new_qty,
                    average_price=blended_avg,
                    realized_pnl=existing.realized_pnl,
                    unrealized_pnl=existing.unrealized_pnl,
                )
        return list(merged.values())

    def get_holdings(self) -> list[Position]:
        """Raw /v2/holdings view — long-term (T+1 settled) demat holdings only.

        Prefer `get_positions()` for executor logic (it merges this with
        /v2/positions); this remains exposed for diagnostics and the
        smoke-test path.
        """
        raw = self._request("GET", "/v2/holdings") or []
        out: list[Position] = []
        for r in raw if isinstance(raw, list) else []:
            out.append(
                Position(
                    ticker=(r.get("tradingSymbol") or "").upper(),
                    quantity=int(r.get("totalQty") or 0),
                    average_price=float(r.get("avgCostPrice") or 0.0),
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                )
            )
        return out

    # ── orders ──

    def place_order(self, req: OrderRequest, *, as_of_date=None) -> OrderResponse:
        # `as_of_date` kwarg accepted (ignored) so DhanBroker and DhanMock
        # share an identical call signature — paper's mock uses it to drive
        # the Phase B yfinance fill-price fetcher; live ignores it (the
        # exchange supplies the true fill price via tradedPrice).
        security_id = self.security_id_for(req.ticker)
        body: dict = {
            "dhanClientId": self.client_id,
            "correlationId": self.algo_id,  # SEBI algo stamp
            "transactionType": req.transaction_type.upper(),
            "exchangeSegment": EXCHANGE_NSE_EQ,
            "productType": PRODUCT_CNC,
            "orderType": req.order_type,
            "validity": VALIDITY_DAY,
            "securityId": security_id,
            "quantity": int(req.quantity),
        }
        if req.order_type == ORDER_TYPE_LIMIT:
            if req.price is None:
                raise ValueError("LIMIT order requires `price`")
            body["price"] = float(req.price)
        if req.order_type in (ORDER_TYPE_SL, ORDER_TYPE_SLM):
            if req.trigger_price is None:
                raise ValueError("SL/SLM order requires `trigger_price`")
            body["triggerPrice"] = float(req.trigger_price)
        if req.order_type == ORDER_TYPE_SL and req.price is not None:
            body["price"] = float(req.price)
        raw = self._request("POST", "/v2/orders", body=body) or {}
        order_id = str(raw.get("orderId") or raw.get("orderID") or "")
        status = str(raw.get("orderStatus") or "PENDING")
        if not order_id:
            raise RuntimeError(f"Dhan accepted but returned no orderId: {raw}")
        return OrderResponse(order_id=order_id, status=status, raw=raw)

    def get_order(self, order_id: str) -> OrderResponse:
        raw = self._request("GET", f"/v2/orders/{order_id}")
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        if not isinstance(raw, dict):
            raw = {}
        return OrderResponse(
            order_id=str(raw.get("orderId") or order_id),
            status=str(raw.get("orderStatus") or "UNKNOWN"),
            raw=raw,
        )

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._request("DELETE", f"/v2/orders/{order_id}")
            return True
        except requests.RequestException as e:
            logger.error("cancel %s failed: %s", order_id, e)
            return False

    def list_today_orders(self) -> list[OrderResponse]:
        raw = self._request("GET", "/v2/orders") or []
        out: list[OrderResponse] = []
        for r in raw if isinstance(raw, list) else []:
            out.append(
                OrderResponse(
                    order_id=str(r.get("orderId") or ""),
                    status=str(r.get("orderStatus") or "UNKNOWN"),
                    raw=r,
                )
            )
        return out

    def get_fills(self) -> list[Fill]:
        raw = self._request("GET", "/v2/trades") or []
        out: list[Fill] = []
        for r in raw if isinstance(raw, list) else []:
            try:
                fill_time = datetime.fromisoformat(
                    str(r.get("tradeTime") or "").replace("Z", "+00:00")
                )
            except ValueError:
                fill_time = datetime.utcnow()
            order_id = str(r.get("orderId") or "")
            # Dhan's /v2/trades may split one order into multiple legs.
            # The leg's unique ID lives in `exchangeTradeId` (or `tradeId` in
            # some envelopes); fall back to a (orderId,tradeTime,qty) synthetic
            # so the ledger PK never collides on partial fills.
            trade_id = (
                str(r.get("exchangeTradeId") or "")
                or str(r.get("tradeId") or "")
                or f"{order_id}:{r.get('tradeTime') or ''}:{r.get('tradedQuantity') or 0}"
            )
            out.append(
                Fill(
                    order_id=order_id,
                    ticker=(r.get("tradingSymbol") or "").upper(),
                    side=str(r.get("transactionType") or "").upper(),
                    quantity=int(r.get("tradedQuantity") or 0),
                    price=float(r.get("tradedPrice") or 0.0),
                    fill_time=fill_time,
                    commission=float(r.get("brokerage") or 0.0),
                    trade_id=trade_id,
                    raw=r,
                )
            )
        return out

    # ── polling loop ──

    def wait_for_done(
        self,
        order_id: str,
        *,
        timeout_sec: int = 120,
        poll_interval_sec: float = 2.0,
    ) -> OrderResponse:
        """Poll an order until it reaches a terminal state or timeout fires."""
        deadline = time.monotonic() + timeout_sec
        last: OrderResponse | None = None
        while time.monotonic() < deadline:
            last = self.get_order(order_id)
            if last.status in _TERMINAL_STATES:
                return last
            time.sleep(poll_interval_sec)
        if last is None:
            return OrderResponse(order_id=order_id, status="TIMEOUT", raw={})
        return last


__all__ = [
    "OrderRequest",
    "OrderResponse",
    "Fill",
    "Position",
    "DhanBroker",
    "ORDER_TYPE_MARKET",
    "ORDER_TYPE_LIMIT",
    "ORDER_TYPE_SL",
    "ORDER_TYPE_SLM",
    "PRODUCT_CNC",
    "EXCHANGE_NSE_EQ",
    "VALIDITY_DAY",
    "STATUS_PENDING",
    "STATUS_TRADED",
    "STATUS_REJECTED",
    "STATUS_CANCELLED",
    "fetch_scrip_master",
    "parse_scrip_master",
    "cache_scrip_master",
]
