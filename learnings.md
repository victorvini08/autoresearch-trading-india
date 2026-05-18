# Domain learnings — Indian equities autoresearch

Compounding insights specific to the Indian market, accumulated by the autoresearch loop and by humans across iterations. Distinct from `journal.md` (per-iteration history) — this file is for durable knowledge that future iterations should *start* from.

**Historical insights from the US-stocks predecessor** are preserved in `docs/learnings-from-us-build.md` (universal architecture patterns) and `docs/handoff-india-pivot.md` (pivot decisions). The notes below are India-specific only.

---

## 1. Market microstructure

### 1.1 NSE T+1 settlement (since Jan 2023)

Equity delivery settles T+1: shares from a buy on day T are available to sell on day T+1. CNC orders that try to "intraday sell" what's not yet settled will be rejected by Dhan or treated as short positions. The strategy's biweekly rebalance is safely above the T+1 boundary.

### 1.2 Pre-open auction (09:00–09:15 IST)

NSE has a pre-open price-discovery window. Volumes are low; spreads are wide. Premarket-scan can read these prices for sanity but should NOT place orders.

### 1.3 Circuit limits

Indian stocks have daily price-band limits (5% / 10% / 20% depending on F&O status). Stocks hitting an upper circuit can't be bought; lower circuit can't be sold. Premarket scan flags stocks near limits; risk_check halts entry on circuit-bound names.

### 1.4 Holiday calendar (NSE)

Indian markets observe ~12-15 holidays per year. `_trading_days_in_window` reads from `prices.duckdb`, so calendar is automatic once data is ingested. Notable: Diwali Muhurat trading (1-hour evening session) is excluded from our regular run windows.

---

## 2. Cost economics

### 2.1 DP charge dominates at small capital

Dhan brokerage on delivery is ₹0, but the depository DP charge of ₹14.75 per scrip per sell is unavoidable (NSDL/CDSL set it). At ₹50k capital with 10 positions:
- 10 sells per rebalance × ₹14.75 = ₹147.50 per rebalance
- 26 rebalances/year (biweekly) × 0.5 turnover = ~₹1,920/yr
- That's ~3.8% of capital per year in DP charges alone

**Reducing to 6 positions cuts this to ~₹1,150/yr (2.3%).** Strategy defaults to 6.

### 2.2 STT is sell-only

0.1% of sell-side notional (set by Govt of India). Identical across brokers. Build into the cost model on the sell leg.

### 2.3 No fractional shares on NSE

All Indian equities trade in whole-share units. No fractional question; small capital → smaller positions, not fractional positions.

---

## 3. Regime patterns observed (2024-2026)

### 3.1 FII-led drawdowns are deep but DII-floored

The Oct-2024 → Feb-2025 drawdown (-16% on Nifty 50) and the Jan-2026 → Mar-2026 drawdown (-14%) were both driven by sustained FII selling (~₹1.15 lakh crore in 2025 alone) that DII flows partially absorbed. The regime gate (`FII 20d net < -₹15kCr`) captures this; the asymmetric defense (block new entries, hold existing) avoids the "exit everything" whipsaw that would have been disastrous in the DII-supported recoveries.

### 3.2 Mid-caps lead in DII-driven recoveries

The 2024-26 winners were defence PSUs (HAL, BEL, Mazagon Dock), capital-goods midcaps (Polycab, KEI, Voltas), and select retailers (Trent). Most were OUTSIDE Nifty 100. Universe widening (Nifty 500 top-200-ADV) is the architectural answer.

### 3.3 Quality beats Momentum during corrections

Aug-2024 onward, Nifty Quality 30 and Low Vol 50 decisively outperformed Nifty Momentum 30. The quality screen on top of momentum (rather than pure momentum) is intended to capture this.

### 3.4 Sector concentration is structural

Top 5 Nifty 100 weights = 24%; financials 35-38% of the broad index. Without a sector cap, momentum-ranked portfolios collapse into financials beta. The 25% sector cap is non-negotiable.

