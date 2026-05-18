# PIT fundamentals + earnings (PEAD) signal — design

**Date:** 2026-05-18
**Branch:** `production-strategy`
**Status:** Approved design, pre-implementation

---

## 1. Motivation

The autoresearch loop has exhausted every price/structure lever on the
long-only momentum-quality book. Both `learnings.md` §6.1/§6.2 and
`docs/superpowers/specs/2026-05-17-robust-india-strategy-roadmap.md` §6
independently conclude that the only genuine remaining edge is an
**orthogonal data signal** (fundamentals / earnings), explicitly deferred
out of the price-only loop.

The infrastructure is **half-built**:

- `data/quality_screen.py` is a *consumer* expecting
  `storage/fundamentals.duckdb` (table `fundamentals_quarterly`) that
  **nothing populates** → it is a permanent no-op today.
- `data/ingest_earnings.py` is a *producer* of an `earnings_calendar`
  whose `surprise_pct` comes from yfinance (restated, not point-in-time)
  and which **no strategy consumes**.

This design closes both gaps with a **point-in-time-clean** pipeline and a
**quality-conditioned post-earnings-announcement-drift (PEAD) event gate**.

### 1.1 Why PEAD, why quality-conditioned

- PEAD is statistically significant on NSE 2002–2017, robust to
  sub-periods and to controls for beta/size/P-B/illiquidity/idio-vol, and
  **stronger in lower-cap names post-2008** — directly relevant to our
  mid-cap-heavy top-200-ADV universe.
  (Theoretical Economics Letters / SCIRP paperid=88060.)
- Earnings-momentum × price-momentum conditional bivariate sorts produced
  the highest supernormal returns (~1.1%/mo) on NSE 200 (2005–2016) —
  motivating *conditioning* the surprise on quality rather than using it
  raw.
- It is **orthogonal to price momentum** (an event/accounting signal, not
  another price-derived cross-sectional rank), so it sidesteps roadmap §6's
  burned "more cross-sectional rank factors" trap by construction.

---

> **Source correction (2026-05-18, post-implementation, verified live).**
> The original design named BSE result-XBRL as the backfill source. At the
> real-network gate this produced **0 rows**: BSE's announcement
> attachment is the human-readable **PDF**, not XBRL. Corrected source =
> **NSE `corporates-financial-results` API** (`?index=equities&symbol=
> <SYM>&period=Quarterly`), which returns per-symbol rows carrying
> `broadCastDate` (the PIT timestamp, as a field — no parsing), `toDate`
> (period end), `isin`, `consolidated`, and a **direct `xbrl` URL** to the
> real XBRL on `nsearchives.nseindia.com`. All PIT/derivation/SUE/
> accessor/firewall design below is source-agnostic and unchanged; only
> the fetch+parse layer was re-pointed (and made XBRL-context-aware so the
> standalone quarter, not the cumulative YTD or a segment, is read).
>
> **Data limitation (verified):** NSE quarterly-results XBRL is
> P&L-centric — EPS / revenue / PBT / PAT are present (so **SUE works**),
> but net worth & borrowings are not, so `roe_ttm` / `op_margin_ttm` are
> usually `None` and `debt_to_equity` falls back to the filing's own
> reported `DebtEquityRatio` (thin/0.0 for some names). The
> quality-conditioner therefore mostly soft-degrades to the base SUE cut
> on quarterly-only data; this is acceptable (the design's soft-degrade
> path handles it) but means "quality-conditioned" is weak until annual /
> balance-sheet filings are added (future work, out of scope here).

## 2. Scope & decomposition

Two subsystems, **built and validated pipeline-first**:

1. **Subsystem 1 — PIT-clean fundamentals + earnings/SUE data pipeline**
   (producer). The foundation; the place where look-ahead / restatement /
   survivorship bugs silently corrupt everything downstream. Built and
   validated *before* any strategy code consumes it.
2. **Subsystem 2 — strategy integration** (consumer): a PIT accessor + a
   quality-conditioned PEAD event gate in `strategy.py`, **phase-gated**
   (Phase A shipped & forward-validated before Phase B is built).

---

## 3. The point-in-time principle (the whole game)

Every *convenient* India fundamentals source (screener.in, yfinance,
Tickertape, Trendlyne, FMP-India) serves a **current/restated snapshot
keyed only to the period-end** — no announcement date. Backtesting on those
= look-ahead + restatement + survivorship bias: precisely the
"just overfits on backtest" failure mode this whole effort must avoid.

Only the **exchange filing feeds (BSE/NSE)** natively carry (a) the actual
**broadcast timestamp** (when the market truly learned the number) and
(b) **as-originally-reported** figures (no later restatement overwriting
history). Every other free source is a *downstream restated copy* of
exactly these filings — so none can be "better" on the axis that decides
whether the backtest is honest. This is a forced choice, not a preference.

### 3.1 Backfill vs live — the source split (key architecture decision)

