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

## Iteration 2026-05-16-6376e36 — REVERTED

**Hypothesis:** Ranking candidates by 12-1 momentum divided by realized downside deviation will improve mean validation Sortino by favoring trends with less negative-path volatility, while preserving cadence, sizing, universe, and hyperparameter count.

**Change:** Replaced raw momentum ranking with a no-new-parameter downside-risk-adjusted momentum score and kept the execution contract unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 60.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9954 >= alpha/N=0.0038) · random_walk_mc(only 87.30% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23)

**Result:**
- validation_sortino_mean: 2.100424669002477
- validation_folds: 20
- per_fold_sortinos: [9.6457, 2.6603, 0.0264, 1.5281, -0.4638, -1.4669, -1.1245, -0.9193, -2.6907, -3.7448, 2.8739, 14.073, 5.0652, 3.3471, 2.9886, 2.6216, 1.6049, 2.2223, 3.4647, 0.2965]
- calmar_mean: 6.233121021366566
- hit_rate_mean: 0.2891666666666667
- profit_factor_mean: 0.0834237373910782
- trade_count_total: 31
- aggregate_max_dd: 0.6047759765374946
- worst_fold_max_dd: 0.25284261999262175
- max_position_frac_peak: 1.0404314311657057
- lower_quartile_fold_calmar: -1.4285715822846714
- n_negative_folds: 7/20
- risk.passed: False
- risk.violations: ['max drawdown: 60.5% > 50% (account-wipe territory)']

**Learning:** Sortino scored 2.100 with no prior kept baseline. Aggregate DD was 60.5%; negative folds were 7/20; trades=31. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 60.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9954 >= alpha/N=0.0038) · random_walk_mc(only 87.30% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23).

---

## Iteration 2026-05-16-d43e8ae — REVERTED

**Hypothesis:** Implementing 12-1 momentum divided by same-window realized volatility, with the prior disallowed-import failure removed, will improve mean validation Sortino by ranking smoother trend leaders ahead of high-volatility rebound names.

**Change:** Replaced raw momentum ranking with a no-new-parameter volatility-adjusted momentum score while keeping the PIT universe, retention, regime gate, sector cap, and order_target_percent-only execution contract intact.

**Decision:** REVERTED — catastrophe: max drawdown: 63.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8652 >= alpha/N=0.0036) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24)

**Result:**
- validation_sortino_mean: 2.2776703396583278
- validation_folds: 20
- per_fold_sortinos: [9.6457, 2.6603, 0.0264, 1.5281, -0.4638, -1.4669, -1.9454, -0.1135, -1.5044, -2.0607, 3.5624, 14.3913, 4.9626, 3.1229, 3.7835, 2.9501, 1.4006, 2.0791, 1.9247, 1.0702]
- calmar_mean: 6.220993298192086
- hit_rate_mean: 0.31
- profit_factor_mean: 0.01212069052940692
- trade_count_total: 25
- aggregate_max_dd: 0.6329346642370864
- worst_fold_max_dd: 0.3607359288792167
- max_position_frac_peak: 1.0404314311657057
- lower_quartile_fold_calmar: -1.3173434612774306
- n_negative_folds: 7/20
- risk.passed: False
- risk.violations: ['max drawdown: 63.3% > 50% (account-wipe territory)']

**Learning:** Sortino scored 2.278 with no prior kept baseline. Aggregate DD was 63.3%; negative folds were 7/20; trades=25. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 63.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8652 >= alpha/N=0.0036) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24).

---

## Iteration 2026-05-16-dc0a356 — REVERTED

**Hypothesis:** Reducing retained-position gross exposure to 50% only during numeric macro stress should improve mean validation Sortino by cutting the drawdown tail without the whipsaw and trade-count collapse of full liquidation.

**Change:** I added a no-new-parameter macro-stress detector using cached regime, India VIX percentile, and Nifty 50 200-DMA trend, then half-sized selected holdings and blocked new entries only while that stress flag is active.

**Decision:** REVERTED — catastrophe: max drawdown: 78.6% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9994 >= alpha/N=0.0033) · random_walk_mc(only 1.20% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.10)