### 3.5 Gross volatility-scaling clips the right tail of a long-only momentum book

Conditional realized-vol scaling of *gross* (Barroso–Santa-Clara crash defense) was tested twice on the momentum-quality book (2026-05-17, journal `A1-volscale-median`, `A2-volscale-p80`). Both REVERTED for the **same structural reason**, so the gross-vol-scaling family is exhausted — do not retry with new thresholds. Finding: it strictly improves *every* robustness axis (A.v2: 0/13 negative folds vs 3, drawdown 4.17% vs 5.18%, worst fold +0.05 vs −2.07, passes the sub-period gate) yet *lowers* mean validation Sortino (2.26 vs 2.63). Cause: this long-only book's Sortino is **right-tail-driven** (a few explosive bull folds dominate the mean), and realized vol is **symmetric** — in Indian midcaps a high-realized-vol regime is frequently an explosive move *up*, so any gross reduction clips melt-ups as much as it cushions crashes. Barroso–Santa-Clara's ~2× Sharpe is for the long-*short* momentum factor, not a long-only right-tail book. Implication: defend the downside *without* touching gross — re-weight *within* fixed gross (inverse-vol / risk-parity per-name sizing) or change the entry thesis; never scale gross down on a long-only right-tail momentum book.

---

## 4. SEBI retail algo framework (effective 2026-04-01)

### 4.1 Mandatory registration

Every algo running on a broker's API must be registered with the broker. Dhan offers "Personal Algo" (for own funds; what we use) and "Trading Provider" (for managing others' money; requires SEBI empanelment). One-time setup; algo ID stamped on every order.

### 4.2 Per-client API keys + static IP

Dhan's `DHAN_ACCESS_TOKEN` is per-client by default. The static-IP whitelist is the user's responsibility — home IP works if static; cloud bastion otherwise.

### 4.3 OPS counter

>10 orders per second triggers mandatory empanelment. We're at ~0.001 OPS (6 orders biweekly). `scripts/sebi_compliance.py` logs daily order counts for audit-readiness.

---

## 5. Scraping discipline

### 5.1 NSE rate-limits aggressive crawlers

Use polite delays (1-2 sec between requests), browser-style User-Agent header, persistent cache, and exponential backoff on 429/403. NSE has been known to IP-ban scrapers; our requests are spaced out enough that this has not been an issue in development.

### 5.2 MoneyControl page structure changes

When MoneyControl renames a CSS class or changes URL structure, the scraper breaks silently (returns empty news). Mitigation: per-source `last_successful_fetch` timestamp in `news.duckdb`; daily alert if any source has gone > 48 hours without a successful fetch.

### 5.3 NSE bhav files sometimes delayed

Bhav for date T is typically published by T+1 07:00 IST, but occasionally 30+ minutes late. Our daily_update job runs at 09:15 IST — far enough to be safe in 99% of cases; for the remaining 1%, the executor uses yesterday's close from yfinance as a fallback.

---

(append future Indian-market-specific learnings below; keep US-stocks-specific lessons in `docs/learnings-from-us-build.md`)

## 6. Deployment is throttled by gross-sizing, not by the entry filter

### 6.1 The cash-drag root cause is `breadth_scaled_gross` × fixed-slot sizing — NOT eligibility

