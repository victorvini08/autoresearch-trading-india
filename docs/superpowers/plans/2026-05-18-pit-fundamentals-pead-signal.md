# PIT fundamentals + PEAD signal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a point-in-time-clean Indian-equity fundamentals + earnings-surprise pipeline and wire a quality-conditioned, asymmetric PEAD suppression gate into `strategy.py`.

**Architecture:** BSE XBRL result filings (broadcast-timestamped, as-reported) backfill `storage/fundamentals.duckdb`; SUE is derived from that as-reported EPS via a seasonal-random-walk expectation; a pure PIT accessor exposes it; `strategy.py` uses it only to *suppress* (block-entry / sever-held) momentum-qualified names with a quality-conditioned negative surprise inside the ~60-trading-day drift window. Phase B (positive tilt) is explicitly out of scope until Phase A clears forward `dhan-paper`.

**Tech Stack:** Python 3, DuckDB, `requests` + `tenacity` (existing `data/bse.py` pattern), `lxml` for XBRL, `backtrader` strategy, `pytest`, `uv`.

**Spec:** `docs/superpowers/specs/2026-05-18-pit-fundamentals-pead-signal-design.md`

**Out of scope (do not implement):** Phase B positive tilt (spec §5.3); quality-screen as integration mechanism; consensus-estimate SUE; live daily XBRL parsing (live uses self-timestamped snapshot, Task 10).

---

## File structure

| File | New/Mod | Responsibility |
|---|---|---|
| `data/fundamentals_xbrl.py` | New | Pure: download a BSE result attachment, parse XBRL bytes → raw financial facts (era-pinned tag map). No DB, no network policy. |
| `data/ingest_fundamentals.py` | New | Orchestration: PIT-universe iteration → BSE scrip resolve → fetch result announcements → parse → derive TTM ratios → write `fundamentals_quarterly` with `as_of_date = broadcast date`; PIT sanity-band quarantine; coverage/lag report; live snapshot. |
| `data/pead.py` | New | SUE math (seasonal random walk) + theory-pinned constants + `pead_signal()` PIT accessor with quality conditioner + soft-degrade. |
| `data/ingest_earnings.py` | Mod | Add SUE columns to `earnings_calendar`; `compute_sue_from_fundamentals()`. |
| `strategy.py` | Mod | Plumbing params (`earnings_db_path`, `fundamentals_db_path`, `enable_pead`) + asymmetric suppression in `next()`. |
| `scripts/daily_update.py` | Mod | Live source-split: self-timestamped fundamentals snapshot step. |
| `tests/test_fundamentals_xbrl.py` | New | XBRL parse, both schema eras. |
| `tests/test_ingest_fundamentals.py` | New | Orchestration + ratio derivation + quarantine. |
| `tests/test_pead_signal.py` | New | SUE math + accessor + quality conditioner + soft-degrade. |
| `tests/test_pead_lookahead.py` | New | **Hard gate** look-ahead tripwire. |
| `tests/test_strategy_pead_gate.py` | New | Strategy suppression behavior + parsimony-count unchanged. |

**Theory-pinned constants live in `data/pead.py` as module constants, NOT `strategy.params`** — so `prepare.count_hyperparameters` stays unchanged (verified in Task 8). This is the codebase convention for theory-pinned values (cf. `strategy._structural_ma_window`).

---

### Task 1: XBRL fact parser (era-pinned)

**Goal:** Pure function turning a BSE result-filing XBRL document into a typed raw-facts record, handling both the pre-Mar-2025 results taxonomy and the Mar-2025+ "Integrated Filing" taxonomy.

**Files:**
- Create: `data/fundamentals_xbrl.py`
- Test: `tests/test_fundamentals_xbrl.py`

**Acceptance Criteria:**
- [ ] `parse_xbrl_facts(xml_bytes: bytes) -> XbrlFacts | None` extracts revenue, EBIT/operating profit, PBT, PAT, basic & diluted EPS, total equity/net worth, total borrowings, shares, period-end, consolidated flag.
- [ ] Element matching is by XML **local-name** (namespace-agnostic) against a documented tag map, so a namespace/era change does not silently zero a field.
- [ ] Returns `None` (never raises) on malformed/empty/non-financial XML.
- [ ] Both era fixtures parse to the same `XbrlFacts` shape.

**Verify:** `uv run pytest tests/test_fundamentals_xbrl.py -q` → all pass

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fundamentals_xbrl.py
"""Unit tests for data.fundamentals_xbrl."""
from __future__ import annotations

from data.fundamentals_xbrl import XbrlFacts, parse_xbrl_facts

# Minimal synthetic XBRL — pre-Mar-2025 results taxonomy (in-bse-fin namespace).
_OLD_ERA = b"""<?xml version="1.0"?>
<xbrl xmlns:inbse="http://www.bseindia.com/xbrl/fin/2016-03-31/in-bse-fin">
  <inbse:RevenueFromOperations contextRef="C">5000000</inbse:RevenueFromOperations>
  <inbse:ProfitBeforeTax contextRef="C">900000</inbse:ProfitBeforeTax>
  <inbse:ProfitLossForPeriod contextRef="C">650000</inbse:ProfitLossForPeriod>
  <inbse:ProfitBeforeInterestAndTax contextRef="C">1100000</inbse:ProfitBeforeInterestAndTax>
  <inbse:BasicEarningsPerShare contextRef="C">12.5</inbse:BasicEarningsPerShare>
  <inbse:DilutedEarningsPerShare contextRef="C">12.1</inbse:DilutedEarningsPerShare>
  <inbse:EquityShareCapital contextRef="C">100000</inbse:EquityShareCapital>
  <inbse:OtherEquity contextRef="C">4000000</inbse:OtherEquity>
  <inbse:Borrowings contextRef="C">2000000</inbse:Borrowings>
  <inbse:PaidUpEquityShareCapital contextRef="C">52000</inbse:PaidUpEquityShareCapital>
  <inbse:DateOfEndOfReportingPeriod contextRef="C">2024-12-31</inbse:DateOfEndOfReportingPeriod>
  <inbse:NatureOfReportStandaloneConsolidated contextRef="C">Consolidated</inbse:NatureOfReportStandaloneConsolidated>
</xbrl>"""

# Mar-2025+ Integrated Filing taxonomy: different namespace, same local-names
# plus the integrated-filing variants.
_NEW_ERA = _OLD_ERA.replace(
    b"in-bse-fin/2016-03-31/in-bse-fin",
    b"in-capmkt/2024-09-30/in-capmkt",
)


def test_parses_old_era() -> None:
    f = parse_xbrl_facts(_OLD_ERA)
    assert f is not None
    assert f.revenue == 5_000_000.0
    assert f.pat == 650_000.0
    assert f.ebit == 1_100_000.0
    assert f.eps_basic == 12.5
    assert f.eps_diluted == 12.1
    assert f.equity == 4_100_000.0  # EquityShareCapital + OtherEquity
    assert f.debt == 2_000_000.0
    assert f.is_consolidated is True
    assert f.period_end_date.isoformat() == "2024-12-31"