**Result:**
- validation_sortino_mean: 1.6742237086698644
- validation_folds: 20
- per_fold_sortinos: [13.5316, 4.2456, 0.2156, -0.6318, -2.284, -2.6522, -2.6269, -3.31, -2.7456, -1.9693, 5.4067, 17.4763, 6.2773, 3.128, 2.8153, 3.1902, 0.9882, -0.681, -3.2094, -3.6799]
- calmar_mean: 6.406931578916395
- hit_rate_mean: 0.2125
- profit_factor_mean: 0.4482217929677605
- trade_count_total: 31
- aggregate_max_dd: 0.7857809712930339
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 10/20
- risk.passed: False
- risk.violations: ['max drawdown: 78.6% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.674 with no prior kept baseline. Aggregate DD was 78.6%; negative folds were 10/20; trades=31. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 78.6% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9994 >= alpha/N=0.0033) · random_walk_mc(only 1.20% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.10).

---

## Iteration 2026-05-16-f504777 — REVERTED

**Hypothesis:** Adding a no-new-parameter skip-window confirmation should improve mean validation Sortino by avoiding stale 12-1 momentum leaders whose most recent skipped month has already turned negative.

**Change:** I kept the 12-1 ranking intact but require both retained holdings and new entries to have non-negative last-skip-window return, and replaced the disallowed bisect lookup with a manual point-in-time universe scan.

**Decision:** REVERTED — catastrophe: max drawdown: 86.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0031) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24)

**Result:**
- validation_sortino_mean: 1.0348193959564003
- validation_folds: 20
- per_fold_sortinos: [5.3446, 0.4285, -2.2628, 0.7454, -3.9352, -3.655, -0.755, -1.6548, -2.3027, -2.619, 2.0931, 15.3413, 5.9887, 2.3872, 3.5027, 3.061, 2.1804, 1.1016, -3.8408, -0.453]
- calmar_mean: 5.866803545913642
- hit_rate_mean: 0.525952380952381
- profit_factor_mean: 8.018803118548991
- trade_count_total: 62
- aggregate_max_dd: 0.8627912264070263
- worst_fold_max_dd: 0.42633993151702443
- max_position_frac_peak: 1.2775739462384716
- lower_quartile_fold_calmar: -1.8381669387490214
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 86.3% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.035 with no prior kept baseline. Aggregate DD was 86.3%; negative folds were 9/20; trades=62. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 86.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0031) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.24).

---

## Iteration 2026-05-16-f58e7e4 — REVERTED

**Hypothesis:** Blocking fresh entries with same-day negative actionable news will improve mean validation Sortino by avoiding momentum buys where new adverse information has not yet been reflected in the 12-1 rank, while leaving existing holdings and no-news names unchanged.

**Change:** Added a cached adverse-news veto for new entries using point-in-time news_volume and sentiment, preserving the existing momentum rank, retention behavior, sector cap, cadence, and order_target_percent-only execution contract.

**Decision:** REVERTED — catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0029) · random_walk_mc(only 0.80% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.7679442219627446
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 5.4043, 17.5131, 6.2747, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.2921]
- calmar_mean: 6.878682347903437
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 29
- aggregate_max_dd: 0.7774196732828635
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 77.7% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.768 with no prior kept baseline. Aggregate DD was 77.7%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0029) · random_walk_mc(only 0.80% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-9353e61 — REJECTED

**Hypothesis:** Adding a no-new-parameter absolute market trend sleeve that only carries half gross exposure when Nifty 50 is below its 200-day average should improve mean validation Sortino by reducing broad-market drawdown without fully abandoning momentum exposure.

**Change:** I replaced the entry-only regime gate with a continuous gross-exposure scaler using existing macro signals, preserving ranking, retention, sector cap, and order_target_percent-only execution.

**Decision:** REJECTED — prepare.py crashed: 'dict' object has no attribute 'ticker'

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: 'dict' object has no attribute 'ticker'.

---

## Iteration 2026-05-16-c6dc0a1 — REVERTED

**Hypothesis:** Replacing equal weights with inverse-volatility target weights for the already-selected momentum names should improve mean validation Sortino by reducing high-volatility winner concentration without changing the signal family or adding hyperparameters.

**Change:** I kept the 12-1 momentum selection, retention, quality screen, regime entry gate, and cadence intact, but changed the final order_target_percent targets to inverse realized-volatility weights clipped by the existing 25% sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0050) · random_walk_mc(only 87.62% percentile vs RW null)

