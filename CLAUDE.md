# Autoresearch Trading — India

LLM-driven autoresearch swing-trading system for Indian equities, delivery (CNC) only, via the Dhan HQ Trading API. Inherits architecture from `autoresearch-trading-us` (archived); the data/broker/strategy/cost layers are India-specific.

**Current phase:** v1 paper-only (`dhan-paper`), built against an in-memory mock Dhan client (`DHAN_MOCK=1`). Live execution (`dhan-live`) is built but disabled by `state/halt.json` until 4 weeks of clean paper validation. A **real-world paper-trading + self-improving review layer** now sits on top (daily reconciliation, a deterministic safety state machine, a month-end LLM review gated by deterministic policy checks, and a faithful replay harness). The nightly autoresearch loop is **NOT** scheduled — `strategy.py` is locked; any strategy evolution is on-demand only.

> **Branch state (2026-06-03 consolidation):** `main` is the **SOLE canonical
> branch**. The locked strategy is **`IndiaMomentumQualityCarry`** in
> `strategy.py` (cross-sectional 12-1 momentum-quality; see the locked-decisions
> table). The parallel experiment branches (`mean-reversion-quant-strategy`,
> `realworld-autoresearch`, `production-strategy`) have been merged/deleted —
> all of that work is now on `main`. (The stale "Strategy B" docstring note
> was resolved 2026-06-10 when the docstring was rewritten for the low-vol
> filter promotion.)

---

## How to think about this codebase

**Three layers, broker- and market-agnostic at the top, India-specific at the bottom:**

1. **Autoresearch loop** (`scripts/loop.py`, `scripts/run_overnight.py`): Claude Opus 4.7 reads `journal.md`, proposes a `strategy.py` edit, runs walk-forward backtest, KEEP/REVERT based on multi-dimensional gates. Universal.
2. **Strategy + classifiers** (`strategy.py`, `llm/`): the strategy is a backtrader subclass that reads pre-computed LLM classifier outputs (`macro_regime`, `sentiment`, `events`) for India. The classifier prompts are India-specific (RBI / FII / INR / Nifty 50 / India VIX inputs).
3. **Executor + broker + data** (`scripts/executors/dhan.py`, `brokers/dhan.py`, `data/*`): India-specific. Dhan Trading API for orders; NSE bhav archive for prices; Pulse RSS + MoneyControl + NSE filings + RBI/SEBI press for news; FRED + NSE indices + RBI for macro.

**The Karpathy 3-file pattern is core:**
- `prepare.py` — IMMUTABLE walk-forward evaluator with anti-overfit gates. The autoresearch loop never edits this.
- `strategy.py` — loop-EDITABLE signal logic. Every overnight iteration may mutate this.
- `journal.md` — append-only memory of every iteration's hypothesis, change, result, and KEEP/REVERT decision. The loop reads this each iteration to avoid re-proposing burned ideas.

---

## Locked decisions (do not re-debate without explicit user input)

