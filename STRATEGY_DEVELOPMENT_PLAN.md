# Strategy development plan — real-world generalization

Start here in a new session. Read `PRODUCTION_STRATEGY.md` first (what the
base strategy is + honest caveats), then this.

---

## THE GOAL (this is what "good" means)

A **long-only NSE CNC-delivery strategy** on the top-200-by-ADV point-in-time
universe, ~biweekly, **net of full Dhan costs at ₹50k**, that:

1. **Generalizes across ALL regimes** — positive *or* deliberately
   capital-preserving in **bear, bull, AND neutral**, judged on the **worst**
   regime sub-period, never the average. No sign-flip across regimes. A high
   average that hides a losing regime is a FAILURE.
2. **Beats buy-and-hold Nifty 500 risk-adjusted across a full cycle.**
3. **Survives forward.** The 2025-01→2026-05 sealed window is **BURNED** (we
   peeked 24+ times). Only **4-week forward `dhan-paper`** validation can
   certify. Optimise for robustness, never for a backtest number.

Non-goal: maximising backtest Sortino — chased blindly it produced the
3.8-validation / −8%-OOS blow-up. **Worst-regime robustness is the target.**

## STARTING POINT

`strategy.py` on this branch = checkpoint `2026-05-17-a05b891`, class
`IndiaMomentumQualityCarry`: long-only cross-sectional **momentum-quality
carry** — 12-1 + mid-horizon relative strength gated by quality/defensive
overlays (low downside vol, limited drawdown, proximity to trailing high),
diversified fixed-slot sizing, sector cap, biweekly. OOS over the (burned)
window: +5.36%, Sortino +0.75, 4.7% maxDD, sidestepped the −14% 2026-Q1
crash. Modest, plausible, unproven.

## DESIGN PRINCIPLES (priority order)

### 1. Let winners run / kill churn — do this first
Returns AND cost both win at ₹50k (momentum's edge is the right tail; cutting
winners early kills it and burns ₹14.75/scrip DP on every needless sell).
**Asymmetric retention:** a held name still in a confirmed uptrend and above
its volatility-scaled trailing stop is **RETAINED** even if its rank slips
into a *wide* buffer. Sell only on breakdown (#2), regime de-risk (#3), or
deep rank decay *while not trending*. Never sell a healthy winner just because
something out-ranked it this fortnight.

### 2. Asymmetric, volatility-scaled loss handling
Cut real losers; don't whipsaw on normal corrections (Indian mid-caps routinely
correct 5–10% as noise). Exit only if **all** of: price > k × the stock's own
downside-deviation/ATR below its trailing peak (the code already computes
`downside_vol` — reuse it; a fixed-% stop is wrong), AND structure broken
(close below 50/100-DMA), AND persisted ≥ N closes. Tighter on losers, loose
on winners — the textbook momentum-crash tamer, so it also serves the
regime-generalization goal.

### 3. Regime adaptivity — the core generalization lever
A **continuous risk dial** from `india_vix_percentile(date)` +
`nifty_vs_200dma_pct(date)` (real coverage in `llm.features`) that scales
gross exposure and tilts toward lower-beta/quality as risk rises — NOT a
binary gate (the loop overfit binary gates). In a true bear a long-only book's
only tool is **graceful de-risking toward cash/defensive**. Use **hysteresis**
(asymmetric on/off thresholds or a min dwell) so it does not whipsaw.

### 4. Anti-re-overfitting discipline (non-negotiable)
Sealed window is gone — do not optimise to any single backtest. Each change,
evaluate: (a) walk-forward Sortino, (b) the **WORST** regime sub-period,
(c) **turnover & net-of-cost drag at ₹50k**, (d) worst-sub-period maxDD. Keep
a change only if it improves **worst-regime** behaviour without ballooning
turnover. One mechanism per iteration — no bundled changes. Forward
`dhan-paper` is the real arbiter.

## ORDER OF WORK

1. Let-winners-run asymmetric retention (#1) — biggest expected win, lowest risk.
2. Volatility-scaled, structurally-confirmed, asymmetric stops (#2).
3. Continuous regime dial + hysteresis (#3).
4. Throughout: worst-regime + cost-at-₹50k evaluation; then **forward paper**.

## DEFERRED — per-ticker news (add later, no code rework needed)

Left out for now: raw news exists (72k ticker-tagged articles 2021→2026) but
the `sentiment()`/`events()` LLM classifier cache is near-empty (~1,575 rows),
so they return defaults today. **Precompute estimate: ~1–4 hrs wall time**,
one-time, for the full backtest window (Sonnet 4.6; the empty-news
short-circuit skips ~80% of cells; subscription-bounded cost). It is
**resumable** (cache keyed by date/ticker/prompt_hash/model_id, model-agnostic
lookup) so it can run incrementally as a background batch across sessions.
Once populated, `sentiment()`/`events()` light up with **zero strategy-code
change** (write news logic as an overlay that no-ops on empty cache). When
added, use it **asymmetrically as a risk overlay** (act hard on negative
news/earnings-miss to accelerate exits / veto entries; only a mild tilt on
positive). `news_volume()` + earnings surprise are usable now if wanted.
**Verdict: safe to defer; addable anytime as a data/ops task.**

## DO-NOT-REPEAT (lessons already paid for)

- Chasing mean validation Sortino → rotation hit 3.8, lost −8% OOS. Optimise
  worst-regime, not the mean.
- Binary regime gates / selected-count sizing → catastrophe drawdowns.
- Hidden hard-coded windows that dodge the parsimony gate → silent overfit.
- Re-using the burned sealed window as "proof".

---

## PROMPT FOR THE `goal` SKILL (new session)

> Use the goal skill. Branch: `production-strategy`. Read
> `PRODUCTION_STRATEGY.md` and `STRATEGY_DEVELOPMENT_PLAN.md` first.
>
> Goal: evolve `strategy.py` (long-only momentum-quality carry) so it
> **generalizes across bear, bull, and neutral regimes** for real ₹50k
> Indian CNC trading net of Dhan costs — judged on the **worst** regime
> sub-period, never average/backtest Sortino (the sealed window is burned;
> chasing that metric already caused a 3.8→−8% blow-up).
>
> Do, one mechanism per iteration, in order: (1) let-winners-run asymmetric
> retention, (2) volatility-scaled structurally-confirmed asymmetric stops,
> (3) continuous regime dial with hysteresis. After each, check walk-forward
> Sortino, the worst regime sub-period, and turnover/net-cost at ₹50k; keep
> the change only if the worst regime improves without turnover ballooning.
> Respect CLAUDE.md hard constraints (long-only, `order_target_percent` only,
> PIT universe, never edit `prepare.py`/`backtest/anti_overfit.py`). Commit
> as victorvini08; do not touch other branches. (News is deferred — ignore.)
