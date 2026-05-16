# Journal — momentum-rotation-strategy

**Fresh start 2026-05-16.** Prior history archived in
`journal_pre-2026-05-16_archive.md` — those REVERT verdicts were produced
by the broken evaluator (degenerate RW-MC null, 5-name-universe poisoning,
parsimony double-jeopardy) and are NOT reliable signals of which ideas are
bad. Evaluator now at `EVALUATOR_VERSION = 2026-05-16-univfloor`. Durable
structural learnings are codified in `program.md`. Explore freely.

---


## Iteration 2026-05-16-36a6b5e — REVERTED

**Hypothesis:** Fixed risk-slot sizing will improve validation Sortino by cutting concentration and drawdowns when quality, regime, or sector filters leave fewer than 25 eligible names.

**Change:** Changed portfolio construction so every selected name gets 0.99 / n_positions and unfilled or sector-capped slots remain cash, with the 25% sector cap enforced across retained holdings and new entries.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1846 (need ≥ 0.20); sub-periods = [+3.472, -0.641])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.206417688069978
- validation_folds: 13
- per_fold_sortinos: [1.5791, -1.1386, -1.7245, 6.1919, 11.6122, 4.5783, 4.3657, 0.0129, 5.7698, 1.4911, 1.2409, -2.3017, -2.9936]
- calmar_mean: 2.321831785386836
- hit_rate_mean: 0.7243589743589745
- profit_factor_mean: 3.1692336740598224
- trade_count_total: 56
- aggregate_max_dd: 0.15161747970591322
- worst_fold_max_dd: 0.09085207626058876
- max_position_frac_peak: 0.042315182839088264
- lower_quartile_fold_calmar: -1.090818616697613
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.206 with no prior kept baseline. Aggregate DD was 15.2%; negative folds were 5/13; trades=56. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1846 (need ≥ 0.20); sub-periods = [+3.472, -0.641]).

---

## Iteration 2026-05-16-15152fa — REVERTED

**Hypothesis:** A PIT-safe fixed-slot version of the momentum book will improve validation Sortino by reducing concentration and avoiding the prior variant's off-universe retention bug.

**Change:** Changed sizing to 0.99 / n_positions with empty slots left in cash, removed the banned pathlib import, and made retention explicitly require current point-in-time universe membership.

**Decision:** REVERTED — catastrophe: gross exposure: max 117.2% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2250 (need ≥ 0.20); sub-periods = [+2.595, -0.584])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.6169712206302143
- validation_folds: 13
- per_fold_sortinos: [1.22, -1.6285, -2.5774, 3.7922, 11.0557, 4.0126, 3.4635, 2.158, 1.8602, 1.1978, 1.3871, -2.588, -2.3326]
- calmar_mean: 5.68856631455032
- hit_rate_mean: 0.5644135217009711
- profit_factor_mean: 11.58981345885666
- trade_count_total: 213
- aggregate_max_dd: 0.3007529271378043
- worst_fold_max_dd: 0.21352830563426595
- max_position_frac_peak: 0.045661659196724734
- lower_quartile_fold_calmar: -1.5599362355522555
- n_negative_folds: 4/13
- risk.passed: False
- risk.violations: ['gross exposure: max 117.2% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 1.617 with no prior kept baseline. Aggregate DD was 30.1%; negative folds were 4/13; trades=213. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 117.2% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2250 (need ≥ 0.20); sub-periods = [+2.595, -0.584]).

---

## Iteration 2026-05-16-b5eb411 — REVERTED

**Hypothesis:** A defensive fixed-slot momentum book that halves gross exposure during adverse macro regimes will improve validation Sortino by reducing the negative-fold drawdowns that caused the prior fixed-slot variants to fail stationarity.

**Change:** Removed the banned pathlib import, made sizing use fixed risk slots with a 99% cap, forced retained holdings to remain PIT-eligible, and added a continuous macro-risk gross scaler based on India VIX percentile and Nifty distance from its 200DMA.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2103 (need ≥ 0.20); sub-periods = [+2.829, -0.595])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.775481803098717
- validation_folds: 13
- per_fold_sortinos: [2.4506, -0.817, -2.3196, 3.6351, 10.8936, 3.4538, 2.3902, 3.0679, 2.7067, 1.9561, 1.1093, -2.9464, -2.4991]
- calmar_mean: 4.855183895152188
- hit_rate_mean: 0.5258326601696202
- profit_factor_mean: 2.412379010713737
- trade_count_total: 344
- aggregate_max_dd: 0.24258067473823078
- worst_fold_max_dd: 0.15403344920969977
- max_position_frac_peak: 0.04567750566131409
- lower_quartile_fold_calmar: -1.0292730109122372
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.775 with no prior kept baseline. Aggregate DD was 24.3%; negative folds were 4/13; trades=344. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2103 (need ≥ 0.20); sub-periods = [+2.829, -0.595]).