**Result:**
- validation_sortino_mean: 1.353027053544714
- validation_folds: 20
- per_fold_sortinos: [7.3368, 3.2882, 0.0934, 1.5032, -1.6995, -3.0228, 0.1747, 4.2811, -0.4672, -1.5437, 2.525, 8.7481, 1.373, 2.6914, 0.0521, 5.4455, 0.8845, -1.3004, -0.5736, -2.7292]
- calmar_mean: 1.6860806393624408
- hit_rate_mean: 0.3091666666666667
- profit_factor_mean: 3.9763222486583762
- trade_count_total: 32
- aggregate_max_dd: 0.3079565382925208
- worst_fold_max_dd: 0.1915316301722045
- max_position_frac_peak: 0.25984594676673634
- lower_quartile_fold_calmar: -0.6468872667893536
- n_negative_folds: 8/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.353 with no prior kept baseline. Aggregate DD was 30.8%; negative folds were 8/20; trades=32. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0050) · random_walk_mc(only 87.62% percentile vs RW null).

---

## Iteration 2026-05-16-551cf32 — REVERTED

**Hypothesis:** Replacing pure 12-1 trend chasing with a pullback-within-uptrend rank should improve validation Sortino by buying established relative-strength names after short-term mean-reversion instead of after the most crowded recent extension.

**Change:** I kept the PIT universe, biweekly cadence, retention, sector cap, and order_target_percent-only contract, but changed ranking to require positive long-horizon momentum and score candidates by weaker skipped-month return first, with long-horizon momentum as the tie-breaker.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.7516 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.02)

**Result:**
- validation_sortino_mean: 2.294775094680033
- validation_folds: 20
- per_fold_sortinos: [12.7049, 5.8301, 5.4752, 1.3245, -0.644, -1.0531, -0.7916, 0.2922, 2.9337, 0.3275, 0.9133, 6.4331, 2.3772, 1.8272, 2.7201, -0.6184, -1.7859, 7.5209, 2.0948, -1.9862]
- calmar_mean: 5.775935382241768
- hit_rate_mean: 0.5533333333333333
- profit_factor_mean: 3.423366454548941
- trade_count_total: 67
- aggregate_max_dd: 0.3774675150187024
- worst_fold_max_dd: 0.2586767142705873
- max_position_frac_peak: 1.0813006730976544
- lower_quartile_fold_calmar: -1.0408059633957953
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.295 with no prior kept baseline. Aggregate DD was 37.7%; negative folds were 6/20; trades=67. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.7516 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.02).

---

## Iteration 2026-05-16-2bf4194 — REVERTED

**Hypothesis:** Ranking stocks by sector-relative 12-1 momentum will improve mean validation Sortino by selecting idiosyncratic leaders instead of repeatedly concentrating in the hottest broad sector or market beta sleeve.

**Change:** I changed the momentum ranking score from raw 12-1 return to raw momentum minus the same-sector median momentum when enough sector peers are available, while preserving cadence, retention, sector cap, sizing, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 0.90% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.7679442219627446
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 5.4043, 17.5131, 6.2747, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.2921]
- calmar_mean: 6.878682347903437
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 29
- aggregate_max_dd: 0.7774196732828635
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 77.7% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.768 with no prior kept baseline. Aggregate DD was 77.7%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 0.90% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-7eadd74 — REVERTED

**Hypothesis:** Replacing raw 12-1 momentum with a quality-of-trend score based on momentum minus realized drawdown should improve validation Sortino by favoring persistent upward trends that did not require deep interim losses.

**Change:** I changed the ranking score to combine 12-1 momentum with an embedded same-window maximum drawdown penalty, preserving the existing universe, cadence, retention, sector cap, and equal-weight order_target_percent execution.

