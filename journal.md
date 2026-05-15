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

## Iteration 2026-05-16-626dc61 — REVERTED

**Hypothesis:** Using residual t-stat scores instead of raw cumulative residual scores will improve mean validation Sortino by avoiding high-idiosyncratic-volatility falling knives whose oversold signal is mostly noise.

**Change:** Changed reversion_scores to divide each formation-window residual shock by that ticker's own pre-formation residual volatility before the final cross-sectional z-score, with no new hyperparameters.

**Decision:** REVERTED — catastrophe: max drawdown: 57.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9830 >= alpha/N=0.0125)

**Result:**
- validation_sortino_mean: 1.1599273984215848
- validation_folds: 20
- per_fold_sortinos: [8.5191, 3.8836, 0.8374, 0.9052, -0.3008, -1.5688, 0.3249, 6.0651, -0.5381, -1.7002, 3.1029, 1.5344, 2.9028, 5.7172, -0.8921, 0.2466, 3.6339, -0.3238, -2.7134, -6.4372]
- calmar_mean: 3.2769144963472705
- hit_rate_mean: 0.41083333333333333
- profit_factor_mean: 8.114490894097813
- trade_count_total: 61
- aggregate_max_dd: 0.569684012509127
- worst_fold_max_dd: 0.3399065474713948
- max_position_frac_peak: 1.0211215738374773
- lower_quartile_fold_calmar: -1.3605134689769902
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['max drawdown: 57.0% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.160 with no prior kept baseline. Aggregate DD was 57.0%; negative folds were 8/20; trades=61. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 57.0% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9830 >= alpha/N=0.0125).

---

## Iteration 2026-05-16-949f4a1 — REVERTED

**Hypothesis:** Promoting the regime gate from entry-only to full de-risking when the equal-weight market factor is in its recent left tail will improve mean validation Sortino by avoiding the broad selloff periods that create residual-reversal falling knives.

**Change:** Added a no-new-parameter market-stress gate using the existing regime_pct threshold and made any failed stress or macro gate exit current holdings instead of merely blocking new entries.

**Decision:** REVERTED — catastrophe: gross exposure: max 50692.3% > 100% (cash account — leverage error) · max drawdown: 112.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8596 >= alpha/N=0.0100) · random_walk_mc(only 59.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.09)

**Result:**
- validation_sortino_mean: 0.5505456062864758
- validation_folds: 20
- per_fold_sortinos: [10.3399, 1.2234, -0.5287, 0.8817, -2.4394, -2.4052, 5.0838, 8.2706, -1.4153, -2.903, 0.0277, 0.9638, 0.4982, -0.0268, -1.0392, -0.5173, -0.4992, 1.2609, -1.0817, -4.6832]
- calmar_mean: nan
- hit_rate_mean: 0.47833333333333333
- profit_factor_mean: 1.9271118366795585
- trade_count_total: 65
- aggregate_max_dd: 1.1227906352764778
- worst_fold_max_dd: 1.5817518830979787
- max_position_frac_peak: 2361.3801
- lower_quartile_fold_calmar: -1.477708482415676
- n_negative_folds: 13/20
- risk.passed: False
- risk.violations: ['gross exposure: max 50692.3% > 100% (cash account — leverage error)', 'max drawdown: 112.3% > 50% (account-wipe territory)']

**Learning:** Sortino scored 0.551 with no prior kept baseline. Aggregate DD was 112.3%; negative folds were 13/20; trades=65. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 50692.3% > 100% (cash account — leverage error) · max drawdown: 112.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8596 >= alpha/N=0.0100) · random_walk_mc(only 59.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.09).

---

## Iteration 2026-05-16-293ae9e — REVERTED

**Hypothesis:** Blocking new residual-reversal entries when India VIX is in the existing regime_pct stress tail will improve mean validation Sortino by avoiding falling-knife entries during volatility spikes without forcing costly liquidation of current positions.