def test_parses_new_era_same_shape() -> None:
    f = parse_xbrl_facts(_NEW_ERA)
    assert f is not None
    assert f.revenue == 5_000_000.0
    assert f.pat == 650_000.0


def test_malformed_returns_none() -> None:
    assert parse_xbrl_facts(b"not xml") is None
    assert parse_xbrl_facts(b"<xbrl></xbrl>") is None  # no financial facts
```

- [ ] **Step 2: Run test, expect failure**

Run: `uv run pytest tests/test_fundamentals_xbrl.py -q`
Expected: FAIL — `ModuleNotFoundError: data.fundamentals_xbrl`

- [ ] **Step 3: Implement**

```python
# data/fundamentals_xbrl.py
"""Parse a BSE result-filing XBRL document into raw financial facts.

Matching is by XML *local-name* (namespace-stripped) so the Mar-2025
"Integrated Filing" taxonomy change (new namespace, same element local
names) does not silently zero a field. Each logical field maps to an
ordered list of acceptable local-names; first present wins.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from lxml import etree

logger = logging.getLogger(__name__)

# Ordered local-name candidates per logical field (era-union).
_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": ("RevenueFromOperations", "Revenue", "TotalIncome"),
    "ebit": ("ProfitBeforeInterestAndTax", "OperatingProfit",
             "ProfitBeforeFinanceCostsAndTax"),
    "pbt": ("ProfitBeforeTax", "ProfitLossBeforeTax"),
    "pat": ("ProfitLossForPeriod", "ProfitLossForThePeriod",
            "NetProfitLossForThePeriod"),
    "eps_basic": ("BasicEarningsPerShare", "BasicEarningsLossPerShare"),
    "eps_diluted": ("DilutedEarningsPerShare", "DilutedEarningsLossPerShare"),
    "share_capital": ("EquityShareCapital", "PaidUpValueOfEquityShareCapital"),
    "other_equity": ("OtherEquity", "ReservesAndSurplus"),
    "debt": ("Borrowings", "TotalBorrowings", "DebtSecurities"),
    "period_end": ("DateOfEndOfReportingPeriod",
                   "DateOfEndOfFinancialYear"),
    "nature": ("NatureOfReportStandaloneConsolidated",
               "TypeOfResultStandaloneConsolidated"),
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
        idx.setdefault(_local(el.tag), []).append(
            (el.text or "").strip()
        )
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

    pe = None
    for raw in idx.get(_TAGS["period_end"][0], []) + idx.get(
        _TAGS["period_end"][1], []
    ):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                pe = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        if pe:
            break

    nature = " ".join(
        idx.get(_TAGS["nature"][0], []) + idx.get(_TAGS["nature"][1], [])
    ).lower()
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


__all__ = ["XbrlFacts", "parse_xbrl_facts"]
```

- [ ] **Step 4: Run test, expect pass**

Run: `uv run pytest tests/test_fundamentals_xbrl.py -q` → PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add data/fundamentals_xbrl.py tests/test_fundamentals_xbrl.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: XBRL fact parser (era-pinned, local-name match)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: BSE attachment download

**Goal:** Fetch a result filing's XBRL attachment bytes from BSE, reusing the existing `data/bse.py` header/retry discipline.

**Files:**
- Modify: `data/fundamentals_xbrl.py` (add `download_attachment`)
- Test: `tests/test_fundamentals_xbrl.py` (add cases)

**Acceptance Criteria:**
- [ ] `download_attachment(attachment_name: str, *, polite_delay_sec=0.6) -> bytes | None` tries the live then historical BSE attachment path.
- [ ] Uses the `data.bse._HEADERS` (Referer) and a `tenacity` exponential retry identical in policy to `data.bse._fetch_ann_page`.
- [ ] Empty `attachment_name` → `None` (no request).

**Verify:** `uv run pytest tests/test_fundamentals_xbrl.py -q` → all pass

**Steps:**

- [ ] **Step 1: Add failing test**

```python
# append to tests/test_fundamentals_xbrl.py
import data.fundamentals_xbrl as fx


def test_download_attachment_empty_is_none() -> None:
    assert fx.download_attachment("") is None


def test_download_attachment_uses_live_then_hist(monkeypatch) -> None:
    calls: list[str] = []

    class _Resp:
        status_code = 200
        content = b"<xbrl/>"

        def raise_for_status(self) -> None:  # noqa: D401
            ...

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return _Resp()

    monkeypatch.setattr(fx.requests, "get", fake_get)
    out = fx.download_attachment("ABC123.xml", polite_delay_sec=0.0)
    assert out == b"<xbrl/>"
    assert calls and "AttachLive" in calls[0]
```

- [ ] **Step 2: Run, expect FAIL** (`download_attachment` undefined)

Run: `uv run pytest tests/test_fundamentals_xbrl.py -q`

- [ ] **Step 3: Implement (append to `data/fundamentals_xbrl.py`)**

```python
import time

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from data.bse import _HEADERS as _BSE_HEADERS

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
        time.sleep(polite_delay_sec)
    return None
```

Add `download_attachment` to `__all__`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_fundamentals_xbrl.py -q`

- [ ] **Step 5: Commit**

```bash
git add data/fundamentals_xbrl.py tests/test_fundamentals_xbrl.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: BSE result-attachment download (live→hist, retry)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: TTM ratio derivation (pure)

**Goal:** Pure function deriving `roe_ttm`, `debt_to_equity`, `op_margin_ttm` from the last ≤4 as-reported quarters, each known as-of its broadcast date.

**Files:**
- Create: `data/ingest_fundamentals.py`
- Test: `tests/test_ingest_fundamentals.py`

**Acceptance Criteria:**
- [ ] `derive_ttm(quarters: list[QuarterFacts]) -> DerivedRatios` where `quarters` is ascending by `period_end`, length 1–4.
- [ ] `op_margin_ttm = sum(ebit_4q) / sum(revenue_4q)`; `roe_ttm = sum(pat_4q) / equity_latest`; `debt_to_equity = debt_latest / equity_latest`.
- [ ] Any required input `None`/`equity<=0` → that ratio is `None` (never raises, never 0-fills).

**Verify:** `uv run pytest tests/test_ingest_fundamentals.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test**

```python
# tests/test_ingest_fundamentals.py
from __future__ import annotations

from datetime import date

from data.fundamentals_xbrl import XbrlFacts
from data.ingest_fundamentals import QuarterFacts, derive_ttm


def _q(pe: str, rev, ebit, pat, eq, debt) -> QuarterFacts:
    return QuarterFacts(
        ticker="X",
        period_end=date.fromisoformat(pe),
        broadcast_date=date.fromisoformat(pe),  # not used by derive_ttm
        facts=XbrlFacts(rev, ebit, None, pat, None, None, eq, debt,
                        date.fromisoformat(pe), True),
    )


def test_ttm_ratios() -> None:
    qs = [
        _q("2024-03-31", 100, 20, 10, 500, 250),
        _q("2024-06-30", 110, 22, 11, 510, 250),
        _q("2024-09-30", 120, 24, 12, 520, 260),
        _q("2024-12-31", 130, 26, 13, 540, 270),
    ]
    r = derive_ttm(qs)
    assert round(r.op_margin_ttm, 4) == round(92 / 460, 4)
    assert round(r.roe_ttm, 4) == round(46 / 540, 4)
    assert round(r.debt_to_equity, 4) == round(270 / 540, 4)


def test_ttm_missing_inputs_yield_none() -> None:
    qs = [_q("2024-12-31", None, None, 13, 0, 270)]
    r = derive_ttm(qs)
    assert r.op_margin_ttm is None
    assert r.roe_ttm is None  # equity 0
    assert r.debt_to_equity is None
```

- [ ] **Step 2: Run, expect FAIL**

Run: `uv run pytest tests/test_ingest_fundamentals.py -q`

- [ ] **Step 3: Implement (start `data/ingest_fundamentals.py`)**

```python
# data/ingest_fundamentals.py
"""PIT-clean fundamentals pipeline → storage/fundamentals.duckdb.

