# Learnings from the US-Stocks Build (Phase 1: 2026-04 → 2026-05-14)

**Audience:** the fresh session executing the India pivot per `handoff-india-pivot.md`.

**Purpose:** capture every non-obvious insight from the first phase of this project so the rebuild doesn't have to re-discover them. Everything below is empirically observed, not theory.

---

## 1. Strategy learnings (what worked, what didn't)

### 1.1 Rank-retention beats fixed-cadence rotation

The original strategy rotated every 5 trading days. Q1 2024 paper-trade post-mortem showed it was selling winners during natural drawdowns and re-buying after the bounce — death by a thousand fee-cuts. Fix that shipped 2026-05-12:

```
selected = (held_positions_still_in_top_K + new_top_K_entries)[:top_k]
```

Adding a **retention_buffer = top_k // 2 = 5** (held positions stay if still in top-15, not just top-10) materially closed the gap to QQQ buy-and-hold. **2025 paper backtest: +19.21% vs QQQ +18.83%, Sortino 1.04 → 1.51, max DD 13.96%.**

**Transfer to Indian rebuild**: keep the rank-retention logic. It's universe-agnostic — anywhere there's persistent momentum, rotation friction hurts.

### 1.2 ATR trailing stop sized at 5× ATR_20 worked

Tighter (2-3× ATR) cut winners early; looser (8-10×) didn't protect during real reversals. 5× ATR_20 is the sweet spot for 3-5 day NDX swings. Indian markets have higher retail-driven volatility — likely need to RE-TUNE this; first-pass keep at 5× then run a sensitivity analysis (3×, 4×, 5×, 6×, 7×) and pick by validation Sortino.

### 1.3 Regime-gated entry selectivity (asymmetric defense)

When `macro_regime ∈ {risk_off, shock}` on a rebalance day, the strategy now BLOCKS new entries but holds existing positions (ATR stops still fire). This asymmetry preserves winners through normal drawdowns while preventing fresh capital from chasing weakening tape. Avoid the trap of symmetric "exit everything on risk-off" — it's expensive whipsaw.

**Indian rebuild**: same logic, but the macro_regime LLM prompt needs Indian-context inputs (RBI repo trajectory, FII/DII flows, INR strength, India VIX) instead of US-context (Fed, USD/DXY, US 10Y, VIX).

### 1.4 Mega-cap dominance regimes are a structural drag

2023-24 Nasdaq-100 was dominated by 5-7 mega-caps (NVDA/META/MSFT/AAPL/GOOG). Equal-weight rotation strategies systematically lagged. **The strategy isn't broken — the regime is.** Don't over-tune.

**India parallel**: Nifty has its own dominance pattern (HDFC Bank, Reliance, TCS, Infosys, ICICI). Same risk applies — equal-weight may lag during heavy index concentration. Track relative performance vs Nifty 100 ETF, not absolute returns.

### 1.5 Walk-forward Sortino is informational; aggregate-DD regression is the real gate

The `loop.py` KEEP/REVERT decision was tuned to use multi-dimensional gates rather than pure Sortino:
- KEEP requires: improved Sortino AND Sortino > 0 AND |Sortino| < 10 AND aggregate-DD didn't regress >10pp vs prev KEPT AND catastrophe gate clear

The "DD regression guard" is critical — without it the agent trades 15pp of DD for 0.05 Sortino gain (a classic local-max trap). Keep this gate verbatim in the rebuild.

### 1.6 Catastrophe-only auto-rejects work better than hard parameter caps

We tried hard caps (max 20% per position, max 100% gross, etc.) early — they were unwinnably tight on long-only NDX through 2018-23. Switched to **catastrophe-only**:
- >100% gross exposure (leverage error)
- >50% aggregate chained-fold DD (account-wipe territory)
- <20 trades total (statistic too noisy)

Soft signals (worst-fold DD, max position frac peak, n_negative_folds) are reported but never gated. The agent reasons about them in journal but the loop never auto-rejects. This balance lets exploration breathe without enabling disaster.

### 1.7 Held-vs-new branch separation in strategy code

The strategy logic splits into two clean paths: (a) update held positions (peak tracking, ATR stop check), (b) re-rank universe for new entries. Each path has its own gate. **Don't merge these — keeping them separate makes the regime-gating retrofit (1.3) clean.**

---

## 2. Architecture wins (worth preserving verbatim)

