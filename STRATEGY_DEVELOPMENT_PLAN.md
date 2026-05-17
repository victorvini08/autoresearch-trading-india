# Strategy development — goal & guardrails

Read `PRODUCTION_STRATEGY.md` first (what the base strategy is + honest
caveats), then this. This is **not a recipe**. It states the goal, the
constraints, the hard-won guardrails, and some considerations to weigh. How
to get there is yours to reason out — design the best strategy you can; the
items below are inputs, not a checklist.

---

## THE GOAL (what "good" means)

A **long-only NSE CNC-delivery strategy** on the top-200-by-ADV point-in-time
universe, **net of full Dhan costs at ₹50k**, that:

1. **Generalizes across ALL regimes** — positive *or* deliberately
   capital-preserving in **bear, bull, AND neutral**, judged on the **worst**
   regime sub-period, never the average. No sign-flip across regimes. A high
   average that hides a losing regime is a FAILURE.
2. **Beats buy-and-hold Nifty 500 risk-adjusted across a full cycle.**
3. **Survives forward.** The 2025-01→2026-05 sealed window is **BURNED** (we
   peeked 24+ times). Only forward `dhan-paper` validation certifies.
   Optimise for robustness, never for a backtest number.

Non-goal: maximising backtest Sortino — chased blindly it produced a
3.8-validation / −8%-OOS blow-up. **Worst-regime robustness is the target.**

## STARTING POINT

`strategy.py` on this branch = checkpoint `2026-05-17-a05b891`, class
`IndiaMomentumQualityCarry`: long-only cross-sectional momentum-quality carry
(12-1 + mid-horizon relative strength gated by quality/defensive overlays,
diversified fixed-slot sizing, sector cap, biweekly). OOS over the burned
window: +5.36%, Sortino +0.75, 4.7% maxDD, sidestepped the −14% 2026-Q1
crash. Modest, plausible, unproven. It is a starting point, not sacred —
replace or rebuild whatever the goal requires.

## GUARDRAILS (non-negotiable — these are paid-for facts, not preferences)

- **Optimise the worst regime sub-period, not the mean.** Chasing mean
  validation Sortino is exactly what produced the −8%-OOS blow-up.
- **The sealed 2025-01→2026-05 window is burned** — never tune to it or treat
  any historical backtest as proof. Forward `dhan-paper` is the only arbiter.
- **No hidden complexity.** Every window/threshold a real, named parameter —
  hard-coded knobs that dodge the parsimony gate are how silent overfit
  happens.
- **Hard constraints** (CLAUDE.md): long-only; `order_target_percent` only;
  trade only the injected PIT universe; size from `n_positions` not
  `len(selected)`; never edit `prepare.py` / `backtest/anti_overfit.py`;
  commit as victorvini08; stay on `production-strategy`.
- Cost matters at ₹50k — ₹14.75/scrip DP per sell is a dominant drag; net of
  cost is the only number that counts.

## CONSIDERATIONS (weigh these; discard freely if a better idea wins)

Observations from prior work and from real-trading experience — *inputs to
reason about*, not steps to execute:

- **Letting winners run tends to beat churning them.** Momentum's edge lives
  in the right tail; rotating out healthy uptrending names early both caps
  returns and burns DP cost. Worth questioning any logic that sells a still-
  trending winner just because something out-ranked it.
- **Loss handling should distinguish a breakdown from normal noise.** Indian
  mid-caps correct 5–10% routinely; an exit keyed to a stock's *own*
  volatility and confirmed by structure avoids whipsawing on ordinary
  pullbacks while still cutting genuine deterioration.
- **Regime awareness is likely the core generalization lever.** Continuous,
  hysteretic risk scaling (e.g. India VIX percentile, Nifty vs 200-DMA — real
  coverage in `llm.features`) generalised far better than binary gates, which
  the loop overfit. A long-only book's only bear tool is graceful de-risking.

These are leads, not a mandate. If the evidence points elsewhere, follow the
evidence.

## DEFERRED — per-ticker news (out of scope for now)

Raw news exists (72k ticker-tagged articles 2021→2026) but the
`sentiment()`/`events()` classifier cache is near-empty (~1,575 rows) so they
return defaults today. Precompute is ~1–4 hrs wall time, one-time,
**resumable**, and once populated those features light up with **no
strategy-code change** (write any news logic to no-op on an empty cache).
Safe to add later as a pure data/ops task — ignore news for now.

---

## PROMPT FOR THE NEW SESSION

> Branch: `production-strategy` (verify with `git branch --show-current`;
> `git checkout production-strategy` if not — never work on `main`). Read
> `PRODUCTION_STRATEGY.md` and `STRATEGY_DEVELOPMENT_PLAN.md` in full first.
>
> Goal: build the best long-only Indian-equity (NSE, CNC, top-200-ADV, ₹50k,
> net of Dhan costs) strategy you can from the `IndiaMomentumQualityCarry`
> starting point — one that **generalizes across bear, bull, and neutral
> regimes**, judged on its **worst** regime sub-period and on forward
> robustness, never average/backtest Sortino (the sealed window is burned).
>
> Use your own judgment on approach — the considerations in the plan are
> leads to weigh, not a sequence to follow. Respect the guardrails and
> CLAUDE.md hard constraints (long-only, `order_target_percent` only, PIT
> universe, never edit `prepare.py`/`backtest/anti_overfit.py`, commit as
> victorvini08, don't touch other branches). News is deferred — ignore it.