**Change:** Changed the regime gate to use india_vix_percentile(today) >= regime_pct/100 as an entry veto before falling back to the LLM macro_regime label, with missing macro data treated as no veto and no new hyperparameters.

**Decision:** REVERTED — catastrophe: max drawdown: 86.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9978 >= alpha/N=0.0083) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27)

**Result:**
- validation_sortino_mean: 0.2517169842627092
- validation_folds: 20
- per_fold_sortinos: [11.2321, 3.8089, 1.2031, 0.9052, -1.3099, -1.6081, 0.8601, 5.1614, -1.0308, -2.5321, 0.0364, 1.2949, 0.3812, 0.4818, -0.908, -1.8978, -2.1351, -2.5208, -1.7049, -4.6832]
- calmar_mean: 1.116124526042559
- hit_rate_mean: 0.31666666666666665
- profit_factor_mean: 2.34229248733348
- trade_count_total: 58
- aggregate_max_dd: 0.8614848308823423
- worst_fold_max_dd: 0.382906221160284
- max_position_frac_peak: 1.0167832254178246
- lower_quartile_fold_calmar: -1.8019884488967088
- n_negative_folds: 11/20
- risk.passed: False
- risk.violations: ['max drawdown: 86.1% > 50% (account-wipe territory)']

**Learning:** Sortino scored 0.252 with no prior kept baseline. Aggregate DD was 86.1%; negative folds were 11/20; trades=58. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 86.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9978 >= alpha/N=0.0083) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27).

---

## Iteration 2026-05-16-6a67387 — REVERTED

**Hypothesis:** Adding a no-new-parameter absolute-trend veto for new residual-reversal entries will improve validation Sortino by avoiding oversold names whose short-horizon residual weakness is aligned with a broader price downtrend rather than temporary factor-relative dislocation.

**Change:** I changed candidate selection so new entries require the latest close to be above the ticker's beta-window moving average, while retained holdings and sector-cap sizing remain unchanged to avoid forced churn.

**Decision:** REVERTED — catastrophe: gross exposure: max 101.7% > 100% (cash account — leverage error) · max drawdown: 58.9% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8660 >= alpha/N=0.0071) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.01)

**Result:**
- validation_sortino_mean: 3.1846784244263153
- validation_folds: 20
- per_fold_sortinos: [11.0171, 3.8123, 1.2603, 0.7804, -1.7056, -1.0091, 2.9967, 2.2931, -2.4781, -3.0426, -0.7997, 3.4749, 4.0283, 3.5421, 0.6841, 0.337, 36.067, 2.4906, 1.4266, -1.4817]
- calmar_mean: 3.6301629103355184
- hit_rate_mean: 0.3591666666666666
- profit_factor_mean: 3.778923271028143
- trade_count_total: 60
- aggregate_max_dd: 0.5890559594699059
- worst_fold_max_dd: 0.41393053283909775
- max_position_frac_peak: 1.0527391028282467
- lower_quartile_fold_calmar: -1.0757757697903774
- n_negative_folds: 6/20
- risk.passed: False
- risk.violations: ['gross exposure: max 101.7% > 100% (cash account — leverage error)', 'max drawdown: 58.9% > 50% (account-wipe territory)']

**Learning:** Sortino scored 3.185 with no prior kept baseline. Aggregate DD was 58.9%; negative folds were 6/20; trades=60. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 101.7% > 100% (cash account — leverage error) · max drawdown: 58.9% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8660 >= alpha/N=0.0071) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.01).

---

## Iteration 2026-05-16-a27ed61 — REVERTED

**Hypothesis:** Sizing selected names against the intended slot count rather than the number of currently selected names will improve mean validation Sortino by keeping cash when the regime gate or sector cap leaves sparse signals, reducing concentrated falling-knife exposure without adding a parameter.