**Decision:** REVERTED — catastrophe: max drawdown: 75.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 0.24% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25)

**Result:**
- validation_sortino_mean: 1.6603698970071732
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.4638, -2.0323, -2.1564, -2.5165, -1.992, -2.1572, 5.9806, 11.7162, 6.9479, 3.128, 4.885, -0.5469, 0.7573, 1.4193, -3.4841, -3.4215]
- calmar_mean: 6.237870385932987
- hit_rate_mean: 0.21666666666666665
- profit_factor_mean: 0.003557653216853632
- trade_count_total: 29
- aggregate_max_dd: 0.7501248221904888
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.1476740643523569
- lower_quartile_fold_calmar: -1.8133032172396257
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 75.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.660 with no prior kept baseline. Aggregate DD was 75.0%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 75.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 0.24% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25).

---

## Iteration 2026-05-16-0a2255d — REJECTED

**Hypothesis:** Adding a simple absolute momentum filter for new entries will improve validation Sortino by avoiding long positions in relative winners whose own 12-1 return is negative, while preserving existing retention behavior and cadence.

**Change:** I filtered fresh candidates to require positive 12-1 momentum before quality screening and sector-cap selection, reducing broad downtrend exposure without adding a new hyperparameter.

**Decision:** REJECTED — validation failed: disallowed import: bisect

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: disallowed import: bisect.

---

## Iteration 2026-05-16-9473b4c — REVERTED

**Hypothesis:** Adding a lightweight earnings-gap avoider to the existing momentum selection should improve validation Sortino by skipping candidates with recent extreme single-day upside gaps, which are often reversal-prone after crowded news-driven moves.

**Change:** I kept the PIT universe, biweekly cadence, retention, quality soft-degrade, regime gate, sector cap, and equal-weight sizing, but changed fresh-entry ranking to exclude candidates whose last 21 trading days contain a single-day close-to-close gain above 18%.

**Decision:** REVERTED — catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9062 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.821377929861546
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 5.7401, 19.2371, 6.2747, 2.8975, 1.4795, 3.1902, 0.7265, -0.4423, -3.2094, -2.717]
- calmar_mean: 7.276804813339543
- hit_rate_mean: 0.125
- profit_factor_mean: 0.13067399856569273
- trade_count_total: 27
- aggregate_max_dd: 0.7774196732828635
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8571554808879012
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 77.7% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.821 with no prior kept baseline. Aggregate DD was 77.7%; negative folds were 9/20; trades=27. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9062 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-c0d38a7 — REVERTED

**Hypothesis:** Applying a simple 63-day reversal filter to fresh entries will improve mean validation Sortino by avoiding long-term momentum winners that are already in intermediate-term breakdowns, while retaining existing winners through the retention buffer.

**Change:** I changed only the fresh-entry candidate pool to require positive 63-day price momentum in addition to the existing 12-1 rank, keeping retention, cadence, sector cap, regime gate, and equal-weight sizing unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 76.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9580 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.20)

**Result:**
- validation_sortino_mean: 1.9289695499104762
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2196, 1.1078, 1.6464, -0.4257, -1.5312, -2.954, -1.9298, -2.7456, -2.4365, 9.051, 17.517, 5.2958, 3.128, 2.8153, 3.1902, 0.25, -0.4423, -3.6678, -3.7167]
- calmar_mean: 6.8061153527901705
- hit_rate_mean: 0.25
- profit_factor_mean: 0.8189091737128608
- trade_count_total: 28
- aggregate_max_dd: 0.7645628463302342
- worst_fold_max_dd: 0.4105950256929986
- max_position_frac_peak: 1.075379485424019
- lower_quartile_fold_calmar: -1.8605644730667275
- n_negative_folds: 10/20
- risk.passed: False
- risk.violations: ['max drawdown: 76.5% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.929 with no prior kept baseline. Aggregate DD was 76.5%; negative folds were 10/20; trades=28. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 76.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9580 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.20).

---

## Iteration 2026-05-16-99182c3 — REVERTED

**Hypothesis:** Capping the portfolio at 63% gross exposure should reduce the recurring account-wipe drawdown enough to improve validation Sortino while preserving the same cross-sectional momentum ordering and trade count.

**Change:** I replaced near-fully-invested equal weighting with a fixed 63% gross exposure budget spread across selected names, removing disallowed non-program imports while keeping the PIT universe, quality soft-degrade, regime gate, retention buffer, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: gross exposure: max 127.2% > 100% (cash account — leverage error) · max drawdown: 57.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9968 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23)