The PIT-source requirement **only binds the historical backfill**. For
live/forward operation, a value is point-in-time *by construction* if we
snapshot it the day it is released and stamp our own capture date — even
from a "restated" source. Therefore the brittle daily XBRL parser is an
operational liability we do **not** need going forward (learnings §5.1:
NSE IP-bans scrapers; the XBRL taxonomy changed with the Mar-2025
"Integrated Filing" schema).

| Path | Source | Rationale |
|---|---|---|
| **Historical backfill (2019→2026)** | BSE XBRL results primary, NSE `corporates-financial-results` fallback | Only free PIT-clean option; one-time cost |
| **Live trigger** | NSE/BSE corporate-announcement feed already hit for `nse_filing` news + `ingest_earnings.py` | Reuses existing plumbing; signals *when* a result drops |
| **Live value capture** | Lightweight daily snapshot (screener.in / MoneyControl already scraped) stamped with our own capture timestamp | PIT-clean by construction; removes fragile daily XBRL dependency |
| **Cross-check (offline)** | screener.in oracle | Catches XBRL parse errors; never in the signal path |

Known XBRL warts to handle explicitly: schema-era change (parser pinned
per era — pre-Mar-2025 results-XBRL vs Mar-2025+ Integrated Filing);
consolidated-vs-standalone must be picked **consistently** (prefer
consolidated, fall back to standalone — the convention screener.in uses).

---

## 4. Subsystem 1 — pipeline

### 4.1 `data/ingest_fundamentals.py` (NEW) → `storage/fundamentals.duckdb`

- **Source:** BSE XBRL results feed primary (`api.bseindia.com`
  `AnnSubCategoryGetData`, `strCat=Result`, `Referer` header required;
  use the maintained `bse`/`BseIndiaApi` wrapper plumbing pattern). NSE
  `corporates-financial-results` + `corporate-announcements` as
  cross-check / fallback (cookie-bootstrap session like existing NSE
  ingest).
- **Per filing capture:** `broadcast_datetime` (the PIT availability key),
  `period_end_date`, `ticker`, raw XBRL line items — revenue, EBIT /
  operating profit, PBT, PAT, EPS (basic & diluted), net worth / total
  equity, total borrowings, shares outstanding, consolidated/standalone
  flag.
- **Derived ratios, PIT-clean:** `roe_ttm`, `debt_to_equity`,
  `op_margin_ttm` from a rolling sum of the last 4 *as-reported* quarters
  known **as of the broadcast date** (never period-end).
- **Schema:** superset of what `quality_screen.py` already expects — table
  `fundamentals_quarterly` with at minimum
  `(ticker, as_of_date, roe_ttm, debt_to_equity, op_margin_ttm,
  is_financial)` where **`as_of_date` = broadcast date**, plus raw
  columns `eps_basic, eps_diluted, revenue, ebit, pat, equity, debt,
  shares, period_end_date, broadcast_datetime, is_consolidated, source`.
  This also resurrects the dormant quality screen for free.
- **`is_financial`:** from `data/sectors.py` map (financials get the D-E
  exemption `quality_screen.py` already encodes).
- **Backfill universe:** the **PIT** top-200-ADV membership via
  `data/universe.py` point-in-time API — no survivor-only fetch.
- **Scraping discipline (learnings §5):** polite 1–2s delay, browser UA,
  persistent cache, exponential backoff on 429/403, per-source
  `last_successful_fetch` row + >48h staleness alert.
- **Reconciliation:** where BSE & NSE both present, compare key figures
  within tolerance; disagreement → quarantine + log, prefer BSE.
  screener.in is an **offline** oracle only.

### 4.2 SUE computation (extend `data/ingest_earnings.py`)

- The existing yfinance `surprise_pct` is restated → **discarded for
  signal use** (kept only as a non-signal provenance column).
- EPS source becomes the **as-reported EPS from `fundamentals.duckdb`**
  keyed to broadcast date.
- **SUE (standardized unexpected earnings)** per the India PEAD
  literature: seasonal-random-walk expectation `E[EPS_q] = EPS_{q-4}`
  (same quarter prior year, as-reported, known as-of), unexpected
  `= EPS_q - E[EPS_q]`, standardized by the rolling std of the last 8
  seasonal forecast errors. **Every input strictly as-of broadcast date.**
- Store `sue`, `surprise_eps`, `expectation_basis` on `earnings_calendar`,
  `announcement_date` = broadcast date.

### 4.3 PIT guarantee

- `as_of_date` = actual broadcast datetime. Missing → conservative SEBI
  LODR Reg 33 fallback: `period_end + 45d` (Q1–Q3) / `FY_end + 60d` (Q4).
  **Never `period_end` itself.**
- Every row asserted `period_end_date <= as_of_date <= period_end + 75d`
  (sanity band). Rows outside → quarantined, logged, excluded from signal.

### 4.4 Pipeline validation firewall (hard gate before any strategy use)

1. **Look-ahead tripwire test (hard CI gate):** constructing any signal
   as-of date D using only rows with `as_of_date <= D` must expose **zero**
   row whose `period_end > D`. Strategy code is blocked from consuming the
   pipeline until this test passes.
