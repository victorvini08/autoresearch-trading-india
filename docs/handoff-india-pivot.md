# India Markets Pivot — Handoff Document

**Audience:** A fresh Claude Code session that will rebuild this codebase to trade Indian equities via Upstox.

**Goal:** Pivot from US stocks (Nasdaq-100 + IBKR) to Indian stocks (Nifty 100 + Upstox) in one focused 1-day session.

**Status as of 2026-05-14:**
The US-stocks/IBKR path was abandoned after empirically confirming:
- IBKR TWS API rejects fractional stock orders (Error 10243) — hard limitation
- IBKR CP-API supports fractional but charges **1% commission per side** on fractional trades (verified live: $0.60 commission on a $59.57 trade)
- At $500 capital with ~10 positions, every position is fractional → 2% per round-trip → strategy economics broken
- LRS overhead + Cloudflare-blocked indmoney + Alpaca-funding-broken-from-India left no good US path at small capital

For India resident + $500-2k capital + automated trading, **Indian markets are the right fit**. Upstox API is free, Indian commissions scale linearly with trade size (no 1% floor like IBKR fractional), and no LRS/FX/TCS overhead.

---

## 1. Locked decisions (do not re-debate)

| Decision | Choice | Why |
|---|---|---|
| Market | **Indian equities (NSE)** | User is India resident; native market |
| Broker | **Dhan HQ** | Free brokerage on delivery; free API (no subscription); ₹14.75 DP charge per scrip per sell; 20 req/s rate limits (industry's most liberal); algo-first design; access token lasts 1 year. See §17 for empirical cost comparison. **NOTE:** Earlier draft of this doc recommended Upstox — that was based on incomplete research. Upstox actually charges ₹20/order on delivery via API, making it 2-3× more expensive than Dhan. |
| Universe | **Nifty 100** | Analog to Nasdaq-100 — 100 large-cap liquid names with good news coverage |
| Backtester | **backtrader** (unchanged) | Already validated for our strategy shape |
| LLM stack | **Claude Code SDK (primary), Qwen3 fallback** (unchanged) | Same daily-cache pattern, just translate prompts for Indian context |
| Strategy shape | **Rank-retention momentum + ATR trailing stop** (current `strategy.py` logic) | Universal; needs re-validation on Indian data |
| Project structure | **Karpathy 3-file**: `prepare.py` (immutable evaluator), `strategy.py` (editable), `journal.md` (memory) | Unchanged |
| Starting paper capital | **₹50,000** (≈$600) | Realistic small-account starting point; user can adjust |
| LLM model tiering | Sonnet for classifiers, Opus for the autoresearch loop | Unchanged |

## 2. Open questions to confirm with user at session start

1. **Exact starting paper capital** — ₹50k recommended; user may want different.
2. **Universe**: Nifty 100 (recommended) vs Nifty 50 (more concentrated) vs Nifty 200 (more breadth, more noise). Confirm before re-running validation.
3. **Hold period**: current strategy targets 3-5 day swings. Indian retail flows make 5-10 day swings sometimes more profitable. Worth A/B-ing once data is ingested.
4. **Branch strategy**: keep `production-strategy-momentum-rotation` (US) as archive? Create new branch `production-india-momentum`?
5. **Live capital target** when paper validates: ₹50k? ₹2 lakh? Affects whether DP charges (₹15.93 per scrip per sell) materially impact economics.

---

## 3. Architecture: what survives, what changes (file-by-file inventory)

Every Python source file in the repo (excluding `.venv`, `__pycache__`, `iterations/`, `.git/`) is categorized below. **Verified complete against `find . -name '*.py'` on 2026-05-14.**

### Categories

| Category | Meaning |
|---|---|
| **KEEP** | Use verbatim. No changes. |
| **TWEAK** | Same file, minor edits (constants, imports, currency strings). |
| **REWRITE** | Replace contents entirely. Same interface where possible. |
| **DELETE** | No longer relevant. Remove from tree. |

### Backtester + risk

| File | Action | Notes |
|---|---|---|
| `prepare.py` | TWEAK | `STCG_RATE = 0.15`; `LTCG_HOLDING_DAYS = 365`; `LTCG_THRESHOLD_INR = 100_000`; `INITIAL_CASH = 100_000` (₹1L feels right). Walk-forward structure unchanged. |
| `backtest/__init__.py` | KEEP | Trivial init. |
| `backtest/engine.py` | KEEP | backtrader cerebro wrapper. Universal. |
| `backtest/metrics.py` | KEEP | Sortino/Calmar/max_dd. Universal. |
| `backtest/risk.py` | KEEP | Catastrophe validator. Universal. |
| `backtest/costs.py` | REWRITE | IBKR Tiered → Dhan delivery (free brokerage + ₹14.75 DP + STT + GST + stamp duty). See §5 for exact code. |

### Strategy

| File | Action | Notes |
|---|---|---|
| `strategy.py` | TWEAK | Logic universal. Indicator periods (atr_period=20, ranking lookback) may need re-tuning for Indian volatility. First-pass: keep params, run validation, then tune. |
| `strategy_variant_a.py` | DELETE | Autoresearch agent's earlier variant from US run. Indian rebuild starts fresh. |
| `strategy_variant_b.py` | DELETE | Same. |
| `strategy_variant_c.py` | DELETE | Same. |

### Brokers

| File | Action | Notes |
|---|---|---|
| `brokers/__init__.py` | TWEAK | Update docstring to reference Dhan instead of IBKR. |
| `brokers/ibkr.py` | DELETE | US-specific. Already broken for Indian use. |
| `brokers/dhan.py` | **CREATE** | New file, ~400 LOC. Hand-rolled REST client against `https://api.dhan.co`. Same public interface as old `IBKRBroker` so executor is plug-compatible. See §4 for endpoints. |

### Data ingest (the layer that gets fully replaced)

| File | Action | Notes |
|---|---|---|
| `data/__init__.py` | KEEP | Trivial init. |
| `data/universe.py` | REWRITE | Nasdaq-100 hardcoded list → Nifty 100 from NSE CSV. Lock to snapshot date for survivorship safety. |
| `data/fetch_nasdaq100.py` | DELETE | US-specific one-shot universe fetcher. |
| `data/ingest_prices.py` | REWRITE | yfinance → Dhan historical API OR NSE bhav copy files. Same `storage/prices.duckdb` schema. |
| `data/ingest_news.py` | REWRITE | Finnhub → Pulse-by-Zerodha RSS + NSE corporate announcements. Same `storage/news.duckdb` schema. |
| `data/ingest_general_news.py` | REWRITE | Alpha Vantage NEWS_SENTIMENT topics → Pulse RSS + ET Markets RSS for macro context. Used by `macro_regime` prompt. |
| `data/ingest_macro.py` | REWRITE | FRED → RBI DBIE for repo rate, CPI, USD/INR; NSE for India VIX, Nifty indices. |
| `data/ingest_earnings.py` | REWRITE | yfinance calendar → NSE corporate announcements filtered for "Financial Results". |
| `data/ingest_corporate_actions.py` | REWRITE | yfinance `Ticker.actions` → NSE bhav splits/bonuses OR Dhan API corporate-actions endpoint. |

### LLM stack (mostly universal, except prompts)

| File | Action | Notes |
|---|---|---|
| `llm/__init__.py` | KEEP | Trivial init. |
| `llm/provider.py` | KEEP | Claude Code / Codex / Qwen3 abstraction. Subscription-aware via local CLI auth. Universal. |
| `llm/classify.py` | KEEP | Batch classifier engine. **Fix the silent-drop bug** at line 262-264 (see learnings doc §4.1). Universal. |
| `llm/features.py` | KEEP | macro_regime / sentiment / events accessors. Universal. |
| `llm/cache.py` | KEEP | sqlite cache keyed by `(date, ticker, prompt_hash, model_id)`. Universal. |
| `llm/prompts.py` | **REWRITE** | **All prompts (macro_regime, sentiment, events) are US-context.** Need Indian-context rewrite: macro inputs = RBI repo + FII/DII flows + INR + India VIX (not Fed/USD/DXY); sentiment templates reference Indian companies + INR amounts. Bump `MACRO_REGIME_PROMPT_VERSION` to invalidate cache cleanly. |

### Scripts — orchestrators + utilities

| File | Action | Notes |
|---|---|---|
| `scripts/__init__.py` | KEEP | Trivial init. |
| `scripts/run_live.py` | TWEAK | Default `EXECUTION_MODE='dhan-paper'`; `_SUPPORTED_MODES=('dhan-paper','dhan-live')`; `EXECUTION_WINDOW_IST=(time(10,0), time(15,0))`. Otherwise unchanged. |
| `scripts/run_daily.py` | TWEAK | Adjust IST timing (no overnight wait needed since user is in same TZ as market). |
| `scripts/run_overnight.py` | KEEP | Autoresearch overnight harness. Universal. |
| `scripts/signal_today.py` | KEEP | Strategy → target dict extractor. Universal. |
| `scripts/loop.py` | KEEP | Autoresearch KEEP/REVERT loop driver. Universal. **Preserve the literal-line parse for `**Decision:** KEPT`** (learnings §4.4). |
| `scripts/risk_check.py` | KEEP | Operational risk gates. Universal. RiskParams stay (max_position_frac=0.20, max_gross_exposure=1.00). |
| `scripts/halt.py` | KEEP | halt.json management. Universal. |
| `scripts/daily_report.py` | TWEAK | Format INR amounts (₹ symbol, lakh/crore conventions); strip references to "Indmoney / IBKR" specific things. |
| `scripts/dashboard.py` | TWEAK | Same as daily_report — currency formatting. |
| `scripts/_dashboard.py` | KEEP | Autoresearch-LOOP dashboard (iterations/log.csv → HTML). Universal. Different from `dashboard.py`. |
| `scripts/_smoke_compare.py` | DELETE | paper_trade comparator. paper_trade is gone. |
| `scripts/ledger_writer.py` | TWEAK | Currency='INR' for new mode rows; otherwise unchanged. |
| `scripts/premarket_scan.py` | TWEAK | Logic universal; swap data sources to Indian (NSE pre-open feed, India VIX). |
| `scripts/daily_update.py` | TWEAK | Logic universal; swap to Indian ingest functions. |
| `scripts/precompute_macro_cache.py` | TWEAK | Logic universal; swap macro inputs. |
| `scripts/precompute_news_features.py` | TWEAK | Logic universal; swap news inputs. |
| `scripts/promote.py` | KEEP | Promotion-gate utility (sealed-test reveal). Universal. |
| `scripts/baseline_ablation.py` | KEEP | Strategy ablation utility. Useful for the rebuild's first validation. |
| `scripts/ibkr_smoke.py` | DELETE | IBKR-specific read-only probe. |
| `scripts/indmoney_login.py` | DELETE | Indmoney browser auth (abandoned). |
| `scripts/indmoney_recon.py` | DELETE | Indmoney reconciliation (abandoned). |

### Executors

| File | Action | Notes |
|---|---|---|
| `scripts/executors/__init__.py` | TWEAK | Update exports: `DhanExecutor` instead of `IBKRExecutor`. |
| `scripts/executors/protocol.py` | KEEP | Executor interface. Universal. |
| `scripts/executors/ibkr.py` | DELETE | IBKR-specific. |
| `scripts/executors/dhan.py` | **CREATE** | New file, ~600 LOC. Mirrors `IBKRExecutor` logic but uses `DhanBroker`. ~95% of the per-day pipeline (signal → risk → orders → wait → reconcile → ledger write) is reusable; only the broker call lines change. |

### Executor playwright (entire directory — abandoned, all DELETE)

`scripts/executor_playwright/` — entire dir: `__init__.py`, `auth.py`, `errors.py`, `fills.py`, `orders.py`, `positions.py`, `selectors.py`.

The entire `scripts/executor_playwright/` directory was the indmoney browser-automation attempt that we abandoned when Cloudflare blocked it. Not needed.

### Storage

| File | Action | Notes |
|---|---|---|
| `storage/__init__.py` | KEEP | |
| `storage/portfolio_db.py` | TWEAK | `STCG_RATE=0.15`; `LTCG_RATE=0.10`; `LTCG_HOLDING_DAYS=365`; `LTCG_THRESHOLD_INR=100_000`; `_fy_start_for` already Apr-Mar (correct for India). Schema columns unchanged — `currency` column accepts 'INR'. |

### Tests — KEEP / TWEAK

| File | Action | Notes |
|---|---|---|
| `tests/test_smoke.py` | KEEP | Trivial dependency-discovery test. |
| `tests/test_engine.py` | KEEP | backtrader engine test. Universal. |
| `tests/test_prepare.py` | TWEAK | Update constants references; verify walk-forward fold structure still asserts correctly. |
| `tests/test_metrics.py` | KEEP | Sortino/Calmar tests. Universal. |
| `tests/test_risk.py` | KEEP | Catastrophe validator tests. Universal. |
| `tests/test_strategy_retention.py` | KEEP | Rank-retention + ATR stop synthetic-data tests. Universal. |
| `tests/test_signal_today.py` | KEEP | signal_today projection logic. Universal. |
| `tests/test_run_live.py` | TWEAK | Update mode strings (`'dhan-paper'` instead of `'ibkr-paper'`). |
| `tests/test_halt.py` | KEEP | halt.json mechanics. Universal. |
| `tests/test_risk_check.py` | KEEP | Operational risk gates. Universal. |
| `tests/test_loop_journal.py` | KEEP | Journal parsing tests (preserve literal-line match). |
| `tests/test_premarket_scan.py` | TWEAK | Update data-source mocks. |
| `tests/test_daily_report.py` | TWEAK | Currency formatting; mode names. |
| `tests/test_dashboard.py` | TWEAK | Same. |
| `tests/test_e2e.py` | REVIEW | May reference deleted code; needs visual inspection on rebuild. Likely TWEAK. |
| `tests/test_portfolio_db.py` | TWEAK | Currency='INR'; tax rate constants. |
| `tests/test_program_md.py` | KEEP | Just checks program.md exists/parses. Universal. |
| `tests/test_llm_cache.py` | KEEP | Cache mechanics universal. |
| `tests/test_llm_features.py` | KEEP | Accessor universal. |
| `tests/test_llm_provider.py` | KEEP | Provider abstraction universal. |
| `tests/test_classify_events.py` | TWEAK | Update prompt content references (Indian context). |
| `tests/test_classify_macro.py` | TWEAK | Same. |
| `tests/test_classify_sentiment.py` | TWEAK | Same. |
| `tests/test_precompute_macro.py` | TWEAK | Update inputs. |
| `tests/test_executors/__init__.py` | KEEP | |

### Tests — REWRITE / DELETE / CREATE

| File | Action | Notes |
|---|---|---|
| `tests/test_costs.py` | REWRITE | New cost model for Dhan delivery. |
| `tests/test_universe.py` | REWRITE | Test against Nifty 100 instead of NDX names. |
| `tests/test_ingest_prices.py` | REWRITE | New data source (Dhan / NSE bhav). |
| `tests/test_ingest_news.py` | REWRITE | New data source (Pulse RSS + NSE corp announcements). |
| `tests/test_ingest_macro.py` | REWRITE | New data source (RBI DBIE). |
| `tests/test_ingest_earnings.py` | REWRITE | New data source (NSE corporate filings). |
| `tests/test_prompts.py` | REWRITE | Prompt content tests need full rewrite for Indian-context prompts. |
| `tests/test_ibkr_broker.py` | DELETE | Replaced by `test_dhan_broker.py`. |
| `tests/test_executors/test_ibkr_executor.py` | DELETE | Replaced by `test_dhan_executor.py`. |
| `tests/test_executor_playwright/` | DELETE | Entire dir (7 files): `__init__.py`, `test_deltas.py`, `test_errors.py`, `test_fills_polling.py`, `test_limit_price.py`, `test_qty.py`, `test_selectors_assertion.py`. |
| `tests/test_dhan_broker.py` | **CREATE** | Mock `requests.Session` against Dhan endpoints; cover connect/disconnect, place_order success+reply-chain, wait_for_done polling, get_fills, get_positions, get_cash. ~17 tests like the IBKR pattern. |
| `tests/test_executors/test_dhan_executor.py` | **CREATE** | Stub broker (in-memory) + synthetic prices.duckdb; verify halt-blocking, idempotency, full buy cycle (lots+cash+positions), FRACTION_CHANGE_THRESHOLD suppression. ~6 tests. |

### Non-Python files

| File | Action | Notes |
|---|---|---|
| `pyproject.toml` | TWEAK | Drop `playwright` (no browser), drop `ib_async` (no IBKR), add `requests` if not already; otherwise unchanged. |
| `scripts/launchd/com.autoresearch.run_daily.plist` | TWEAK | Fire time → ~9:30 IST (Mon-Fri); `EXECUTION_MODE=dhan-paper`. |
| `CLAUDE.md` | TWEAK | Remove US-specific constraints (LRS, browser execution, indmoney); add Indian-specific constraints (Dhan API, NSE universe, INR-denominated). |
| `program.md` | TWEAK | Update goal/constraints to reference Indian market. |
| `journal.md` | KEEP | Persist across pivot — the autoresearch loop's memory is universal. New entries on Indian rebuild append cleanly. |
| `learnings.md` | KEEP | Same. |
| `.env`, `.env.example` | TWEAK | Drop IBKR/Alpha Vantage/Finnhub; add `DHAN_ACCESS_TOKEN`, `DHAN_CLIENT_ID`. |
| `docs/handoff-india-pivot.md` | KEEP | This document. |
| `docs/learnings-from-us-build.md` | KEEP | Companion learnings doc. |
| `docs/superpowers/specs/*.md` | KEEP | Historical design docs. Reference material; rebuild can append new ones for India-specific decisions. |
| `iterations/log.csv` | RESET | Wipe the US-run iteration log; Indian rebuild starts iteration count from 1 on new branch. |
| `iterations/<iter_id>/` directories | DELETE | All per-iteration artifacts from US run. |
| `storage/prices.duckdb` | RESET | Wipe; fresh ingest on Nifty 100. |
| `storage/news.duckdb` | RESET | Wipe; fresh Indian news ingest. |
| `storage/macro.duckdb` | RESET | Wipe; fresh RBI / NSE macro ingest. |
| `storage/earnings.duckdb` | RESET | Wipe; fresh NSE corporate filings ingest. |
| `storage/corp_actions.duckdb` | RESET | Wipe; fresh NSE corp actions ingest. |
| `storage/portfolio.duckdb` | KEEP-OR-RESET | User's call. Old US-mode rows are harmless (mode-scoped). Cleaner to start fresh. |
| `storage/llm_cache.sqlite` | RESET | Wipe entirely. New model_ids + new prompts → cache invalidates anyway, but cleaner to start fresh. |

### Final tally

- **KEEP verbatim:** 24 files (architecture + universal logic)
- **TWEAK (constants/imports/currency):** 23 files (mostly orchestrator + tests)
- **REWRITE (same interface, new implementation):** 13 files (data layer + cost model + prompts)
- **DELETE:** 25 files (US-/indmoney-/IBKR-specific + abandoned browser layer)
- **CREATE (new for Indian):** 4 files (`brokers/dhan.py`, `scripts/executors/dhan.py`, `tests/test_dhan_broker.py`, `tests/test_executors/test_dhan_executor.py`)

The architecture survives. The data layer and broker layer are what change. Estimated effort confirmed: ~9-10 hours of focused work for the full pivot.

---

## 4. Recommended tech stack (detailed)

### Broker: Dhan HQ (primary recommendation)

- **Docs:** https://dhanhq.co/docs/v2/
- **Python SDK:** `dhanhq` on PyPI (`pip install dhanhq` or via uv add). Maintained `dhan-oss/DhanHQ-py` on GitHub.
- **Auth:** Static access token model. Generate from https://web.dhan.co/dhan-hq → API Section → "Generate Access Token". Token lasts 1 year (longer than Upstox's daily renewal or IBKR's 24h reauth — a real ops advantage).
- **Free tier:** Yes, completely free. No subscription, no per-order fee for free API tier. 20 req/sec rate limit (industry's most liberal), 100,000 requests/day for historical data.
- **Endpoints we'll use** (base: `https://api.dhan.co`):
  - `POST /v2/orders` — place an order
  - `GET /v2/orders/{order-id}` — order status
  - `DELETE /v2/orders/{order-id}` — cancel
  - `GET /v2/orders` — all today's orders
  - `GET /v2/trades` — today's executions (with commission)
  - `GET /v2/positions` — current positions
  - `GET /v2/holdings` — long-term holdings
  - `GET /v2/fundlimit` — cash + margin available
  - `GET /v2/charts/historical` — historical OHLCV daily/intraday
  - `GET /v2/charts/intraday` — intraday bars
- **Order types Dhan supports:** MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET. For our LMT swing strategy: `orderType='LIMIT'`, `validity='DAY'`, `productType='CNC'` (Cash & Carry, i.e. delivery).
- **Instrument identification:** Dhan uses two IDs together:
  - `securityId` (int) — Dhan's internal ID for the instrument
  - `exchangeSegment` (str) — e.g. `'NSE_EQ'`
  - Master list downloadable from: `https://images.dhan.co/api-data/api-scrip-master.csv` (free, public). Cache locally once per day.
- **WebSocket:** `wss://api-feed.dhan.co` — real-time market data + order updates. Optional for v1; polling /orders every 5s suffices for swing trading.

**Python SDK:** Dhan provides `dhanhq` on PyPI. **Recommendation:** hand-roll with requests (we have a working pattern from prior CP-API client). The SDK is fine but pulls in extra deps; our hand-rolled REST pattern is debugger-friendly and matches what worked for IBKR.

### Why NOT Upstox (despite earlier recommendation in this doc)

Empirical pricing (see §17): Upstox charges **₹20/order on delivery via API** (₹10 promo until Dec 31, 2025; reverts to ₹20 after). Round-trip on a ₹5,000 trade with Upstox is ₹66.71 (1.33% of position) vs Dhan's ₹20.91 (0.42%). At 50 round-trips/year, that's a **45 percentage-point** annual drag difference. Not viable.

Upstox is still a fine UI/retail broker; just not for our API-driven swing trading at small capital.

### Why NOT Zerodha (yet)

Zerodha Kite Connect made orders + account APIs free in March 2025. But **historical data + real-time quotes API costs ₹500/month**. That's ₹6,000/year of fixed cost = 12% of ₹50,000 paper capital per year. Even excellent strategy performance doesn't justify that on small capital.

**Migration trigger:** when paper capital scales to ₹5L+ (~$6k+), the ₹6,000/yr data fee becomes 0.12% of capital — negligible. At that point Zerodha's community, maturity, and tooling justify the migration.

### Historical price data (5 years for backtest)

**Two options, recommend using both with a preference:**

1. **Upstox historical candle API (primary)** — `GET /v3/historical-candle/...`
   - Free, no auth needed for some endpoints (some need bearer token)
   - 5+ years of daily bars available
   - 1m/5m/30m/day/week/month intervals
   - JSON response, fast
   - **Bulk-ingest 100 tickers × 5 years × daily = manageable in one batch run**

2. **NSE bhav copy (fallback / cross-source validation)** — `https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20100`
   - Free, official, daily ZIP file with all NSE EOD bars
   - For prior-day validation across symbols
   - URL pattern: `https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv`
   - Use for the structural integrity checks (positive prices, OHLC bounds)

**For autoresearch loop**: store all in `storage/prices.duckdb` (same schema as today, no changes).

### News data

**Recommend layered approach:**

1. **Pulse by Zerodha (primary)** — `https://pulse.zerodha.com/`
   - Aggregates MoneyControl, ET, Bloomberg Quint, etc.
   - Public RSS feed: `https://pulse.zerodha.com/feed.php`
   - No auth, no rate limit
   - Headlines tagged with relevant tickers (sometimes)
   - **Best free source for general market news**

2. **NSE corporate announcements (filter by ticker)** — `https://www.nseindia.com/companies-listing/corporate-filings-announcements`
   - Free, official, structured data
   - Per-ticker corporate actions, results, regulatory filings
   - Need to scrape (no official API for retail)
   - Critical for the `events` LLM classifier (earnings, M&A, board changes)

3. **MoneyControl RSS** (per-ticker, supplementary) — `https://www.moneycontrol.com/news/business/stocks.rss`
   - Per-section feeds available
   - Good for sentiment classifier

4. **Inshorts (general macro context)** — unofficial API, gives 60-char summaries
   - Use if regulatory or geopolitical news isn't well-covered elsewhere

**Don't use:** Finnhub (US-focused), Alpha Vantage News (US-only for news), Bloomberg API (paywall), Marketaux free tier (limited).

### Macro data

- **RBI Database on Indian Economy (DBIE)** — `https://dbie.rbi.org.in/DBIE/dbie.rbi`
  - Free, official
  - Repo rate, CRR, CPI, IIP, USD/INR, FX reserves, money supply
- **FRED still useful** — has India CPI, India interest rate, USD/INR FX (already integrated in current `ingest_macro.py`, just swap which indicators are pulled)
- **NSE indices** — direct from NSE: Nifty 50, Bank Nifty, Nifty IT, India VIX
  - `https://www.nseindia.com/api/allIndices`
  - Free, daily values
- **Government data portal** (`data.gov.in`) — additional macro indicators, slower update cycle

Adapt the `macro_regime` LLM classifier prompt: instead of "risk-on/risk-off based on VIX + USD + 10Y", use "Bull/Bear/Neutral on Indian equities based on India VIX, repo rate trajectory, FII/DII flows, INR strength".

### Corporate actions (splits, dividends, bonuses)

- **Upstox API includes** corporate-actions data in the instrument metadata
- **NSE bhav files** include split/bonus adjustments
- For backtest accuracy: ingest into `storage/corp_actions.duckdb` (same schema as today). Critical to back-adjust historical bars when running across split boundaries.

### Earnings calendar

- **NSE corporate announcements feed** (filter for "Financial Results")
- **Tickertape (unofficial scraping)** has cleaner forward calendar but use sparingly
- For each ticker in universe, fetch quarterly result dates; gate the strategy to avoid holding through earnings if our analysis says they're a fragile time (this is a strategy choice we made for US, should re-examine for India where most reports beat consensus initially then drift down).

---

## 5. Cost model — real numbers for Dhan HQ delivery trading

```python
# backtest/costs.py rewrite
def commission_inr(notional_inr: float, side: str) -> float:
    """Dhan + NSE + government charges for delivery trading.

    Per executed order (one side):
      - Brokerage: ₹0 (Dhan delivery is FREE)
      - STT: 0.1% × notional (SELL ONLY)
      - Exchange transaction charges (NSE): 0.00345% × notional
      - SEBI charges: ₹10 per crore (negligible)
      - GST: 18% on (brokerage + exchange + SEBI)
      - Stamp duty: 0.015% × notional (BUY ONLY)
      - DP charges: ₹12.50 + GST = ₹14.75 per scrip per debit (SELL ONLY)
    """
    brokerage = 0.0  # Dhan delivery free
    exchange = 0.0000345 * notional_inr
    sebi = (notional_inr / 10_000_000) * 0.10  # ₹10/crore, negligible

    stt = 0.001 * notional_inr if side == "sell" else 0.0
    stamp = 0.00015 * notional_inr if side == "buy" else 0.0
    dp_charge = 14.75 if side == "sell" else 0.0  # Dhan: ₹12.50 × 1.18 GST

    gst_base = brokerage + exchange + sebi  # 18% GST on these
    gst = 0.18 * gst_base

    return brokerage + exchange + sebi + stt + stamp + dp_charge + gst
```

### Empirical cost projections (Dhan delivery)

For ₹50,000 capital, 10 positions (₹5,000 each):

| Trade size | Brokerage | STT (sell) | DP (sell) | Exch + GST | All charges (round-trip) | % of position |
|---|---|---|---|---|---|---|
| ₹5,000 (≈$60) | ₹0 | ₹5 | ₹14.75 | ~₹1.16 | **~₹20.91** | **0.42%** |
| ₹10,000 (≈$120) | ₹0 | ₹10 | ₹14.75 | ~₹1.85 | ~₹26.60 | 0.27% |
| ₹20,000 (≈$240) | ₹0 | ₹20 | ₹14.75 | ~₹3.24 | ~₹37.99 | 0.19% |
| ₹50,000 (≈$600) | ₹0 | ₹50 | ₹14.75 | ~₹7.42 | ~₹72.17 | 0.14% |

**Honest comparison vs IBKR:**

| Capital | Indian (Dhan) round-trip | US (IBKR fractional CP-API) | Winner |
|---|---|---|---|
| $500 / ₹40k | 0.42% | 2.0% | **Dhan (4.8× cheaper)** |
| $1k / ₹80k | 0.27% | 2.0% | Dhan (7× cheaper) |
| $5k / ₹4L | 0.14% | 0.7% (mixed whole/frac) | Dhan (5× cheaper) |
| $10k / ₹8L | 0.10% | 0.07% (whole) | IBKR (slight edge) |

**Below ~$8k capital, Dhan dominates. Above ~$10k, IBKR's whole-share Tiered breaks even or wins.** For the user's $500-2k real-money target, Dhan is the right call by a large margin.

**Important caveat: DP charges (₹14.75) are a per-scrip flat sell fee, not percentage.** This means many small positions amplify the drag. Strategy implication: prefer fewer, larger positions over many small ones. At ₹50k capital with 10 positions, DP charges alone are ~3% of capital per full-rotation. **Recommend reducing to 5-6 positions at ₹50k capital, scaling up to 10 positions only at ₹1L+ capital.**

---

## 6. Tax model — Indian equities, India resident

Adjust `prepare.py` constants and `storage/portfolio_db.compute_tax()`:

```python
# prepare.py
STCG_RATE = 0.15   # 15% flat for stocks held < 12 months (Indian equities)
LTCG_RATE = 0.10   # 10% on gains > ₹1 lakh per FY, stocks held ≥ 12 months
LTCG_THRESHOLD_INR = 100_000  # ₹1 lakh annual exemption
```

```python
# storage/portfolio_db.compute_tax()
LTCG_HOLDING_DAYS = 365   # 1 year (was 730 for US/STCG cutoff)
STCG_RATE = 0.15
LTCG_RATE = 0.10

def compute_tax(realized_pnl_inr: float, holding_days: int) -> float:
    if realized_pnl_inr <= 0:
        return 0.0
    if holding_days < LTCG_HOLDING_DAYS:
        return realized_pnl_inr * STCG_RATE
    # LTCG: 10% above ₹1L threshold — handled at FY-net level in
    # get_ytd_tax_estimate, not per-trade
    return realized_pnl_inr * LTCG_RATE
```

The FY-net STCG/LTCG accounting in `portfolio_db.get_ytd_tax_estimate()` needs minor rework — Indian FY runs Apr 1 → Mar 31 (already what the function does, since `_fy_start_for` was written for India anyway). Verify.

**Other regulatory:**
- **No LRS overhead** (only applies to foreign assets)
- **No Schedule FA** (only applies to foreign assets)
- **No Form 67** (DTAA, only for foreign tax credit)
- **No TCS on remittances** (TCS only applies to outbound LRS remittances)
- **Schedule CG**: regular capital gains schedule in ITR — straightforward for Indian equities

---

## 7. Strategy considerations for Indian market

The current strategy (rank-retention momentum + ATR trailing stop, ~10 positions equal-weight) has these characteristics that **may need adjustment** for Indian markets:

| Characteristic | US markets behavior | Indian markets behavior | Likely action |
|---|---|---|---|
| Retail participation | ~10-15% of volume | ~30-40% of volume | Higher noise → maybe widen entry filters |
| Sector rotation | Visible, multi-month cycles | More crowded into a few sectors at a time | Sector cap may be needed |
| Earnings volatility | ±5-8% on results | ±10-15% on results | Tighter earnings-window exit |
| Stock-specific news weight | Moderate | High | Sentiment classifier may have more signal |
| Macro regime | Fed-driven | RBI + INR + global crude | Different macro inputs |
| Settlement | T+1 (recently) | T+1 (since Jan 2023) | No change |
| Holding-period skew | 3-5 day swings common | 5-10 day swings sometimes more profitable | A/B test rebalance cadence |
| Survivorship bias | Nasdaq-100 fairly stable | Nifty 100 has more churn | Lock constituents to entry-date snapshot, watch for delistings |

**Recommended first-pass approach:**
1. Port strategy with **same params**
2. Validate on Indian 2018-2025 walk-forward (mean Sortino target ≥ 1.0)
3. If validation reasonable: paper-trade live for 4 weeks
4. If not: tune ATR multiplier (5× may be wrong for Indian volatility), then revalidate

**Don't optimize on Indian-specific intuitions before validating.** Run the strategy as-is first. Treat divergence from US results as data, not a problem to solve.

---

## 8. Implementation order (the 1-session rebuild script)

A focused session should execute roughly in this order:

### Phase 1: Foundation (~30 min)
1. New branch: `production-india-momentum` from `main` (NOT from current `production-strategy-momentum-rotation`, which has US-specific changes)
2. Delete US-specific files listed in §3
3. Update `pyproject.toml`: remove `playwright` (no browser needed); requests + duckdb + backtrader stay
4. Update `data/__init__.py` and other module init files

### Phase 2: Data layer (~3 hours)
5. Write `data/universe.py` — fetch Nifty 100 constituents from NSE (https://www1.nseindia.com/content/indices/ind_nifty100list.csv)
6. Write `data/ingest_prices.py` — Upstox historical API, ingest 5 years × 100 tickers to `storage/prices.duckdb`
7. Write `data/ingest_macro.py` — RBI repo rate, India VIX, USD/INR FX from FRED + NSE indices
8. Write `data/ingest_corporate_actions.py` — NSE bhav splits/bonuses
9. Write `data/ingest_earnings.py` — NSE corporate filings (filter for Results category)
10. Write `data/ingest_news.py` — Pulse RSS + NSE announcements
11. **Run a bulk ingest** to populate all the storage DBs (this is mostly compute time, ~30 min for 5 years × 100 tickers via Upstox)

### Phase 3: Broker layer (~2 hours)
12. Write `brokers/upstox.py` — same public interface as `IBKRBroker` (connect, disconnect, place_order, wait_for_done, get_fills, get_positions, get_cash)
13. Write `tests/test_upstox_broker.py` — mock requests.Session for unit tests
14. Smoke test: connect → get_cash → get_positions → place small order → cancel
15. Rename `scripts/executors/ibkr.py` → `scripts/executors/upstox.py`. Replace `IBKRBroker` import with `UpstoxBroker`. Update mode names (`'upstox-paper'`, `'upstox-live'`). The Executor logic itself shouldn't need changes.

### Phase 4: Cost + risk (~30 min)
16. Rewrite `backtest/costs.py` per §5
17. Update `prepare.py` constants per §6
18. Update `storage/portfolio_db.py:compute_tax()` and `LTCG_HOLDING_DAYS`
19. Re-run `tests/test_costs.py` against new model

### Phase 5: Validation (~2 hours, mostly compute time)
20. Run `uv run python prepare.py research` — walk-forward Sortino validation
21. Check: does the strategy clear validation_sortino_mean ≥ 1.0 on Indian data?
22. If yes: proceed to paper-trade smoke. If no: stop, tune, retry.

### Phase 6: Live wire-up (~1 hour)
23. Update `scripts/run_live.py` — default mode `'upstox-paper'`, `_SUPPORTED_MODES = ('upstox-paper', 'upstox-live')`
24. Update `scripts/run_daily.py` — adjust execution window for IST (9:30-15:00 IST instead of ET window) — see §9
25. Update launchd plist — `EXECUTION_MODE=upstox-paper`, schedule for ~10:00 IST (right after market open)
26. Reset paper account state in `portfolio.duckdb` — wipe old `mode='paper'` and `mode='ibkr-paper'` rows; add ₹50,000 seed
27. Manual smoke test: `uv run python -m scripts.run_live --date <today>`

### Phase 7: Documentation update (~30 min)
28. Update `CLAUDE.md` constraints (no LRS, INR-denominated, NSE universe)
29. Update `program.md` (autoresearch loop instructions)
30. Update `journal.md` and `learnings.md` — note the pivot, what carries over from US insights, what doesn't

**Total: ~1 long focused day (9-10 hours including compute time for data ingest and validation runs).**

---

## 9. Timing — IST execution window

US market hours were 9:30–16:00 ET = 19:00–01:30 IST (overnight for the user).

Indian market hours: **9:15–15:30 IST**.

`scripts/run_live.py` `EXECUTION_WINDOW_ET` becomes `EXECUTION_WINDOW_IST = (time(10, 0), time(15, 0))`. Inside that window any trade time is fine.

`scripts/run_daily.py` cron timing: fire at **~9:30 IST** (15 min after market open, spreads have normalized). The wait-gate becomes unnecessary — by the time daily_update finishes (~5-10 min), we're inside the trading window.

LaunchD plist update: fire Mon-Fri 9:30 IST.

---

## 10. Dhan HQ setup checklist (user action items)

Before the rebuild session, the user needs to do these one-time setups:

1. **Open Dhan account** (if not already) at https://dhan.co — provide PAN + Aadhaar + bank account. Online process; usually completes within a day.
2. **Activate trading**: enable equity delivery segment (default for new accounts). For F&O / commodities (we don't need v1), separate activation required.
3. **Generate access token**:
   - Log in to https://web.dhan.co
   - Top-right profile menu → "DhanHQ Trading APIs" or directly: https://web.dhan.co/dhan-hq
   - Click "Generate Access Token" — token is valid for ~1 year (one-time, no daily refresh hassle, unlike Upstox/IBKR)
4. **Note your `dhan_client_id`** (visible in the API section; format like `1000001234`)
5. **Save credentials in `.env`**:
   ```
   DHAN_ACCESS_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
   DHAN_CLIENT_ID=1000001234
   ```
6. **Token renewal**: the 1-year validity means we don't need IBeam-style daemons. Just regenerate annually. Set a calendar reminder for ~340 days from generation.
7. **Sandbox / paper testing**: Dhan offers a sandbox at https://developer.dhanhq.co with fixed-price simulated fills. Useful for API integration testing but **NOT for performance benchmarking** (fills always at ₹100, not real prices). For realistic paper-trade validation, we'll use a small live-account capital (₹5k-10k) instead.

---

## 11. Risks & gotchas

| Risk | Mitigation |
|---|---|
| Strategy doesn't validate on Indian data | If validation Sortino < 1.0, stop, tune ATR multiplier and rank lookback before going live |
| Upstox daily token expiry breaks cron | First month: manual reauth each morning. Phase 2: automated TOTP flow |
| News scraping fragility (RSS works, HTML scrape breaks) | Prefer official feeds (NSE corporate filings RSS, Pulse RSS) over HTML scraping |
| NSE bhav file delays (sometimes posted 30+ min late) | Use Upstox API for daily prices; bhav files only for cross-source validation |
| Survivorship bias on Nifty 100 | Snapshot constituents on backtest start date; ignore later additions/deletions in walk-forward; revisit for v2 |
| Survivorship bias on stock-level (delistings) | Filter out tickers with < N bars in window (same as current `_MIN_BARS_PER_FEED` logic) |
| DP charges destroy small-trade economics | Strategy should favor fewer, larger positions. Consider reducing position count from 10 → 5-6 at small capital |
| Earnings window risk amplified in India (±15% moves common) | Strategy has `events` LLM classifier already; verify it actually filters Indian earnings-impacted names |
| Indian market closures (holidays) differ from US | `_trading_days_in_window` reads from prices.duckdb so this is automatic once data is in |
| INR vs USD reporting | Portfolio DB schema is currency-agnostic. Just write `currency='INR'` on cash_ledger rows. Reports format INR explicitly. |
| Mutual fund / ETF lot sizes (some Nifty ETFs trade in lots) | Use only "EQ" series for Nifty 100; avoid ETFs in v1 |
| Strategy uses `order_target_percent` (backtrader) | This is universal — works on any backtrader-supported broker scheme |

---

## 12. Test plan post-rebuild

Once Phase 6 (live wire-up) completes:

1. **Unit tests**: `uv run pytest -q` — should pass with same count as before (~300+ tests) minus US-specific tests, plus new Upstox tests
2. **Smoke test (read-only)**: `uv run python -m scripts.upstox_smoke` — connect, fetch cash, list positions
3. **Smoke test (one tiny order)**: place 1 share of a ₹50-₹200 stock (HDFCBANK at ~₹1500, ITC at ~₹450), wait for fill, cancel
4. **End-to-end paper trade**: `uv run python -m scripts.run_live --date <today>` against ₹50k paper capital
5. **Verify ledger writes**: query `portfolio.duckdb` for desired_targets, submitted_orders, actual_fills, broker_positions for today
6. **Verify dashboard**: open `state/reports/dashboard.html`; new ledger rows should appear under "upstox-paper" tab
7. **Run for 5 trading days** before claiming victory — single-day success doesn't prove pipeline robustness

---

## 13. What to do with the existing US-stocks code

**Option A (recommended):** archive the current branch as `archive/us-stocks-ibkr-2026-05`, then start fresh on `production-india-momentum`. The CP-API code from today represents real learning; preserve it.

**Option B:** delete CP-API broker code entirely. Cleaner repo but loses the empirical work.

**Option C:** keep both brokers in `brokers/`. Hybrid setups (e.g., monitor US via IBKR, trade India via Upstox) become possible. **Don't do this for v1 — it adds complexity for no current benefit.**

`storage/portfolio.duckdb` has historical `mode='paper'` (US simulator) and `mode='ibkr-paper'` (today's CP-API fills) rows. **Recommend:** keep these in place but don't add to them. Add new `mode='upstox-paper'` and `mode='upstox-live'` rows. Dashboard already shows by mode, so the comparison is automatic.

---

## 14. Things this doc deliberately doesn't decide

These are for the rebuild session to handle with the user:

- Exact strategy parameters (ATR multiplier, ranking lookback) — rerun validation, see what works
- Whether to add a sector cap (concentration risk in India is higher than US)
- Whether to add intraday signals (Upstox supports intraday data; out of scope for v1)
- F&O trading (futures + options) — explicitly OUT for v1, equity delivery only
- Real-money launch threshold (current US criteria: live paper Sortino within 50% of backtest Sortino over 4 weeks)
- News classifier prompts — translate to Indian context (e.g., "FII outflows" replaces "Fed hawkish")

---

## 15. Quick reference: API endpoint cheatsheet

### Dhan HQ (all base URL `https://api.dhan.co`)

All requests need header: `access-token: <DHAN_ACCESS_TOKEN>` and `Content-Type: application/json`.

```
POST /v2/orders
  body: {
    "dhanClientId": "<DHAN_CLIENT_ID>",
    "transactionType": "BUY"|"SELL",
    "exchangeSegment": "NSE_EQ",
    "productType": "CNC",          # CNC = delivery (Cash & Carry)
    "orderType": "LIMIT"|"MARKET",
    "validity": "DAY",
    "securityId": "1234",          # from scrip master CSV
    "quantity": 10,
    "price": 250.50               # required for LIMIT
  }
  → returns {orderId: "...", orderStatus: "PENDING"|...}

GET /v2/orders
  → all today's orders + their status (also handy for polling)

GET /v2/orders/{order-id}
  → single order status + fill info

DELETE /v2/orders/{order-id}
  → cancel an open order

GET /v2/trades
  → today's executions with commission

GET /v2/positions
  → currently open positions

GET /v2/holdings
  → long-term holdings (T+1 settled delivery)

GET /v2/fundlimit
  → {availableBalance, sodLimit, collateralAmount, ...} → cash for sizing

GET /v2/charts/historical
  body: {securityId, exchangeSegment, instrument="EQUITY",
         expiryCode=0, fromDate, toDate}
  → daily OHLCV (up to several years)

GET /v2/charts/intraday
  body: {securityId, exchangeSegment, instrument="EQUITY",
         interval="1"|"5"|"15"|"60", fromDate, toDate}
  → intraday bars
```

Scrip master (universe instrument IDs):
```
GET https://images.dhan.co/api-data/api-scrip-master.csv
  → CSV with securityId, symbol, ISIN, exchange, segment, lot, tick size
  → cache locally; refresh weekly
```

### NSE (public, no auth)
```
GET https://www1.nseindia.com/content/indices/ind_nifty100list.csv
  → Nifty 100 constituents (universe)

GET https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
  → daily bhav copy (all NSE EOD bars)

GET https://www.nseindia.com/api/corporate-announcements?index=equities
  → corporate filings (need browser-style User-Agent header)
```

### Pulse by Zerodha (news)
```
GET https://pulse.zerodha.com/feed.php
  → aggregated RSS of Indian financial news
```

### RBI (macro)
```
DBIE web portal: https://dbie.rbi.org.in/DBIE/dbie.rbi
  → manual download for now; programmatic access requires scraping their XBRL
    feeds. Alternative: FRED has key India indicators already.
```

### FRED (macro, for the few India indicators they index)
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=INDCPIALLAINMEI&api_key=...
  → India CPI All Items

Useful series_ids: INTDSRINM193N (India interest rate), INDCPIALLAINMEI (CPI),
                   DEXINUS (USD/INR daily)
```

---

## 17. Empirical broker cost comparison (verified 2026-05-14)

Round-trip cost on a **₹5,000 delivery trade**. Government charges (~₹6.16 — STT, exchange, SEBI, stamp duty, GST on those) are identical across brokers. Only **brokerage + GST-on-brokerage + DP charges** vary.

| Rank | Broker | Brokerage RT | GST | DP charge | API monthly | **Total RT** | **% of ₹5k** |
|---|---|---|---|---|---|---|---|
| 🥇 1 | **Dhan HQ** | ₹0 (free delivery) | ₹0 | ₹14.75 | Free | **₹20.91** | **0.42%** |
| 🥈 2 | **Zerodha** | ₹0 (free delivery) | ₹0 | ₹15.93 | ₹500/mo for data | ₹22.09 + ₹6k/yr | 0.44% |
| 3 | Angel One | ₹10 (₹5 min × 2) | ₹1.80 | ₹23.60 | Free | ₹41.56 | 0.83% |
| 4 | Groww | ₹10 (₹5 min × 2) | ₹1.80 | ₹23.60 | ₹499/mo (₹588.82 w/ GST) | ₹41.56 + ₹7k/yr | 0.83% + sub |
| 5 | Upstox (promo until Dec 31, 2025) | ₹20 | ₹3.60 | ₹14.75 | Free (basic) | ₹44.51 | 0.89% |
| 6 | **Upstox (post-promo)** | ₹40 | ₹7.20 | ₹14.75 | Free (basic) | **₹66.71** | **1.33%** |
| 7 | Alice Blue | ₹40 | ₹7.20 | ₹17.70 | Free | ₹71.06 | 1.42% |

### Annual cost drag at ₹50k capital, 50 round-trips/year, 10 positions

| Broker | Annual drag | Annual ₹ on ₹50k | Notes |
|---|---|---|---|
| **Dhan** | 21% | ₹10,455 | **Selected — best API + lowest realized cost** |
| Zerodha | 22% + ₹6k data fee | ₹17,045 | Expensive at small capital |
| Angel One | 42% | ₹20,780 | DP charges hurt |
| Groww | 42% + ₹7k subscription | ₹27,846 | Same per-trade as Angel One but adds ₹499/mo sub — worst free-tier overall |
| Upstox (promo) | 45% | ₹22,255 | Temporary discount only |
| Upstox (post-promo) | 67% | ₹33,355 | Brutal |
| Alice Blue | 71% | ₹35,530 | Avoid |

**Strategy implication:** at ₹50k capital with 10 positions, Dhan eats ~21% of capital annually in commissions. **Reduce to 5-6 positions at this capital level** to halve the drag.

### Migration trigger to switch brokers later

Stay on Dhan unless one of these specific triggers fires:
- **Capital scales to ₹5L+ (~$6k+)**: Zerodha's ₹500/mo data fee becomes negligible (0.12% of capital). Zerodha's mature community + tooling justifies the migration.
- **Dhan has a multi-day API outage** that materially disrupts the daily cron: have an off-the-shelf fallback plan written down but don't preemptively code it.

Other brokers (Angel One, Groww, Upstox, Alice Blue) are not better than Dhan on any axis at any capital level we're targeting. Excluded from consideration. Specifically Groww was checked because the user asked — and confirmed worse than Dhan because Groww charges ₹499/mo API subscription on top of standard ₹5-20/order brokerage.

---

## 16. Closing note from this session

The pivot from US-stocks/IBKR to Indian-stocks/Upstox is the right call for the user's situation (India resident, $500-2k capital target, wants automation). The technical reasons are documented above; the empirical evidence is in this codebase's IBKR CP-API code and today's $0.60 commission on a $59.57 trade.

The architecture (Karpathy 3-file + 8-table ledger + Executor protocol + walk-forward backtester + daily LLM cache) is broker- and market-agnostic. Pivoting is a data/broker/cost replacement, not a rewrite from scratch.

Expect the rebuild session to take ~9-10 hours of focused work to be back to today's state but on Indian markets with cleaner economics.

The autoresearch loop, the strategy logic, and everything we learned about position sizing, ATR stops, retention logic, fraction-change thresholds, and risk gates — all that survives intact. We're not throwing anything important away.

Sources used to inform this doc:
- [Upstox Developer API docs](https://upstox.com/developer/api-documentation/)
- [Upstox Brokerage Charges](https://upstox.com/brokerage-charges/)
- [Pulse by Zerodha (news aggregator)](https://pulse.zerodha.com/)
- [NSE official site](https://www.nseindia.com/)
- [RBI DBIE](https://dbie.rbi.org.in/DBIE/dbie.rbi)
- Empirical verification (2026-05-14): CP-API fractional commission $0.60 on $59.57 trade (1.0%)