Sealed-window measurement (Improvement D, 2026-05-18): widening the
per-name entry gate (asymmetric fast re-entry, research trade-count
23→81, all 5 atomic gates passed) left average gross **unchanged**:
D 14.6% vs B 15.5%, per-quarter virtually identical, max still ~25%. The
book is ~85% cash because `breadth_scaled_gross` (step 0.35–0.99) ×
fixed-slot sizing (`gross / n_positions`, unfilled slots → cash) caps
total deployment; in a low-breadth post-correction regime gross is pinned
at ~15% no matter how many names qualify. **Implication:** the
upside-capture weakness (strategy badly trails the index in up-quarters)
is a DEPLOYMENT problem owned by the gross/sizing mechanism, and cannot
be moved by signal/eligibility changes. Every non-burned lever against it
is now exhausted; the gross mechanism itself is the locus and is
roadmap-§6 / A-family burned-adjacent. Forward dhan-paper validation and
the deferred news/fundamentals levers (out of this loop's scope) are the
genuine next steps, not more in-sample gross/eligibility iteration on a
backtest known to be heavily overfit with the sealed window burned.

### 6.2 The ~15% deployment ceiling is STRUCTURAL, not a small-capital artifact

User-directed capital sweep (2026-05-18, sealed window): scaling ₹50k →
₹5L (10×, which removes the whole-share execution floor) lifts average
gross only ~+3–5pp (baseline 15.6%→20.1%; npos15 15.7%→18.4%) — the book
is STILL ~80% cash at 10× capital. So the cash-drag / poor-upside-capture
is overwhelmingly the `breadth_scaled_gross` step × slow-entry-gate
structural throttle, NOT the small-₹50k whole-share lumpiness (that
explains only a few points). Corollary: n_positions=15 on baseline added
+2.17pp sealed total at ₹50k but it was pure concentration AND a
small-capital lumpiness artifact — it COLLAPSES at ₹5L (+8.30%→+1.43%,
Sortino 0.834→0.213) while baseline n_positions=25 is scale-stable
(+6.13%→+7.28%, Sortino ≈0.95–1.0). Always validate a candidate at ≥1
larger capital before believing a ₹50k backtest gain. Net: every
price/structure lever against the upside problem is now exhausted/
disproven (A vol-scaled gross, B inverse-vol, C residual momentum, D
asymmetric eligibility, E concentration). The binding locus is
`breadth_scaled_gross` itself (roadmap-§6 "gross gate" burned). Honest
forward paths only: (a) a DELIBERATE, user-authorized redesign of the
gross/deployment mechanism with eyes open, or (b) forward dhan-paper
validation + the deferred news/fundamentals data edge. Baseline e745434
is the robust, scale-stable committed endpoint.

## 7. The 25% "sector cap" was a whole-book exposure bug; vol-targeting is the real edge

### 7.1 Sector-wiring bug invalidated the entire prior research history
`backtest/engine.py` and live `scripts/signal_today.py` build
`bt.feeds.PandasData` WITHOUT an industry attribute, and the old
`_load_sector_map` read that absent attr → all names 'OTHER' → the 25%
per-sector cap acted as a hard 25% whole-book net-exposure ceiling in
EVERY backtest and live. Every pre-2026-05-18 result (baseline, A–F,
sealed +6.13%, "~5% maxDD", all anti-overfit gates) was an artefact of
this: a ~75%-cash book by accident. Fix: source industry from the PIT
universe DB enrichment in `_load_sector_map`. **Lesson: when a strategy's
risk profile seems "too clean," instrument the actual per-rebalance
deployment before trusting ANY backtest metric — a metadata-wiring bug can
silently dominate every result for weeks.**

### 7.2 Prior reverts measured on a bugged engine are VOID
A-family (conditional vol-scaled gross) and B (inverse-vol) were reverted
based on a 25%-capped book — those conclusions did not transfer. On the
corrected engine, volatility targeting (Barroso–Santa-Clara 2015;
Moreira–Muir 2017) is the single most robust improvement: it raised
held-out sealed return to +12.07% (vs index −1.94%), cut aggregate DD
20.9%→12.8%, made sub-period Sortinos the most stable ever ([3.15, 2.32]),
and is SCALE-ROBUST at ₹5L (+9.96%) where naive variants collapsed.
**Lesson: re-test "burned" ideas after any engine/data correction; a
learning is only valid on a correct harness.**

### 7.3 Always validate at ≥10× capital
E (+8.30%@₹50k→+1.43%@₹5L) and G (+1.74%→−9.87%) looked fine at ₹50k and
were small-capital lumpiness/over-concentration artefacts. H survives
(+12.07%→+9.96%). Capital-scale robustness is now a mandatory gate before
believing any ₹50k sealed result.
