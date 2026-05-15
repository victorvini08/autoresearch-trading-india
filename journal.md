# Autoresearch journal — Indian equities

This is the autoresearch loop's persistent memory. Every iteration appends an entry with hypothesis, change, result, and decision (KEEP / REVERT). Entries compound across runs and inform future proposals.

**Parser hazard:** the KEEP/REVERT parser in `scripts/loop.py` matches the literal line `**Decision:** KEPT` (not substring). Preserve the exact format.

---

## Iter 0 — Baseline (2026-05-14)

**Hypothesis:** A sparse, theory-backed cross-sectional momentum strategy with quality screen, sector cap, and Indian-context regime gate will produce a positive Sortino on the train+val window (2018-01 to 2023-12) when run on the top-200-by-ADV liquid Nifty 500 slice, after Dhan delivery costs.

**Theoretical basis:**
- 12-1 cross-sectional momentum: Jegadeesh & Titman 1993; Asness, Moskowitz, Pedersen 2013
- Quality screen (ROE / D-E / Op-margin): Novy-Marx 2013; Asness, Frazzini, Pedersen 2019
- Equal-weight sizing: DeMiguel, Garlappi, Uppal 2009
- Regime-gated entries: Cooper, Gutierrez, Hameed 2004; 2024-26 Indian regime evidence (FII outflows, Quality > Momentum during corrections)

**Change:** N/A — this is the seed strategy. See `strategy.py` for the implementation.

**Hyperparameters (5):**
- `lookback_days = 252`, `skip_days = 21`
- `retention_mult = 2.0`
- `quality_pct = 50`
- `regime_pct = 95`, `fii_threshold_cr = -15000`
- `n_positions = 6`

**Result:** Pending first walk-forward run.

**Learning:** (to be filled by the first iteration after walk-forward results land) — what did this baseline teach us about Indian-market behaviour under the chosen parameter set? Was the regime gate signal active during 2024-Q4 / 2026-Q1 drawdowns? Did the quality screen materially change which names were selected?

**Decision:** PENDING

---

(future iteration entries will be appended below this line by `scripts/loop.py`)

## Iteration smoke-codex-1778866545 — REJECTED

**Hypothesis:** Ranking candidates by volatility-adjusted 12-1 momentum instead of raw 12-1 momentum should improve validation Sortino by reducing concentration in high-beta winners that later mean-revert or crash.

**Change:** Changed the momentum score to divide 12-1 return by realized daily volatility over the same lookback window, using existing lookback and skip parameters without adding a new hyperparameter.

**Decision:** REJECTED — validation failed: syntax error: unexpected character after line continuation character (line 1)

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: syntax error: unexpected character after line continuation character (line 1).

---

## Iteration 2026-05-15-50c1342 — REJECTED

**Hypothesis:** Replacing raw 12-1 momentum with volatility-adjusted 12-1 momentum will improve mean validation Sortino by favoring steadier trend leaders and reducing exposure to high-beta reversals without adding a new hyperparameter.

**Change:** Changed the ranking score to divide 12-1 return by realized daily volatility over the same lookback window, preserving the existing cadence, sector cap, retention buffer, and order_target_percent-only trade contract.

**Decision:** REJECTED — prepare.py crashed: 'str' object has no attribute 'exists'

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: 'str' object has no attribute 'exists'.

---

## Iteration 2026-05-15-7786d97 — REVERTED

**Hypothesis:** Requiring a strictly positive 12-1 momentum score for new entries will improve mean validation Sortino by avoiding forced allocation into relative winners that are still absolute downtrends during broad selloffs.

**Change:** Filtered quality-passed new-entry candidates to names with momentum greater than zero while leaving retention, cadence, sizing, sector caps, and existing hyperparameters unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9846 >= alpha/N=0.0250) · random_walk_mc(only 52.50% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.7672545809923377
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.7074, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 5.4043, 17.5131, 6.2747, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.2921]
- calmar_mean: 6.878353634393159
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 29
- aggregate_max_dd: 0.7777282617212222
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 77.8% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.767 with no prior kept baseline. Aggregate DD was 77.8%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9846 >= alpha/N=0.0250) · random_walk_mc(only 52.50% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-15-5171fc9 — REVERTED

**Hypothesis:** Adding a simple market breadth confirmation to new entries should improve validation Sortino by avoiding momentum buys when most eligible stocks are trading below their 200-day trend, while still allowing retained winners to run.

**Change:** I changed the regime gate to also require at least 45% of ranked PIT-universe stocks to be above their 200-day price trend before opening new positions, without adding a new tunable parameter.

**Decision:** REVERTED — catastrophe: max drawdown: 80.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.08)

**Result:**
- validation_sortino_mean: 1.6440130118753427
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.2367, -5.0673, -3.8447, -2.4906, -2.1572, 5.4043, 17.5131, 6.2747, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.1739]
- calmar_mean: 6.89243941608498
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 28
- aggregate_max_dd: 0.8052176819843461
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8691549552756037
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 80.5% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.644 with no prior kept baseline. Aggregate DD was 80.5%; negative folds were 9/20; trades=28. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 80.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.08).

---