**Result:**
- validation_sortino_mean: 1.5465889615282358
- validation_folds: 20
- per_fold_sortinos: [11.2798, 4.4216, 0.3027, 0.6957, -0.7425, -1.8201, -2.5419, -1.854, -2.3016, -2.6962, 5.2071, 12.4, 4.808, 2.1813, 5.1413, 2.8868, 0.6608, 0.0493, -3.2949, -3.8515]
- calmar_mean: 4.379012938835853
- hit_rate_mean: 0.32880952380952383
- profit_factor_mean: 5.792775754779668
- trade_count_total: 81
- aggregate_max_dd: 0.5701965249726522
- worst_fold_max_dd: 0.2469557676463756
- max_position_frac_peak: 0.7670227064236587
- lower_quartile_fold_calmar: -1.877779098057512
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['gross exposure: max 127.2% > 100% (cash account — leverage error)', 'max drawdown: 57.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.547 with no prior kept baseline. Aggregate DD was 57.0%; negative folds were 9/20; trades=81. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 127.2% > 100% (cash account — leverage error) · max drawdown: 57.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9968 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23).

---

## Iteration 2026-05-16-e52aaf5 — REVERTED

**Hypothesis:** Replacing raw fully invested 12-1 momentum with a defensive uptrend-pullback score and fixed half-gross slot sizing should reduce crash drawdowns while preserving the momentum/reversal edge enough to improve validation Sortino.

**Change:** I changed the rank to prefer positive long-term trends with recent pullbacks and shallow path drawdowns, then select an eight-slot sector-capped portfolio at fixed 55% gross exposure to address the recurring concentration and account-wipe failures.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 43.94% percentile vs RW null)

**Result:**
- validation_sortino_mean: 1.6157489105707286
- validation_folds: 20
- per_fold_sortinos: [8.9427, 3.8522, 0.3854, 0.531, -0.6995, -0.7663, 0.7863, 1.8737, -2.2094, -2.5716, 4.564, 10.2482, 3.9712, 2.5479, 0.8262, 2.91, 0.9528, 1.2345, -1.3071, -3.7572]
- calmar_mean: 2.8696967118480377
- hit_rate_mean: 0.4151030260589084
- profit_factor_mean: 5.3464504049906365
- trade_count_total: 160
- aggregate_max_dd: 0.28765724950238514
- worst_fold_max_dd: 0.15266045022547203
- max_position_frac_peak: 0.07990314671350335
- lower_quartile_fold_calmar: -0.6335141078678919
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.616 with no prior kept baseline. Aggregate DD was 28.8%; negative folds were 6/20; trades=160. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9998 >= alpha/N=0.0050) · random_walk_mc(only 43.94% percentile vs RW null).

---

## Iteration 2026-05-16-edc5576 — REVERTED

**Hypothesis:** Adding a high-cash defensive construction that selects only positive 12-1 momentum names and sizes them across fixed risk slots should reduce the recurring drawdown failures while preserving enough cross-sectional momentum edge to improve validation Sortino.

**Change:** I replaced fully invested selected-name equal weighting with fixed-slot 60% gross exposure and a positive-momentum entry requirement, so sparse eligible sets do not unintentionally concentrate the book.

**Decision:** REVERTED — catastrophe: gross exposure: max 100.7% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.8374 >= alpha/N=0.0050)

