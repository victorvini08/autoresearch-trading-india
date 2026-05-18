# Autoresearch Trading — India

LLM-driven autoresearch swing-trading system for Indian equities, delivery (CNC) only, via the Dhan HQ Trading API. Inherits architecture from `autoresearch-trading-us` (archived); the data/broker/strategy/cost layers are India-specific.

**Current phase:** v1 paper-only (`dhan-paper`), built against an in-memory mock Dhan client. Live execution (`dhan-live`) is built but disabled by `halt.json` until 4 weeks of clean paper validation.

> **Branch `mean-reversion-quant-strategy` (parallel experiment):** on this
> branch `strategy.py` is `IndiaResidualReversalStatArb` — a long-only
> short-horizon residual mean-reversion stat-arb book, the structural
> inverse of `main`'s momentum strategy. It runs its own isolated
> autoresearch loop (own `journal.md`/`program.md`) so the two experiments
> cannot converge. The locked-decisions table below documents `main`'s
> momentum rationale and is intentionally left intact for reference.

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
| Strategy shape | Cross-sectional 12-1 momentum-quality **selection** → **bounded gross-targeting** construction (deploy intended gross down the ranked list, per-name ≤ `_MAX_NAME_WEIGHT`=10% AND per-sector ≤25%) → **volatility-targeted gross** (`clip(0.12/realised_mkt_vol_ann, 0, 0.99)`). KEPT 2026-05-18 (Improvement GH). | Theory-backed (Jegadeesh-Titman / Asness / Novy-Marx selection; Barroso–Santa-Clara 2015 & Moreira–Muir 2017 vol-managed momentum). Replaces the old fixed-slot `gross/n_positions` + 4-step `breadth_scaled_gross`, which only ever deployed ~24% (see sector-wiring row). Held-out sealed +12.07% vs Nifty −1.94%, scale-robust at ₹5L. |
| **Sector-wiring fix** (root cause) | `_load_sector_map` sources per-ticker industry from the **PIT universe DB** (point-in-time-safe enrichment), NOT the feed attribute. | The backtest/live `bt.feeds.PandasData` never carried an industry attr, so every name was 'OTHER' → the 25% sector cap was a hidden **25% whole-book net-exposure ceiling** in EVERY pre-2026-05-18 backtest AND live. **All pre-2026-05-18 results, gates, and A–F reverts are VOID** — re-test any "burned" idea on the corrected engine. |
| Anti-overfit gates | Sealed 2024-26 test, Bonferroni p-correction, RW Monte Carlo, parsimony budget, sub-period stationarity, cost-aware Sortino | **NEW for India**; addresses US multi-strategy overfit failure |
| Rebalance cadence | **Biweekly** (alternate Fridays) | User-specified |
| Starting capital | ₹50,000 paper. Position count is now an *outcome* of bounded gross-targeting (~10–15 names when fully invested at the 10% per-name cap), not a fixed 5–6. | DP-charge optimization, now subordinate to the 10% concentration limit |
| LLM stack | Claude Code SDK: **Opus 4.7** for autoresearch loop, **Sonnet 4.6** for classifiers; Qwen3 fallback | Subscription-bounded cost; cache keyed by `(date, ticker, prompt_hash, model_id)` |
| Live mode | Built but disabled (`halt.json` defaults to halted=true for `dhan-live`) | 4-week paper validation gate |
| News sources | **5 trusted free**: MoneyControl, Pulse RSS, NSE filings, RBI press, SEBI press | No paid APIs |

---

## Hard constraints (real money risk if violated)

