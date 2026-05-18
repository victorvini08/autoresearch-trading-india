"""Fetch + parse NSE quarterly-results XBRL into raw financial facts.

SOURCE (verified 2026-05-18 against live data): NSE's
``corporates-financial-results`` API returns, per symbol, a list of result
filings each carrying ``broadCastDate`` (the point-in-time availability
timestamp — a field, no parsing), ``toDate`` (period end), ``isin``,
``consolidated``, and a direct ``xbrl`` URL to the real XBRL document on
``nsearchives.nseindia.com``. We download that XBRL and extract the
*quarter* facts.

Earlier design fetched BSE announcement attachments — those are PDFs, not
XBRL (the pipeline produced 0 rows). This module is the corrected source.

XBRL context discipline (correctness-critical): a results XBRL contains
the standalone quarter (duration ~92d ending on period_end), the
cumulative YTD (duration ending on the same date but starting at FY
start), an instant context at period_end (balance items), and many
segment contexts. We read P&L facts ONLY from the non-segment duration
context whose endDate == period_end and whose length is ~one quarter, so
cumulative / prior-period / segment values can never leak in.

Real data limitation: NSE quarterly-results XBRL is P&L-centric. It
carries EPS / revenue / PBT / PAT (so SUE works), but NOT net worth or
borrowings — so roe_ttm / debt_to_equity / op_margin are usually None
from quarterly filings. ``debt_equity_ratio`` is read straight from the
filing's own pre-computed ``DebtEquityRatio`` element when present.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime

import requests
from lxml import etree

logger = logging.getLogger(__name__)

_NSE_HOME = "https://www.nseindia.com/"
_NSE_RESULTS_PAGE = (
    "https://www.nseindia.com/companies-listing/"
    "corporate-filings-financial-results"
)
_NSE_RESULTS_API = (
    "https://www.nseindia.com/api/corporates-financial-results"
    "?index=equities&symbol={symbol}&period=Quarterly"
)
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)

# Ordered local-name candidates per logical field (verified against real
# NSE IND-AS results XBRL, 2026-05-18).
_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": ("RevenueFromOperations", "Revenue", "Income"),
    "ebit": (
        "ProfitBeforeInterestAndTax",
        "ProfitBeforeFinanceCostsAndTax",
    ),
    "pbt": ("ProfitBeforeTax", "ProfitLossBeforeTax"),
    "pat": (
        "ProfitLossForPeriod",
        "ProfitLossForThePeriod",
        "NetProfitLossForThePeriod",
    ),
    "eps_basic": (
        "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
        "BasicEarningsLossPerShareFromContinuingOperations",
        "BasicEarningsPerShare",
    ),
    "eps_diluted": (
        "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
        "DilutedEarningsLossPerShareFromContinuingOperations",
        "DilutedEarningsPerShare",
    ),
    "net_worth": (
        "EquityAttributableToOwnersOfParent",
        "TotalEquity",
        "Equity",
    ),
    "share_capital": (
        "PaidUpValueOfEquityShareCapital",
        "EquityShareCapital",
    ),
    "other_equity": ("OtherEquity", "ReservesAndSurplus"),
    "debt": ("Borrowings", "TotalBorrowings"),
    "debt_equity_ratio": ("DebtEquityRatio",),
    "period_end": ("DateOfEndOfReportingPeriod",),
    "period_start": ("DateOfStartOfReportingPeriod",),
    "nature": ("NatureOfReportStandaloneConsolidated",),
}

_QUARTER_MIN_DAYS = 80
_QUARTER_MAX_DAYS = 100


@dataclass(frozen=True)
class XbrlFacts:
    revenue: float | None
    ebit: float | None
    pbt: float | None
    pat: float | None
    eps_basic: float | None
    eps_diluted: float | None
    equity: float | None
    debt: float | None
    debt_equity_ratio: float | None
    period_end_date: date | None
    is_consolidated: bool | None


@dataclass(frozen=True)
class NseResultRow:
    symbol: str
    isin: str
    period_end: date
    broadcast_date: date
    is_consolidated: bool | None
    xbrl_url: str


def _local(tag) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _to_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(s[: len(fmt) + 4], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s[:19]).date()
    except ValueError:
        return None


def _num(v: str) -> float | None:
    v = (v or "").strip()
    if v in ("", "-"):
        return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def _context_map(root) -> dict[str, tuple]:
    """contextRef -> (start, end, instant, has_segment)."""
    ctx: dict[str, tuple] = {}
    for el in root.iter():
        if _local(el.tag) != "context":
            continue
        cid = el.get("id")
        start = end = inst = None
        seg = False
        for c in el.iter():
            lc = _local(c.tag)
            if lc == "startDate":
                start = _to_date(c.text or "")
            elif lc == "endDate":
                end = _to_date(c.text or "")
            elif lc == "instant":
                inst = _to_date(c.text or "")
            elif lc in ("segment", "explicitMember", "scenario"):
                seg = True
        ctx[cid] = (start, end, inst, seg)
    return ctx


def _pick_quarter_ctx(ctx: dict[str, tuple], period_end: date) -> str | None:
    """Non-segment duration context, endDate == period_end, ~1 quarter long."""
    best: tuple[int, str] | None = None
    for cid, (s, e, _i, seg) in ctx.items():
        if seg or s is None or e is None or e != period_end:
            continue
        days = (e - s).days
        if _QUARTER_MIN_DAYS <= days <= _QUARTER_MAX_DAYS:
            return cid
        if best is None or days < best[0]:
            best = (days, cid)
    return best[1] if best else None


def _pick_instant_ctx(ctx: dict[str, tuple], period_end: date) -> str | None:
    for cid, (_s, _e, i, seg) in ctx.items():
        if not seg and i == period_end:
            return cid
    return None


def _facts_for_ctx(root, ctxref: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.get("contextRef") != ctxref:
            continue
        out.setdefault(_local(el.tag), []).append((el.text or "").strip())
    return out


def _first(idx: dict[str, list[str]], field: str) -> str | None:
    for name in _TAGS[field]:
        for raw in idx.get(name, []):
            if raw not in ("", "-"):
                return raw
    return None


def parse_xbrl_facts(
    xml_bytes: bytes, period_end: date | None = None
) -> XbrlFacts | None:
    """Parse the *quarter* facts. ``period_end`` (from the NSE row's
    ``toDate``) selects the correct context; if omitted it is read from
    the document and the shortest non-segment duration is used."""
    try:
        root = etree.fromstring(xml_bytes)  # noqa: S320 — trusted NSE feed
    except etree.XMLSyntaxError:
        return None

    ctx = _context_map(root)
    if not ctx:
        return None

    if period_end is None:
        # Discover period_end from any non-segment duration's endDate.
        ends = sorted(
            {e for (_s, e, _i, seg) in ctx.values() if e and not seg}
        )
        period_end = ends[-1] if ends else None
    if period_end is None:
        return None

    qctx = _pick_quarter_ctx(ctx, period_end)
    if qctx is None:
        return None
    q = _facts_for_ctx(root, qctx)

    rev = _num(_first(q, "revenue") or "")
    pat = _num(_first(q, "pat") or "")
    if rev is None and pat is None:
        return None  # not a results document / wrong context

    ictx = _pick_instant_ctx(ctx, period_end)
    inst = _facts_for_ctx(root, ictx) if ictx else {}

    nw = _num(_first(inst, "net_worth") or _first(q, "net_worth") or "")
    if nw is not None:
        equity = nw
    else:
        sc = _num(_first(inst, "share_capital") or _first(q, "share_capital") or "")
        oe = _num(_first(inst, "other_equity") or _first(q, "other_equity") or "")
        equity = None if sc is None and oe is None else (sc or 0.0) + (oe or 0.0)

    pe_raw = _first(q, "period_end")
    pe = _to_date(pe_raw) if pe_raw else period_end
    nature = (_first(q, "nature") or "").lower()
    is_cons = "consolidated" in nature if nature else None

    return XbrlFacts(
        revenue=rev,
        ebit=_num(_first(q, "ebit") or ""),
        pbt=_num(_first(q, "pbt") or ""),
        pat=pat,
        eps_basic=_num(_first(q, "eps_basic") or ""),
        eps_diluted=_num(_first(q, "eps_diluted") or ""),
        equity=equity,
        debt=_num(_first(inst, "debt") or _first(q, "debt") or ""),
        debt_equity_ratio=_num(_first(q, "debt_equity_ratio") or ""),
        period_end_date=pe,
        is_consolidated=is_cons,
    )


# ──────────────────────────────────────────────────────────────────────
# NSE fetch
# ──────────────────────────────────────────────────────────────────────


_THROTTLE_STATUSES = frozenset({401, 403, 429, 503})
_MAX_TRIES = 4


def _bootstrap(s: requests.Session) -> None:
    try:
        s.get(_NSE_HOME, timeout=15)
        s.get(_NSE_RESULTS_PAGE, timeout=15)
    except requests.RequestException as e:  # noqa: BLE001
        logger.warning("NSE cookie bootstrap failed: %s", e)


def _nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": _BROWSER_UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": _NSE_RESULTS_PAGE,
        }
    )
    _bootstrap(s)
    return s


def _robust_get(
    s: requests.Session,
    url: str,
    *,
    timeout: int,
    extra_headers: dict | None = None,
) -> requests.Response | None:
    """GET with throttle-aware retry. On a throttle status (NSE rate-limit
    via Akamai) re-bootstrap the SAME session and back off, instead of
    silently dropping the symbol (which would thin coverage). Returns the
    final response (caller checks status) or None on exhausted retries.
    """
    last: requests.Response | None = None
    for attempt in range(_MAX_TRIES):
        try:
            last = s.get(url, timeout=timeout, headers=extra_headers)
        except requests.RequestException as e:  # noqa: BLE001
            logger.warning("GET %s attempt %d err: %s", url, attempt, e)
            time.sleep(2 ** attempt)
            continue
        if last.status_code in _THROTTLE_STATUSES and attempt < _MAX_TRIES - 1:
            time.sleep(2 ** attempt + 1)
            _bootstrap(s)  # refresh cookies on the reused session
            continue
        return last
    return last


def fetch_nse_results(
    symbol: str, *, session: requests.Session | None = None
) -> list[NseResultRow]:
    """All quarterly result filings for `symbol` (point-in-time rows)."""
    s = session or _nse_session()
    r = _robust_get(s, _NSE_RESULTS_API.format(symbol=symbol), timeout=30)
    if r is None or r.status_code != 200:
        logger.warning(
            "NSE results fetch %s failed: status=%s",
            symbol,
            None if r is None else r.status_code,
        )
        return []
    try:
        rows = r.json()
    except ValueError as e:
        logger.warning("NSE results %s bad json: %s", symbol, e)
        return []
    if not isinstance(rows, list):
        rows = rows.get("data", []) if isinstance(rows, dict) else []
    out: list[NseResultRow] = []
    for row in rows:
        xurl = (row.get("xbrl") or "").strip()
        if not xurl.lower().endswith(".xml"):
            continue
        pe = _to_date(row.get("toDate") or "")
        bd = _to_date(row.get("broadCastDate") or row.get("filingDate") or "")
        if pe is None or bd is None:
            continue
        cons = (row.get("consolidated") or "").strip().lower()
        out.append(
            NseResultRow(
                symbol=symbol.upper(),
                isin=(row.get("isin") or "").strip().upper(),
                period_end=pe,
                broadcast_date=bd,
                is_consolidated=(
                    True
                    if cons == "consolidated"
                    else False
                    if cons in ("non-consolidated", "standalone")
                    else None
                ),
                xbrl_url=xurl,
            )
        )
    return out


def download_xbrl(
    url: str, *, session: requests.Session | None = None
) -> bytes | None:
    if not (url or "").strip():
        return None
    s = session or _nse_session()
    r = _robust_get(
        s,
        url,
        timeout=45,
        extra_headers={"User-Agent": _BROWSER_UA, "Referer": _NSE_HOME},
    )
    if r is None or r.status_code == 404:
        return None
    if r.status_code != 200:
        logger.warning("xbrl download %s status %s", url, r.status_code)
        return None
    return r.content


__all__ = [
    "XbrlFacts",
    "NseResultRow",
    "parse_xbrl_facts",
    "fetch_nse_results",
    "download_xbrl",
]
