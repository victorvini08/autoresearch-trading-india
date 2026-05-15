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

## Iteration 2026-05-15-deb30f4 — REVERTED

**Hypothesis:** Reducing target concentration from six to eight equal-weight positions should improve validation Sortino by lowering drawdown and fold instability while staying within the existing allowed n_positions hyperparameter range.

**Change:** Changed the existing n_positions hyperparameter from 6 to 8 so the strategy spreads each rebalance across more liquid momentum names without adding a new parameter or changing the trade contract.

**Decision:** REVERTED — catastrophe: max drawdown: 64.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8966 >= alpha/N=0.0125) · random_walk_mc(only 57.48% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.18)

**Result:**
- validation_sortino_mean: 2.32903422717595
- validation_folds: 20
- per_fold_sortinos: [11.8299, 2.3938, 0.4165, 0.8087, -0.925, -1.7644, -1.5502, -1.4964, -2.3017, -1.8456, 5.3624, 19.4051, 5.8167, 5.2924, 3.1927, 2.0884, 1.4909, 1.3719, -3.7313, 0.7258]
- calmar_mean: 8.799551455331605
- hit_rate_mean: 0.4498214285714287
- profit_factor_mean: 4.359428041097232
- trade_count_total: 68
- aggregate_max_dd: 0.6421912759991257
- worst_fold_max_dd: 0.36097871984213514
- max_position_frac_peak: 0.6442447448440024
- lower_quartile_fold_calmar: -1.5879495855046075
- n_negative_folds: 7/20
- risk.passed: False
- risk.violations: ['max drawdown: 64.2% > 50% (account-wipe territory)']

**Learning:** Sortino scored 2.329 with no prior kept baseline. Aggregate DD was 64.2%; negative folds were 7/20; trades=68. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 64.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8966 >= alpha/N=0.0125) · random_walk_mc(only 57.48% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.18).

---

## Iteration 2026-05-15-4b51da1 — REVERTED

**Hypothesis:** Capping gross target exposure at 80% should improve validation Sortino and reduce catastrophe-gate drawdowns by adding a permanent cash buffer without adding signal complexity or new hyperparameters.

**Change:** Changed the rebalance sizing from 99% gross exposure to 80% gross exposure while preserving the existing ranking, retention, sector cap, cadence, and order_target_percent-only trade contract.

**Decision:** REVERTED — catastrophe: gross exposure: max 120.4% > 100% (cash account — leverage error) · max drawdown: 69.1% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 67.18% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.22)

**Result:**
- validation_sortino_mean: 1.707838415087069
- validation_folds: 20
- per_fold_sortinos: [12.6701, 4.669, 0.3696, 0.8291, -0.8865, -1.8059, -3.0851, -2.8974, -2.3726, -2.6499, 4.6625, 14.3678, 5.7167, 4.2489, 4.4192, 2.1729, 0.6791, 0.0634, -3.1349, -3.8794]
- calmar_mean: 6.653640125235578
- hit_rate_mean: 0.3464285714285714
- profit_factor_mean: 2.4275071034833013
- trade_count_total: 67
- aggregate_max_dd: 0.6910581561540975
- worst_fold_max_dd: 0.3200008548164628
- max_position_frac_peak: 1.1016387111354207
- lower_quartile_fold_calmar: -1.8260419290008607
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['gross exposure: max 120.4% > 100% (cash account — leverage error)', 'max drawdown: 69.1% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.708 with no prior kept baseline. Aggregate DD was 69.1%; negative folds were 9/20; trades=67. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 120.4% > 100% (cash account — leverage error) · max drawdown: 69.1% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 67.18% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.22).

---

## Iteration 2026-05-16-f1dd62e — REVERTED

**Hypothesis:** Increasing diversification to ten equal-weight positions should reduce fold-level drawdowns and improve mean validation Sortino versus the current six-name concentration while staying inside the existing n_positions hyperparameter range.

**Change:** I changed only the existing n_positions parameter from 6 to 10, leaving the ranking, retention, regime gate, sector cap, cadence, and order_target_percent-only contract unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 64.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9882 >= alpha/N=0.0083) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16)