---

## Iteration 2026-05-16-b767729 — REVERTED

**Hypothesis:** Replacing raw 12-1 momentum with positive risk-adjusted momentum should improve validation Sortino by favoring steadier trends and avoiding volatile rebound names while keeping fixed-slot cash discipline.

**Change:** Removed the banned pathlib import, made quality loading use the configured path string directly, changed ranking to volatility-adjusted positive momentum, and sized positions at 90% gross divided by n_positions so unused slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1597 (need ≥ 0.20); sub-periods = [+2.708, -0.432])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.7420135527460874
- validation_folds: 13
- per_fold_sortinos: [2.0482, -1.0941, -1.4439, 3.7374, 9.7519, 3.6394, 3.8001, 2.8685, 1.0686, 0.9551, 1.6141, -1.6384, -2.6607]
- calmar_mean: 4.711550779685966
- hit_rate_mean: 0.5590015978173872
- profit_factor_mean: 3.984663708024587
- trade_count_total: 188
- aggregate_max_dd: 0.1911825294139835
- worst_fold_max_dd: 0.11037444118742717
- max_position_frac_peak: 0.049941324387045245
- lower_quartile_fold_calmar: -1.3565684713735158
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.742 with no prior kept baseline. Aggregate DD was 19.1%; negative folds were 4/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1597 (need ≥ 0.20); sub-periods = [+2.708, -0.432]).

---

## Iteration 2026-05-16-d5845c6 — REJECTED

**Hypothesis:** A diversified low-downside-volatility trend book should improve validation Sortino by avoiding high-beta momentum reversals that drove the negative sub-periods in prior variants.

**Change:** Replaced raw 12-1 momentum plus inactive quality screen with a PIT-safe 6-month trend score divided by downside volatility, requiring positive absolute trend and 200DMA confirmation while using fixed-slot sizing so blocked slots remain cash.

**Decision:** REJECTED — validation failed: no bt.Strategy subclass defined

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: no bt.Strategy subclass defined.

---

## Iteration 2026-05-16-1d407b5 — REVERTED

**Hypothesis:** A positive six-month trend book ranked by downside-volatility-adjusted momentum will improve validation Sortino by avoiding volatile rebound names that caused the prior raw-momentum variants to lose in adverse sub-periods.

**Change:** Replaced raw 12-1 momentum with a PIT-safe positive-trend/downside-volatility score plus 200DMA confirmation, removed the banned pathlib dependency, and used 30 fixed 80%-gross risk slots with portfolio-level sector-cap enforcement.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0905 >= alpha/N=0.0200) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0171 (need ≥ 0.20); sub-periods = [+2.311, -0.039])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.587670483783276
- validation_folds: 13
- per_fold_sortinos: [0.6389, -0.3469, -1.9107, 3.8321, 12.6126, 4.4508, 2.5728, 0.3042, -1.3563, -1.1078, 1.1788, 0.6379, -0.8667]
- calmar_mean: 0.8076214622123451
- hit_rate_mean: 0.6203626438920556
- profit_factor_mean: 7.122053328185047
- trade_count_total: 123
- aggregate_max_dd: 0.0794905892614491
- worst_fold_max_dd: 0.053040710021354104
- max_position_frac_peak: 0.04187831436880299
- lower_quartile_fold_calmar: -0.4403737647637085
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.588 with no prior kept baseline. Aggregate DD was 7.9%; negative folds were 5/13; trades=123. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0905 >= alpha/N=0.0200) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0171 (need ≥ 0.20); sub-periods = [+2.311, -0.039]).