| Decision | Choice | Source |
|---|---|---|
| Market | Indian equities (NSE), CNC delivery | India-resident user; eliminates LRS / TCS / Schedule FA |
| Broker | **Dhan HQ Trading API** (free brokerage on delivery) | docs/superpowers/specs/2026-05-14-india-autoresearch-trading-design.md §3 |
| Price data | **NSE bhav archive** (free public ZIPs) | Dhan Data API is paid ₹500/mo — we don't use it |
| Universe | **Top 200 by 20-day ADV, point-in-time from the full NSE EQ bhav** (survivorship-free; the current Nifty 500 list is sector/ISIN enrichment only, NOT the membership gate) | 2026-05-15 audit: using today's Nifty 500 list historically censored 293 delisted names → inflated momentum backtest. PIT membership from price history fixes it with data we already have |
| Strategy shape | Class **`IndiaMomentumQualityCarry`** — **PROMOTED 2026-06-10: low-vol pre-filter** (`low_vol_eligible`: keep the calmer HALF of candidates by trailing-252d realized vol — parameter-free median split reusing `beta_window`, held names grandfathered) → cross-sectional 12-1 momentum-quality **selection** → **bounded gross-targeting** construction (per-name ≤10% AND per-sector ≤25%) → **downside-vol-targeted gross** (`clip(0.12/downside_vol_ann, 0, 0.99)`, risk input = MAX of slow ~6m / fast ~1m downside semi-deviation of the held book) → between-rebalance **structural MA exit** (~190d). Idle cash → **LIQUIDCASE cash floor** (executor-level policy, `scripts/cash_floor.py` — banded ±5%, stripped from the signal seed; NOT strategy code; NOT LIQUIDBEES, whose return arrives as dividend units invisible to price series). | **2026-06-10 re-measurement on repaired data** (split/bonus-adjusted, gap days re-ingested, EQ+BE series, extended 2017-07 evaluator window — see journal 2026-06-10): the pre-repair era conclusions ("defensive-only, trails Nifty ~10pp, alpha exhausted") were substantially DATA ARTIFACTS — unadjusted splits alone cost ~5pp/yr of phantom losses. @₹50k deployment scale the filtered book is the ONLY variant passing ALL 5 atomic gates on the extended window (34 folds, val Sortino 1.995, stationarity 0.236; unfiltered scores 2.088 but FAILS stationarity 0.169); continuous 2019-2026 +floor: filter +13.4%/yr maxDD −17.9%, unfiltered +14.5%/yr −13.5%, Nifty +11.1%/−38.4%. Scale caveat: stationarity verdicts mirror-flip at ₹5L (re-adjudicate before scaling past ~₹2-3L). Forward dhan-paper validation = the remaining arbiter. |
| **Sector-wiring fix** (root cause) | `_load_sector_map` sources per-ticker industry from the **PIT universe DB** (point-in-time-safe enrichment), NOT the feed attribute. | The backtest/live `bt.feeds.PandasData` never carried an industry attr, so every name was 'OTHER' → the 25% sector cap was a hidden **25% whole-book net-exposure ceiling** in EVERY pre-2026-05-18 backtest AND live. **All pre-2026-05-18 results, gates, and A–F reverts are VOID** — re-test any "burned" idea on the corrected engine. |
| Anti-overfit gates | Sealed **2025-01-01 → 2026-05-14** test, Bonferroni p-correction, RW Monte Carlo, parsimony budget, sub-period stationarity, cost-aware Sortino | **NEW for India**; addresses US multi-strategy overfit failure |
| Rebalance cadence | **Biweekly** (alternate Fridays), anchored to a fixed parity constant `_REBALANCE_PARITY=0` so the rebalance-Friday set is reproducible across runs (fixes the 2026-05-26 parity-drift incident — NOT a tunable knob) | User-specified |
| Starting capital | **₹1,00,000** paper account (`dhan-paper`; raised from ₹50k). NOTE: the `prepare.py` walk-forward evaluator still uses **₹50k** as its `INITIAL_CASH` base, and variants are additionally validated at ≥10× (₹5L). Position count is an *outcome* of bounded gross-targeting (~10–15 names when fully invested at the 10% per-name cap), not a fixed 5–6. | DP-charge optimization, now subordinate to the 10% concentration limit |
| LLM stack | Claude Code SDK: **Opus** for the (now on-demand, **unscheduled**) autoresearch loop, **Sonnet** for classifiers; Qwen3 fallback. Current models: Opus 4.8 / Sonnet 4.6. NOTE: the locked `strategy.py` is **purely price-derived** — it does NOT read the LLM classifier features; those feed the research loop and the monthly review, not the live signal. | Subscription-bounded cost; cache keyed by `(date, ticker, prompt_hash, model_id)` |
| Live mode | Built but disabled (`halt.json` defaults to halted=true for `dhan-live`) | 4-week paper validation gate |
| News sources | **5 trusted free**: MoneyControl, Pulse RSS, NSE filings, RBI press, SEBI press | No paid APIs |

---

## Hard constraints (real money risk if violated)