as_of_date is ALWAYS the filing broadcast date (when the market learned
the number), never the period-end. See spec §3, §4.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from data.fundamentals_xbrl import XbrlFacts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuarterFacts:
    ticker: str
    period_end: date
    broadcast_date: date
    facts: XbrlFacts


@dataclass(frozen=True)
class DerivedRatios:
    roe_ttm: float | None
    debt_to_equity: float | None
    op_margin_ttm: float | None


def _sum(vals: list[float | None]) -> float | None:
    present = [v for v in vals if v is not None]
    return sum(present) if len(present) == len(vals) and vals else None


def derive_ttm(quarters: list[QuarterFacts]) -> DerivedRatios:
    """quarters ascending by period_end, length 1..4 (the trailing window)."""
    qs = sorted(quarters, key=lambda q: q.period_end)[-4:]
    latest = qs[-1].facts
    rev = _sum([q.facts.revenue for q in qs])
    ebit = _sum([q.facts.ebit for q in qs])
    pat = _sum([q.facts.pat for q in qs])
    eq = latest.equity
    debt = latest.debt

    op_margin = (ebit / rev) if (ebit is not None and rev not in (None, 0)) else None
    roe = (pat / eq) if (pat is not None and eq not in (None, 0) and eq > 0) else None
    de = (debt / eq) if (debt is not None and eq not in (None, 0) and eq > 0) else None
    return DerivedRatios(roe_ttm=roe, debt_to_equity=de, op_margin_ttm=op_margin)


__all__ = ["QuarterFacts", "DerivedRatios", "derive_ttm"]
```

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_ingest_fundamentals.py -q`

- [ ] **Step 5: Commit**

```bash
git add data/ingest_fundamentals.py tests/test_ingest_fundamentals.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: TTM ratio derivation (PIT, none-safe)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Fundamentals orchestration + schema + PIT quarantine

**Goal:** `ingest_fundamentals(...)` walks the PIT universe, resolves BSE scrip via ISIN, fetches result announcements, parses XBRL, derives TTM ratios, and writes `fundamentals_quarterly` with `as_of_date = broadcast date`, quarantining rows outside the PIT sanity band.

**Files:**
- Modify: `data/ingest_fundamentals.py`
- Test: `tests/test_ingest_fundamentals.py`

**Acceptance Criteria:**
- [ ] Schema matches `data/quality_screen.py`'s expectation (`fundamentals_quarterly(ticker, as_of_date, roe_ttm, debt_to_equity, op_margin_ttm, is_financial, ...)` superset) — `test_quality_screen.py` still passes against a populated DB.
- [ ] `as_of_date` = broadcast date; missing broadcast → `period_end + 45d` (Q1–Q3) / `+60d` (Q4 = Mar-31).
- [ ] Rows where `not (period_end <= as_of_date <= period_end + 75d)` are quarantined (logged, not written to `fundamentals_quarterly`).
- [ ] PIT universe iterated via `data.universe.snapshot_dates` + `load_universe` (ISIN per row); no survivor-only fetch.
- [ ] Idempotent: PK `(ticker, period_end_date)`; re-run does not duplicate.

**Verify:** `uv run pytest tests/test_ingest_fundamentals.py tests/test_quality_screen.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test (monkeypatched BSE + XBRL)**

```python
# append to tests/test_ingest_fundamentals.py
from pathlib import Path

import duckdb

import data.ingest_fundamentals as ingf
from data.quality_screen import load_fundamentals


def test_ingest_writes_pit_rows_and_quarantines(tmp_path, monkeypatch) -> None:
    fdb = tmp_path / "fundamentals.duckdb"

    # Universe: one name 'ACME' isin 'IN0ACME' present at one snapshot.
    monkeypatch.setattr(ingf, "_pit_universe",
                         lambda *_: {"ACME": "IN0ACME"})
    monkeypatch.setattr(ingf, "_scrip_for_isin", lambda *_: "500001")

    # Two filings: one valid (broadcast 45d after Q-end), one look-ahead-bad.
    from data.fundamentals_xbrl import XbrlFacts
    good = XbrlFacts(100, 20, 18, 12, 5.0, 4.9, 600, 300,
                     date(2024, 12, 31), True)
    monkeypatch.setattr(
        ingf, "_fetch_result_filings",
        lambda scrip, sym, s, e: [
            ingf.RawFiling("ACME", date(2025, 2, 12),
                           date(2024, 12, 31), good),
            ingf.RawFiling("ACME", date(2024, 1, 1),       # before period_end
                           date(2024, 12, 31), good),
        ],
    )
    monkeypatch.setattr(ingf, "_is_financial", lambda *_: False)

    n = ingf.ingest_fundamentals(
        universe_db=Path("ignored"), fundamentals_db=fdb,
        start=date(2024, 1, 1), end=date(2025, 6, 30),
    )
    assert n == 1  # the look-ahead row quarantined

    rows = load_fundamentals(fdb, ["ACME"], date(2025, 3, 1))
    assert "ACME" in rows
    assert rows["ACME"].as_of_date == date(2025, 2, 12)  # broadcast, not Q-end
    # Not visible before broadcast:
    assert load_fundamentals(fdb, ["ACME"], date(2025, 1, 1)) == {}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `uv run pytest tests/test_ingest_fundamentals.py -q`

- [ ] **Step 3: Implement (append to `data/ingest_fundamentals.py`)**

```python
from datetime import timedelta
from pathlib import Path

import duckdb

from data.bse import build_scrip_map, fetch_bse_announcements, resolve_scrip_code
from data.fundamentals_xbrl import download_attachment, parse_xbrl_facts
from data.sectors import assign_sectors
from data.universe import load_universe, snapshot_dates

DEFAULT_FUNDAMENTALS_DB = Path("storage/fundamentals.duckdb")
_RESULT_SUBJECT = "financial result"
_PIT_BAND_DAYS = 75


@dataclass(frozen=True)
class RawFiling:
    ticker: str
    broadcast_date: date | None
    period_end: date
    facts: XbrlFacts


def _sebi_fallback(period_end: date) -> date:
    # Q4 (FY end = Mar 31): +60d; else +45d.
    days = 60 if (period_end.month == 3 and period_end.day == 31) else 45
    return period_end + timedelta(days=days)


