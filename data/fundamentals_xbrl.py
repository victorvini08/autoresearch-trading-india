"""Parse a BSE result-filing XBRL document into raw financial facts.

Matching is by XML *local-name* (namespace-stripped) so the Mar-2025
"Integrated Filing" taxonomy change (new namespace, same element local
names) does not silently zero a field. Each logical field maps to an
ordered list of acceptable local-names; first present wins.

Also handles fetching the attachment bytes from BSE's public corp-filing
store, reusing the Referer/retry discipline from ``data.bse``.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime

import requests
from lxml import etree
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from data.bse import _HEADERS as _BSE_HEADERS

logger = logging.getLogger(__name__)

# Ordered local-name candidates per logical field (era-union).
_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": ("RevenueFromOperations", "Revenue", "TotalIncome"),
    "ebit": (
        "ProfitBeforeInterestAndTax",
        "OperatingProfit",
        "ProfitBeforeFinanceCostsAndTax",
    ),
    "pbt": ("ProfitBeforeTax", "ProfitLossBeforeTax"),
    "pat": (
        "ProfitLossForPeriod",
        "ProfitLossForThePeriod",
        "NetProfitLossForThePeriod",
    ),
    "eps_basic": ("BasicEarningsPerShare", "BasicEarningsLossPerShare"),
    "eps_diluted": ("DilutedEarningsPerShare", "DilutedEarningsLossPerShare"),
    "share_capital": (
        "EquityShareCapital",
        "PaidUpValueOfEquityShareCapital",
    ),
    "other_equity": ("OtherEquity", "ReservesAndSurplus"),
    "debt": ("Borrowings", "TotalBorrowings", "DebtSecurities"),
    "period_end": ("DateOfEndOfReportingPeriod", "DateOfEndOfFinancialYear"),
    "nature": (
        "NatureOfReportStandaloneConsolidated",
        "TypeOfResultStandaloneConsolidated",
    ),
}


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
    period_end_date: date | None
    is_consolidated: bool | None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _index(root) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        idx.setdefault(_local(el.tag), []).append((el.text or "").strip())
    return idx


def _num(idx: dict[str, list[str]], field: str) -> float | None:
    for name in _TAGS[field]:
        for raw in idx.get(name, []):
            if raw in ("", "-"):
                continue
            try:
                return float(raw.replace(",", ""))
            except ValueError:
                continue
    return None


def parse_xbrl_facts(xml_bytes: bytes) -> XbrlFacts | None:
    try:
        root = etree.fromstring(xml_bytes)  # noqa: S320 — trusted exchange feed
    except etree.XMLSyntaxError:
        return None
    idx = _index(root)
    revenue = _num(idx, "revenue")
    pat = _num(idx, "pat")
    if revenue is None and pat is None:
        return None  # not a financial-results document

    sc = _num(idx, "share_capital")
    oe = _num(idx, "other_equity")
    equity = None if sc is None and oe is None else (sc or 0.0) + (oe or 0.0)

    pe: date | None = None
    pe_candidates: list[str] = []
    for name in _TAGS["period_end"]:
        pe_candidates.extend(idx.get(name, []))
    for raw in pe_candidates:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                pe = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        if pe:
            break

    nature_vals: list[str] = []
    for name in _TAGS["nature"]:
        nature_vals.extend(idx.get(name, []))
    nature = " ".join(nature_vals).lower()
    is_cons = "consolidated" in nature if nature else None

    return XbrlFacts(
        revenue=revenue,
        ebit=_num(idx, "ebit"),
        pbt=_num(idx, "pbt"),
        pat=pat,
        eps_basic=_num(idx, "eps_basic"),
        eps_diluted=_num(idx, "eps_diluted"),
        equity=equity,
        debt=_num(idx, "debt"),
        period_end_date=pe,
        is_consolidated=is_cons,
    )


# ──────────────────────────────────────────────────────────────────────
# Attachment download (BSE corp-filing store)
# ──────────────────────────────────────────────────────────────────────

_ATTACH_LIVE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/{}"
_ATTACH_HIST = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/{}"


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=20),
    reraise=True,
)
def _get(url: str) -> bytes | None:
    resp = requests.get(url, headers=_BSE_HEADERS, timeout=45)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


def download_attachment(
    attachment_name: str, *, polite_delay_sec: float = 0.6
) -> bytes | None:
    """Live path first (recent filings), historical path as fallback."""
    name = (attachment_name or "").strip()
    if not name:
        return None
    for tmpl in (_ATTACH_LIVE, _ATTACH_HIST):
        try:
            data = _get(tmpl.format(name))
        except requests.RequestException as e:  # noqa: BLE001
            logger.warning("attachment %s failed: %s", name, e)
            data = None
        if data:
            return data
        if polite_delay_sec:
            time.sleep(polite_delay_sec)
    return None


__all__ = ["XbrlFacts", "parse_xbrl_facts", "download_attachment"]