1. **Never enable `dhan-live` mode without explicit user approval AND a successful 4-week `dhan-paper` validation run** logged in `iterations/log.csv` and `journal.md`. The `halt.json` mechanism is the gate.
2. **SEBI algo-ID stamp is OPTIONAL** (confirmed 2026-06-04). When `$SEBI_ALGO_ID` is set, every order carries it (per the 2026-04-01 retail algo framework); a missing stamp does **not** block orders — the executor treats it as optional (commit `80f77fe` relaxed the old B7 hard-fail). Set it if you have one; it is not required to paper- or live-trade at our OPS level.
3. **Strategy uses `order_target_percent` only** (no `self.buy()` / `self.close()`). Required by `scripts/signal_today.py`'s capture logic.
4. **FRACTION_CHANGE_THRESHOLD = 0.005** on `target_fraction` (not `target_qty`) suppresses mark-drift churn. Do not remove.
5. **Cash-ledger entries write on `fill_date`, not `signal_date`** (US repo learnings §4.3 — get_cash over-counts if we use signal_date).
6. **Journal parser uses literal-line match for `**Decision:** KEPT`** — never substring (US repo learnings §4.4).
7. **LLM cache rows are still WRITTEN keyed by `model_id`** (audit/ablation provenance preserved). But as of 2026-05-15 (explicit user decision) the precompute cache-SKIP lookup is **model-agnostic by default**: a cell already classified by ANY provider is reused, so a Codex-filled half-cache is *continued* by a later Claude run instead of recomputed. This matches `llm.features` reading the cache model-agnostically (these coarse 4-class/[-1,1]/7-flag outputs are treated as model-interchangeable). Set `LLM_STRICT_MODEL_CACHE=1` to restore strict per-model isolation for a clean single-model ablation. (Supersedes the original "swapping models invalidates the slice" rule.)
8. **Anti-overfit gates are atomic.** A variant that fails ANY gate is REJECTED, not partially accepted.
9. **Sealed test set (2025-01-01 → 2026-05-14, per `prepare.py`) is revealed ONCE per promotion** — no retries on the same variant. The sealed reveal has **already been SPENT** on the locked book, so a genuinely new finalist needs fresh out-of-sample confirmation (forward paper), not a sealed re-reveal.
10. **Concentration is bounded by `construct_gross_targets`, not by `len(selected)` sizing.** The §-old "never size from `len(selected)`" blow-up rule is now *enforced structurally*: deployment walks the ranked list bounded by per-name ≤ `_MAX_NAME_WEIGHT` (10%) AND per-sector ≤ 25%, so a 1-name regime puts ≤10% in that name (rest stays cash) — strictly safer than the old scheme. Do not reintroduce naive `gross/len(selected)` or unbounded per-name weight.
11. **Validate every variant at ≥10× capital (₹5L), not just ₹50k.** ₹50k sealed wins are routinely small-capital whole-share/concentration lumpiness that collapse at scale (variants E, G). Capital-scale robustness is a mandatory check alongside the atomic gates and the sealed reveal.
12. **Pre-2026-05-18 backtest numbers and KEEP/REVERT decisions are void** (produced by the sector-wiring bug = accidental 25% whole-book cap). Baseline e745434 / Improvement B are obsolete; their headline metrics were the bug. The "downside protection" of that era was ~75% forced cash, not strategy skill.

---

## User action items (one-time setup, do these in order)

These steps are required before `dhan-paper` can run against a real Dhan account. While they're pending, `DHAN_MOCK=1` in `.env` keeps the system runnable against an in-memory mock.

### 1. Open a Dhan account
Sign up at https://dhan.co. KYC requires PAN + Aadhaar + bank account. Process usually completes in 1 business day.

### 2. Enable equity delivery
Default on for new accounts. (F&O / commodities are not used; do not enable.)

### 3. Generate the Dhan access token
- Log in to https://web.dhan.co
- Top-right profile menu → "DhanHQ Trading APIs"
- Click "Generate Access Token". **Token validity is 24 hours** (NOT 1 year —
  the handoff doc was wrong). It is auto-renewed daily by
  `scripts/dhan_token_refresh.py` (see "Token auto-refresh" below), so you
  only paste it once.
- Note your `dhanClientId` (visible in the API section). You don't strictly
  need to copy it — the refresher reads it from `/v2/profile` and writes
  `DHAN_CLIENT_ID` into `.env` automatically on first run.