def _pit_universe(universe_db: Path, start: date, end: date) -> dict[str, str]:
    """Union of {ticker: isin} across every PIT snapshot in [start,end]."""
    out: dict[str, str] = {}
    for snap in snapshot_dates(universe_db):
        if snap < start or snap > end:
            continue
        for row in load_universe(universe_db, snap):
            if row.ticker not in out:
                out[row.ticker] = row.isin
    return out


def _scrip_for_isin(scrip_map: dict, isin: str, sym: str) -> str | None:
    return resolve_scrip_code(scrip_map, isin=isin, nse_symbol=sym)


def _is_financial(ticker: str, industry: str) -> bool:
    sa = assign_sectors([type("R", (), {"ticker": ticker,
                                         "industry": industry})()])
    return ticker in sa and sa[ticker].sector == "FINANCIAL_SERVICES"


def _fetch_result_filings(
    scrip: str, sym: str, start: date, end: date
) -> list[RawFiling]:
    anns = fetch_bse_announcements(scrip, start, end, nse_symbol=sym)
    out: list[RawFiling] = []
    for a in anns:
        if _RESULT_SUBJECT not in (a.subject or "").lower():
            continue
        blob = download_attachment(a.attachment)
        if not blob:
            continue
        facts = parse_xbrl_facts(blob)
        if facts is None or facts.period_end_date is None:
            continue
        out.append(RawFiling(sym, a.dt, facts.period_end_date, facts))
    return out


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
            ticker VARCHAR NOT NULL,
            period_end_date DATE NOT NULL,
            as_of_date DATE NOT NULL,
            broadcast_date DATE,
            roe_ttm DOUBLE, debt_to_equity DOUBLE, op_margin_ttm DOUBLE,
            is_financial BOOLEAN,
            eps_basic DOUBLE, eps_diluted DOUBLE,
            revenue DOUBLE, ebit DOUBLE, pat DOUBLE,
            equity DOUBLE, debt DOUBLE,
            is_consolidated BOOLEAN, source VARCHAR DEFAULT 'bse_xbrl',
            PRIMARY KEY (ticker, period_end_date)
        )
        """
    )


def ingest_fundamentals(
    universe_db: Path,
    fundamentals_db: Path = DEFAULT_FUNDAMENTALS_DB,
    *,
    start: date,
    end: date,
) -> int:
    """Backfill fundamentals_quarterly over the PIT universe. Returns rows written."""
    uni = _pit_universe(universe_db, start, end)
    scrip_map = build_scrip_map()
    written = 0
    fundamentals_db.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(fundamentals_db))
    try:
        _ensure_schema(conn)
        for sym, isin in uni.items():
            scrip = _scrip_for_isin(scrip_map, isin, sym)
            if not scrip:
                logger.warning("no BSE scrip for %s/%s", sym, isin)
                continue
            filings = sorted(
                _fetch_result_filings(scrip, sym, start, end),
                key=lambda f: f.period_end,
            )
            history: list[QuarterFacts] = []
            for f in filings:
                aod = f.broadcast_date or _sebi_fallback(f.period_end)
                if not (f.period_end <= aod
                        <= f.period_end + timedelta(days=_PIT_BAND_DAYS)):
                    logger.warning(
                        "QUARANTINE %s %s: as_of %s outside PIT band",
                        sym, f.period_end, aod,
                    )
                    continue
                history.append(QuarterFacts(sym, f.period_end, aod, f.facts))
                ratios = derive_ttm(history)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fundamentals_quarterly VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'bse_xbrl')
                    """,
                    (sym, f.period_end, aod, f.broadcast_date,
                     ratios.roe_ttm, ratios.debt_to_equity,
                     ratios.op_margin_ttm, _is_financial(sym, ""),
                     f.facts.eps_basic, f.facts.eps_diluted,
                     f.facts.revenue, f.facts.ebit, f.facts.pat,
                     f.facts.equity, f.facts.debt, f.facts.is_consolidated),
                )
                written += 1
    finally:
        conn.close()
    logger.info("fundamentals: wrote %d rows for %d names", written, len(uni))
    return written
```

Extend `__all__` with `RawFiling`, `ingest_fundamentals`, `DEFAULT_FUNDAMENTALS_DB`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_ingest_fundamentals.py tests/test_quality_screen.py -q`

- [ ] **Step 5: Commit**

```bash
git add data/ingest_fundamentals.py tests/test_ingest_fundamentals.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: fundamentals orchestration + PIT quarantine + schema

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Look-ahead tripwire (HARD GATE)

**Goal:** A test asserting that, building the signal as-of any date D, no row with `period_end > D` is ever visible — the firewall that blocks strategy use until green.

**Files:**
- Create: `tests/test_pead_lookahead.py`
- Modify: `data/ingest_fundamentals.py` (add `assert_no_lookahead`)

**Acceptance Criteria:**
- [ ] `assert_no_lookahead(fundamentals_db)` raises `LookaheadError` if any row has `as_of_date < period_end_date` OR `as_of_date > period_end_date + 75d`.
- [ ] Test builds a DB with a deliberately leaked row and asserts the tripwire fires; and a clean DB passes.

**Verify:** `uv run pytest tests/test_pead_lookahead.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test**

```python
# tests/test_pead_lookahead.py
from __future__ import annotations

from datetime import date

import duckdb
import pytest

from data.ingest_fundamentals import LookaheadError, assert_no_lookahead


def _db(tmp_path, rows):
    p = tmp_path / "f.duckdb"
    c = duckdb.connect(str(p))
    c.execute("CREATE TABLE fundamentals_quarterly "
              "(ticker VARCHAR, period_end_date DATE, as_of_date DATE)")
    for t, pe, ao in rows:
        c.execute("INSERT INTO fundamentals_quarterly VALUES (?,?,?)",
                  (t, pe, ao))
    c.close()
    return p


def test_clean_db_passes(tmp_path) -> None:
    p = _db(tmp_path, [("A", date(2024, 12, 31), date(2025, 2, 10))])
    assert_no_lookahead(p)  # no raise


def test_leaked_row_trips(tmp_path) -> None:
    p = _db(tmp_path, [("A", date(2024, 12, 31), date(2024, 6, 1))])
    with pytest.raises(LookaheadError):
        assert_no_lookahead(p)
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement (append to `data/ingest_fundamentals.py`)**

```python
class LookaheadError(RuntimeError):
    """Raised when fundamentals_quarterly contains a look-ahead row."""


def assert_no_lookahead(fundamentals_db: Path) -> None:
    conn = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        bad = conn.execute(
            f"""
            SELECT ticker, period_end_date, as_of_date
              FROM fundamentals_quarterly
             WHERE as_of_date < period_end_date
                OR as_of_date > period_end_date + INTERVAL {_PIT_BAND_DAYS} DAY
            """
        ).fetchall()
    finally:
        conn.close()
    if bad:
        raise LookaheadError(f"{len(bad)} look-ahead rows, e.g. {bad[:3]}")
