# Improvement A — Conditional realized-volatility scaling of gross

Engineering design for roadmap item **A** (the roadmap
`docs/superpowers/specs/2026-05-17-robust-india-strategy-roadmap.md` is the
approved strategic brainstorm; this is the detailed design it asks §8 to
produce). One change, forward-validated via `prepare.py research` only.

## 1. Problem

`strategy.py::breadth_scaled_gross` sets whole-book gross from a **4-level
step function** on (breadth, median-short-return): `{0.35, 0.55, 0.75,
0.99}` with arbitrary cutoffs `{0.35, 0.45, 0.55}`. Three defects:

1. **Discontinuous** — a hairline move of breadth across 0.45 swings gross
   0.55→0.75. Step cliffs land arbitrarily across regimes; this is exactly
   the failure the roadmap §6 + journal record for binary gross gates
   ("degraded worst bucket").
2. **Hidden arbitrary knobs** — the 3 cutoffs and 4 levels are pinned to
   nothing (not theory, not structure). Roadmap §3.1: "our gross proxy is
   a crude step function."
3. **Wrong risk variable** — breadth (count above an MA) is a
   cross-sectional health proxy, not the book's own realized risk.
   Momentum-crash risk is forecastable from the *strategy's own realized
   variance* (Barroso–Santa-Clara; Daniel–Moskowitz), not a breadth count.

## 2. Mechanism (theory-pinned; zero new counted hyperparameters)

Replace the step function with the **conditional volatility-targeting law**
the roadmap §4–§5A specifies (Barroso–Santa-Clara crash defense, made
*conditional* per Daniel–Moskowitz / Man: long-only equity must **de-risk
only in elevated-vol states** — naive constant-vol-targeting backfires by
truncating the bull).

Risk variable: `r_t = mean_i ret_{i,t}` — the equal-weight active-universe
daily return (the existing `strategy.market_factor` of per-name returns).
For a long, ≈equal-weight book this **is** the book's realized return
series, i.e. exactly the Barroso–Santa-Clara construct adapted to a long
book. Endogenous, continuous — not an external macro label.

All PIT, from the `close_by_ticker` already passed into the gross function:

1. Per-ticker daily returns → align on common trailing length →
   `r = market_factor(returns_by_ticker)` (length `T`).
2. Guard: `usable ≥ 20` names **and** `T ≥ beta_window`. Else **fallback
   `0.75`** — the same conservative default the old function returned for
   `usable < 20` (keeps the book invested in thin/early windows; preserves
   the ≥20-trade catastrophe gate and the warmup contract).
3. `σ_fast` = std of the last `formation_days` (~21) of `r` — recent
   realized vol over the strategy's **own existing** skip/formation unit
   (the canonical Barroso–Santa-Clara ~1-month realized-vol horizon).
4. `σ_ref` = **median** of the rolling `formation_days`-window std of `r`
   over the last `beta_window` (~252) days. Median (not mean) is a
   *structural* choice: the "normal vol" anchor must not be inflated by
   the crash spikes we defend against — with the median, a blow-out does
   not drag the anchor up, so the multiplier truly contracts into the
   crash. No fitted level — a robust central tendency of the book's own
   realized-vol history.
5. **Conditional multiplier** (de-risk only):
   - `σ_fast ≤ σ_ref` → `m = 1.0` — vol normal/low vs its own history ⇒
     **full exposure, no bull truncation** (the conditionality the
     roadmap §4 demands; naive targeting would wrongly cut here).
   - `σ_fast > σ_ref` → `m = σ_ref / σ_fast` — Barroso–Santa-Clara
     inverse-vol law, engaged **only** in the elevated-vol tail;
     continuous, monotone ↓ in `σ_fast`; → small as a crash blows vol out.
   - `m = clip(m, 0.35, 1.0)` — `0.35` is the **existing**
     `breadth_scaled_gross` most-defensive level, preserved (not a new
     number): avoids all-to-cash whipsaw, keeps catastrophe-clear.
6. `gross = m * 0.99` — `0.99` is the **existing** fully-invested cap,
   unchanged ⇒ calm-regime behaviour is *identical to today's best case*;
   never levered; long-only ≤100%.

