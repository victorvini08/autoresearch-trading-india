# Autoresearch journal — Indian equities (branch: mean-reversion-quant-strategy)

This is the autoresearch loop's persistent memory for the **residual
mean-reversion stat-arb** parallel experiment. Every iteration appends an
entry with hypothesis, change, result, and decision (KEEP / REVERT).
Entries compound across runs and inform future proposals.

This branch is intentionally isolated from `main`'s momentum lineage: its
journal starts fresh so the reversion loop is not biased by burned
momentum ideas (and vice-versa). The two experiments are compared as
separate lineages.

**Parser hazard:** the KEEP/REVERT parser in `scripts/loop.py` matches the literal line `**Decision:** KEPT` (not substring). Preserve the exact format.

---

## Iter 0 — Baseline (2026-05-15)

**Hypothesis:** A sparse, theory-backed long-only cross-sectional residual mean-reversion strategy — buying names oversold relative to their market + size factor exposures, with a retention buffer, sector cap, and Indian-context regime gate — will produce a positive Sortino on the train+val window (2018-01 to 2023-12) on the top-200-by-ADV liquid slice, after Dhan delivery costs. It is the structural inverse of the momentum book on `main`, so the two autoresearch loops cannot converge.

**Theoretical basis:**
- Short-horizon cross-sectional reversal / statistical arbitrage: Lehmann 1990; Lo & MacKinlay 1990; Avellaneda & Lee 2010 (factor-residual reversion)
- Factor neutralization (market + size) before scoring residuals: standard stat-arb desk construction (residual = idiosyncratic, mean-reverting component)
- Size proxied by ADV (no market cap available; Amihud 2002 illiquidity/size linkage)
- Equal-weight sizing: DeMiguel, Garlappi, Uppal 2009
- Regime-gated entries: reversion suffers "falling-knife" failure in trending crashes — defensive gating is more important here than for momentum

**Change:** N/A — this is the seed strategy. See `strategy.py` (`IndiaResidualReversalStatArb`) for the implementation.

**Hyperparameters (7 counted signal knobs):**
- `beta_window = 60`, `formation_days = 5`
- `retention_mult = 2.0`
- `entry_pct = 0.20`
- `regime_pct = 95`
- `n_positions = 6`
- `sector_cap = 0.25`

**Result:** Pending first walk-forward run.

**Learning:** (to be filled by the first iteration after walk-forward results land) — does the long-only residual-reversion edge survive Dhan DP costs at biweekly cadence? Is the cross-sectional market factor informative on real data (vs the near-degenerate synthetic case), and how often does the regime gate block entries during the 2024-Q4 / 2026-Q1 drawdowns?

**Decision:** PENDING

---

(future iteration entries will be appended below this line by `scripts/loop.py`)

## Iteration 2026-05-16-75b69ef — REVERTED

**Hypothesis:** Estimating market and size betas before the formation window will improve validation Sortino by preventing the short-term oversold shock from being absorbed into the factor model used to rank reversals.

**Change:** Changed residual scoring to use out-of-sample formation-window residuals when enough history is available, while preserving the prior in-sample path for legacy callers with exactly beta_window returns.

**Decision:** REVERTED — catastrophe: max drawdown: 87.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9872 >= alpha/N=0.0167) · random_walk_mc(only 24.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24)

**Result:**
- validation_sortino_mean: 0.07125192459576865
- validation_folds: 20
- per_fold_sortinos: [10.3259, 2.5994, -0.3348, 1.7635, -0.7809, -1.5394, 0.2967, 5.1614, -1.0243, -2.5319, 0.0364, 1.2949, 0.3812, 0.4818, -0.9031, -1.8978, -2.1351, -2.5208, -1.7049, -5.5434]
- calmar_mean: 0.7893011884286053
- hit_rate_mean: 0.3341666666666666
- profit_factor_mean: 4.567321606770621
- trade_count_total: 60
- aggregate_max_dd: 0.8695990454096255
- worst_fold_max_dd: 0.382906221160284
- max_position_frac_peak: 1.0424126316184374
- lower_quartile_fold_calmar: -1.8015546478968714
- n_negative_folds: 12/20
- risk.passed: False
- risk.violations: ['max drawdown: 87.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 0.071 with no prior kept baseline. Aggregate DD was 87.0%; negative folds were 12/20; trades=60. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 87.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9872 >= alpha/N=0.0167) · random_walk_mc(only 24.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24).

---