```

Add `LookaheadError`, `assert_no_lookahead` to `__all__`.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add data/ingest_fundamentals.py tests/test_pead_lookahead.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: look-ahead tripwire (hard gate)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: SUE from as-reported EPS (extend `data/ingest_earnings.py`)

**Goal:** Add `sue`/`surprise_eps`/`expectation_basis` columns and `compute_sue_from_fundamentals()` using a seasonal random walk on as-reported EPS, all inputs as-of broadcast date.

**Files:**
- Modify: `data/ingest_earnings.py`
- Test: `tests/test_pead_signal.py` (SUE-math section)

**Acceptance Criteria:**
- [ ] `compute_sue_from_fundamentals(fundamentals_db, earnings_db)` writes `sue` per `(ticker, announcement_date)` where `announcement_date` = the fundamentals `as_of_date` (broadcast).
- [ ] `E[EPS_q] = EPS_{q-4}` (same quarter prior year); `unexpected = EPS_q − E[EPS_q]`; standardized by std of the last 8 seasonal forecast errors (need ≥ 6 prior errors else `sue=None`).
- [ ] Existing yfinance `surprise_pct` retained but never used as signal (provenance only). `test_ingest_earnings_yf.py` still passes.

**Verify:** `uv run pytest tests/test_pead_signal.py tests/test_ingest_earnings_yf.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test**

```python
# tests/test_pead_signal.py
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from data.ingest_earnings import compute_sue_from_fundamentals


def _seed_fundamentals(p: Path, eps_series: list[tuple[str, str, float]]):
    c = duckdb.connect(str(p))
    c.execute("CREATE TABLE fundamentals_quarterly "
              "(ticker VARCHAR, period_end_date DATE, as_of_date DATE, "
              " eps_basic DOUBLE)")
    for pe, ao, eps in eps_series:
        c.execute("INSERT INTO fundamentals_quarterly "
                  "(ticker, period_end_date, as_of_date, eps_basic) "
                  "VALUES ('Z', ?, ?, ?)", (pe, ao, eps))
    c.close()


def test_sue_seasonal_random_walk(tmp_path) -> None:
    fdb = tmp_path / "f.duckdb"
    edb = tmp_path / "e.duckdb"
    # 9 quarters so the latest has 4 seasonal pairs of errors available.
    rows = []
    for i, eps in enumerate([5, 6, 4, 7, 6, 7, 5, 9, 14]):
        pe = date(2023, 3, 31)
        # rough quarterly stride
        y = 2023 + (i // 4)
        m = [3, 6, 9, 12][i % 4]
        rows.append((f"{y}-{m:02d}-28", f"{y}-{m:02d}-28", float(eps)))
    _seed_fundamentals(fdb, rows)
    n = compute_sue_from_fundamentals(fdb, edb)
    assert n >= 1
    c = duckdb.connect(str(edb), read_only=True)
    sue = c.execute("SELECT sue FROM earnings_calendar "
                     "WHERE ticker='Z' ORDER BY announcement_date DESC "
                     "LIMIT 1").fetchone()[0]
    c.close()
    assert sue is not None and sue > 0  # 14 vs prior-year 7 → positive surprise
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement (append to `data/ingest_earnings.py`)**

```python
import statistics
from pathlib import Path as _Path

import duckdb as _ddb


def compute_sue_from_fundamentals(
    fundamentals_db: _Path, earnings_db: _Path
) -> int:
    """SUE via seasonal random walk on as-reported EPS (PIT)."""
    fc = _ddb.connect(str(fundamentals_db), read_only=True)
    try:
        rows = fc.execute(
            "SELECT ticker, period_end_date, as_of_date, eps_basic "
            "FROM fundamentals_quarterly "
            "WHERE eps_basic IS NOT NULL ORDER BY ticker, period_end_date"
        ).fetchall()
    finally:
        fc.close()

    by_t: dict[str, list[tuple]] = {}
    for t, pe, ao, eps in rows:
        by_t.setdefault(t, []).append((pe, ao, float(eps)))

    out: list[tuple] = []
    for t, series in by_t.items():
        for i in range(4, len(series)):
            pe, ao, eps = series[i]
            exp = series[i - 4][2]                     # EPS same quarter, prior year
            unexpected = eps - exp
            errs = [
                series[j][2] - series[j - 4][2]
                for j in range(4, i)                   # strictly prior errors
            ]
            if len(errs) < 6:
                continue
            sd = statistics.pstdev(errs)
            sue = unexpected / sd if sd > 0 else None
            out.append((t, ao, unexpected, sue, "seasonal_rw"))

    if not out:
        return 0
    conn = _ddb.connect(str(earnings_db))
    try:
        _ensure_schema(conn)
        for col in ("sue", "surprise_eps", "expectation_basis"):
            conn.execute(
                f"ALTER TABLE earnings_calendar ADD COLUMN IF NOT EXISTS "
                f"{col} {'VARCHAR' if col == 'expectation_basis' else 'DOUBLE'}"
            )
        for t, ao, ue, sue, basis in out:
            conn.execute(
                """
                INSERT INTO earnings_calendar
                    (ticker, announcement_date, title, source,
                     surprise_eps, sue, expectation_basis)
                VALUES (?, ?, 'SUE (computed)', 'fundamentals_sue', ?, ?, ?)
                ON CONFLICT (ticker, announcement_date) DO UPDATE SET
                    surprise_eps=excluded.surprise_eps,
                    sue=excluded.sue,
                    expectation_basis=excluded.expectation_basis
                """,
                (t, ao, ue, sue, basis),
            )
    finally:
        conn.close()
    return len(out)
```

Add `compute_sue_from_fundamentals` to `__all__`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_pead_signal.py tests/test_ingest_earnings_yf.py -q`

- [ ] **Step 5: Commit**

```bash
git add data/ingest_earnings.py tests/test_pead_signal.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: SUE from as-reported EPS (seasonal RW, PIT)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: PEAD PIT accessor + quality conditioner

**Goal:** `data/pead.py` exposing theory-pinned constants and `pead_signal(ticker, today, ...)` that returns the quality-conditioned suppression verdict using only data with `as_of_date <= today`.

**Files:**
- Create: `data/pead.py`
- Test: `tests/test_pead_signal.py` (accessor section)

**Acceptance Criteria:**
- [ ] Module constants `DRIFT_WINDOW_TD=60`, `SUE_BLOCK=1.0`, `SUE_SEVERE=2.0` (theory-pinned; documented as not window-tuned).
- [ ] `pead_signal(ticker, today, *, earnings_db, fundamentals_db) -> dict | None`: reads the most recent `earnings_calendar` row with `announcement_date <= today` within `DRIFT_WINDOW_TD` *calendar-approx* (≤ 90 days) ; `None` when no row (soft-degrade).
- [ ] Returns `{'sue', 'days_since', 'block': bool, 'sever': bool}`. `block` true iff `sue <= -effective_cut`; `effective_cut` = `SUE_BLOCK` tightened to `0.5` when the name fails the reused `quality_screen` ROE/D-E/op-margin test, loosened to `1.5` when it strongly passes. `sever` true iff `sue <= -SUE_SEVERE`.
- [ ] Missing fundamentals → no quality adjustment (use base `SUE_BLOCK`), never errors.

**Verify:** `uv run pytest tests/test_pead_signal.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test (append)**