### 4. (Optional) Register the algo with Dhan (SEBI algo framework, 2026-04-01)
This step is **optional** — the system places orders with or without the stamp. Do it only if you want the algo ID on your orders.
- In the Dhan API portal, register a new "Personal Algo" (NOT "Trading Provider").
- You'll receive a unique `SEBI_ALGO_ID`, stamped on every order when it is set.
- Confirm your home IP is static (most ISPs are; check at `whatismyip.com` over 24h). If dynamic, a cheap cloud bastion (Hetzner CX22, ~₹500/mo) is the workaround.

### 5. Populate `.env`
Copy `.env.example` to `.env` and fill in:
- `DHAN_ACCESS_TOKEN`
- `DHAN_CLIENT_ID`
- `SEBI_ALGO_ID`
- `FRED_API_KEY` (sign up at https://fred.stlouisfed.org/docs/api/api_key.html if needed)
- Toggle `DHAN_MOCK=0` once the real token is in place.

### 6. Verify with the read-only smoke
```
uv run python -m scripts.dhan_smoke
```
This calls `get_cash`, `get_positions`, `get_holdings`, `get_historical_candles` and exits. No orders placed.

### 7. Token auto-refresh (no calendar reminder needed)
DhanHQ self-generated tokens expire after **24 hours**, but can be renewed
any time while still active (`GET /v2/RenewToken`), yielding a fresh 24h
token. `scripts/dhan_token_refresh.py` automates this:

```
uv run python -m scripts.dhan_token_refresh            # validate + renew + rewrite .env
uv run python -m scripts.dhan_token_refresh --check-only  # just print expiry
```

Install the launchd job so it runs at **09:00 and 21:00 IST** (the 09:00 run
precedes the 09:30 daily update and 10:00 premarket scan):

```
cp deploy/launchd/com.autoresearch.dhan_token_refresh.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.autoresearch.dhan_token_refresh.plist
```

As long as the machine is on at least once per 24h, the token chains
forever — you paste it **once**. Only failure mode: machine off > 24h →
token lapses (can't renew an expired token) → regenerate once at
https://web.dhan.co and the cron resumes automatically. Verified live
2026-05-15 (renew is a GET; new JWT is the `token` field).

---

## Daily operation

### Cron / launchd schedule (IST)

| Job | Time (IST) | Plist file | What it does |
|---|---|---|---|
| Dhan token refresh | 09:00 & 21:00 | `deploy/launchd/com.autoresearch.dhan_token_refresh.plist` | Validate + renew the 24h Dhan token; rewrite `.env` |
| Daily update | 09:30 | `deploy/launchd/com.autoresearch.daily_update.plist` | Ingest yesterday's bhav, macro, earnings deltas (runs `--skip-classify`) |
| Premarket scan | 10:00 | `deploy/launchd/com.autoresearch.premarket_scan.plist` | Check overnight gaps, India VIX spike, halts |
| Run live | 10:15 | `deploy/launchd/com.autoresearch.run_live.plist` | Signal → orders → fills → ledger writes (no-op on non-rebalance days) |
| Risk check + daily report | 15:35 | `deploy/launchd/com.autoresearch.daily_report.plist` | Post-close summary; also folds in the daily safety-state eval and the month-end LLM review |

The nightly autoresearch loop is **NOT scheduled** — there is no `run_overnight` plist. `strategy.py` is locked and the system is paper-only; strategy evolution is on-demand (`scripts/loop.py` / `scripts/run_overnight.py` are run manually). All five plists above run via `uv run python -m scripts.<job>`.

NSE trading hours: 09:15 – 15:30 IST. Our execution window for biweekly rebalance is **10:00–15:00 IST** (avoids open-spread chaos and close-auction overlap).

### Manual commands

```bash
# Run tests
uv run pytest -q

# Walk-forward backtest of current strategy.py (on synthetic prices for first run)
uv run python prepare.py research

# End-to-end paper run for today
uv run python -m scripts.run_live --date $(date +%Y-%m-%d)

# Autoresearch loop (single iteration)
uv run python -m scripts.loop --iterations 1

# Overnight autoresearch (8-12 iterations)
uv run python -m scripts.run_overnight

# Dashboard
uv run python -m scripts.dashboard
open state/reports/dashboard.html
```

---

## Repository structure

```
.
├── prepare.py            # IMMUTABLE walk-forward evaluator + anti-overfit gates
├── strategy.py           # LOOP-EDITABLE: IndiaMomentumQualityCarry — 12-1 momentum-quality selection
│                         #   → bounded gross-targeting → downside-vol-targeted gross + structural MA exit
├── program.md            # Goal + constraints (read by autoresearch loop)
├── journal.md            # Append-only iteration memory (pre-2026-05-16 in journal_pre-2026-05-16_archive.md)
├── learnings.md          # Compounding domain insights
├── PRODUCTION_STRATEGY.md        # Canonical locked-strategy definition + honest caveats
├── STRATEGY_DEVELOPMENT_PLAN.md  # Goal + guardrails for on-demand strategy development
├── AGENTS.md             # Mirror of this file (kept byte-identical to CLAUDE.md)
├── backtest/             # engine, metrics, risk, costs (Dhan), anti_overfit
├── brokers/              # dhan (Trading API), dhan_mock (paper)
├── data/                 # universe, sectors, quality_screen, safety_state, pead, news_filter, bse,
│                         #   ingest_{prices,news,macro,earnings,fundamentals,fii_dii_history,corporate_actions,gdelt},
│                         #   fundamentals_xbrl, realworld_review_validator
├── llm/                  # provider, classify, features, cache, prompts (India)
├── scripts/              # operational + research entrypoints:
│                         #   run_live, daily_update, premarket_scan, daily_report, dashboard, halt, risk_check, signal_today
│                         #   reconciliation, safety_evaluator, trade_context            (real-world paper layer)
│                         #   realworld_context, realworld_review, realworld_validator, review_schedule  (monthly LLM review)
│                         #   replay_paper (faithful paper replay); eval_variant, capture_ratio, blend_frontier (research instruments)
│                         #   loop, run_overnight (autoresearch loop — UNSCHEDULED); promote_live; dhan_token_refresh, dhan_smoke
├── storage/              # portfolio_db.py (paper/real ledger), realworld_db.py (review store); *.duckdb generated (gitignored)
├── tests/                # pytest tree
├── deploy/launchd/       # macOS plists (IST schedules — see Daily operation)
└── docs/
    ├── handoff-india-pivot.md     # carried from US repo (historical)
    ├── learnings-from-us-build.md # carried from US repo (historical)
    ├── strategy-candidates.md     # parking lot of rigorously-tested-but-not-promoted ideas
    └── superpowers/
        ├── specs/                 # design specs (incl. 2026-05-28 realworld-autoresearch)
        └── plans/                 # implementation plans
```

---

## Indian-market specifics worth knowing

- **Trading hours:** 09:15–15:30 IST (pre-open 09:00–09:15)
- **Settlement:** T+1 for equities (since Jan 2023)
- **Tax (India resident):**
  - STCG (held < 12 months): 15% flat
  - LTCG (held ≥ 12 months): 10% on gains above ₹1 lakh / financial year
  - FY runs Apr 1 → Mar 31
  - No LRS / Schedule FA / Form 67 / TCS overhead (those are foreign-asset concerns only)
- **DP charge:** ₹14.75 per scrip per sell (flat). Dominant cost component at our trade size — strategy caps positions to limit total DP drag.
- **SEBI retail algo framework** (effective 2026-04-01): the algo-ID stamp is **optional** at our scale — orders carry it when `SEBI_ALGO_ID` is set; >10 OPS triggers the empanelment requirement (we're at ~0.001 OPS, easy).

---

## When in doubt

- **Don't add features the loop hasn't earned.** Each new hyperparameter must clear the parsimony budget (§6.4 of spec).
- **Don't pre-emptively delete code** even if it looks unused — the US repo learned this the hard way (US repo learnings §8.4).
- **Don't skip the empty-news short-circuit** in classifiers — saves ~80% of LLM calls (US repo learnings §6.5).
- **Don't trust LLM-generated strategy code without running anti-overfit gates.** The whole point of the gates is that the loop *will* try to overfit; it's the gates that catch it.
- **Read `docs/handoff-india-pivot.md` and `docs/learnings-from-us-build.md`** before making non-trivial changes. These capture empirical lessons from the US-stocks predecessor (3 pivots in 3 days, ~4 weeks of trial-and-error compressed into reference docs).
- **The strategy is replaceable; the gates are not.** A bad strategy that passes the gates is a learning data point; a good strategy that bypasses the gates is a future blow-up.