**Change:** Changed target sizing from 0.99 divided by len(selected) to 0.99 divided by n_positions, so empty slots remain cash instead of levering up the remaining residual-reversal bets.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9738 >= alpha/N=0.0063) · random_walk_mc(only 46.48% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.13)

**Result:**
- validation_sortino_mean: 0.5413993321742143
- validation_folds: 20
- per_fold_sortinos: [10.9447, 4.2213, 0.4274, 0.7367, -0.8658, -1.7499, -0.7268, 0.2028, -0.8637, -1.1338, 0.0376, 2.4552, 1.9134, -0.3134, -1.2913, -0.8393, 0.3719, 0.9017, -2.4795, -1.1214]
- calmar_mean: 0.4631821177322097
- hit_rate_mean: 0.3765873015873016
- profit_factor_mean: 2.680559056163559
- trade_count_total: 112
- aggregate_max_dd: 0.3165885464298234
- worst_fold_max_dd: 0.1235288882901726
- max_position_frac_peak: 0.18165511243730334
- lower_quartile_fold_calmar: -1.2174111041364544
- n_negative_folds: 11/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.541 with no prior kept baseline. Aggregate DD was 31.7%; negative folds were 11/20; trades=112. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9738 >= alpha/N=0.0063) · random_walk_mc(only 46.48% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.13).

---

## Iteration 2026-05-16-c194208 — REVERTED

**Hypothesis:** Revisiting the prior high-Sortino absolute-trend veto with fixed slot sizing will improve validation Sortino by keeping residual-reversal entries in names whose larger trend is intact while preventing sparse signal sets from becoming concentrated falling-knife bets.

**Change:** New entries must have the latest close above their beta-window average, and selected names are sized against n_positions with the sector-cap ceiling so unused slots remain cash instead of being redistributed.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0056)

**Result:**
- validation_sortino_mean: 1.4831232227849551
- validation_folds: 20
- per_fold_sortinos: [10.9564, 4.1931, 0.3848, 0.795, -0.8638, -1.7682, -0.2638, 4.3461, -0.7608, -2.7339, -0.8129, 4.232, 3.2605, 1.5216, 0.3351, 0.1406, 2.8889, 1.2647, 2.5709, -0.0238]
- calmar_mean: 1.2884712237919727
- hit_rate_mean: 0.36269841269841263
- profit_factor_mean: 1.4182645288047195
- trade_count_total: 106
- aggregate_max_dd: 0.25067371963732044
- worst_fold_max_dd: 0.1366005141704394
- max_position_frac_peak: 0.1807291500529344
- lower_quartile_fold_calmar: -0.6424117905306452
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.483 with no prior kept baseline. Aggregate DD was 25.1%; negative folds were 7/20; trades=106. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0056).

---

## Iteration 2026-05-16-61d1b22 — REVERTED

**Hypothesis:** Prioritizing oversold new-entry candidates whose latest close has already stabilized will improve mean validation Sortino by replacing some still-falling residual losers with early-reversion setups without adding parameters or turnover.

**Change:** I added a one-bar rebound priority for new entries: candidates with current close greater than or equal to the prior close are passed to sector-cap selection first, while retained positions, PIT universe handling, and sizing remain unchanged.

**Decision:** REVERTED — catastrophe: gross exposure: max 103.6% > 100% (cash account — leverage error) · max drawdown: 61.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9876 >= alpha/N=0.0050)