1. **Never enable `dhan-live` mode without explicit user approval AND a successful 4-week `dhan-paper` validation run** logged in `iterations/log.csv` and `journal.md`. The `halt.json` mechanism is the gate.
2. **All orders must carry the SEBI algo ID stamp** (`$SEBI_ALGO_ID` env var) per the 2026-04-01 retail algo framework. Orders without it are non-compliant.
3. **Strategy uses `order_target_percent` only** (no `self.buy()` / `self.close()`). Required by `scripts/signal_today.py`'s capture logic.
4. **FRACTION_CHANGE_THRESHOLD = 0.005** on `target_fraction` (not `target_qty`) suppresses mark-drift churn. Do not remove.
5. **Cash-ledger entries write on `fill_date`, not `signal_date`** (US repo learnings §4.3 — get_cash over-counts if we use signal_date).
6. **Journal parser uses literal-line match for `**Decision:** KEPT`** — never substring (US repo learnings §4.4).
7. **LLM cache rows are still WRITTEN keyed by `model_id`** (audit/ablation provenance preserved). But as of 2026-05-15 (explicit user decision) the precompute cache-SKIP lookup is **model-agnostic by default**: a cell already classified by ANY provider is reused, so a Codex-filled half-cache is *continued* by a later Claude run instead of recomputed. This matches `llm.features` reading the cache model-agnostically (these coarse 4-class/[-1,1]/7-flag outputs are treated as model-interchangeable). Set `LLM_STRICT_MODEL_CACHE=1` to restore strict per-model isolation for a clean single-model ablation. (Supersedes the original "swapping models invalidates the slice" rule.)
8. **Anti-overfit gates are atomic.** A variant that fails ANY gate is REJECTED, not partially accepted.
9. **Sealed test set (2024-01 → 2026-05) is revealed ONCE per promotion** — no retries on the same variant.
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

### 4. Register the algo with Dhan (SEBI compliance, mandatory from 2026-04-01)
- In the Dhan API portal, register a new "Personal Algo" (NOT "Trading Provider").
- You'll receive a unique `SEBI_ALGO_ID`. This will be stamped on every order our system places.
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

Install the launchd job so it runs daily at 08:45 IST (before the 09:00
premarket scan):

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

| Job | Time | Plist file | What it does |
|---|---|---|---|
| Premarket scan | 09:00 | `deploy/launchd/com.autoresearch.premarket_scan.plist` | Check overnight gaps, India VIX spike, halts |
| Daily update | 09:15 | `deploy/launchd/com.autoresearch.daily_update.plist` | Ingest yesterday's bhav, news, macro deltas |
| Run live (rebalance days only) | 10:00 | `deploy/launchd/com.autoresearch.run_live.plist` | Signal → orders → fills → ledger writes |
| Risk check + daily report | 15:35 | `deploy/launchd/com.autoresearch.daily_report.plist` | Post-close summary |
| Autoresearch loop | 22:00 | Manual or `deploy/launchd/com.autoresearch.run_overnight.plist` | LLM proposes strategy edit; backtest; KEEP/REVERT |

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
├── strategy.py           # LOOP-EDITABLE: 12-1 momentum-quality selection → bounded gross-targeting → vol-targeted gross (sector-fixed)
├── program.md            # Goal + constraints (read by autoresearch loop)
├── journal.md            # Append-only memory of every iteration
├── learnings.md          # Compounding domain insights
├── backtest/             # engine, metrics, risk, costs (Dhan), anti_overfit
├── brokers/              # dhan (Trading API), dhan_mock (paper)
├── data/                 # universe, sectors, quality_screen, ingest_{prices,news,macro,earnings,corp_actions}
├── llm/                  # provider, classify, features, cache, prompts (India)
├── scripts/              # loop, run_live, run_overnight, executors/dhan, sebi_compliance, ...
├── storage/              # *.duckdb generated (gitignored)
├── tests/                # pytest tree
├── deploy/launchd/       # macOS plists (IST schedules)
└── docs/
    ├── handoff-india-pivot.md     # carried from US repo (historical)
    ├── learnings-from-us-build.md # carried from US repo (historical)
    └── superpowers/
        ├── specs/                 # design spec (this rebuild)
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
- **SEBI retail algo framework** (effective 2026-04-01): every order must carry our algo ID; >10 OPS triggers empanelment requirement (we're at ~0.001 OPS, easy).

---

## When in doubt

- **Don't add features the loop hasn't earned.** Each new hyperparameter must clear the parsimony budget (§6.4 of spec).
- **Don't pre-emptively delete code** even if it looks unused — the US repo learned this the hard way (US repo learnings §8.4).
- **Don't skip the empty-news short-circuit** in classifiers — saves ~80% of LLM calls (US repo learnings §6.5).
- **Don't trust LLM-generated strategy code without running anti-overfit gates.** The whole point of the gates is that the loop *will* try to overfit; it's the gates that catch it.
- **Read `docs/handoff-india-pivot.md` and `docs/learnings-from-us-build.md`** before making non-trivial changes. These capture empirical lessons from the US-stocks predecessor (3 pivots in 3 days, ~4 weeks of trial-and-error compressed into reference docs).
- **The strategy is replaceable; the gates are not.** A bad strategy that passes the gates is a learning data point; a good strategy that bypasses the gates is a future blow-up.