### 2.1 Karpathy three-file + journal pattern

```
prepare.py    # IMMUTABLE evaluator. Walk-forward backtest, Sortino+side panel.
strategy.py   # Agent-editable. Signal logic, sizing, entry/exit.
program.md    # Goal + constraints in natural language.
journal.md    # Hypothesis → change → result → learning. Compounds across runs.
```

The journal.md persistence across overnight loop iterations is what makes the agent NOT re-propose ideas it already burned. **Critical: must be on the same branch the loop runs on; cross-laptop merge conflicts on journal+log.csv are real.**

### 2.2 8-table ledger schema (mode-scoped PKs)

```
desired_targets  — strategy intent per (date, ticker, mode)
submitted_orders — orders sent to broker
actual_fills     — what filled (with broker-reported commission)
broker_positions — EOD snapshot from broker, per (date, ticker, mode)
cash_ledger      — every buy/sell/commission/dividend/deposit
position_lots    — FIFO tax lot tracking (open on buy)
realized_trades  — FIFO consumption rows (per sell × matched lot)
discrepancies    — informational + auditing
```

`mode` column on every PK lets paper / IBKR-paper / IBKR-live / future modes coexist in the same DB. Dashboard shows them as separate tabs. **Indian rebuild: keep this schema verbatim, just add 'dhan-paper' and 'dhan-live' modes.**

### 2.3 Idempotent _process_day with atomic transaction

```python
conn.execute("BEGIN TRANSACTION")
try:
    delete_day(conn, as_of_date, mode)   # clean prior run if any
    write_targets(...)
    write_orders(...)
    write_fills(...)
    write_lots(...)
    write_realized_trades(...)
    write_positions(...)
    write_discrepancies(...)
    conn.execute("COMMIT")
except Exception:
    conn.execute("ROLLBACK")
    raise
```

A failed run never leaves partial state. A rerun overwrites cleanly. **Keep this pattern exactly in the Dhan executor.**

### 2.4 Executor protocol decouples broker from orchestrator

```python
class Executor(Protocol):
    mode: str
    def execute_day(self, as_of_date, *, strategy_module, source_tag) -> ExecutionSummary: ...
```

scripts/run_live.py only calls `executor.execute_day(today)` and reads the summary. Broker-specific code never leaks into the orchestrator. **Indian rebuild: `DhanExecutor` implements this protocol; orchestrator is unchanged.**

### 2.5 LLM cache short-circuit + model_id stamping

```python
# llm/cache.py
cache_key = (date, ticker, prompt_hash, model_id)
# Empty-news cells short-circuit to default WITHOUT an LLM call
# Each cache row stores model_id, so swapping Sonnet → Opus auto-invalidates
```

This pattern is universal and important — the backtest re-runs hundreds of times during the autoresearch loop; without aggressive caching the LLM cost (or rate limit) would be the bottleneck.

### 2.6 signal_today projection (broker state + last-rebalance overlay)

We discovered (the hard way) that just capturing `order_target_percent` calls doesn't work — non-rebalance days produce empty captured dicts, breaking the simulator. The fix:

```python
projected = current_broker_positions_as_fractions  +  last_non_empty_rebalance_calls (overlay)
```

This gives the true "what the strategy intends to hold at next session open" — including held positions the strategy didn't touch this rebalance.

---

## 3. Cost economics — the capital-scaling thresholds we discovered

### 3.1 IBKR US stocks