**Result:**
- validation_sortino_mean: 1.5628148134356263
- validation_folds: 20
- per_fold_sortinos: [6.9897, 2.9878, -0.2905, 0.9052, -0.0634, -1.3287, 2.4714, 6.5187, -0.9377, -3.1668, -2.3814, 0.641, 0.8985, 1.0219, 1.103, 0.4318, 19.0097, 0.3164, -2.4225, -1.4479]
- calmar_mean: 2.338499788516152
- hit_rate_mean: 0.3775
- profit_factor_mean: 1.441925170219892
- trade_count_total: 61
- aggregate_max_dd: 0.6120789556696081
- worst_fold_max_dd: 0.41596878990984604
- max_position_frac_peak: 1.088378944825857
- lower_quartile_fold_calmar: -1.298506803181767
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['gross exposure: max 103.6% > 100% (cash account — leverage error)', 'max drawdown: 61.2% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.563 with no prior kept baseline. Aggregate DD was 61.2%; negative folds were 8/20; trades=61. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 103.6% > 100% (cash account — leverage error) · max drawdown: 61.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9876 >= alpha/N=0.0050).

---

## Iteration 2026-05-16-3a60d56 — REVERTED

**Hypothesis:** Skipping new residual-reversal entries only when the oversold move coincides with unusually heavy recent news and negative ticker sentiment will improve mean validation Sortino by avoiding event-driven falling knives while preserving ordinary factor-dislocation trades.

**Change:** Added a news-and-sentiment veto for new entries, leaving retention, PIT universe handling, sector caps, and sizing unchanged so the test isolates whether event-risk filtering improves residual reversion.

**Decision:** REVERTED — catastrophe: max drawdown: 86.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9982 >= alpha/N=0.0045) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27)

**Result:**
- validation_sortino_mean: 0.2517169842627092
- validation_folds: 20
- per_fold_sortinos: [11.2321, 3.8089, 1.2031, 0.9052, -1.3099, -1.6081, 0.8601, 5.1614, -1.0308, -2.5321, 0.0364, 1.2949, 0.3812, 0.4818, -0.908, -1.8978, -2.1351, -2.5208, -1.7049, -4.6832]
- calmar_mean: 1.116124526042559
- hit_rate_mean: 0.31666666666666665
- profit_factor_mean: 2.34229248733348
- trade_count_total: 58
- aggregate_max_dd: 0.8614848308823423
- worst_fold_max_dd: 0.382906221160284
- max_position_frac_peak: 1.0167832254178246
- lower_quartile_fold_calmar: -1.8019884488967088
- n_negative_folds: 11/20
- risk.passed: False
- risk.violations: ['max drawdown: 86.1% > 50% (account-wipe territory)']

**Learning:** Sortino scored 0.252 with no prior kept baseline. Aggregate DD was 86.1%; negative folds were 11/20; trades=58. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 86.1% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9982 >= alpha/N=0.0045) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27).

---

## Iteration 2026-05-16-9152566 — REVERTED

**Hypothesis:** Adding a short-horizon absolute-trend confirmation for new residual-reversal entries will improve validation Sortino by filtering out oversold names that are still breaking down while leaving retained positions, PIT universe handling, and turnover controls unchanged.

**Change:** I changed new-entry selection so candidates must have the latest close at or above their 20-day in-feed average before sector-cap selection, using the existing ADV lookback as a non-tuned stability check.

**Decision:** REVERTED — catastrophe: gross exposure: max 101.6% > 100% (cash account — leverage error) · max drawdown: 58.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9940 >= alpha/N=0.0042)

**Result:**
- validation_sortino_mean: 1.2550544461426543
- validation_folds: 20
- per_fold_sortinos: [10.8658, 3.8209, 1.4175, 0.8402, -1.2755, 0.1012, -0.0812, 0.5197, -2.7091, -3.0048, 2.4604, 2.3486, 1.2542, 0.4238, -0.2209, 0.4855, 10.33, 0.7496, -1.2777, -1.947]
- calmar_mean: 2.1439041157407566
- hit_rate_mean: 0.38166666666666665
- profit_factor_mean: 2.470237441117267
- trade_count_total: 55
- aggregate_max_dd: 0.5852857451197399
- worst_fold_max_dd: 0.43014570468668045
- max_position_frac_peak: 1.1670458792767393
- lower_quartile_fold_calmar: -1.0395501494394457
- n_negative_folds: 8/20
- risk.passed: False
- risk.violations: ['gross exposure: max 101.6% > 100% (cash account — leverage error)', 'max drawdown: 58.5% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.255 with no prior kept baseline. Aggregate DD was 58.5%; negative folds were 8/20; trades=55. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 101.6% > 100% (cash account — leverage error) · max drawdown: 58.5% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9940 >= alpha/N=0.0042).

---

## Iteration 2026-05-16-1791ad5 — REVERTED

**Hypothesis:** Applying the 25% sector cap to the entire target book, including retained positions and sparse baskets, will improve validation Sortino by reducing sector-cluster and single-name drawdowns without adding a new signal parameter.

**Change:** I changed final portfolio construction so retained names and new entries are capped together by sector, with per-name sizing capped at the sector limit when fewer than four names qualify.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9578 >= alpha/N=0.0038) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.06)

