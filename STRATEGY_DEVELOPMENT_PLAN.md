# Strategy development plan — real-world generalization

Start here in a new session. Read `PRODUCTION_STRATEGY.md` first (what the
base strategy is and the honest caveats), then this.

---

## THE GOAL (precise, this is what "good" means)

Build a **long-only NSE CNC-delivery strategy** on the top-200-by-ADV
point-in-time universe, ~biweekly, **net of full Dhan costs at ₹50k**, that:

1. **Generalizes across ALL regimes.** Positive *or* deliberately
   capital-preserving in **bear, bull, AND neutral** sub-periods — measured on
   the **worst** regime sub-period, never the average. No sign-flip across
   regime sub-periods. This is the primary objective; a high average Sortino
   that hides a losing regime is a FAILURE, not a success.
2. **Beats buy-and-hold Nifty 500 on risk-adjusted terms across a full
   cycle**, not just on the mean.
3. **Survives forward.** The historical sealed window (2025-01→2026-05) is
   **BURNED** — we peeked at it 24+ times selecting checkpoints. It can no
   longer certify anything. The only real proof is **4-week forward
   `dhan-paper` validation** (CLAUDE.md hard constraint). Optimise for
   robustness, not for any backtest number.
4. **Stays simple enough to reason about.** Expose hidden hard-coded windows
   as named params; respect the parsimony principle honestly.

Non-goal: maximising validation/backtest Sortino. That metric, chased blindly,
produced the 3.8→loss disaster. Worst-regime robustness is the target.

## STARTING POINT

`strategy.py` on this branch = checkpoint `2026-05-17-a05b891`, a **long-only
cross-sectional momentum-quality carry** book (NOT mean-reversion despite the
class name — rename it first). 12-1 + mid-horizon relative strength, gated by
quality/defensive overlays (low downside vol, limited drawdown, proximity to
trailing high), diversified fixed-slot sizing, sector cap, biweekly. OOS over
the (now-burned) test window: +5.36%, Sortino +0.75, 4.7% maxDD, sidestepped
the −14% 2026-Q1 crash. Modest, plausible, unproven.

## DESIGN PRINCIPLES (the manual-improvement agenda, priority order)

### 1. Regime adaptivity — the #1 generalization lever
Replace any binary regime gate (the loop overfit those) with a **continuous
risk dial** from `india_vix_percentile(date)` + `nifty_vs_200dma_pct(date)`
(both in `llm.features`, real coverage). The dial scales **gross exposure** and
tilts selection toward lower-beta/quality as risk rises; in a true bear a
long-only book's only tool is **graceful de-risking toward cash/defensive**.
Apply **hysteresis** (different thresholds to risk-off vs risk-on, and/or a
min dwell time) so it does not whipsaw at the boundary.

### 2. Let winners run / kill churn (returns AND cost both win at ₹50k)
The user's US lesson, and correct for momentum (returns live in the right
tail; cutting winners early destroys the edge AND burns ₹14.75/scrip DP on
every needless sell). Implement **asymmetric retention**: a held name that is
**still in a confirmed uptrend and above its volatility-scaled trailing stop
is RETAINED** even if its cross-sectional rank slips into a *wide* buffer.
Sell only on: breakdown (principle 3), regime de-risk (principle 1), or deep
rank decay *while not trending*. Never sell a healthy winner merely because
something else out-ranked it this fortnight.

### 3. Asymmetric, volatility-scaled loss handling (the user's nuance)
"Cut losers, but don't whipsaw on normal corrections." Indian mid-caps
routinely correct 5–10% as noise. So an exit must be **relative to the
stock's own volatility, structurally confirmed, and persisted**:
- Trigger only if price falls > **k × the stock's own downside-deviation/ATR**
  below its trailing peak (the code already computes `downside_vol` — reuse
  it). A fixed % stop is wrong; a vol-scaled stop adapts to each name.
- AND structure broken (e.g. close below 50/100-DMA), persisted ≥ N closes /
  confirmed at the next rebalance unless catastrophic — filters single-bar
  wicks.
- **Asymmetric:** tighter on losers (protect capital), loose on winners (let
  them run). This is also the textbook momentum-crash tamer → directly serves
  the regime-generalization goal.

### 4. Per-ticker news — asymmetric RISK overlay, NOT primary alpha
Reality check (verified):
- **Available now:** `news_volume(ticker, date)` (raw article count, 72k
  articles 2021→2026) and earnings surprise (`news.duckdb earnings_calendar`,
  `surprise_pct`).