```python
# append to tests/test_pead_signal.py
from data.pead import DRIFT_WINDOW_TD, pead_signal


def _seed_earn(p, ticker, ad, sue):
    c = duckdb.connect(str(p))
    c.execute("CREATE TABLE IF NOT EXISTS earnings_calendar "
              "(ticker VARCHAR, announcement_date DATE, title VARCHAR, "
              " source VARCHAR, eps_estimate DOUBLE, eps_reported DOUBLE, "
              " surprise_pct DOUBLE, period_end_date DATE, "
              " surprise_eps DOUBLE, sue DOUBLE, expectation_basis VARCHAR)")
    c.execute("INSERT INTO earnings_calendar (ticker, announcement_date, sue) "
              "VALUES (?,?,?)", (ticker, ad, sue))
    c.close()


def test_negative_surprise_blocks(tmp_path) -> None:
    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2025, 2, 10), -1.4)
    sig = pead_signal("ACME", date(2025, 2, 20),
                      earnings_db=edb, fundamentals_db=tmp_path / "missing.db")
    assert sig is not None and sig["block"] is True and sig["sever"] is False


def test_positive_surprise_no_block(tmp_path) -> None:
    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2025, 2, 10), 2.0)
    sig = pead_signal("ACME", date(2025, 2, 20),
                      earnings_db=edb, fundamentals_db=tmp_path / "x.db")
    assert sig["block"] is False


def test_stale_surprise_soft_degrades(tmp_path) -> None:
    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2024, 1, 1), -3.0)
    sig = pead_signal("ACME", date(2025, 2, 20),
                      earnings_db=edb, fundamentals_db=tmp_path / "x.db")
    assert sig is None  # outside drift window → no signal
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
# data/pead.py
"""Point-in-time PEAD accessor.

Theory-pinned constants (NOT strategy hyperparameters — kept here, not on
strategy.params, so prepare.count_hyperparameters is unchanged; same
convention as strategy._structural_ma_window):

  DRIFT_WINDOW_TD : PEAD drift horizon ~64 trading days (literature) → 60.
  SUE_BLOCK       : standard PEAD decile-ish boundary, |SUE| ~ 1σ.
  SUE_SEVERE      : sever a held name on a ~2σ negative miss.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import duckdb

from data.quality_screen import load_fundamentals

logger = logging.getLogger(__name__)

DRIFT_WINDOW_TD = 60
_DRIFT_CAL_DAYS = 90          # ~60 trading days, calendar-approx upper bound
SUE_BLOCK = 1.0
SUE_SEVERE = 2.0


def _quality_cut(ticker: str, today: date, fundamentals_db: Path) -> float:
    """Tighten the block threshold for weak fundamentals, loosen for strong."""
    try:
        funds = load_fundamentals(fundamentals_db, [ticker], today)
    except Exception:  # noqa: BLE001 — accessor must never break the strategy
        funds = {}
    f = funds.get(ticker)
    if f is None:
        return SUE_BLOCK
    weak = (
        (f.roe_ttm is not None and f.roe_ttm < 0.0)
        or (f.debt_to_equity is not None and f.debt_to_equity > 2.0)
        or (f.op_margin_ttm is not None and f.op_margin_ttm <= 0.0)
    )
    strong = (
        (f.roe_ttm or 0.0) > 0.15
        and (f.debt_to_equity is None or f.debt_to_equity < 0.5)
        and (f.op_margin_ttm or 0.0) > 0.10
    )
    if weak:
        return 0.5
    if strong:
        return 1.5
    return SUE_BLOCK


def pead_signal(
    ticker: str,
    today: date,
    *,
    earnings_db: Path,
    fundamentals_db: Path,
) -> dict | None:
    earnings_db = Path(earnings_db)
    if not earnings_db.exists():
        return None
    conn = duckdb.connect(str(earnings_db), read_only=True)
    try:
        row = conn.execute(
            """
            SELECT announcement_date, sue
              FROM earnings_calendar
             WHERE ticker = ? AND sue IS NOT NULL
               AND announcement_date <= ?
               AND announcement_date >= ?
             ORDER BY announcement_date DESC
             LIMIT 1
            """,
            (ticker, today, today - timedelta(days=_DRIFT_CAL_DAYS)),
        ).fetchone()
    except Exception:  # noqa: BLE001
        return None
    finally:
        conn.close()
    if row is None:
        return None
    ad, sue = row
    if sue is None:
        return None
    cut = _quality_cut(ticker, today, Path(fundamentals_db))
    return {
        "sue": float(sue),
        "days_since": (today - ad).days,
        "block": float(sue) <= -cut,
        "sever": float(sue) <= -SUE_SEVERE,
    }


__all__ = [
    "DRIFT_WINDOW_TD", "SUE_BLOCK", "SUE_SEVERE", "pead_signal",
]
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add data/pead.py tests/test_pead_signal.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: PEAD PIT accessor + quality conditioner

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Strategy asymmetric suppression (Phase A)

**Goal:** `strategy.py` gains plumbing params and, in `next()`, blocks new entry on a quality-conditioned negative SUE in the drift window, and severs a held name on a severe miss — never adds names. Parsimony hyperparameter count must be unchanged.

**Files:**
- Modify: `strategy.py`
- Test: `tests/test_strategy_pead_gate.py`

**Acceptance Criteria:**
- [ ] New params `('earnings_db_path', 'storage/news.duckdb')`, `('fundamentals_db_path', 'storage/fundamentals.duckdb')`, `('enable_pead', True)` — all plumbing (str/bool), so `prepare.count_hyperparameters(IndiaMomentumQualityCarry)` is **unchanged** vs `main`.
- [ ] In the rebalance path, a `block`ed candidate is removed from `entry_priority` (not entered); a held name with `sever` gets `order_target_percent(d, 0.0)` using the existing `_stop_pending` machinery.
- [ ] `enable_pead=False` → byte-for-byte the pre-PEAD selection (regression guard).
- [ ] Missing dbs → no suppression (soft-degrade); existing strategy tests still pass.

**Verify:** `uv run pytest tests/test_strategy_pead_gate.py tests/test_warmup_scoring.py tests/test_gross_targeting.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test**

```python
# tests/test_strategy_pead_gate.py
from __future__ import annotations

from prepare import count_hyperparameters
from strategy import IndiaMomentumQualityCarry


def test_parsimony_count_unchanged() -> None:
    # PEAD adds only plumbing/bool params → tunable count must equal the
    # known pre-PEAD value (6 honest hyperparameters; see roadmap §2).
    assert count_hyperparameters(IndiaMomentumQualityCarry) == 6


def test_pead_params_are_plumbing() -> None:
    p = dict(IndiaMomentumQualityCarry.params._getitems())
    assert p["enable_pead"] is True
    assert isinstance(p["earnings_db_path"], str)
    assert isinstance(p["fundamentals_db_path"], str)
```