**Result:**
- validation_sortino_mean: 0.11498623269635548
- validation_folds: 20
- per_fold_sortinos: [3.5262, 3.7324, 2.472, -0.5347, -0.7857, -2.8796, -0.3673, 0.172, -2.1628, -2.7191, 0.3007, 2.2823, 1.9606, 0.3841, -0.594, -0.501, -0.5714, -0.7368, -0.1692, -0.509]
- calmar_mean: -0.022281150876833127
- hit_rate_mean: 0.4010119047619048
- profit_factor_mean: 0.7822077378993411
- trade_count_total: 85
- aggregate_max_dd: 0.32525268853865985
- worst_fold_max_dd: 0.14935408979248976
- max_position_frac_peak: 0.27486088174851864
- lower_quartile_fold_calmar: -0.9895379959108361
- n_negative_folds: 12/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.115 with no prior kept baseline. Aggregate DD was 32.5%; negative folds were 12/20; trades=85. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.9578 >= alpha/N=0.0038) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.06).

---

## Iteration 2026-05-16-ff54a95 — REVERTED

**Hypothesis:** Requiring the strategy to rank and retain only names with genuinely negative cumulative factor residuals will improve validation Sortino by avoiding forced relative-value buys where the stock is merely less strong than peers rather than actually oversold.

**Change:** I added an absolute residual-sign gate in portfolio construction so new entries and retained positions must have negative cumulative market-plus-size residuals, while preserving the existing z-score ranking, cadence, PIT universe, sector cap, and sizing logic.

**Decision:** REVERTED — sortino -0.563 not positive — won't compound on losing baseline | catastrophe: max drawdown: 86.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0036) · random_walk_mc(only 8.22% percentile vs RW null) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.56) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.11)

**Result:**
- validation_sortino_mean: -0.5628923278136998
- validation_folds: 20
- per_fold_sortinos: [0.3331, -0.7148, -0.5632, 2.305, -2.2917, -1.8988, 2.0006, 5.1135, -1.0367, -2.5238, 0.036, 0.9697, 0.3812, 0.4818, -0.908, -1.8978, -2.1351, -2.5208, -1.7049, -4.6832]
- calmar_mean: 0.05202078300802215
- hit_rate_mean: 0.4008333333333334
- profit_factor_mean: 1.4147639257559488
- trade_count_total: 70
- aggregate_max_dd: 0.8629334982368633
- worst_fold_max_dd: 0.382906221160284
- max_position_frac_peak: 1.0171293528304304
- lower_quartile_fold_calmar: -1.8944802390645987
- n_negative_folds: 13/20
- risk.passed: False
- risk.violations: ['max drawdown: 86.3% > 50% (account-wipe territory)']

**Learning:** Sortino scored -0.563 with no prior kept baseline. Aggregate DD was 86.3%; negative folds were 13/20; trades=70. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino -0.563 not positive — won't compound on losing baseline | catastrophe: max drawdown: 86.3% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0036) · random_walk_mc(only 8.22% percentile vs RW null) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.56) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.11).

---