**Result:**
- validation_sortino_mean: 1.7524273978430371
- validation_folds: 20
- per_fold_sortinos: [10.0883, 3.9734, 0.3847, 0.5808, -0.5134, -1.3122, -1.8099, 0.1783, -1.894, -2.655, 5.7022, 14.9082, 4.9821, 3.1774, 0.2201, 2.8916, 0.8412, 1.0933, -3.0057, -2.7829]
- calmar_mean: 3.688576751341027
- hit_rate_mean: 0.4552651515151515
- profit_factor_mean: 2.3708707320203586
- trade_count_total: 105
- aggregate_max_dd: 0.38087732046780376
- worst_fold_max_dd: 0.23467156723814592
- max_position_frac_peak: 0.11619828002377378
- lower_quartile_fold_calmar: -1.554334299103245
- n_negative_folds: 7/20
- risk.passed: False
- risk.violations: ['gross exposure: max 100.7% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 1.752 with no prior kept baseline. Aggregate DD was 38.1%; negative folds were 7/20; trades=105. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 100.7% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.8374 >= alpha/N=0.0050).

---

## Iteration 2026-05-16-587a7b9 — REVERTED

**Hypothesis:** Adding a portfolio-level 12-1 market breadth gate will improve validation Sortino by avoiding fresh momentum entries when leadership is too narrow, while still allowing retained winners to age out through the existing rank buffer.

**Change:** I changed the regime gate to also require at least 45% of ranked point-in-time universe names to have positive 12-1 momentum before opening new positions, preserving cadence, ranking, retention, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: max drawdown: 78.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9862 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.10)

**Result:**
- validation_sortino_mean: 1.6807630323755678
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.2367, -2.6865, -4.5436, -3.4648, -1.8987, 4.6358, 20.259, 7.0541, 3.3435, -0.27, 3.1902, 0.7265, -0.4423, -3.2094, -3.2921]
- calmar_mean: 9.260146088779809
- hit_rate_mean: 0.275
- profit_factor_mean: 0.07605894399609311
- trade_count_total: 26
- aggregate_max_dd: 0.7807937271671364
- worst_fold_max_dd: 0.3836677847346603
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.9165133735340978
- n_negative_folds: 10/20
- risk.passed: False
- risk.violations: ['max drawdown: 78.1% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.681 with no prior kept baseline. Aggregate DD was 78.1%; negative folds were 10/20; trades=26. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 78.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9862 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.10).

---

## Iteration 2026-05-16-bf04c42 — REVERTED

**Hypothesis:** Replacing single-window 12-1 endpoint momentum with a no-new-parameter 3/6/12-month persistent trend score will improve mean validation Sortino by avoiding one-window spike leaders and favoring names with steadier momentum across horizons.

**Change:** I changed only the ranking signal so _momentum_for scores each ticker by the weakest plus average component of its skipped 3-, 6-, and 12-month returns, while preserving the PIT universe, cadence, quality soft-degrade, regime gate, retention, sector cap, sizing, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: gross exposure: max 2091.4% > 100% (cash account — leverage error) · max drawdown: 456.2% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.7646 >= alpha/N=0.0050) · random_walk_mc(only 30.56% percentile vs RW null)

**Result:**
- validation_sortino_mean: 1.0631798231924598
- validation_folds: 20
- per_fold_sortinos: [10.2889, 3.4762, 0.183, 1.9025, 0.4686, -0.9225, -0.8218, 0.1516, -0.2714, -0.764, 0.3494, 1.899, 5.5109, 0.1823, 0.1062, 3.1911, 0.259, 0.0541, -3.7708, -0.2086]
- calmar_mean: nan
- hit_rate_mean: 0.3083333333333333
- profit_factor_mean: 3.270196421096952
- trade_count_total: 45
- aggregate_max_dd: 4.562283247656237
- worst_fold_max_dd: 4.233315961647441
- max_position_frac_peak: 90897.42600000002
- lower_quartile_fold_calmar: -0.9380672258922194
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['gross exposure: max 2091.4% > 100% (cash account — leverage error)', 'max drawdown: 456.2% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.063 with no prior kept baseline. Aggregate DD was 456.2%; negative folds were 9/20; trades=45. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 2091.4% > 100% (cash account — leverage error) · max drawdown: 456.2% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.7646 >= alpha/N=0.0050) · random_walk_mc(only 30.56% percentile vs RW null).

---

## Iteration 2026-05-16-a70d7d0 — REVERTED

**Hypothesis:** Moving from a concentrated 6-name nearly fully invested book to a 10-slot 95% gross construction should improve validation Sortino by reducing idiosyncratic drawdown without changing the underlying 12-1 momentum thesis.

**Change:** I changed the default target portfolio from 6 positions at 99% gross to 10 positions at 95% gross, keeping the PIT universe, cadence, retention, regime gate, sector cap, and order_target_percent-only execution intact.

**Decision:** REVERTED — catastrophe: gross exposure: max 131.8% > 100% (cash account — leverage error) · max drawdown: 61.4% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0050) · random_walk_mc(only 0.62% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23)