**Result:**
- validation_sortino_mean: 2.2868682447822124
- validation_folds: 20
- per_fold_sortinos: [11.8299, 2.3938, 0.4165, 0.8087, -0.925, -1.7644, -1.5502, -1.9836, -2.3353, -2.2431, 5.3624, 19.4051, 5.8167, 5.2924, 3.1728, 2.1833, 1.4909, 1.3719, -3.7313, 0.7258]
- calmar_mean: 8.657005544446779
- hit_rate_mean: 0.44523809523809527
- profit_factor_mean: 3.2923815059584984
- trade_count_total: 65
- aggregate_max_dd: 0.6471321681388055
- worst_fold_max_dd: 0.36097871984213514
- max_position_frac_peak: 0.6442447448440024
- lower_quartile_fold_calmar: -1.663648708434562
- n_negative_folds: 7/20
- risk.passed: False
- risk.violations: ['max drawdown: 64.7% > 50% (account-wipe territory)']

**Learning:** Sortino scored 2.287 with no prior kept baseline. Aggregate DD was 64.7%; negative folds were 7/20; trades=65. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 64.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9882 >= alpha/N=0.0083) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16).

---

## Iteration 2026-05-16-f0acc10 — REJECTED

**Hypothesis:** Using the existing regime gate as a full de-risking switch, rather than only blocking new entries, should reduce aggregate drawdown and improve validation Sortino by exiting momentum holdings during risk_off or shock regimes.

**Change:** Changed the rebalance selection so a failed regime gate liquidates held positions instead of retaining them, while preserving the existing ranking, sector cap, cadence, parameters, and order_target_percent-only contract.

**Decision:** REJECTED — prepare.py crashed: Query interrupted

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: Query interrupted.

---

## Iteration 2026-05-16-1811297 — REVERTED

**Hypothesis:** Switching a failed regime gate from entry-only behavior to full liquidation during risk_off or shock regimes should reduce account-wipe drawdowns and improve validation Sortino by removing stale momentum exposure during macro stress.

**Change:** Changed the regime gate so failed regimes set retention to empty and prevent new entries, causing existing holdings to be exited via order_target_percent while leaving ranking, sector cap, cadence, and sizing unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 84.1% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.04)

**Result:**
- validation_sortino_mean: 1.3683827674327886
- validation_folds: 20
- per_fold_sortinos: [10.7038, 4.2456, -1.6998, -0.2555, -3.3946, -3.3788, -1.9271, -2.8589, -2.7456, -1.9959, 5.0844, 15.4237, 6.2159, 3.128, 2.8153, 3.1902, 1.3742, -0.7422, -3.2094, -2.6056]
- calmar_mean: 6.432951608973691
- hit_rate_mean: 0.25833333333333336
- profit_factor_mean: 1.2661747307426021
- trade_count_total: 39
- aggregate_max_dd: 0.8412546130170832
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.9069675608148007
- n_negative_folds: 11/20
- risk.passed: False
- risk.violations: ['max drawdown: 84.1% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.368 with no prior kept baseline. Aggregate DD was 84.1%; negative folds were 11/20; trades=39. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 84.1% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.04).

---

## Iteration 2026-05-16-361c56b — REVERTED

**Hypothesis:** Treating n_positions as fixed risk slots and applying the 25% sector cap to retained holdings as well as new entries should improve validation Sortino by preventing risk-off or cap-bound rebalances from concentrating capital into too few names.

**Change:** I changed portfolio construction so retained names and new buys pass through one sector-capped selection pool, and each selected name gets the fixed slot weight 0.99 / n_positions so unfilled slots remain cash.

**Decision:** REVERTED — catastrophe: min trades: 14 < 20 — too sparse to evaluate | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0056) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.17)