2. **Coverage report** by year over the PIT universe. Below a documented
   floor → the gate **soft-degrades to "no signal"**, never to a
   pass/fail default (identical philosophy to `llm/features.py`
   accessors and `quality_screen.py`).
3. **Lag-distribution histogram:** must cluster 30–50 days post
   quarter-end (matches SEBI Reg 33 empirics); `<20d` or `>75d`
   quarantined.
4. **Offline reconciliation** sample vs screener.in oracle within a
   tolerance band — CI/manual, never in the signal path.

---

## 5. Subsystem 2 — strategy integration

### 5.1 PIT accessor

A pure accessor (mirroring the `llm/features.py` pattern) e.g.
`pead_signal(ticker, today) -> {'sue', 'days_since_announce',
'quality': {...}} | None`. Reads only rows with `as_of_date <= today`
within the drift window. Returns `None` when absent → the strategy treats
absence as **no signal** (never as a block or a pass).

### 5.2 Phase A — asymmetric suppression (ships first)

In `strategy.py`'s rebalance `next()`, after candidate ranking and before
final selection:

- A momentum-qualified name carrying a **quality-conditioned negative
  surprise** inside the ~60-trading-day drift window is **removed from
  `entry_priority`** (blocked from a new entry).
- If the name is **already held** and the negative surprise is **severe**,
  it is exited via `order_target_percent(d, target=0.0)`, reusing the
  existing structural-exit `_stop_pending` machinery.
- It **never adds** a name momentum did not already select.

This mirrors the one philosophy this codebase has repeatedly found robust:
asymmetric defense (learnings §3.1 FII gate "block entries, don't chase";
the symmetric structural exit). It directly attacks momentum's specific
known failure — holding/buying a name whose fundamentals just
deteriorated (the classic momentum-crash mechanism).

**Theory-pinned constants (NOT window-tuned):**

- Drift window ≈ 60 trading days (literature ~64).
- SUE threshold a fixed standardized cut (|SUE| ≈ 1.0–1.5σ — the standard
  PEAD decile-ish boundary), with a single severe multiple for the
  held-name exit.
- Quality conditioner **reuses `quality_screen.py`'s existing ROE / D-E /
  op-margin constants** (single source of truth) — a positive surprise is
  trusted more in low-D-E/high-ROE names; a negative surprise in a
  leveraged / low-margin name is the harder avoid.

Net **≤ 2 genuinely new honest hyperparameters**, documented against the
parsimony budget. Soft-degrade: no PIT row → no suppression.

### 5.3 Phase B — categorical positive tilt (specced, NOT built yet)

Gated explicitly on **Phase A passing forward `dhan-paper` validation**.
Names with a strong positive quality-conditioned SUE in-window are moved
ahead **within `entry_priority` ordering**, inside the *same fixed
gross/slots* — **categorical bucket reordering only**, never a continuous
score added to the 7-rank sum (stays clear of the burned "more rank
factors" trap). Implementation deferred until the gate is opened; no extra
brainstorm needed.

---

## 6. Validation & guardrails (cross-cutting)

- `prepare.py research` **only**. Judge on the **worst sub-period** + all
  anti-overfit gates + controlled drawdown + gross ≤ 100%; mean Sortino is
  **reference only** (robustness-over-validation-Sortino standard).
- **Never** run `prepare.py promotion`; the sealed window stays burned.
  **Forward `dhan-paper` is the real arbiter** of both phases.
- The §4.4 look-ahead tripwire is a hard gate *before any backtest number
  is believed*.
- Anti-overfit gates are atomic — a variant failing any gate is rejected,
  not partially accepted.
- One change at a time; revert decisively. `prepare.py` and
  `backtest/anti_overfit.py` are **never edited**. Commit as
  `victorvini08`. Stay on `production-strategy`.

---

## 7. Out of scope

- Quality screen as the integration mechanism (the pipeline resurrects it
  for free, but the chosen integration is the PEAD gate, not the screen).
- Standalone PEAD sleeve / separate book (explicitly rejected).
- Consensus-estimate SUE (no free PIT-clean Indian consensus feed exists;
  seasonal-random-walk expectation is the defensible substitute).
- Paid vendors (Global Datafeeds, FMP paid, EODHD paid).
- Dhan Data API pricing change (search suggests it may now be free vs the
  ₹500/mo locked decision) — noted for a *separate* review; irrelevant
  here since Dhan carries no fundamentals.

---

## 8. Build order (pipeline-first)

1. `data/ingest_fundamentals.py` + schema + scraping discipline.
2. PIT guarantee (§4.3) + validation firewall (§4.4) — **gate**.
3. SUE extension to `data/ingest_earnings.py` (§4.2).
4. Backfill 2019→2026 over PIT universe; run the firewall; coverage/lag
   reports reviewed.
5. PIT accessor (§5.1).
6. Phase A asymmetric suppression in `strategy.py` (§5.2); `prepare.py
   research`; worst sub-period + atomic gates + drawdown.
7. Live source split wiring (§3.1) for forward `dhan-paper`.
8. (Later, gated) Phase B (§5.3).