(Note: if the pre-PEAD count differs from 6 on this branch, set the
expected value to `count_hyperparameters` of the parent commit — capture
it first with `git stash && uv run python -c "from prepare import
count_hyperparameters; from strategy import IndiaMomentumQualityCarry as
S; print(count_hyperparameters(S))" && git stash pop` and use that
literal.)

- [ ] **Step 2: Run, expect FAIL** (params not present yet)

- [ ] **Step 3: Implement**

In `strategy.py` `params` tuple, add:

```python
        ('earnings_db_path', 'storage/news.duckdb'),
        ('fundamentals_db_path', 'storage/fundamentals.duckdb'),
        ('enable_pead', True),
```

Add import near the top:

```python
from datetime import date
from pathlib import Path
```

Add a helper method on `IndiaMomentumQualityCarry`:

```python
    def _pead_verdict(self, ticker: str, today: date) -> dict | None:
        if not self.p.enable_pead:
            return None
        try:
            from data.pead import pead_signal
            return pead_signal(
                ticker, today,
                earnings_db=Path(self.p.earnings_db_path),
                fundamentals_db=Path(self.p.fundamentals_db_path),
            )
        except Exception:  # noqa: BLE001 — never let the gate break trading
            return None
```

In `next()`, immediately after `entry_priority` / `priority` are built and
before `gross = breadth_scaled_gross(...)`, insert:

```python
        if self.p.enable_pead:
            blocked = {
                t for t in priority
                if (v := self._pead_verdict(t, today)) and v["block"]
            }
            priority = [t for t in priority if t not in blocked]
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held and t not in self._stop_pending:
                    v = self._pead_verdict(t, today)
                    if v and v["sever"]:
                        self.order_target_percent(d, target=0.0)
                        self._stop_pending.add(t)
                        held.pop(t, None)
```

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_strategy_pead_gate.py tests/test_warmup_scoring.py tests/test_gross_targeting.py -q`

- [ ] **Step 5: Commit**

```bash
git add strategy.py tests/test_strategy_pead_gate.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: Phase A asymmetric PEAD suppression in strategy

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Backfill runner + coverage/lag firewall report

**Goal:** A CLI that backfills 2019→2026, runs `assert_no_lookahead`, and prints coverage-by-year + lag-distribution so the human can review before any backtest is believed.

**Files:**
- Modify: `data/ingest_fundamentals.py` (add `coverage_report`, `__main__`)
- Test: `tests/test_ingest_fundamentals.py` (report section)

**Acceptance Criteria:**
- [ ] `coverage_report(fundamentals_db) -> dict` returns `{year: n_rows}` and lag-bucket counts (`<20d`, `20-50d`, `50-75d`).
- [ ] `python -m data.ingest_fundamentals --start 2019-01-01 --end 2026-05-18` runs ingest, then `assert_no_lookahead`, then prints the report; non-zero exit if the tripwire raises.

**Verify:** `uv run pytest tests/test_ingest_fundamentals.py -q` → pass

**Steps:**

- [ ] **Step 1: Failing test**

```python
# append to tests/test_ingest_fundamentals.py
from data.ingest_fundamentals import coverage_report


def test_coverage_report(tmp_path) -> None:
    p = tmp_path / "f.duckdb"
    c = duckdb.connect(str(p))
    c.execute("CREATE TABLE fundamentals_quarterly "
              "(ticker VARCHAR, period_end_date DATE, as_of_date DATE)")
    c.execute("INSERT INTO fundamentals_quarterly VALUES "
              "('A', DATE '2024-12-31', DATE '2025-02-12')")
    c.close()
    rep = coverage_report(p)
    assert rep["by_year"][2025] == 1
    assert rep["lag_buckets"]["20-50d"] == 1
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement (append to `data/ingest_fundamentals.py`)**

```python
def coverage_report(fundamentals_db: Path) -> dict:
    conn = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        by_year = dict(conn.execute(
            "SELECT EXTRACT(year FROM as_of_date)::INT, COUNT(*) "
            "FROM fundamentals_quarterly GROUP BY 1 ORDER BY 1"
        ).fetchall())
        lag = conn.execute(
            """
            SELECT
              SUM(CASE WHEN as_of_date - period_end_date < 20 THEN 1 ELSE 0 END),
              SUM(CASE WHEN as_of_date - period_end_date BETWEEN 20 AND 50
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN as_of_date - period_end_date > 50 THEN 1 ELSE 0 END)
            FROM fundamentals_quarterly
            """
        ).fetchone()
    finally:
        conn.close()
    return {
        "by_year": by_year,
        "lag_buckets": {"<20d": lag[0] or 0, "20-50d": lag[1] or 0,
                        "50-75d": lag[2] or 0},
    }


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--universe-db", default="storage/universe.duckdb")
    ap.add_argument("--fundamentals-db",
                    default=str(DEFAULT_FUNDAMENTALS_DB))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    fdb = Path(a.fundamentals_db)
    ingest_fundamentals(
        Path(a.universe_db), fdb,
        start=date.fromisoformat(a.start), end=date.fromisoformat(a.end),
    )
    try:
        assert_no_lookahead(fdb)
    except LookaheadError as e:
        print(f"LOOK-AHEAD TRIPWIRE FIRED: {e}", file=sys.stderr)
        sys.exit(1)
    print(coverage_report(fdb))
```

Add `coverage_report` to `__all__`.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add data/ingest_fundamentals.py tests/test_ingest_fundamentals.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: backfill CLI + coverage/lag firewall report

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Live source-split wiring (self-timestamped snapshot)

**Goal:** `scripts/daily_update.py` gains a step that, after the daily news/filings ingest, snapshots that day's newly-filed fundamentals into `fundamentals.duckdb` with the capture date as `as_of_date` — PIT-clean by construction, no fragile daily XBRL dependency beyond the same BSE attachment path already used.

**Files:**
- Modify: `data/ingest_fundamentals.py` (add `snapshot_live`)
- Modify: `scripts/daily_update.py`
- Test: `tests/test_ingest_fundamentals.py` (snapshot section)

**Acceptance Criteria:**
- [ ] `snapshot_live(universe_db, fundamentals_db, on_date)` = `ingest_fundamentals(start=on_date, end=on_date)` but stamps `as_of_date = on_date` for any filing whose broadcast date is `on_date` (capture-time guarantee), and is a no-op for already-present `(ticker, period_end)`.
- [ ] `scripts/daily_update.py` calls `snapshot_live` once per run after Step 4 (earnings), guarded by a `--skip-fundamentals` flag, never aborting the cron on failure (logged).

**Verify:** `uv run pytest tests/test_ingest_fundamentals.py -q && uv run python -m scripts.daily_update --help` → pass / help prints

**Steps:**

- [ ] **Step 1: Failing test**

```python
# append to tests/test_ingest_fundamentals.py
import data.ingest_fundamentals as ingf2