**Result:**
- validation_sortino_mean: 2.2735490492349486
- validation_folds: 20
- per_fold_sortinos: [12.2844, 4.1122, 0.3696, 0.7872, -0.9294, -1.8263, -1.542, -2.0227, -1.9732, -2.2402, 6.9566, 15.4011, 6.0682, 4.3136, 3.7534, 2.685, 1.6876, 1.4, -3.4043, -0.4101]
- calmar_mean: 7.239589977160188
- hit_rate_mean: 0.40476190476190477
- profit_factor_mean: 6.637404914305014
- trade_count_total: 78
- aggregate_max_dd: 0.6136243219592777
- worst_fold_max_dd: 0.32579839990392023
- max_position_frac_peak: 0.5970083684474943
- lower_quartile_fold_calmar: -1.6650292245543468
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['gross exposure: max 131.8% > 100% (cash account — leverage error)', 'max drawdown: 61.4% > 50% (account-wipe territory)']

**Learning:** Sortino scored 2.274 with no prior kept baseline. Aggregate DD was 61.4%; negative folds were 8/20; trades=78. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 131.8% > 100% (cash account — leverage error) · max drawdown: 61.4% > 50% (account-wipe territory) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0050) · random_walk_mc(only 0.62% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.23).

---

## Iteration 2026-05-16-14a8b77 — REVERTED

**Hypothesis:** Ranking 12-1 momentum candidates by momentum confirmed by recent participation should improve validation Sortino by preferring liquid, actively-accumulated leaders over thin endpoint-price moves that are more reversal-prone after Dhan costs.

**Change:** I removed the disallowed pathlib import and changed the ranking signal to multiply 12-1 momentum by a bounded recent-volume-confirmation factor, preserving the PIT universe, biweekly cadence, retention, sector cap, equal sizing, and order_target_percent-only contract.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.9990 >= alpha/N=0.0050)

**Result:**
- validation_sortino_mean: 2.2303887559231144
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.1347, -0.1017, 1.5292, -1.5074, -1.6526, 0.7799, 2.7337, -0.1742, -1.9536, 3.434, 15.3959, 6.1994, 2.5565, 3.92, 1.9608, -0.8671, 0.2602, 0.2069, -2.4547]
- calmar_mean: 7.639408478741032
- hit_rate_mean: 0.4008333333333334
- profit_factor_mean: 1.0354479731763395
- trade_count_total: 46
- aggregate_max_dd: 0.4279372986645177
- worst_fold_max_dd: 0.26728465232310045
- max_position_frac_peak: 1.1380368239406862
- lower_quartile_fold_calmar: -0.9626392201134022
- n_negative_folds: 9/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.230 with no prior kept baseline. Aggregate DD was 42.8%; negative folds were 9/20; trades=46. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.9990 >= alpha/N=0.0050).

---

## Iteration 2026-05-16-8d9a010 — REVERTED

**Hypothesis:** Replacing raw 12-1 momentum with a no-new-parameter consistency-adjusted momentum score should improve validation Sortino by favoring names whose long-term gains were earned through persistent positive monthly returns rather than one-off jumps that tend to mean-revert after costs.

**Change:** I removed the disallowed pathlib import and changed only the ranking score so each ticker is ranked by 12-1 momentum multiplied by the fraction of positive 21-day blocks inside the lookback window, preserving the PIT universe, cadence, quality soft-degrade, regime gate, sector cap, sizing, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: max drawdown: 59.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9766 >= alpha/N=0.0050) · random_walk_mc(only 65.36% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25)