**Result:**
- validation_sortino_mean: 1.5050858372164977
- validation_folds: 20
- per_fold_sortinos: [8.1347, 3.458, 0.0747, 1.4897, -0.7748, 1.1945, -1.6737, -3.5439, -3.0928, -2.4832, 3.9549, 15.3119, 7.4317, 1.6856, 0.1893, 5.3613, 0.7359, -1.3262, -2.9873, -3.0386]
- calmar_mean: 1.3672834672640217
- hit_rate_mean: 0.175
- profit_factor_mean: 4.939333601287776
- trade_count_total: 14
- aggregate_max_dd: 0.2482551840455244
- worst_fold_max_dd: 0.08333832854516199
- max_position_frac_peak: 0.16148340022877344
- lower_quartile_fold_calmar: -1.8375109970927737
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['min trades: 14 < 20 — too sparse to evaluate']

**Learning:** Sortino scored 1.505 with no prior kept baseline. Aggregate DD was 24.8%; negative folds were 8/20; trades=14. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: min trades: 14 < 20 — too sparse to evaluate | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0056) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.17).

---

## Iteration 2026-05-16-99c9fb5 — REVERTED

**Hypothesis:** Sizing selected holdings by fixed portfolio slots instead of the number of currently selected names will improve validation Sortino by preventing unintended concentration when regime or sector filters leave fewer than six active holdings.

**Change:** Changed target sizing so unfilled n_positions slots remain cash while preserving the existing ranking, retention, regime gate, sector cap, and order_target_percent-only trade contract.

**Decision:** REVERTED — catastrophe: gross exposure: max 127.7% > 100% (cash account — leverage error) · max drawdown: 51.6% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9586 >= alpha/N=0.0050) · random_walk_mc(only 93.04% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.26)

**Result:**
- validation_sortino_mean: 1.6213218283364426
- validation_folds: 20
- per_fold_sortinos: [11.0124, 4.1456, 0.4083, 0.7272, -0.9725, -1.6218, -2.9849, -0.6862, -1.9298, -2.3279, 4.6396, 12.7705, 4.575, 2.1501, 5.1672, 2.7724, 1.1264, 0.0659, -3.3159, -3.295]
- calmar_mean: 5.148424575897847
- hit_rate_mean: 0.37940476190476197
- profit_factor_mean: 7.26955183249875
- trade_count_total: 73
- aggregate_max_dd: 0.5162125771322711
- worst_fold_max_dd: 0.31392352356658065
- max_position_frac_peak: 0.21473374593157787
- lower_quartile_fold_calmar: -1.6901805974692996
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['gross exposure: max 127.7% > 100% (cash account — leverage error)', 'max drawdown: 51.6% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.621 with no prior kept baseline. Aggregate DD was 51.6%; negative folds were 9/20; trades=73. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 127.7% > 100% (cash account — leverage error) · max drawdown: 51.6% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9586 >= alpha/N=0.0050) · random_walk_mc(only 93.04% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.26).

---

## Iteration 2026-05-16-788276a — REVERTED

**Hypothesis:** Requiring retained holdings as well as new buys to have positive absolute 12-1 momentum will improve mean validation Sortino by exiting relative winners that are still in broad downtrends instead of carrying them through drawdowns.

**Change:** Added a positive 12-1 momentum floor to both retention and new-entry selection, leaving the existing ranking, quality screen, regime gate, sector cap, cadence, and order_target_percent-only execution contract intact.

**Decision:** REVERTED — catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9876 >= alpha/N=0.0045) · random_walk_mc(only 53.18% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

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

**Learning:** Sortino scored 1.767 with no prior kept baseline. Aggregate DD was 77.8%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9876 >= alpha/N=0.0045) · random_walk_mc(only 53.18% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-51266e0 — REJECTED

**Hypothesis:** Ranking candidates by 12-1 momentum divided by recent volatility should improve validation Sortino by favoring smoother trend leaders while preserving the existing universe, cadence, retention, sector cap, and sizing rules.

**Change:** I replaced raw momentum ranking with volatility-adjusted momentum using the existing lookback window, with no new tunable parameters.

**Decision:** REJECTED — validation failed: disallowed import: bisect

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: disallowed import: bisect.

---