def test_snapshot_live_stamps_capture_date(tmp_path, monkeypatch) -> None:
    fdb = tmp_path / "f.duckdb"
    monkeypatch.setattr(ingf2, "_pit_universe",
                        lambda *_: {"ACME": "IN0ACME"})
    monkeypatch.setattr(ingf2, "_scrip_for_isin", lambda *_: "500001")
    monkeypatch.setattr(ingf2, "_is_financial", lambda *_: False)
    from data.fundamentals_xbrl import XbrlFacts
    fx = XbrlFacts(100, 20, 18, 12, 5.0, 4.9, 600, 300,
                   date(2024, 12, 31), True)
    monkeypatch.setattr(
        ingf2, "_fetch_result_filings",
        lambda *_: [ingf2.RawFiling("ACME", None, date(2024, 12, 31), fx)],
    )
    n = ingf2.snapshot_live(Path("x"), fdb, on_date=date(2025, 2, 12))
    assert n == 1
    c = duckdb.connect(str(fdb), read_only=True)
    ao = c.execute("SELECT as_of_date FROM fundamentals_quarterly").fetchone()[0]
    c.close()
    assert ao == date(2025, 2, 12)  # capture date, not SEBI fallback
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

Append to `data/ingest_fundamentals.py`:

```python
def snapshot_live(
    universe_db: Path,
    fundamentals_db: Path = DEFAULT_FUNDAMENTALS_DB,
    *,
    on_date: date,
) -> int:
    """Live capture: stamp as_of_date = on_date for filings broadcast today.

    PIT-clean by construction (we record the value the day we see it), so
    the live path does not depend on a reliable historical broadcast
    timestamp. Reuses ingest_fundamentals' fetch/parse path with a
    capture-date override.
    """
    written = 0
    fundamentals_db.parent.mkdir(parents=True, exist_ok=True)
    scrip_map = build_scrip_map()
    conn = duckdb.connect(str(fundamentals_db))
    try:
        _ensure_schema(conn)
        existing = {
            (t, pe) for t, pe in conn.execute(
                "SELECT ticker, period_end_date FROM fundamentals_quarterly"
            ).fetchall()
        }
        uni = _pit_universe(universe_db, on_date, on_date) or \
            {r.ticker: r.isin for r in load_universe(
                universe_db, snapshot_dates(universe_db)[-1])} \
            if snapshot_dates(universe_db) else {}
        for sym, isin in uni.items():
            scrip = _scrip_for_isin(scrip_map, isin, sym)
            if not scrip:
                continue
            for f in _fetch_result_filings(scrip, sym, on_date, on_date):
                if (sym, f.period_end) in existing:
                    continue
                ratios = derive_ttm(
                    [QuarterFacts(sym, f.period_end, on_date, f.facts)]
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fundamentals_quarterly VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'bse_live')
                    """,
                    (sym, f.period_end, on_date, on_date,
                     ratios.roe_ttm, ratios.debt_to_equity,
                     ratios.op_margin_ttm, _is_financial(sym, ""),
                     f.facts.eps_basic, f.facts.eps_diluted,
                     f.facts.revenue, f.facts.ebit, f.facts.pat,
                     f.facts.equity, f.facts.debt, f.facts.is_consolidated),
                )
                written += 1
    finally:
        conn.close()
    return written
```

Add `snapshot_live` to `__all__`.

In `scripts/daily_update.py`, after the earnings step (the `[4/6]` block
around line 117–119), add:

```python
    if not args.skip_fundamentals:
        try:
            from pathlib import Path

            from data.ingest_fundamentals import snapshot_live
            n_fund = snapshot_live(
                Path("storage/universe.duckdb"),
                on_date=today_d,
            )
            print(f"[4b] fundamentals snapshot: {n_fund} new", flush=True)
        except Exception as e:  # noqa: BLE001 — cron must not abort
            print(f"[4b] fundamentals snapshot FAILED (non-fatal): {e}",
                  flush=True)
```

And add the arg near the other `add_argument` calls:

```python
    parser.add_argument("--skip-fundamentals", action="store_true",
                        help="Skip the live fundamentals snapshot step.")
```

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_ingest_fundamentals.py -q && uv run python -m scripts.daily_update --help`

- [ ] **Step 5: Commit**

```bash
git add data/ingest_fundamentals.py scripts/daily_update.py tests/test_ingest_fundamentals.py
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -m "production-strategy: live source-split — self-timestamped fundamentals snapshot

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Full-suite regression + research backtest sanity

**Goal:** Confirm the whole suite is green and `prepare.py research` still runs with PEAD enabled (no crash, gates evaluated). This is the gate before any forward `dhan-paper`.

**Files:** none (verification only)

**Acceptance Criteria:**
- [ ] `uv run pytest -q` fully green.
- [ ] `uv run python prepare.py research` completes; PEAD path exercised (soft-degrades cleanly if `fundamentals.duckdb` not yet backfilled — never crashes).
- [ ] Atomic anti-overfit gates evaluated as before (no gate bypassed); judged on worst sub-period per spec §6 — **no `prepare.py promotion`**.

**Verify:** `uv run pytest -q && uv run python prepare.py research`

**Steps:**

- [ ] **Step 1:** Run `uv run pytest -q`. If red, fix the offending task's code (do not weaken anti-overfit tests).
- [ ] **Step 2:** Run `uv run python prepare.py research`. Confirm it completes and prints the gate table. With no `fundamentals.duckdb`, PEAD soft-degrades (accessor returns `None`) — strategy behaves as pre-PEAD; this is expected and correct.
- [ ] **Step 3: Commit** (if any fixups)

```bash
git -c user.name=victorvini08 -c user.email=aryan08vini@gmail.com commit -am "production-strategy: full-suite green + research sanity with PEAD wired

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4:** Record the result in `journal.md` per the existing iteration format (hypothesis, change, research metrics, KEEP/REVERT). Do NOT run `prepare.py promotion`. Forward `dhan-paper` is the real arbiter (spec §6).

---

## Self-review

**Spec coverage:** §3 source split → Tasks 1,2,4,10. §4.1 ingest/schema → Task 4. §4.2 SUE → Task 6. §4.3 PIT guarantee → Tasks 4,5. §4.4 firewall → Tasks 5,9. §5.1 accessor → Task 7. §5.2 Phase A → Task 8. §6 validation guardrails → Task 11. §5.3 Phase B → explicitly out of scope (header). All spec sections covered.

**Placeholder scan:** No TBD/TODO; every code step has concrete code; the one parametric value (pre-PEAD hyperparameter count) has an explicit capture procedure in Task 8.

**Type consistency:** `XbrlFacts` field order is fixed in Task 1 and constructed positionally consistently in Tasks 3/4/10 tests. `QuarterFacts`/`RawFiling`/`DerivedRatios` defined in Tasks 3–4 and reused unchanged. `pead_signal` returns `{'sue','days_since','block','sever'}` in Task 7 and consumed with exactly those keys in Task 8. `fundamentals_quarterly` column order is identical in the Task 4 INSERT and the Task 10 INSERT (16 cols + source literal).

**Note for executor:** Tasks 1→2→3→4→5→6→7→8 are sequential (each builds on prior types). Tasks 9, 10 depend on Task 4 (+5). Task 11 is last. The real-network backfill (`python -m data.ingest_fundamentals`) and forward `dhan-paper` are operational steps the human runs after Task 11, outside this plan.