---

## Iteration 2026-05-16-94696fa — REVERTED

**Hypothesis:** Replacing raw momentum with a 52-week-high resilience rank should improve validation Sortino by favoring durable uptrends with lower downside volatility and avoiding distressed rebound names that caused prior sign-flipped sub-periods.

**Change:** Changed strategy.py to rank PIT-eligible names by positive 12-month and 6-month trend near the 52-week high divided by downside volatility, while using fixed risk-slot sizing and portfolio-level sector caps so unused slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0280 >= alpha/N=0.0167) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2484 (need ≥ 0.20); sub-periods = [+2.832, -0.704])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.7444203580589588
- validation_folds: 13
- per_fold_sortinos: [2.6894, 0.7286, -0.0298, 4.2674, 7.2892, 3.9176, 2.7823, 0.0927, 3.7542, -0.0275, 1.2586, -1.3706, -2.6747]
- calmar_mean: 1.068017538209794
- hit_rate_mean: 0.4945054945054946
- profit_factor_mean: 4.923147990654314
- trade_count_total: 64
- aggregate_max_dd: 0.06958875391583291
- worst_fold_max_dd: 0.05127829420120309
- max_position_frac_peak: 0.03712862698938827
- lower_quartile_fold_calmar: 0.012469372860533963
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.744 with no prior kept baseline. Aggregate DD was 7.0%; negative folds were 4/13; trades=64. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0280 >= alpha/N=0.0167) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2484 (need ≥ 0.20); sub-periods = [+2.832, -0.704]).

---

## Iteration 2026-05-16-6ecdced — REVERTED

**Hypothesis:** A breadth-gated pullback-in-uptrend book will improve mean validation Sortino by moving to cash when the broad PIT universe is weak and buying temporary pullbacks instead of extended momentum leaders.

**Change:** Replaced raw 12-1 momentum and dead quality loading with a PIT-safe pullback/resilience rank, fixed-slot 90% gross sizing across 30 positions, and a broad-market breadth kill switch to address the prior sign-flipped sub-periods.

**Decision:** REVERTED — sortino -0.759 not positive — won't compound on losing baseline | catastrophe: gross exposure: max 131.2% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0471 (need ≥ 0.20); sub-periods = [-0.105, -2.232])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.7594744250463967
- validation_folds: 13
- per_fold_sortinos: [-0.197, -1.6234, -3.7712, -1.7095, 3.7557, 3.0316, 1.1985, -1.8362, 0.2053, -0.5592, -4.7149, -1.7487, -1.9044]
- calmar_mean: -0.5300171600031109
- hit_rate_mean: 0.47873031716565134
- profit_factor_mean: 1.6902358452661563
- trade_count_total: 404
- aggregate_max_dd: 0.49921197550990426
- worst_fold_max_dd: 0.28925858506091423
- max_position_frac_peak: 0.05254901695101053
- lower_quartile_fold_calmar: -1.4593774471426557
- n_negative_folds: 9/13
- risk.passed: False
- risk.violations: ['gross exposure: max 131.2% > 100% (cash account — leverage error)']

**Learning:** Sortino scored -0.759 with no prior kept baseline. Aggregate DD was 49.9%; negative folds were 9/13; trades=404. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino -0.759 not positive — won't compound on losing baseline | catastrophe: gross exposure: max 131.2% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0471 (need ≥ 0.20); sub-periods = [-0.105, -2.232]).

---

## Iteration 2026-05-16-3d704cf — REVERTED

**Hypothesis:** A low-volatility positive-trend book with fixed risk slots will improve validation Sortino by replacing unstable winner-chasing momentum with defensive names that have smoother uptrends and smaller drawdowns across regimes.

