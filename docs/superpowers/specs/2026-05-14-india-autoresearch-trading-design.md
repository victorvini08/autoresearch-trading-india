# India Autoresearch Trading — Design Spec

**Date:** 2026-05-14
**Status:** Approved by user via brainstorming session 2026-05-14
**Predecessor:** `victorvini08/autoresearch-trading-us` (Phase 1, archived)
**Target market:** Indian equities (NSE), delivery / CNC, swing trading
**Capital scope (v1):** ₹50,000 paper start, scaling to ₹2-5L
**Live exit criteria:** 4 weeks paper validation + walk-forward Sortino gates clear

---

## 1. Goal

Build a research-driven swing-trading system for Indian equities that:

1. Generates a strategy via an **LLM autoresearch loop** (Claude Opus 4.7 overnight, mutates `strategy.py`, journal-based memory across iterations).
2. Validates each candidate strategy on a sealed walk-forward backtest with **rigorous anti-overfit gates**.
3. Executes the surviving strategy daily via a Dhan HQ broker integration, starting with **paper mode** (`dhan-paper`), graduating to `dhan-live` only after 4 weeks of clean paper validation.
4. Is SEBI-compliant under the retail-algo framework effective 2026-04-01 (registered algo ID, static IP, OPS counter).

The system inherits architecture from the abandoned US repo (broker- and market-agnostic infrastructure proven over Phase 1) and replaces the data + broker + cost + strategy layers with India-specific equivalents.

---

## 2. Why we're not doing the US repo's strategy verbatim

Two issues the user flagged that change the strategy design:

1. **The US repo only had 1 year of free news data** (Finnhub free tier). For India, 5+ years of news is accessible from public sources (MoneyControl archive, NSE filings, RBI/SEBI press releases). This **lets the autoresearch loop validate news/macro classifiers on the full backtest horizon**, not just the recent slice — a structural advantage.
2. **The US repo trained several base strategies, most overfit.** This is a known failure mode of LLM-driven strategy search when the gating criteria don't penalize complexity. The Indian rebuild adds **anti-overfit machinery** (sealed test set, Bonferroni significance correction, random-walk Monte Carlo null, parameter parsimony budget, sub-period stationarity check).

A third change (universe) addresses a separate empirical observation:

3. **Nifty 100 mega-caps have been the laggards 2024-2026.** The 24-month winners on NSE are mid-caps (HAL, BEL, Polycab, KEI, Trent, Persistent, defence PSUs). A momentum strategy ranked within Nifty 100 systematically misses them. Universe widens to a **liquid-filtered Nifty 500 slice (top 200 by ADV)**.

---