Net: bull/neutral (vol ≤ its own median) ⇒ gross 0.99, **identical to the
current best case**, full momentum right tail (roadmap goal: "don't
truncate momentum"). Bear/momentum-crash ⇒ gross scales **continuously**
down with realized-vol extremity (roadmap goal: graceful bear de-risk,
controlled drawdown). Monotone & bounded ⇒ no sign-flip.

## 3. Parsimony & distinctness (gate-relevant)

- **Zero** entries added to the `params` tuple ⇒
  `count_hyperparameters` stays **6** ⇒ parsimony gate **N/A**
  (`anti_overfit.parsimony_gate`; program.md §4). `formation_days` /
  `beta_window` are reused existing params; `0.35` / `0.99` are preserved
  existing constants. No new fitted number anywhere — genuinely "replaces
  hidden knobs" (roadmap §5A) and "no hidden complexity" (§7): it removes
  3 cutoffs + 4 levels, adds one continuous law.
- **Distinct from burned §6 traps** (verified vs journal `74550ca`
  residual-breadth step throttle, `0cc1dce` VIX/200DMA binary cap): A is
  (1) **continuous** not stepped, (2) keyed to the **book's own realized
  variance** not external macro/breadth, (3) **inert in calm** (`m=1`
  when vol ≤ its own median) — the precise reason binary/naive versions
  degraded the good buckets. Not a cross-sectional rank factor (signal
  unchanged). Not a price-distance trailing stop (aggregate vol law).
- Pairs with the existing symmetric structural exit: name-level exit vs
  book-level gross — different layers, same de-risk objective; compound.

## 4. Surface

`strategy.py` only. Add `conditional_vol_scaled_gross(close_by_ticker,
lookback_days, formation_days)`; `next()` calls it instead of
`breadth_scaled_gross`. Keep `breadth_scaled_gross` defined and exported
(don't pre-emptively delete — CLAUDE.md / US §8.4; it is in `__all__`).
Reuse `market_factor` (exported, unit-tested). Unchanged: class name
`IndiaMomentumQualityCarry`, `order_target_percent`-only, fixed-slot
`gross / n_positions` sizing, PIT universe handling, 25% sector cap,
structural exit, biweekly cadence.

## 5. Test/validation plan

- TDD: unit-test `conditional_vol_scaled_gross` BEFORE wiring —
  calm/flat-vol ⇒ `0.99`; sustained vol spike ⇒ monotone scale-down
  toward the `0.35*0.99` floor; `usable<20` or `T<beta_window` ⇒ `0.75`;
  output ∈ (0, 0.99]; deterministic; pure (no I/O).
- Do not regress currently-green tests. (`test_strategy_reversion.py::
  test_single_strategy_class_is_residual_reversal` [`==7`] and
  `test_warmup_scoring.py::test_strategy_trades_when_warmed` are
  **pre-existing red** on the untouched baseline — stale mean-reversion-
  branch leftovers; out of scope, must not be "fixed" by adding a knob.)
- `prepare.py research` (never `promotion`). Baseline anchor (reproduced
  exactly): validation **2.6255**, sub-periods **[3.029, 1.717]**, worst
  fold **−2.069**, agg_dd **5.18%**, all gates pass.
- KEEP iff ALL: validation Sortino > 2.6255 & > 0 & |S|<10; **worst
  sub-period not degraded vs 1.717 and no sign-flip** (robustness judged
  on the worst bucket, not the mean — roadmap §1/§7); agg_dd not
  regressing >10pp vs 5.18% (a crash defense should *reduce* it); gross
  ≤100%; ≥20 trades; all anti-overfit gates pass. Else REVERT decisively.
  Append to `journal.md`; commit as victorvini08 on `production-strategy`.

## 6. Risk / failure modes

- **No vol spikes in 2022–24 validation** ⇒ A ≈ inert ⇒ Sortino ≈
  baseline (not strictly >) ⇒ REVERT on KEEP-criterion-1. Acceptable:
  a parsimony-neutral crash defense that doesn't help the *backtest* but
  defends the unseen forward bear is still the roadmap's stated aim
  (forward is the arbiter); but the research gate needs a strict lift, so
  this is an honest REVERT, logged, then proceed to B.
- **σ_ref unstable on short `T`** ⇒ the `T ≥ beta_window` guard forces the
  `0.75` fallback rather than a noisy ratio.
- **Whipsaw** (gross oscillating bar-to-bar) ⇒ bounded by the `0.35`
  floor and the median anchor; gross only changes on rebalance bars
  (biweekly), not daily.