| Position notional | Whole-share commission (Tiered) | Fractional (CP-API) | Notes |
|---|---|---|---|
| $50 | N/A (can't be whole) | $0.50 (1%) | Brutal |
| $100 | $0.35 (floor) | $1.00 (1%) | Floor binds |
| $500 | $0.35 (floor) | $5.00 (1%) | Floor still binds; 1% rule dominates fractional |
| $1,000 | $0.35 (floor) | $10.00 (1%) | |
| $5,000 | $0.35 (floor) | $50 (1%) | |
| $10,000 | $0.35-$0.50 | N/A | Tiered economics start working |

**Key finding: fractional commission floor = 1% × notional, no cap.** This is the "1% rule" that makes IBKR-fractional uneconomical at any small-capital level. Verified empirically 2026-05-14: 0.2 AAPL @ $297.86 = $59.572 notional → $0.60 commission (1.007%).

### 3.2 Indian brokers (Dhan delivery)

| Position notional | Cost (RT) | % drag |
|---|---|---|
| ₹1,000 ($12) | ₹20 | 2.0% |
| ₹5,000 ($60) | ₹20.91 | 0.42% |
| ₹10,000 ($120) | ₹26.60 | 0.27% |
| ₹50,000 ($600) | ₹72.17 | 0.14% |

**DP charges (₹14.75 sell-only) are FLAT per scrip.** This means N small positions amplify cost N-fold while N large positions don't.

**Strategy rule:** Position count should scale with capital. At ₹50k capital: 5-6 positions (not 10). At ₹2L+: 10 positions becomes fine.

### 3.3 Whole shares vs fractional — 17× commission difference

Same broker (IBKR), same account, $59.57 notional:
- **Whole share** (1 share @ $59.57): $0.35 commission (Tiered floor)
- **Fractional** (0.2 shares @ $297.86): $0.60 commission (1% rule)

The choice between "trade 10 small fractional positions" and "trade 1 larger whole-share position" can change strategy economics by 17×. Indian rebuild has no fractional question (one share is small enough), but the lesson generalizes: **for capital-constrained accounts, broker fee structure dictates strategy structure.**

---

## 4. Engineering pitfalls we hit (don't repeat)

### 4.1 The silent-drop bug in `classify_sentiment_batch`

```python
for key, ticker, d_str, _, key_ticker, single_hash in chunk:
    entry = results_by_key.get((ticker, d_str))
    if entry is None or not _validate_sentiment(entry):
        continue   # ← silently skips dropped cells!
```

Sonnet sometimes returns fewer cells than the input chunk (especially under load or with chunk size > 50). Our classifier silently dropped them, leaving `(ticker, date)` cells with no cached LLM output. Strategy then read defaults, masking the bug for days.

**Fix:** detect missing cells, log explicitly, retry the missed cells in a smaller chunk before giving up.

### 4.2 FRACTION_CHANGE_THRESHOLD = 0.005 saves 70%+ of turnover

When today's `target_fraction` for a ticker matches yesterday's within 0.5pp, skip the trade entirely. Mark-drift produces fake-rebalance churn that pays round-trip cost for ~0 alpha.

**Q1 2024 measurement:** 659 fills → 156 fills after threshold (76% reduction). Saved ~50% of paper-period PnL.

This is the most important "engineering as alpha" finding. Indian rebuild: keep verbatim.

### 4.3 Cash-ledger `entry_at = fill_date` (not signal_date)

We initially wrote cash entries with `entry_at = signal_date`. Caused get_cash_balance(as_of=fill_date) to over-count (cash debited BEFORE fills landed). Fix: cash moves on the fill day, not the signal day. as_of_date column stays at signal_date for delete_day scoping.

### 4.4 last_accepted_sortino parser hazard

```python
# loop.py: parse journal.md to find baseline Sortino for KEEP/REVERT comparison
# DO NOT match substring "KEPT" — it matches REVERTED entries that quote prior KEPT
# DO match the literal "**Decision:** KEPT" line
```

Multiple agents have re-written this parser; the substring version silently regresses the baseline because REVERTED hypothesis text often mentions prior KEPT iterations. **Preserve the literal-line match.**

### 4.5 paper_trade re-sizes daily on mark drift

Even with constant `target_fraction`, the simulator re-computes `target_qty = round(target_fraction × mark_equity / close, 6)` every day. mark_equity and close both drift, so target_qty fluctuates daily — generating spurious rebalances. The FRACTION_CHANGE_THRESHOLD (4.2) is the fix; **but it must be applied to `target_fraction` comparison, not `target_qty` delta**, because the latter is what drifts.

### 4.6 iterations/log.csv is load-bearing for the loop's short-term memory

The loop reads last 20 rows into the prompt's "RECENT ATTEMPTS" section. If a collaborator picks up the branch on another machine without log.csv, the agent re-proposes already-burned ideas. **Track log.csv in git** (per-iter trade subdirs stay ignored).

### 4.7 iterations/dashboard.html is heavy (~5MB) and regenerated every iter

Don't commit routinely — only at session-end handoffs, if at all. Can always be regenerated from log.csv + per-iter dirs.

---

## 5. Broker / market pitfalls (from US-stocks attempts)

### 5.1 IBKR TWS API fundamentally cannot do fractional stocks

Empirically verified 2026-05-14: every variant returns Error 10243.
- LMT + Decimal(0.2): rejected
- MKT + Decimal(0.2): rejected
- Adaptive algo + fractional: rejected
- notHeld=True + fractional: rejected
- MKT + cashQty=$50: rejected (Error 10244 — cashQty is mutual-funds-only for stocks)

Whole shares work fine. **The library/version is not the problem.** This is IBKR's published policy: TWS API supports fractional only for crypto and forex.

ib_async (the maintained fork of the abandoned ib_insync) does NOT fix this. We migrated to ib_async, retested — same Error 10243.

### 5.2 IBKR CP-API supports fractional but commission is brutal

CP-API path: fractional LMT orders ACCEPTED. We placed `0.2 AAPL LMT @ $250` empirically and it filled.

But the commission rule for fractional is: `max($0.01, 1% × notional)`. For tiny trades, that's effectively 1% per side. Our $59.57 trade incurred $0.60 commission. Round-trip on $500 capital with 10 fractional positions = 2% per round-trip → strategy mathematically unprofitable.

### 5.3 CP-API session lifecycle gotchas

- **24-hour expiry**: session dies daily, needs IBeam (Voyz/ibeam GitHub) for cron use, or manual browser re-login each morning
- **Paper accounts need the paper-specific username** (not the live credential). Login with live credential lands you in PORTAL context with `iserver.authStatus.authenticated=false` — you can read portfolio but cannot trade. Use `/v1/api/sso/validate` to inspect `PAPER_USER_NAME` vs `USER_NAME`.
- **Paper accounts lack market data subscription** by default. Limit orders sit at `PreSubmitted` forever. Use MKT orders for paper testing, OR subscribe to free delayed data in Client Portal → Settings → Market Data.
- **Reply chain safety**: CP-API order placement may return safety-warning prompts. We auto-confirm specific known-safe messageIds (`o163`, `o403`, `o451`) and refuse unknown ones (`o354` — "no market data" — auto-confirm only in paper mode, never live).

### 5.4 Indmoney (US stocks via DriveWealth) — Cloudflare blocks browser automation

Indmoney has solid commissions (0.25%, capped at $25) and supports fractional natively. But no public API for US stocks — only browser automation via their web UI. Their UI sits behind Cloudflare anti-bot, which blocks Playwright reliably. We tried, gave up.

### 5.5 Alpaca funding is broken from India

Alpaca supports Indian residents (verified via their docs). But funding the account from India fails empirically:
- HDFC/Axis/ICICI all block wires to Alpaca's BMO Harris correspondent account
- CurrencyCloud (Alpaca's USD inbound rail) doesn't support INR
- Wise refuses "investment purpose" remittances

Forum threads (Sahil Mirchandani Dec 2024 et al.) document this. **For Indian residents, Alpaca is effectively closed.**

### 5.6 LRS / TCS / Schedule FA / Form 67 = compliance overhead

For Indian residents trading US stocks:
- LRS cap $250k/year per individual
- TCS 20% on outbound remittance above ₹10L/year (creates working-capital drag)
- Schedule FA mandatory annual disclosure of foreign assets
- Form 67 for foreign-tax-credit (DTAA US-India: 25% dividend withholding, no double tax on cap gains)
- Forex spread 0.5-1.2% each direction (bank-dependent)

**The Indian-market rebuild eliminates all of the above.**

---

## 6. LLM stack learnings

### 6.1 Two LLM channels — keep them separate

```
Autoresearch agent   = Claude Opus 4.7 via Claude Code CLI on laptop
In-strategy classify = Claude Sonnet 4.6 via Claude Agent SDK (reuses local CLI auth)
```

The agent edits strategy.py overnight. The classifiers run programmatically inside the backtest loop. Different cadences, different prices, different rate limits. Mixing them confuses model_id stamping and cache invalidation.

### 6.2 Claude Agent SDK reuses local CLI subscription — no API key

`from claude_agent_sdk import ...` → auto-uses the locally-logged-in Claude Code CLI session. Costs are bounded by your Claude Code subscription, NOT by ANTHROPIC_API_KEY. No secrets in .env, no API key leakage risk.

### 6.3 Sonnet timeouts at 120s under load

We hit this on 2026-05-14: sentiment chunks of 50 cells took >120s under high Sonnet load. Default timeout was 120s; calls would silently retry-fail.

**Fix:** `Provider.classify(timeout=300)` default, chunk_size 50 → 25 in daily_update.py. Empirically validated post-fix: 200s sentiment, 266s events for full universe.

### 6.4 Cache key includes prompt_hash AND model_id

Every cache row stores `(date, ticker, prompt_hash, model_id)`. Two consequences:
- Editing the prompt (bump version in `llm/prompts.py`) auto-invalidates the affected slice; agent recomputes on next run
- Swapping model (Sonnet → Opus, or Claude → Codex) marks cache as MISS for new model_id, cleanly re-classifies

Don't break this invariant. The cache becomes correctness-critical when running 100s of backtest iterations.

### 6.5 Empty-news short-circuit (no LLM call)

When `(ticker, date)` has zero news rows in `news.duckdb`, the classifier returns the default sentiment/events WITHOUT calling Sonnet. Saves ~80% of LLM calls on a typical day (most NDX names have no news on most days). Indian universe likely similar.

---

## 7. Strategy + universe-construction wisdom

### 7.1 Survivorship bias is real

Backtest universe MUST be locked to a historical snapshot of constituents. We snapshot at `BACKTEST_START` (2018-01-01). Tickers added later don't enter the universe; tickers delisted later carry forward as delisted entries (zero qty, no orders). This prevents "we would have held NVDA from 2010" hindsight bias.

**Indian rebuild**: Nifty 100 reconstitutes ~2x/year. Lock to BACKTEST_START snapshot.

### 7.2 _MIN_BARS_PER_FEED = 60 prevents indicator IndexError

Strategies with multi-feed indicators (50-day SMA on 100 tickers) crash with `IndexError` if any feed has <60 bars in the window. Filter feeds at load time. We hit this on multi-feed backtrader vectorized indicator pass.

### 7.3 The strategy generates `order_target_percent`, not `self.buy()/close()`

`signal_today.py` intercepts `order_target_percent()` to capture target fractions. Strategies using `self.buy()` directly produce empty captured target dicts → paper-trade writes nothing → silently broken.

**Indian rebuild: all strategy code uses `order_target_percent`.** This is a contract, not a suggestion.

### 7.4 Held-bar gating logic

Strategy decides "rebalance" vs "no rebalance" days. On non-rebalance bars, the strategy returns early (no order_target_percent calls). signal_today's last-non-empty-rebalance overlay (§2.6) handles this — without it, the simulator on non-rebalance days writes empty desired_targets.

---

## 8. Process learnings

### 8.1 Pivot fatigue is real, and empirical evidence beats hunches

This project pivoted **three times in three days**:
1. indmoney browser automation → IBKR TWS API (driven by Cloudflare block)
2. IBKR TWS API → IBKR CP-API (driven by Error 10243 on fractional)
3. IBKR CP-API → India pivot (driven by 1% fractional commission economics)

Each pivot had emotional + engineering cost. The **right** pattern: **collect empirical evidence (run the broken thing once, see the actual error/cost) BEFORE pivoting**. Pivots driven by hunch were less robust than pivots driven by error messages.

The handoff doc explicitly captures the empirical numbers (commission %, error codes, etc.) so the next session can SEE why each prior choice was discarded.

### 8.2 The "stop and think" moment matters

Late on 2026-05-14 the user asked: "wait, should we have just gone Indian markets from the start?" — that question was worth more than 3 hours of incremental hacking would have been. Build moments of stepping back into the workflow.

### 8.3 Verify gh account before push

Memory: default gh auth is the company account (`aryan-socratic`). Must switch to `victorvini08` (personal) before any push/pr/repo op. `gh auth switch -u victorvini08` is the one-liner. The handoff push followed this.

### 8.4 Don't pre-emptively delete potentially-useful code

When we deleted `scripts/paper_trade.py` and `scripts/executors/paper.py` on the IBKR pivot, the simulator went too. When we later realized IBKR paper accounts have no market data and need a simulator-equivalent — the deleted code became valuable again. **For the India rebuild: keep simulator pattern available even if current path uses real broker. Cheap insurance.**

### 8.5 Single broker per branch at a time

Two laptops running the same branch with different broker configs causes constant merge conflicts on portfolio.duckdb, journal.md, and iterations/log.csv. Either set up a single canonical box or use mode-scoped per-laptop branches.

---

## 9. Specific anti-patterns to avoid in the India rebuild

| Anti-pattern | Why to avoid | Right thing |
|---|---|---|
| Default broker = Upstox | API costs ₹20/order on delivery, 2-3× pricier than Dhan | Default broker = **Dhan HQ** |
| 10 positions at ₹50k capital | DP charges (₹14.75 flat per sell) become 30% drag | 5-6 positions at small capital; scale to 10 at ₹1L+ |
| Limit orders without market data | Paper accounts sit at PreSubmitted forever | MKT orders for paper, LMT for live once market-data subscribed |
| Auto-confirm any reply prompt | Could blindly approve "halted stock" or "size exceeds limit" warnings | Allowlist `o163, o403, o451` always; `o354` only in paper mode |
| Skip the FRACTION_CHANGE_THRESHOLD | 76% turnover reduction → real money | Keep verbatim, 0.005 on `target_fraction` not `target_qty` |
| Substring match for `KEPT` in journal | Silently regresses baseline | Literal-line match for `**Decision:** KEPT` |
| Pre-emptively delete old/branch code | Often re-needed during pivots | Archive, don't delete |
| Run loop on two machines same branch | Merge conflicts on journal+log.csv | Per-laptop branches OR canonical single-box |
| Trust cached LLM output without model_id check | Mixing model outputs breaks reproducibility | Cache key includes model_id always |
| Backtest commission model independent of broker | Real costs diverge wildly | Cost model must match the broker we'll execute on |

---

## 10. Cross-reference to specific files

| File | Key learning embedded |
|---|---|
| `strategy.py` | Rank-retention + ATR trailing stop + regime-gated new entries (§1) |
| `prepare.py` | Walk-forward 2y/6m/3m structure; STCG_RATE side-panel info (§2.1) |
| `scripts/signal_today.py` | Broker state + last-rebalance overlay projection (§2.6) |
| `scripts/loop.py` | Multi-dim KEEP/REVERT gate with DD-regression guard (§1.5) |
| `scripts/risk_check.py` | Halt-flag, max-DD, daily-loss, concentration, gross-exposure gates |
| `scripts/executors/protocol.py` | Executor interface — broker-agnostic (§2.4) |
| `storage/portfolio_db.py` | 8-table mode-scoped schema; FIFO lots; FY-net tax (§2.2) |
| `backtest/risk.py` | Catastrophe-only validator (§1.6) |
| `llm/cache.py` | `(date, ticker, prompt_hash, model_id)` key invariant (§6.4) |
| `llm/classify.py` | The silent-drop bug to fix on rebuild (§4.1) |
| `journal.md` | `**Decision:** KEPT` literal — don't substring match (§4.4) |
| `learnings.md` | Domain-specific insights accumulated by the agent across iterations |

---

## 11. Things we tried that didn't work (for the record)

- **indmoney browser automation via Playwright** — Cloudflare block
- **IBKR TWS API for fractional shares** — Error 10243, regardless of library
- **IBKR cashQty for stocks** — Error 10244 (mutual-funds-only)
- **Alpaca for Indian residents** — funding pipeline broken
- **ib_insync** (deprecated; succeeded by ib_async) — works fine for whole shares, useless for fractional
- **Adaptive algo + fractional** — same Error 10243
- **Order.notHeld=True + fractional** — same Error 10243
- **Tighter ATR multiplier (2-3×)** — cuts winners early
- **Looser ATR multiplier (8-10×)** — doesn't protect during real reversals
- **5-day fixed-cadence rotation** — amputates winners, the original problem
- **Symmetric exit-everything-on-risk-off** — expensive whipsaw

Each of these consumed real engineering time. **Don't re-explore them blindly during the rebuild.**

---

## 12. Closing thought

The framework (Karpathy 3-file, 8-table ledger, walk-forward backtest, daily LLM cache, Executor protocol, autoresearch loop with KEEP/REVERT gates) is broker- and market-agnostic. Most of the engineering effort in Phase 1 went into discovering the cost-economics constraints of US-fractional trading at small capital — not into building wrong abstractions.

**For the Indian rebuild:** the architecture survives. The data layer (broker, prices, news, macro, universe) is what changes. The strategy logic is likely tunable but the SHAPE (momentum + rank-retention + ATR trailing stop + regime gating) carries over.

Estimated effort: 9-10 hours of focused work to be back at "today's state but on Indian markets with cleaner economics" (see handoff §8).