**Result:**
- validation_sortino_mean: 1.542779465901376
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, -0.1017, 1.6464, -1.4787, -1.8219, -0.2223, -1.5583, -2.1039, -1.6518, 3.2477, 13.9777, 6.2747, 3.128, 1.8475, -0.0758, 0.7078, 2.3451, -3.4649, -4.2935]
- calmar_mean: 5.74215024976551
- hit_rate_mean: 0.275
- profit_factor_mean: 0.23157332199765757
- trade_count_total: 34
- aggregate_max_dd: 0.5972323603807009
- worst_fold_max_dd: 0.30964881448594034
- max_position_frac_peak: 1.1476740643523569
- lower_quartile_fold_calmar: -1.826611957862835
- n_negative_folds: 10/20
- risk.passed: False
- risk.violations: ['max drawdown: 59.7% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.543 with no prior kept baseline. Aggregate DD was 59.7%; negative folds were 10/20; trades=34. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 59.7% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9766 >= alpha/N=0.0050) · random_walk_mc(only 65.36% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25).

---

## Iteration 2026-05-16-7135907 — REVERTED

**Hypothesis:** Replacing cross-sectional momentum ranking with a defensive low-downside-volatility rank among non-crashing absolute-trend names should improve validation Sortino by reducing the recurring drawdown tail with a structurally different low-volatility thesis rather than another momentum refinement.

**Change:** I removed the disallowed pathlib dependency and changed the ranking signal to prefer stocks with lower realized downside volatility and shallower drawdowns over the same lookback window, while preserving the PIT universe, biweekly cadence, retention, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: min trades: 15 < 20 — too sparse to evaluate · max drawdown: 53.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9634 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.927961417162051
- validation_folds: 20
- per_fold_sortinos: [8.1237, 2.3273, -0.0892, 1.6677, -1.3307, -3.1525, -1.0779, -1.29, -0.7828, -0.6955, 3.3017, 2.3514, 0.0452, 8.0174, 2.7887, 2.4994, 3.0733, 8.8814, 3.6178, 0.2826]
- calmar_mean: 3.3518898296997293
- hit_rate_mean: 0.16666666666666669
- profit_factor_mean: 0.3178045544673532
- trade_count_total: 15
- aggregate_max_dd: 0.5295393576085258
- worst_fold_max_dd: 0.19774069239880254
- max_position_frac_peak: 1.080377104146988
- lower_quartile_fold_calmar: -1.203466561130474
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['min trades: 15 < 20 — too sparse to evaluate', 'max drawdown: 53.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.928 with no prior kept baseline. Aggregate DD was 53.0%; negative folds were 8/20; trades=15. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: min trades: 15 < 20 — too sparse to evaluate · max drawdown: 53.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9634 >= alpha/N=0.0050) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-9dd8b49 — REVERTED

**Hypothesis:** Selecting 12-1 momentum names only when their long-term trend is not dominated by a single crash-rebound path should improve validation Sortino by keeping the momentum thesis while avoiding unstable recovery spikes that have caused drawdown-heavy folds.

**Change:** I removed the disallowed pathlib import and changed the ranking score to penalize high peak-to-trough drawdown inside the momentum lookback window, preserving PIT universe, biweekly cadence, retention, sector cap, equal sizing, and order_target_percent-only execution.

**Decision:** REVERTED — catastrophe: max drawdown: 75.0% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25)

**Result:**
- validation_sortino_mean: 1.6961577086220014
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.4638, -2.0323, -2.1564, -2.5165, -1.992, -2.1572, 5.9806, 11.7162, 6.9479, 3.128, 5.1665, -0.5469, 0.4414, 1.4283, -3.4097, -2.7546]
- calmar_mean: 6.247131594492658
- hit_rate_mean: 0.26666666666666666
- profit_factor_mean: 0.0037948300979772074
- trade_count_total: 28
- aggregate_max_dd: 0.7501248221904888
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2299775283657293
- lower_quartile_fold_calmar: -1.7566429553097258
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 75.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.696 with no prior kept baseline. Aggregate DD was 75.0%; negative folds were 9/20; trades=28. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 75.0% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25).

---