## 3. Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Market | Indian equities (NSE), CNC / delivery | India-resident user; native market; eliminates LRS / TCS / Schedule FA overhead from US path |
| Broker (execution) | **Dhan HQ Trading API** | Free brokerage on delivery; free Trading API (orders, positions, holdings); 24-hour access token auto-renewed daily via `scripts/dhan_token_refresh.py` (GET /v2/RenewToken — verified live 2026-05-15; the handoff doc's "1-year" claim was wrong); 20 req/s rate limit; cheapest TCO at our capital range per US handoff §17. **Note:** Dhan's separate Data API costs ₹500/mo — we don't use it. Price data comes from free NSE bhav archive. |
| Price data (historical + live EOD) | **NSE bhav archive** (free public ZIP) | Authoritative NSE-published EOD data; same source backtest and live; no monthly fee; corporate actions in NSE bhav include splits/bonuses |
| Universe | **Top 200 by 20d ADV, filtered from Nifty 500** | Includes mid-cap winners that Nifty 100 misses; ADV filter keeps liquidity; quality screen excludes weak names; refreshed monthly |
| Strategy shape | **Cross-sectional 12-1 momentum + retention buffer + quality screen + sector cap + Indian regime gate** | Sparse (4 params), theory-backed (Jegadeesh-Titman / Asness / Novy-Marx); avoids ATR-stop overfit risk from US repo |
| Rebalance cadence | **Biweekly (alternate Fridays)** | User-specified; balances signal turnover vs DP-charge drag |
| Capital | ₹50,000 paper start | Realistic; 5-6 default positions, parameter-flex 4-10 |
| LLM stack | **Claude Code SDK (Opus 4.7 for autoresearch loop, Sonnet 4.6 for in-strategy classifiers)**; Qwen3 fallback | Subscription-bounded cost; daily cache keyed by `(date, ticker, prompt_hash, model_id)` |
| Live trading | **Paper only for v1** (`dhan-paper`). Live code built but disabled by `halt.json` until 4-week paper validation | Safer; matches US repo's promotion-gate discipline |
| Project structure | **Karpathy 3-file**: `prepare.py` (immutable evaluator), `strategy.py` (loop-editable), `journal.md` (memory) | Universal pattern from US repo |
| Backtester | `backtrader` | Validated for strategy shape; carried from US repo |
| Anti-overfit gates | Sealed 2024-2026 test set + Bonferroni p-correction + RW Monte Carlo + parsimony budget + sub-period stationarity + cost-aware Sortino | **NEW for India** — directly addresses the US overfit failure mode |

---

## 4. Strategy specification

### 4.1 Starting strategy (sparse, theory-first)

| Component | Rule | Parameter | Canonical value | Literature |
|---|---|---|---|---|
| **Universe** | Top 200 by 20d ADV from Nifty 500, monthly refresh | — | — | Liquidity filter is industry-standard |
| **Signal** | 12-1 cross-sectional momentum: rank by (252d return, skip last 21d) | `lookback_days = 252, skip_days = 21` | (252, 21) | Jegadeesh & Titman 1993; Asness & Moskowitz 2013 |
| **Quality screen** | Exclude if ROE_TTM < median AND (Debt/Equity > 2 for non-financials OR Op-margin ≤ 0) | `quality_pct = 50` | 50th percentile | Novy-Marx 2013; Asness & Frazzini 2019 |
| **Selection** | Top decile of post-quality universe; retain held names if still in top 2× decile | `retention_mult = 2.0` | 2.0 | US repo learnings §1.1 |
| **Sizing** | Equal-weight | — | — | DeMiguel-Garlappi-Uppal 2009 (1/N beats Markowitz OOS) |
| **Sector cap** | Max 25% gross exposure per NSE sector at rebalance | — (fixed) | 25% | Mutual-fund regulatory standard |
| **Rebalance** | Biweekly (alternate Fridays); EOD orders for next-open execution | — (fixed) | biweekly | User-specified |
| **Regime gate** | Block NEW entries (hold existing) if any of: Nifty 50 < 200DMA; India VIX > 95th percentile (rolling 252d); FII 20d net < -₹15,000 cr | `regime_pct = 95, fii_threshold = -15000cr` | (95, -15000cr) | Cooper-Gutierrez-Hameed 2004; 2024-26 evidence |
| **Position count** | Default 6 at ₹50k; loop can experiment 4-10 | `n_positions = 6` | 6 | DP-charge optimization |

**Total tunable hyperparameters: 5** (lookback, retention_mult, quality_pct, regime_pct, n_positions).

The autoresearch loop may propose adding parameters, but each must clear the parsimony budget in §6.

### 4.2 What's NOT in the starting strategy (loop must earn)

- ATR trailing stops (adds 2 params; was the most over-tuned component in US repo)
- News sentiment as a feature (loop can propose; must clear Bonferroni gate)
- Event-based exits (earnings, M&A windows)
- Dynamic position sizing (vol-targeting, Kelly)
- Sub-daily signals (intraday)
- F&O (out of v1 scope entirely)

### 4.3 Strategy contract (programming interface)

- `strategy.py` is a `backtrader.Strategy` subclass
- All trades use `self.order_target_percent(data, target_fraction)` — never `self.buy()` / `self.close()` (US repo learnings §7.3)
- On non-rebalance bars: early return (no `order_target_percent` calls)
- Strategy reads pre-computed classifier features (`macro_regime`, `sentiment`, `events`) via `llm/features.py` accessors
- Signal extraction via `scripts/signal_today.py` (broker state + last-rebalance overlay; US repo learnings §2.6)

---

## 5. Universe construction

### 5.1 Build pipeline (`data/universe.py`)

1. **Source:** NSE Nifty 500 constituent list — `https://niftyindices.com/IndexConstituent/ind_nifty500list.csv` (free, public)
2. **20-day ADV filter:** trailing 20 trading days; ADV = mean(daily close × daily volume); threshold ≥ ₹10 crore
3. **Series filter:** EQ only (excludes SME, BE, T, Z groups)
4. **Listing-age filter:** must have ≥ 504 trading days of price history (≈2 years)
5. **Free-float market cap filter:** ≥ ₹1,000 crore (read from NSE indices CSV)
6. **Trading-days filter:** ≥ 90% of last 250 sessions had trades (filters circuited/suspended)
7. **Snapshot lock:** For each historical rebalance day, use the constituent list as it was *on that day* (NSE publishes historical monthly index files; cached in repo)

**Output:** `storage/universe.duckdb` with columns `(as_of_date, ticker, isin, security_id, sector, free_float_mcap_cr, adv_20d_cr)`.

### 5.2 Reconstitution handling

Nifty 500 reconstitutes semi-annually. Our monthly ADV-refresh is independent — universe membership flips on monthly recompute, not on NSE reconstitution dates. Backtest sees historically-valid universe on every rebalance day.

### 5.3 Sector classification

NSE publishes sector for each constituent in the index CSV. Sectors used for the 25% cap:
Auto, Banks, Capital Goods, Cement, Chemicals, Consumer Durables, FMCG, Financial Services (ex-Banks), Healthcare, IT, Media, Metals, Oil & Gas, Pharma, Power, Realty, Services, Telecom, Textiles. (~15-19 buckets depending on NSE's current classification.)

---

## 6. Anti-overfit machinery (`backtest/anti_overfit.py` — NEW)

The single biggest divergence from the US repo. Each gate must clear before the loop accepts a strategy variant.

### 6.1 Sealed test set

- Train + validation window: **2018-01-01 → 2023-12-31** (6 years; walk-forward 2y train / 6m val / 3m test internally)
- Sealed test window: **2024-01-01 → 2026-05-31** (~2.4 years; contains both 2024-Q4-correction and 2026-Q1-correction)
- Sealed test is revealed **once per promotion request**. If revealed and the strategy fails, the variant is permanently rejected (no retry on the same variant).
- Tracking: `iterations/sealed_reveals.csv` logs every reveal.

### 6.2 Bonferroni-adjusted Sortino significance

After N variants in the autoresearch loop, the significance threshold for a promotion candidate is:

```
p_threshold = 0.05 / N_active_variants
```

Where `N_active_variants` is the count of variants that have completed walk-forward in this campaign. Conservative — penalizes the loop for exploration.

### 6.3 Random-walk Monte Carlo null

For each promotion candidate:
1. Generate 5,000 bar-permutations of universe returns (preserve cross-sectional structure, shuffle time order within each ticker)
2. Run the strategy on each permutation under the same walk-forward
3. Reject the strategy if its Sortino does not exceed the 95th percentile of RW-null Sortinos

Detects strategies that are exploiting accidental patterns in the data rather than true momentum.

### 6.4 Parameter parsimony budget

- Starting strategy is allowed 5 hyperparameters
- Each additional parameter the loop introduces must improve sealed-test Sortino by ≥ 0.10 AND clear Bonferroni
- Parameters that fail the budget are rolled back

### 6.5 Sub-period stationarity check

- Compute the strategy's Sortino on 4 disjoint 18-month sub-periods of train+val window
- Reject if `min_sortino / max_sortino < 0.3` (strategy works in one regime only)

### 6.6 Cost-aware Sortino

All promotion-gate Sortinos are computed **net of full Dhan delivery costs** (incl. DP charges per scrip per sell). The autoresearch loop sees gross AND net; promotion uses net.

---

## 7. Autoresearch loop

### 7.1 Cadence

- Triggered manually (`scripts/run_overnight.py`) or via `launchd` plist
- One iteration = one strategy variant proposed, backtest run, KEEP/REVERT decision logged
- Iteration time: ~30-60 min depending on cache state (LLM classifiers + walk-forward + RW Monte Carlo)
- Overnight budget: 8-12 iterations per run

### 7.2 Loop driver (`scripts/loop.py`)

- Reads `journal.md` to find last `**Decision:** KEPT` Sortino baseline (literal-line match — see US repo learnings §4.4)
- Reads `iterations/log.csv` last 20 rows as "RECENT ATTEMPTS" context
- Reads `learnings.md` for domain insights
- Prompts Claude Opus 4.7 (via Claude Code CLI) with `program.md` constraints + current `strategy.py`
- Receives proposed `strategy.py` edit
- Runs walk-forward via `prepare.py research`
- Applies anti-overfit gates (§6) — REJECT if any fails
- If all gates pass: applies promotion gate (sealed test reveal once; KEEP if Sortino improves AND DD regression ≤ 10pp AND catastrophe-clear AND new gates clear; otherwise REVERT)
- Appends decision to `journal.md` and `iterations/log.csv`
- Commits to current branch (per-iteration commits enable rollback)

### 7.3 KEEP / REVERT decision gates

A variant is KEPT iff ALL of the following hold:

1. Walk-forward Sortino > baseline AND > 0
2. |Sortino| < 10 (sanity)
3. Aggregate-DD does not regress more than 10pp vs prior KEPT
4. Catastrophe-validator clear (gross > 100%, agg-DD > 50%, n_trades < 20)
5. Anti-overfit gates clear (§6: Bonferroni, RW MC, parsimony, stationarity)
6. Sealed-test reveal Sortino > baseline AND > 0

---

## 8. Data layer (`data/`)

### 8.1 News (5y historical + daily forward)

| Source | Endpoint / Method | Coverage | Storage |
|---|---|---|---|
| **MoneyControl per-ticker** | Polite scrape (1 req/sec) of `moneycontrol.com/india/news/<ticker>/...` | 2018-2026, per ticker in universe | `storage/news.duckdb` |
| **Pulse RSS** | `https://pulse.zerodha.com/feed.php` | Daily forward (aggregates MC, ET, BQ); no archive | Same |
| **NSE corporate filings** | `archives.nseindia.com/.../CF_FY*/announcements.zip` | 2018-2026; structured (earnings, M&A, board, regulatory) | `storage/news.duckdb` with `source='nse_filing'` |
| **RBI press releases** | `rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx` | 2018-2026 monetary policy | `storage/news.duckdb` with `source='rbi'`, ticker=NULL |
| **SEBI press releases & orders** | `sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=10` | 2018-2026 regulatory | `storage/news.duckdb` with `source='sebi'`, ticker=NULL |

Dedup: SHA-1 of `(title, source, date)`. Schema unchanged from US repo.

### 8.2 Prices (historical + live)

**Dhan Data API is paid (₹500/month) as of 2026-05-14 — we do not use it.** All price data comes from free NSE public sources. Dhan is used only for *order execution* (Trading API, still free).

| Source | Use | Cost | Volume |
|---|---|---|---|
| **NSE bhav daily ZIP** (`archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv`) | **Primary** historical 5y daily OHLCV + daily forward EOD update | Free | ~1,250 daily ZIPs × ~50KB filtered to our 200-name slice; total ~300 MB after filtering |
| **yfinance Python lib** | Cross-source validation only (corporate-action handling differs from NSE bhav) | Free | Same coverage |
| **NSE indices public JSON** (`nseindia.com/api/allIndices`, `niftyindices.com/IndexConstituent/...`) | Index levels (Nifty 50, India VIX, Nifty 100/500) and constituent history | Free (browser User-Agent header) | Light |
| Dhan `/v2/charts/historical` | NOT USED — paid endpoint | ₹500/mo | — |

Live order placement: **MKT orders** for biweekly rebalance. At our position size (₹5k-10k) and holding period (10 trading days), the 5-10 bps slippage saved by LMT pricing is dwarfed by the ₹14.75 DP charge and the cost of subscribing to live quotes. If we need a single quote at order time (e.g., for risk check sanity), use NSE's free `nseindia.com/api/quote-equity?symbol=...` endpoint with a browser User-Agent.

Storage: `storage/prices.duckdb` (schema unchanged from US repo).

### 8.3 Macro (`data/ingest_macro.py`)

| Indicator | Source | Series ID / Endpoint |
|---|---|---|
| India CPI YoY | FRED | `INDCPIALLAINMEI` |
| India interest rate | FRED | `INTDSRINM193N` |
| USD/INR daily | FRED | `DEXINUS` |
| RBI repo rate | RBI DBIE / manual snapshot | scraped from press releases |
| India VIX | NSE indices | `https://www.nseindia.com/api/allIndices` |
| Nifty 50 / 100 / Midcap 150 daily levels | NSE indices history | NSE bhav indices CSV |
| FII / DII daily net flows | NSE FII/DII | `https://www.nseindia.com/api/fiidiiTradeReact` |

Storage: `storage/macro.duckdb` (schema unchanged from US repo).

### 8.4 Earnings calendar (`data/ingest_earnings.py`)

- Source: NSE corporate filings, category = "Financial Results"
- Per ticker quarterly result dates
- Used by `events` classifier to gate earnings-window exposure

### 8.5 Corporate actions (`data/ingest_corporate_actions.py`)

- Source: NSE bhav files include splits / bonuses; Dhan API also provides corporate-actions endpoint
- Adjusts historical bars when running across split boundaries

---

## 9. Broker layer (`brokers/`)

### 9.1 Dhan HQ REST client (`brokers/dhan.py` — NEW)

- Hand-rolled `requests.Session` against `https://api.dhan.co` (NOT `dhanhq` SDK; debugger-friendly per US repo pattern)
- Public interface: `connect`, `disconnect`, `place_order`, `wait_for_done`, `get_fills`, `get_positions`, `get_holdings`, `get_cash`
- **Trading endpoints only** (`/v2/orders`, `/v2/trades`, `/v2/positions`, `/v2/holdings`, `/v2/fundlimit`). **No `/v2/charts/*` endpoints** — those are part of Dhan's paid Data API. Price data comes from NSE bhav archive (see §8.2).
- Auth: `access-token: ${DHAN_ACCESS_TOKEN}` header + `dhanClientId` in body
- Order type: **MARKET** (`MKT`) default for biweekly rebalance; `LIMIT` (`LMT`) available but not v1 default; `productType=CNC`; `validity=DAY`
- Instrument resolution: download `api-scrip-master.csv` weekly, cache locally; resolve `(ticker, NSE_EQ) → securityId`
- Rate limit handling: 20 req/s — token-bucket guard with backoff

### 9.2 Dhan mock (`brokers/dhan_mock.py` — NEW)

- In-memory implementation of the same public interface as `brokers/dhan.py`
- Used for v1 paper-only operation (no live Dhan account yet)
- Simulates fills at next-bar open with realistic slippage (5 bps default)
- Maintains positions / cash state in-memory or in a sidecar DuckDB
- Mock toggle: `DHAN_MOCK=1` env var → executor uses mock; otherwise uses real REST client

### 9.3 Dhan Executor (`scripts/executors/dhan.py` — NEW)

- Implements `Executor` protocol (carried from US repo)
- Mirrors `IBKRExecutor` pipeline: signal → risk_check → place orders → wait_for_done → reconcile fills → write 8-table ledger
- Idempotent atomic transaction: `BEGIN → delete_day → writes → COMMIT/ROLLBACK` (US repo learnings §2.3)
- Modes: `dhan-paper` (v1), `dhan-live` (built but gated by `halt.json`)
- FRACTION_CHANGE_THRESHOLD = 0.005 carried verbatim (US repo learnings §4.2)

---

## 10. Cost model (`backtest/costs.py` — REWRITE)

```python
def commission_inr(notional_inr: float, side: str) -> float:
    """Dhan delivery + NSE + government charges (₹)."""
    brokerage = 0.0  # Dhan delivery free
    exchange = 0.0000345 * notional_inr  # NSE transaction charges
    sebi = (notional_inr / 10_000_000) * 0.10  # ₹10/crore; negligible
    stt = 0.001 * notional_inr if side == "sell" else 0.0  # 0.1% sell only
    stamp = 0.00015 * notional_inr if side == "buy" else 0.0  # 0.015% buy only
    dp_charge = 14.75 if side == "sell" else 0.0  # ₹12.50 + 18% GST per scrip per sell
    gst = 0.18 * (brokerage + exchange + sebi)
    return brokerage + exchange + sebi + stt + stamp + dp_charge + gst
```

Empirical: round-trip on ₹5k position ≈ ₹20.91 (0.42%); on ₹50k position ≈ ₹72.17 (0.14%). DP charge is the dominant cost at small capital — argues for fewer larger positions.

---

## 11. Tax model

```python
# prepare.py + storage/portfolio_db.py
STCG_RATE = 0.15            # 15% flat, holding < 365 days
LTCG_RATE = 0.10            # 10% on gains > ₹1L per FY, holding ≥ 365 days
LTCG_HOLDING_DAYS = 365
LTCG_THRESHOLD_INR = 100_000
```

Indian FY runs Apr 1 → Mar 31 (US repo's `_fy_start_for` was already written for India — verify and keep). No LRS / Schedule FA / Form 67 / TCS (those are foreign-asset concerns only).

---

## 12. SEBI algo compliance (NEW — was not a US concern)

Effective 2026-04-01, SEBI mandates retail algo registration.

### 12.1 Requirements we meet

| Requirement | Our approach |
|---|---|
| Algo registered with broker | One-time registration via Dhan portal → obtain `SEBI_ALGO_ID` |
| Per-client API keys | Dhan access token is per-client by default |
| Static IP whitelist | User's home IP (or cloud bastion if dynamic). Documented in CLAUDE.md |
| Unique algo ID stamp on every order | Order tag includes `${SEBI_ALGO_ID}` |
| >10 OPS triggers empanelment | We're at ~0.001 OPS (6 orders biweekly). Counter logged in `scripts/sebi_compliance.py` |
| Daily order log retention | Already covered by 8-table ledger |

### 12.2 Compliance module (`scripts/sebi_compliance.py` — NEW)

- Writes daily record: timestamp, algo_id, source_ip, orders_placed, max_burst_ops
- Reads from `cash_ledger` + `submitted_orders` tables
- Surfaces in dashboard for audit-readiness

---

## 13. Architecture (carries from US, new for India)

### 13.1 Carries verbatim or with constant tweaks (~47 files)

From `victorvini08/autoresearch-trading-us` — all the universal logic that's broker- and market-agnostic:

- **Backtester**: `backtest/{engine,metrics,risk}.py`, `prepare.py` walk-forward structure
- **LLM stack**: `llm/{provider,classify,features,cache}.py` (with silent-drop fix from learnings §4.1)
- **Orchestrators**: `scripts/{loop,signal_today,risk_check,halt,promote,daily_report,dashboard,run_live,run_overnight,run_daily,baseline_ablation,ledger_writer,premarket_scan,daily_update,precompute_macro_cache,precompute_news_features}.py`
- **Executor protocol**: `scripts/executors/{__init__,protocol}.py`
- **Storage**: `storage/portfolio_db.py` (8-table schema; mode-scoped PKs; FIFO lots; FY-net tax)
- **Tests**: all engine/metric/risk/llm/halt/loop/portfolio_db/program_md tests

### 13.2 Rewritten or new

- `backtest/costs.py` — Dhan cost model
- `backtest/anti_overfit.py` — NEW: Bonferroni, RW MC, stationarity, parsimony
- `prepare.py` — adds sealed test reveal mechanic + new gates + India tax constants
- `strategy.py` — new starting strategy (12-1 momentum + quality + sector cap + regime gate)
- `data/universe.py` — Nifty 500 filtered top-200 ADV
- `data/ingest_prices.py` — Dhan historical + NSE bhav
- `data/ingest_news.py` — daily forward (Pulse + sources)
- `data/ingest_news_historical.py` — NEW: 5y backfill (MoneyControl + NSE + RBI + SEBI)
- `data/ingest_macro.py` — RBI + FRED India + NSE indices + FII/DII
- `data/ingest_earnings.py` — NSE corporate filings (Results category)
- `data/ingest_corporate_actions.py` — NSE bhav splits/bonuses
- `data/sectors.py` — NSE sector classification map
- `data/quality_screen.py` — NEW: ROE/DE/Op-margin screen
- `brokers/dhan.py` — Dhan REST client
- `brokers/dhan_mock.py` — NEW: in-memory mock for paper-only v1
- `scripts/executors/dhan.py` — DhanExecutor implementing Executor protocol
- `scripts/sebi_compliance.py` — NEW: algo registration + OPS counter
- `llm/prompts.py` — fully rewritten Indian-context (RBI / FII / INR / Nifty / VIX inputs)
- `tests/test_dhan_broker.py`, `tests/test_executors/test_dhan_executor.py`, `tests/test_universe.py`, `tests/test_anti_overfit.py`, `tests/test_costs.py`, `tests/test_quality_screen.py`, `tests/test_sectors.py`, `tests/test_sebi_compliance.py`, etc.

### 13.3 Deleted (US-specific)

- `brokers/ibkr.py`, `scripts/executors/ibkr.py`, `scripts/executors/paper.py` (US simulator)
- `scripts/executor_playwright/` (entire directory — abandoned indmoney browser auto)
- `scripts/{indmoney_login,indmoney_recon,paper_trade,_smoke_compare}.py`
- `data/_nasdaq100_current.txt`, `data/fetch_nasdaq100.py`
- US-specific tests (`test_ibkr_broker`, `test_executor_playwright/`, `test_paper_trade`)

---

## 14. Repository layout

```
autoresearch-trading-india/
├── CLAUDE.md                          # India-specific constraints, SEBI compliance, Dhan setup steps
├── AGENTS.md                          # Mirror of CLAUDE.md for non-CC agents
├── README.md                          # Quickstart
├── program.md                         # Goal + constraints for autoresearch loop
├── journal.md                         # Loop memory; fresh iter 1
├── learnings.md                       # India-specific learnings (carries US insights as historical reference)
├── pyproject.toml                     # uv-managed
├── .env.example                       # DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID, FRED_API_KEY, SEBI_ALGO_ID, DHAN_MOCK
├── .python-version
├── .gitignore
├── prepare.py                         # walk-forward + India tax constants + new gates
├── strategy.py                        # starting strategy: 12-1 mom + quality + sector cap + regime gate
├── backtest/
│   ├── __init__.py
│   ├── engine.py                      # KEEP
│   ├── metrics.py                     # KEEP
│   ├── risk.py                        # KEEP (catastrophe validator)
│   ├── costs.py                       # REWRITE for Dhan
│   └── anti_overfit.py                # NEW
├── brokers/
│   ├── __init__.py
│   ├── dhan.py                        # NEW: REST client
│   └── dhan_mock.py                   # NEW: in-memory mock
├── data/
│   ├── __init__.py
│   ├── universe.py                    # REWRITE: liquid-filtered Nifty 500 top 200 ADV
│   ├── sectors.py                     # NEW: NSE sector map
│   ├── quality_screen.py              # NEW: ROE/DE/Op-margin
│   ├── ingest_prices.py               # REWRITE: Dhan + NSE bhav
│   ├── ingest_news.py                 # REWRITE: Pulse RSS daily forward
│   ├── ingest_news_historical.py      # NEW: 5y MoneyControl + NSE + RBI + SEBI backfill
│   ├── ingest_macro.py                # REWRITE: RBI + FRED India + NSE indices + FII/DII
│   ├── ingest_earnings.py             # REWRITE: NSE filings (Results category)
│   └── ingest_corporate_actions.py    # REWRITE: NSE bhav splits/bonuses
├── llm/
│   ├── __init__.py
│   ├── provider.py                    # KEEP
│   ├── classify.py                    # KEEP (with silent-drop fix)
│   ├── features.py                    # KEEP
│   ├── cache.py                       # KEEP
│   └── prompts.py                     # REWRITE: Indian-context for macro_regime / sentiment / events
├── scripts/
│   ├── __init__.py
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── protocol.py                # KEEP
│   │   └── dhan.py                    # NEW
│   ├── loop.py                        # KEEP (literal-line KEPT match preserved)
│   ├── signal_today.py                # KEEP (broker state + last-rebalance overlay)
│   ├── risk_check.py                  # KEEP
│   ├── halt.py                        # KEEP
│   ├── promote.py                     # KEEP
│   ├── daily_report.py                # TWEAK (₹ formatting, lakh/crore)
│   ├── dashboard.py                   # TWEAK (₹ formatting)
│   ├── _dashboard.py                  # KEEP (autoresearch loop dashboard)
│   ├── run_live.py                    # TWEAK (modes: dhan-paper, dhan-live; IST window)
│   ├── run_overnight.py               # KEEP
│   ├── run_daily.py                   # TWEAK (IST timing)
│   ├── baseline_ablation.py           # KEEP
│   ├── ledger_writer.py               # TWEAK (currency='INR')
│   ├── premarket_scan.py              # TWEAK (NSE pre-open, India VIX)
│   ├── daily_update.py                # TWEAK (swap ingest sources)
│   ├── precompute_macro_cache.py      # TWEAK
│   ├── precompute_news_features.py    # TWEAK
│   ├── dhan_smoke.py                  # NEW: read-only Dhan probe
│   └── sebi_compliance.py             # NEW: algo registration + OPS counter
├── storage/
│   ├── __init__.py
│   ├── portfolio_db.py                # TWEAK (Indian tax constants)
│   ├── .gitkeep
│   └── (duckdb files generated)
├── tests/
│   └── (mirror of US repo, with new tests for Dhan, universe, anti_overfit, sectors, quality)
├── deploy/
│   └── launchd/
│       ├── com.autoresearch.run_daily.plist   # 9:30 IST Mon-Fri
│       └── com.autoresearch.premarket_scan.plist
└── docs/
    ├── handoff-india-pivot.md         # carried from US (historical)
    ├── learnings-from-us-build.md     # carried from US (historical)
    └── superpowers/
        ├── specs/
        │   └── 2026-05-14-india-autoresearch-trading-design.md  # this doc
        └── plans/
            └── 2026-05-14-india-implementation-plan.md          # from writing-plans next
```

---

## 15. Execution timing (IST)

| Job | Time (IST) | Trigger |
|---|---|---|
| `premarket_scan` | 09:00 | launchd |
| `daily_update` (news + macro + price ingest) | 09:15 | launchd |
| `run_live` (rebalance day) | 10:00 | launchd; checks if today is a rebalance day, exits early otherwise |
| `risk_check` + `daily_report` | 15:35 (post-close) | launchd |
| `run_overnight` (autoresearch loop) | 22:00 | manual or launchd |

NSE trading hours: 09:15 - 15:30 IST. Execution window for our biweekly rebalance: 10:00-15:00 IST.

---

## 16. Acceptance criteria (v1)

- [ ] `uv run pytest -q` passes (target: 250+ tests, parity with US repo minus US-specific)
- [ ] `uv run python prepare.py research --synthetic` runs walk-forward end-to-end on synthetic Indian-like prices (full Dhan ingest gated on user token)
- [ ] `dhan-paper` mode runs end-to-end against mock Dhan: signal → orders → fills → 8-table ledger writes
- [ ] Dashboard renders ₹ values, IST timestamps, both `dhan-paper` and `dhan-live` mode tabs (live mode empty until promoted)
- [ ] `CLAUDE.md` documents the Dhan + SEBI setup user actions
- [ ] `journal.md` initialized with iter 1 baseline (12-1 momentum + quality + sector + regime starting strategy)
- [ ] Code pushed to `victorvini08/autoresearch-trading-india` main; 6-8 phase-boundary commits
- [ ] Background ingest complete: FRED macro, NSE FII/DII history, NSE indices history, NSE corporate filings 5y, RBI press 5y, SEBI press 5y
- [ ] User reads CLAUDE.md and follows the documented steps to open Dhan account + generate token

### Out of v1 scope (post-validation)

- 5y Dhan historical price ingest (requires user's access token)
- 5y MoneyControl news scrape (fragile, do supervised)
- LLM classifier 5y backfill pass (~1-2 days background after news ingest)
- Live trading flip (post 4-week paper validation)
- F&O integration
- Intraday signals
- Multi-broker support

---

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Starting strategy doesn't pass anti-overfit gates on Indian data | Expected outcome; loop's job to find a variant that does. Worst case: relax `lookback` or `quality_pct` priors with theoretical justification, re-run. |
| MoneyControl / NSE / RBI / SEBI scrapers break on page changes | Defensive parsing + tests on saved fixtures + Pulse RSS as forward fallback for breaking news. Monitor weekly. |
| Dhan API outage during cron | Single-broker dependency. Build robust retry + Slack alert (post-v1). For v1, manual recovery is acceptable. |
| LLM classifier backfill cost | Subscription-bounded; empty-news short-circuit eliminates ~80% of calls. Worst case: 2 days background time. |
| SEBI algo framework changes | Re-read SEBI 2025 circular quarterly; update `scripts/sebi_compliance.py` and CLAUDE.md as needed. |
| User's home IP not static | Document cloud bastion option (Hetzner CX22 / DigitalOcean basic ~₹500/mo). Not required for v1. |
| Survivorship bias on Nifty 500 historical universe | Monthly historical constituent snapshots from NSE. Documented as a future hardening if v1 ranking proves sensitive. |
| Strategy uses synthetic data only at v1 acceptance | Acceptable — full Dhan price ingest comes with token. Synthetic data tests the *pipeline*, not strategy alpha. |

---

## 18. Open questions deferred to implementation

- Exact `regime_pct` (95th vs 90th vs 99th) — first-pass 95th, loop tunes
- Whether quality screen should be on TTM ROE or 3y-avg ROE — first-pass TTM
- Whether to use raw 252d return or risk-adjusted (Sharpe) momentum — first-pass raw (canonical)
- Sector classification mapping when NSE doesn't list a sector for a name — first-pass `OTHER` bucket
- Whether ATR trailing stop is added before any other loop variant — loop's choice

These are intentionally left for the autoresearch loop and subsequent iterations.

---

## 19. References

- US repo: `https://github.com/victorvini08/autoresearch-trading-us` (private; predecessor architecture)
- Handoff doc: `docs/handoff-india-pivot.md` (file-by-file inventory; carried verbatim)
- Learnings doc: `docs/learnings-from-us-build.md` (Phase 1 insights; carried verbatim)
- Dhan API: `https://dhanhq.co/docs/v2/`
- NSE: `https://www.nseindia.com/`
- RBI DBIE: `https://dbie.rbi.org.in/DBIE/dbie.rbi`
- SEBI retail algo framework: SEBI circular 2025-02-04, effective 2026-04-01
- Pulse: `https://pulse.zerodha.com/`

Academic:
- Jegadeesh & Titman 1993, "Returns to Buying Winners and Selling Losers"
- Asness, Moskowitz, Pedersen 2013, "Value and Momentum Everywhere"
- Novy-Marx 2013, "The Other Side of Value: The Gross Profitability Premium"
- Asness, Frazzini, Pedersen 2019, "Quality Minus Junk"
- DeMiguel, Garlappi, Uppal 2009, "Optimal Versus Naive Diversification"
- Cooper, Gutierrez, Hameed 2004, "Market States and Momentum"