**Change:** Replaced raw 12-1 momentum and the inactive fundamentals path with a PIT-safe defensive trend-stability rank, fixed gross/n_positions sizing, retention-aware sector-capped selection, and a shock/risk_off gross reducer.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4806 (need ≥ 0.20); sub-periods = [+2.209, -1.062])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.202759017244205
- validation_folds: 13
- per_fold_sortinos: [0.2545, -1.5416, -3.3805, 4.129, 9.5669, 3.4711, 5.1869, 1.0481, 1.1481, -1.3888, 1.5655, -1.3849, -3.0385]
- calmar_mean: 0.7183043718269069
- hit_rate_mean: 0.5082282850382398
- profit_factor_mean: 3.3976009070649345
- trade_count_total: 151
- aggregate_max_dd: 0.1093201847388484
- worst_fold_max_dd: 0.060222103423291054
- max_position_frac_peak: 0.031180761291415032
- lower_quartile_fold_calmar: -1.1546379216694613
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.203 with no prior kept baseline. Aggregate DD was 10.9%; negative folds were 5/13; trades=151. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4806 (need ≥ 0.20); sub-periods = [+2.209, -1.062]).

---

## Iteration 2026-05-16-80bd244 — REVERTED

**Hypothesis:** A fixed-slot long-term-uptrend pullback book with continuous macro de-risking will improve mean validation Sortino by buying resilient leaders after short-term weakness while cutting exposure during broad market stress.

**Change:** Replaced raw 12-1 winner chasing and dead fundamentals screening with PIT-safe trend-confirmed pullback scoring, fixed gross/n_positions sizing, retained-name sector-cap enforcement, and allowed-import macro exposure scaling.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.5607 >= alpha/N=0.0111) · random_walk_mc(only 43.95% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4340 (need ≥ 0.20); sub-periods = [+0.934, -0.406])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.5221383165622278
- validation_folds: 13
- per_fold_sortinos: [1.4402, -0.9773, -3.3055, 1.2301, 6.3872, 5.0447, 1.8996, -3.0092, -0.2997, 0.2478, 4.2437, -3.0142, -3.0995]
- calmar_mean: 0.26913418579096837
- hit_rate_mean: 0.6063795658525394
- profit_factor_mean: 568.6952844352382
- trade_count_total: 246
- aggregate_max_dd: 0.11871521883234781
- worst_fold_max_dd: 0.07533390972069305
- max_position_frac_peak: 0.059462504659381285
- lower_quartile_fold_calmar: -1.7570611189354701
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.522 with no prior kept baseline. Aggregate DD was 11.9%; negative folds were 6/13; trades=246. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.5607 >= alpha/N=0.0111) · random_walk_mc(only 43.95% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4340 (need ≥ 0.20); sub-periods = [+0.934, -0.406]).

---

## Iteration 2026-05-16-970ba09 — REVERTED

**Hypothesis:** A diversified 252-day absolute-momentum book ranked by trend consistency and downside-volatility control will improve validation Sortino by avoiding both weak absolute trends and noisy high-volatility winners while keeping fixed-slot cash discipline.

**Change:** Replaced raw 12-1 momentum plus inactive quality screening with a PIT-safe trend-quality score using absolute momentum, moving-average confirmation, downside volatility, and drawdown penalty, sized strictly by fixed risk slots under the 25% sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0735 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5628 (need ≥ 0.20); sub-periods = [+2.437, -1.371])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.2650995707209856
- validation_folds: 13
- per_fold_sortinos: [3.6098, -0.3468, -2.3386, 2.8482, 7.3444, 2.8243, 3.9586, 0.221, 3.8111, 0.2772, 0.3882, -2.495, -3.6561]
- calmar_mean: 1.0351199179644655
- hit_rate_mean: 0.6272893772893773
- profit_factor_mean: 4.793041889591837
- trade_count_total: 79
- aggregate_max_dd: 0.10434010746632988
- worst_fold_max_dd: 0.05946065259945
- max_position_frac_peak: 0.03935073043671691
- lower_quartile_fold_calmar: -0.2221627824291339
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.265 with no prior kept baseline. Aggregate DD was 10.4%; negative folds were 4/13; trades=79. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0735 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5628 (need ≥ 0.20); sub-periods = [+2.437, -1.371]).

---