- **NOT available until precomputed:** `sentiment()` / `events()` — the LLM
  classifier cache (`llm_cache.sqlite`) has only ~1,575 rows. They return
  defaults today. **Prerequisite task:** run the classifier precompute over
  the backtest window (Sonnet 4.6; the empty-news short-circuit bounds cost)
  BEFORE any sentiment/events logic — otherwise it is silently inert.

Usage (asymmetric — act hard on bad, tilt lightly on good; sentiment is noisy
and often already priced):
- Strong **negative** event / sentiment / earnings miss on a **HELD** name →
  **accelerate the exit** (information leads price — this is *superior* loss
  handling vs price-only stops).
- Fresh **negative** news on a **CANDIDATE** → **veto the entry** (avoids
  momentum/quality traps where the chart looks good but the news is bad).
- **news_volume spike** → elevated uncertainty → **trim size**, don't add.
- **Positive** sentiment → at most a mild tie-breaker among
  comparably-ranked names. Never a standalone entry reason.

### 5. Anti-re-overfitting discipline (non-negotiable)
The sealed window is gone. Do **not** optimise to any single backtest. Each
change: evaluate on (a) walk-forward Sortino, (b) the **WORST** regime
sub-period, (c) **turnover & net-of-cost drag at ₹50k**, (d) worst-sub-period
maxDD. Keep a change only if it improves **worst-regime** behaviour without
ballooning turnover. Forward `dhan-paper` is the real arbiter. Expose hidden
params so parsimony is honest. One mechanism at a time — no bundled changes.

## METHOD / ORDER OF WORK

1. **Rename + de-hide params.** `IndiaResidualReversalStatArb` →
   `IndiaMomentumQualityCarry`; lift every hard-coded window/threshold to a
   named param. (No behaviour change — establishes an honest, reasoned base.)
2. **Principle 2 (let winners run / asymmetric retention)** — biggest
   expected win (returns + cost), lowest risk.
3. **Principle 3 (vol-scaled, confirmed, asymmetric stops).**
4. **Principle 1 (continuous regime dial + hysteresis).**
5. **News precompute, then principle 4** (volume/earnings first — available
   now; sentiment/events after the precompute pass).
6. Throughout: worst-regime + cost-at-₹50k evaluation; then **forward paper**.

## DO-NOT-REPEAT (lessons already paid for)

- Chasing mean validation Sortino → 289-iter rotation hit 3.8, lost −8% OOS.
  Optimise worst-regime, not the mean.
- Binary regime gates and selected-count sizing → catastrophe drawdowns.
- Hidden hard-coded windows that dodge the parsimony gate → silent overfit.
- Building news logic against the empty classifier cache → silently inert.
- Re-using the burned sealed window as "proof".

---

## PROMPT TO GIVE THE `goal` SKILL IN A NEW SESSION

> Use the goal skill. Working branch: `production-strategy`. Read
> `PRODUCTION_STRATEGY.md` and `STRATEGY_DEVELOPMENT_PLAN.md` in full first.
>
> GOAL: evolve `strategy.py` (currently long-only momentum-quality carry,
> checkpoint a05b891) into a strategy that **generalizes across bear, bull,
> and neutral regimes** for real-world Indian-equity CNC delivery trading at
> ₹50k net of Dhan costs — judged on its **worst** regime sub-period and on
> forward robustness, NOT on average/backtest Sortino (chasing that metric
> already produced a 3.8-validation / −8%-OOS blow-up; the historical sealed
> window is burned and must not be optimised against).
>
> Work the agenda in `STRATEGY_DEVELOPMENT_PLAN.md` in order: (1) rename +
> expose hidden params (no behaviour change), (2) let-winners-run asymmetric
> retention, (3) volatility-scaled structurally-confirmed asymmetric loss
> exits, (4) continuous regime dial with hysteresis, (5) news overlay
> (`news_volume`/earnings now; precompute the sentiment/events classifier
> cache before using `sentiment()`/`events()` — they are currently empty).
> One mechanism per iteration. After each, evaluate walk-forward Sortino, the
> worst regime sub-period, and turnover/net-cost at ₹50k; keep a change only
> if it improves worst-regime behaviour without ballooning turnover. Respect
> all CLAUDE.md hard constraints (long-only, `order_target_percent` only, PIT
> universe, never edit `prepare.py`/`backtest/anti_overfit.py`). Commit as
> victorvini08. Do not touch other branches.
