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

## Iteration 2026-05-16-e83fab7 — REVERTED

**Hypothesis:** A volatility-contraction breakout book will improve validation Sortino by selecting liquid NSE names with positive intermediate trend, compressed recent ranges, and fresh upside confirmation rather than chasing raw 12-1 momentum.

**Change:** Replaced the baseline 12-1 momentum rank with a PIT-safe volatility-contraction breakout score, removed the dead fundamentals/path dependency, and sized strictly by fixed risk slots under the sector cap.

**Decision:** REVERTED — sortino -0.463 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · parsimony(baseline params=7, strategy=8; +1 param(s) need Sortino +0.10, has -0.46)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.4627004398143193
- validation_folds: 13
- per_fold_sortinos: [2.749, -2.3274, -5.3429, 0.0549, 1.4799, 1.1871, 3.4567, -2.0752, -2.9492, -2.9243, -2.7701, 5.3735, -1.9272]
- calmar_mean: -0.29137468962859353
- hit_rate_mean: 0.4134415573180755
- profit_factor_mean: 1.2493633273589764
- trade_count_total: 184
- aggregate_max_dd: 0.26273869521887483
- worst_fold_max_dd: 0.08288428400659305
- max_position_frac_peak: 0.05802694724170715
- lower_quartile_fold_calmar: -2.166639060678244
- n_negative_folds: 7/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -0.463 with no prior kept baseline. Aggregate DD was 26.3%; negative folds were 7/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.463 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · parsimony(baseline params=7, strategy=8; +1 param(s) need Sortino +0.10, has -0.46).

---

## Iteration 2026-05-16-a519047 — REVERTED

**Hypothesis:** Adding a PIT-safe adverse-news veto to the canonical momentum book will improve validation Sortino by avoiding event-driven losers that price-only momentum variants kept holding during the sign-flipped sub-periods.

**Change:** I removed the inactive fundamentals dependency and ranked only momentum names with non-adverse LLM sentiment/event evidence, while enforcing fixed n_positions sizing and the sector cap across the whole selected book.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1846 (need ≥ 0.20); sub-periods = [+3.472, -0.641])

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

**Learning:** Sortino scored 2.206 with no prior kept baseline. Aggregate DD was 15.2%; negative folds were 5/13; trades=56. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1846 (need ≥ 0.20); sub-periods = [+3.472, -0.641]).

---

## Iteration 2026-05-16-6794fb6 — REVERTED

**Hypothesis:** A PIT-safe defensive relative-strength book that ranks persistent low-downside-volatility uptrends while sizing on fixed slots will improve validation Sortino by avoiding the unstable high-beta momentum reversals that drove prior negative sub-periods.

**Change:** Replaced raw 12-1 momentum and inactive fundamentals loading with a pure price-based composite of six-month strength, three-month confirmation, MA trend, downside volatility, and drawdown control, while enforcing PIT universe membership, sector caps, and fixed n_positions sizing.

**Decision:** REVERTED — catastrophe: gross exposure: max 110.3% > 100% (cash account — leverage error) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3466 (need ≥ 0.20); sub-periods = [+2.847, -0.987])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.6673176660853302
- validation_folds: 13
- per_fold_sortinos: [1.3018, -0.5941, -2.0873, 2.6244, 12.5121, 4.3401, 4.1162, 3.0732, 0.3362, -2.0795, 2.221, -1.9554, -2.1336]
- calmar_mean: 4.905596874620181
- hit_rate_mean: 0.4646634786422477
- profit_factor_mean: 3.9564893452828325
- trade_count_total: 264
- aggregate_max_dd: 0.27174545075010786
- worst_fold_max_dd: 0.16343061328815633
- max_position_frac_peak: 0.05123334856460133
- lower_quartile_fold_calmar: -1.7503263005464769
- n_negative_folds: 5/13
- risk.passed: False
- risk.violations: ['gross exposure: max 110.3% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 1.667 with no prior kept baseline. Aggregate DD was 27.2%; negative folds were 5/13; trades=264. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 110.3% > 100% (cash account — leverage error) | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3466 (need ≥ 0.20); sub-periods = [+2.847, -0.987]).

---

## Iteration 2026-05-16-6a41683 — REVERTED

**Hypothesis:** A fixed-slot dual-momentum book that requires each stock to beat the broad NSE universe median before ranking should improve validation Sortino by avoiding weak absolute-trend winners during adverse sub-periods while preserving diversified exposure.

**Change:** I replaced the dead quality/fundamentals dependency with a PIT-safe absolute-and-relative momentum score using six-month return, twelve-minus-one return, and trend consistency, while sizing on fixed n_positions slots under the existing sector cap.

**Decision:** REVERTED — catastrophe: gross exposure: max 116.0% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0170 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2265 (need ≥ 0.20); sub-periods = [+2.783, -0.630])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.7325855064965552
- validation_folds: 13
- per_fold_sortinos: [1.8871, -0.5684, -2.1132, 3.4422, 11.2541, 3.8708, 3.461, 2.3146, 1.4968, 0.8036, 1.6332, -2.369, -2.5892]
- calmar_mean: 5.591486339348397
- hit_rate_mean: 0.5370064745134872
- profit_factor_mean: 2.9967899513915275
- trade_count_total: 249
- aggregate_max_dd: 0.2874401885748642
- worst_fold_max_dd: 0.2000328526576534
- max_position_frac_peak: 0.044309303238762886
- lower_quartile_fold_calmar: -0.9802202313726585
- n_negative_folds: 4/13
- risk.passed: False
- risk.violations: ['gross exposure: max 116.0% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 1.733 with no prior kept baseline. Aggregate DD was 28.7%; negative folds were 4/13; trades=249. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 116.0% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0170 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2265 (need ≥ 0.20); sub-periods = [+2.783, -0.630]).

---

## Iteration 2026-05-16-fc5c3f8 — REVERTED

**Hypothesis:** A fixed-slot 52-week-high resilience book with explicit off-universe exits and no selected-count sizing will improve validation Sortino by keeping diversified exposure in persistent leaders while eliminating the prior hard-reject causes.

**Change:** I replaced the no-op quality dependency with a PIT-safe price-only resilience rank, fixed sizing to gross/n_positions, and forced dropped-universe holdings to target zero.

**Decision:** REVERTED — catastrophe: gross exposure: max 109.7% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0340 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5189 (need ≥ 0.20); sub-periods = [+2.616, -1.357])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.393262980760852
- validation_folds: 13
- per_fold_sortinos: [3.0971, 0.4832, -2.2841, 1.8399, 9.7003, 3.5511, 3.8802, 2.0042, 1.2695, -0.4744, 0.0959, -2.6483, -2.4021]
- calmar_mean: 4.118613424134916
- hit_rate_mean: 0.5343525975528383
- profit_factor_mean: 3.0645447174900586
- trade_count_total: 286
- aggregate_max_dd: 0.25212973273008044
- worst_fold_max_dd: 0.1711395057334021
- max_position_frac_peak: 0.0413603400304295
- lower_quartile_fold_calmar: -0.9645132383735757
- n_negative_folds: 4/13
- risk.passed: False
- risk.violations: ['gross exposure: max 109.7% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 1.393 with no prior kept baseline. Aggregate DD was 25.2%; negative folds were 4/13; trades=286. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 109.7% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0340 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5189 (need ≥ 0.20); sub-periods = [+2.616, -1.357]).

---

## Iteration 2026-05-16-bba3f4f — REVERTED

**Hypothesis:** A sector-breadth relative-strength book will improve validation Sortino by owning stocks whose own trend is confirmed by broad sector leadership, while the fixed 80% gross slot budget removes the leverage drift that invalidated recent variants.

**Change:** Replaced single-name raw momentum and selected-count sizing with sector-median-confirmed risk-adjusted momentum, PIT-safe off-universe exits, optional sentiment/event penalties, strict retained-position sector accounting, and fixed 0.80/n_positions targets.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4467 (need ≥ 0.20); sub-periods = [+2.691, -1.202])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.493298271400752
- validation_folds: 13
- per_fold_sortinos: [3.2004, -1.3666, -1.6203, 4.5479, 10.2359, 3.3085, 3.7436, -0.3593, 2.5318, 1.0543, 0.7612, -2.9574, -3.6671]
- calmar_mean: 1.1830206024301568
- hit_rate_mean: 0.6027472527472528
- profit_factor_mean: 7.5361222149132265
- trade_count_total: 71
- aggregate_max_dd: 0.10843167266360754
- worst_fold_max_dd: 0.07084941851431152
- max_position_frac_peak: 0.04973550541313947
- lower_quartile_fold_calmar: -1.1652707255275163
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.493 with no prior kept baseline. Aggregate DD was 10.8%; negative folds were 5/13; trades=71. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4467 (need ≥ 0.20); sub-periods = [+2.691, -1.202]).

---

## Iteration 2026-05-16-bef15c0 — REVERTED

**Hypothesis:** A fixed-slot broad-market equal-weight trend book will improve validation Sortino by replacing unstable winner-chasing with diversified participation in positive intermediate trends while staying cash when fewer names qualify.

**Change:** I replaced selected-count 12-1 momentum sizing with PIT-safe fixed-slot ranking of positive six-month trend, low downside volatility, and mild short-term pullback, using 90% gross across 25 fixed slots and explicit off-universe exits.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.7873 (need ≥ 0.20); sub-periods = [+1.821, -3.255])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.2592360670142141
- validation_folds: 13
- per_fold_sortinos: [0.4394, -1.4185, -3.0191, 4.9922, 8.1425, 2.4962, 1.9143, 4.1453, -1.3023, -4.0455, -3.5385, -1.6939, -3.7418]
- calmar_mean: 0.2709899184421382
- hit_rate_mean: 0.3907214917336374
- profit_factor_mean: 1.7586904402975183
- trade_count_total: 211
- aggregate_max_dd: 0.1898130240612684
- worst_fold_max_dd: 0.0702926133600519
- max_position_frac_peak: 0.049035804269947435
- lower_quartile_fold_calmar: -1.6538384205186043
- n_negative_folds: 7/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.259 with no prior kept baseline. Aggregate DD was 19.0%; negative folds were 7/13; trades=211. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.7873 (need ≥ 0.20); sub-periods = [+1.821, -3.255]).

---

## Iteration 2026-05-16-b6eee96 — REVERTED

**Hypothesis:** A fixed-slot volume-confirmed trend book will improve validation Sortino by selecting positive 12-1 momentum names with recent accumulation and smoother participation while keeping unused slots in cash.

**Change:** Replaced raw selected-count momentum sizing with PIT-safe accumulation-weighted trend ranking, full-book sector-cap selection, macro gross scaling, and fixed 82% gross risk-slot targets to reduce leverage and fragile price-only leaders.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0150 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1415 (need ≥ 0.20); sub-periods = [+2.696, -0.382])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.7493518815972162
- validation_folds: 13
- per_fold_sortinos: [1.4332, -0.417, -2.9167, 4.0742, 11.155, 2.0236, 4.844, 3.1, 0.9712, 0.2458, 1.0423, -1.0854, -1.7288]
- calmar_mean: 1.1291694910339491
- hit_rate_mean: 0.4955932955932956
- profit_factor_mean: 5.307395397305127
- trade_count_total: 95
- aggregate_max_dd: 0.07135330697855025
- worst_fold_max_dd: 0.046924731552829335
- max_position_frac_peak: 0.032832801635965386
- lower_quartile_fold_calmar: -0.3725009189205619
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.749 with no prior kept baseline. Aggregate DD was 7.1%; negative folds were 4/13; trades=95. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0150 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1415 (need ≥ 0.20); sub-periods = [+2.696, -0.382]).

---

## Iteration 2026-05-16-d69ab9e — REVERTED

**Hypothesis:** A PIT-safe diversified momentum book with fixed-slot sizing and continuous macro crash de-risking will improve validation Sortino by preserving the prior volume-confirmed edge while cutting exposure during high-VIX or below-200DMA market regimes that caused the negative sub-period.

**Change:** I replaced concentrated selected-count sizing with 25 fixed risk slots, added liquidity/volume-confirmed risk-adjusted 12-1 momentum, removed forbidden pathlib usage, enforced PIT exits, and scaled gross exposure down under adverse macro signals.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1839 (need ≥ 0.20); sub-periods = [+2.327, -0.428])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.4792598801505759
- validation_folds: 13
- per_fold_sortinos: [0.8641, -0.6545, -2.0942, 2.1642, 7.9218, 3.7514, 2.509, 3.5948, 2.8855, 1.141, 1.845, -2.086, -2.6117]
- calmar_mean: 4.216643932950861
- hit_rate_mean: 0.5170354205213695
- profit_factor_mean: 4.0547940783499605
- trade_count_total: 227
- aggregate_max_dd: 0.18762922862034045
- worst_fold_max_dd: 0.12007738341594765
- max_position_frac_peak: 0.046123588559188265
- lower_quartile_fold_calmar: -0.9293204844414228
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.479 with no prior kept baseline. Aggregate DD was 18.8%; negative folds were 4/13; trades=227. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1839 (need ≥ 0.20); sub-periods = [+2.327, -0.428]).

---

## Iteration 2026-05-16-8da0e91 — REVERTED

**Hypothesis:** A PIT-safe fixed-slot low-volatility momentum book with breadth and macro exposure scaling will improve validation Sortino by preserving cross-sectional trend exposure while reducing the regime sign-flip seen in recent concentrated trend variants.

**Change:** I removed forbidden pathlib usage and selected-count sizing, then changed selection to risk-adjusted 12-1 momentum filtered by absolute trend and market breadth, with fixed 25-slot sizing, sector caps, off-universe exits, and defensive gross scaling from breadth and macro stress.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3057 (need ≥ 0.20); sub-periods = [+2.153, -0.658])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.2882062923720965
- validation_folds: 13
- per_fold_sortinos: [0.0445, -1.5402, -2.7832, 1.6205, 7.4929, 3.4006, 2.7912, 5.1771, 3.1761, 0.3824, 1.7302, -1.6464, -3.0991]
- calmar_mean: 3.698886064322168
- hit_rate_mean: 0.4427486691287595
- profit_factor_mean: 3.8192734538633006
- trade_count_total: 244
- aggregate_max_dd: 0.20755654653870376
- worst_fold_max_dd: 0.1068033558459211
- max_position_frac_peak: 0.035970952396414985
- lower_quartile_fold_calmar: -1.3033566403268395
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.288 with no prior kept baseline. Aggregate DD was 20.8%; negative folds were 4/13; trades=244. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3057 (need ≥ 0.20); sub-periods = [+2.153, -0.658]).

---

## Iteration 2026-05-16-4379df5 — REVERTED

**Hypothesis:** A PIT-safe long-term trend-plus-recent-reversal book will improve validation Sortino by buying liquid NSE names with durable positive intermediate momentum only after a short-term pullback, reducing winner-chasing losses in the weak sub-periods that rejected prior pure momentum variants.

**Change:** I replaced selected-count 12-1 momentum sizing with fixed-slot 82% gross sizing across 25 risk slots, removed the forbidden pathlib dependency, enforced active-universe entries, and ranked candidates by nine-month trend, six-week pullback, and downside-volatility penalty.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.1024 >= alpha/N=0.0250) · random_walk_mc(only 89.80% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1794 (need ≥ 0.20); sub-periods = [+3.474, -0.623])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.213210132592711
- validation_folds: 13
- per_fold_sortinos: [-0.4607, -1.3669, -2.8972, 3.2687, 17.4081, 5.5995, 3.0891, 5.0652, 1.5592, -0.241, 2.2147, -2.4615, -2.0055]
- calmar_mean: 1.4282839155852696
- hit_rate_mean: 0.5994913781410566
- profit_factor_mean: 6.061344979535679
- trade_count_total: 391
- aggregate_max_dd: 0.15297904886404246
- worst_fold_max_dd: 0.0885658513497481
- max_position_frac_peak: 0.03472757411543503
- lower_quartile_fold_calmar: -1.5224617168909134
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.213 with no prior kept baseline. Aggregate DD was 15.3%; negative folds were 6/13; trades=391. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.1024 >= alpha/N=0.0250) · random_walk_mc(only 89.80% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1794 (need ≥ 0.20); sub-periods = [+3.474, -0.623]).

---

## Iteration 2026-05-16-0e81479 — REVERTED

**Hypothesis:** A fixed-slot defensive trend strategy that ranks only positive-trend names by low downside volatility and shallow recent drawdown will reduce the weak-subperiod sign flip that rejected prior high-momentum variants.

**Change:** Replaced top-decile 12-1 winner chasing and selected-count sizing with PIT-safe low-downside-volatility trend selection, fixed gross-per-slot sizing, and full-book sector-cap construction so unused slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0200) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4370 (need ≥ 0.20); sub-periods = [+2.492, -1.089])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.3899546484300238
- validation_folds: 13
- per_fold_sortinos: [0.8911, -0.633, -3.6213, 3.9205, 12.5347, 3.7012, 2.6712, 1.8984, 1.0621, -1.2458, -0.0153, -0.5528, -2.5417]
- calmar_mean: 0.8057662308114228
- hit_rate_mean: 0.5459804084804085
- profit_factor_mean: 4.503828988391199
- trade_count_total: 117
- aggregate_max_dd: 0.09724838154776062
- worst_fold_max_dd: 0.057124356869155624
- max_position_frac_peak: 0.04811034385378316
- lower_quartile_fold_calmar: -0.46169709682767124
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.390 with no prior kept baseline. Aggregate DD was 9.7%; negative folds were 6/13; trades=117. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0200) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.4370 (need ≥ 0.20); sub-periods = [+2.492, -1.089]).

---

## Iteration 2026-05-16-f274135 — REVERTED

**Hypothesis:** Replacing winner-chasing momentum with defensive down-market relative strength will improve validation Sortino by keeping exposure in stocks that remain in absolute uptrends while losing less than the liquid universe on market selloff days.

**Change:** I replaced the 12-1 momentum plus quality scaffold with a PIT-safe defensive relative-strength ranker, fixed gross-per-slot sizing, breadth-based gross de-risking, explicit off-book exits, and sector-cap selection without forbidden imports.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0594 (need ≥ 0.20); sub-periods = [+0.873, -0.052])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.5886902690301
- validation_folds: 13
- per_fold_sortinos: [3.9245, -0.5505, -3.4681, 1.2271, 5.1297, 4.2425, 2.5071, -1.9322, -3.2198, -2.3229, -2.3264, 3.8643, 0.5775]
- calmar_mean: 0.1309494459027977
- hit_rate_mean: 0.46144848531726357
- profit_factor_mean: 2.100423874892947
- trade_count_total: 194
- aggregate_max_dd: 0.2008068794357787
- worst_fold_max_dd: 0.07172501271860392
- max_position_frac_peak: 0.05008199047309564
- lower_quartile_fold_calmar: -2.2018356045153564
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.589 with no prior kept baseline. Aggregate DD was 20.1%; negative folds were 6/13; trades=194. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0594 (need ≥ 0.20); sub-periods = [+0.873, -0.052]).

---

## Iteration 2026-05-16-33707f8 — REVERTED

**Hypothesis:** A PIT-safe fixed-slot reversal-with-trend-filter book will improve validation Sortino by buying liquid NSE names that have positive long-term trend but near-term capitulation, avoiding the previously failed winner-chasing momentum family.

**Change:** I replaced pure 12-1 momentum ranking with intermediate-trend plus 10-day pullback reversal scoring, removed forbidden pathlib/fundamental-screen dependencies, enforced PIT universe membership, and sized strictly by fixed risk slots so unused slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.6522 (need ≥ 0.20); sub-periods = [+1.521, -2.513])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.27981789172248367
- validation_folds: 13
- per_fold_sortinos: [-0.2634, 0.3241, -0.9612, 1.3859, 3.2514, 2.0602, 3.4298, 4.0886, 0.3761, -1.9959, -4.334, -3.5554, -0.1685]
- calmar_mean: 0.5621785395397217
- hit_rate_mean: 0.5640425987198485
- profit_factor_mean: 1.9463947688503394
- trade_count_total: 481
- aggregate_max_dd: 0.33410300214405253
- worst_fold_max_dd: 0.1716157258332864
- max_position_frac_peak: 0.05766637837141089
- lower_quartile_fold_calmar: -0.8746177217968603
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.280 with no prior kept baseline. Aggregate DD was 33.4%; negative folds were 6/13; trades=481. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.6522 (need ≥ 0.20); sub-periods = [+1.521, -2.513]).

---

## Iteration 2026-05-16-46cd091 — KEPT

**Hypothesis:** A PIT-strict fixed-slot low-volatility carry book will improve validation Sortino by selecting liquid stocks with positive absolute trend, low realized volatility, and mild recent momentum while eliminating off-universe order calls that caused recent hard rejects.

**Change:** I replaced the quality/pathlib-dependent 12-1 momentum scaffold with a self-contained low-vol trend scorer, fixed-slot sizing, PIT-only order emission, and sector caps so unused slots remain cash and no off-universe ticker is traded.

**Decision:** KEPT — sortino 2.300 > prev None, agg_dd 13.5%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.300137799824258
- validation_folds: 13
- per_fold_sortinos: [0.9605, -0.2451, -2.2078, 3.3114, 8.4794, 6.8408, 3.9823, 4.0077, 2.1785, 0.2396, 2.3435, 2.1551, -2.1442]
- calmar_mean: 5.893461632919962
- hit_rate_mean: 0.5034653727477847
- profit_factor_mean: 9.655897946766926
- trade_count_total: 216
- aggregate_max_dd: 0.1351700873941156
- worst_fold_max_dd: 0.07499475131662524
- max_position_frac_peak: 0.03743669504283939
- lower_quartile_fold_calmar: 0.3745614192048328
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.300 with no prior kept baseline. Aggregate DD was 13.5%; negative folds were 3/13; trades=216. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.300 > prev None, agg_dd 13.5%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-d04afff — REVERTED

**Hypothesis:** Replacing total-volatility carry with downside-risk-adjusted low-vol trend selection will improve validation Sortino by favoring stocks whose realized volatility comes mainly from upside moves while retaining the PIT-safe fixed-slot construction that passed the gates.

**Change:** I changed the scorer to penalize downside semivolatility and recent losing-day frequency instead of treating all volatility equally, while keeping the same universe, rebalance, sector-cap, and fixed-slot sizing contracts.

**Decision:** REVERTED — sortino 2.271 did not improve on prev 2.300137799824258

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2712257064828467
- validation_folds: 13
- per_fold_sortinos: [1.3072, -0.2372, -2.2867, 2.6748, 7.2456, 6.168, 4.1299, 3.9276, 2.2547, 0.6059, 2.1134, 2.4926, -0.8699]
- calmar_mean: 5.1603722278884145
- hit_rate_mean: 0.5260658272821883
- profit_factor_mean: 12.602526460785286
- trade_count_total: 213
- aggregate_max_dd: 0.13820955252153636
- worst_fold_max_dd: 0.07713044557214493
- max_position_frac_peak: 0.03761862663919408
- lower_quartile_fold_calmar: 1.2336853811531694
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.300 to 2.271 (-0.029). Aggregate DD was 13.8% versus previous kept 13.5%; negative folds were 3/13; trades=213. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.271 did not improve on prev 2.300137799824258.

---

## Iteration 2026-05-16-c05528b — REVERTED

**Hypothesis:** Adding incumbent retention inside the existing low-volatility trend book will improve validation Sortino by reducing DP-cost turnover while preserving the same PIT universe, fixed-slot sizing, and sector-cap construction.

**Change:** I changed selection to keep currently held names that still pass the low-vol trend filter before filling remaining slots from the ranked list, so the strategy trades less without adding new exposed hyperparameters.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1701 (need ≥ 0.20); sub-periods = [+4.579, +0.779])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.409991783517332
- validation_folds: 13
- per_fold_sortinos: [2.5416, -0.0715, -2.1296, 5.9717, 14.9331, 9.1017, 4.7784, 3.9037, 2.1844, 0.6141, 1.9199, 1.3313, -0.749]
- calmar_mean: 4.220219494599306
- hit_rate_mean: 0.6500999000999
- profit_factor_mean: 3.9525301256560104
- trade_count_total: 76
- aggregate_max_dd: 0.12970980301474927
- worst_fold_max_dd: 0.1002012484148835
- max_position_frac_peak: 0.051505477085244285
- lower_quartile_fold_calmar: 1.3556386417163773
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.300 to 3.410 (+1.110). Aggregate DD was 13.0% versus previous kept 13.5%; negative folds were 3/13; trades=76. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1701 (need ≥ 0.20); sub-periods = [+4.579, +0.779]).

---

## Iteration 2026-05-16-f0f8971 — REVERTED

**Hypothesis:** A bounded hysteresis version of the kept low-vol trend book will improve validation Sortino by capturing most of the turnover reduction from incumbent retention while forcing stale holdings back through a rank and score floor so the weak later sub-period does not get diluted by over-held names.

**Change:** I added score-aware incumbent hysteresis that retains current holdings only if they remain PIT-eligible, still pass the low-vol trend scorer, and rank within a modest buffer ahead of new candidates, preserving fixed-slot sizing and sector caps.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1872 (need ≥ 0.20); sub-periods = [+3.315, +0.621])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.486147623361999
- validation_folds: 13
- per_fold_sortinos: [2.5347, -0.9766, -3.103, 3.4609, 12.8094, 5.7812, 3.5845, 3.9741, 1.7723, -0.0149, 1.3683, 2.0834, -0.9545]
- calmar_mean: 4.962513231338374
- hit_rate_mean: 0.6419725573571728
- profit_factor_mean: 4.100769536840994
- trade_count_total: 113
- aggregate_max_dd: 0.16346143742738592
- worst_fold_max_dd: 0.09785084234583012
- max_position_frac_peak: 0.037614434466299154
- lower_quartile_fold_calmar: -0.22442120618662684
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.300 to 2.486 (+0.186). Aggregate DD was 16.3% versus previous kept 13.5%; negative folds were 4/13; trades=113. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1872 (need ≥ 0.20); sub-periods = [+3.315, +0.621]).

---

## Iteration 2026-05-16-2c80c39 — KEPT

**Hypothesis:** Adding a cross-sectional defensive relative-strength term to the kept low-volatility trend book will improve validation Sortino by preferring positive-trend stocks that outperform the liquid PIT universe during weak recent market days, without changing turnover mechanics or fixed-slot sizing.

**Change:** I kept the PIT-safe low-volatility trend framework but added a universe-relative defensive score computed from recent down-market sessions so selection favors names with both absolute trend and lower downside participation.

**Decision:** KEPT — sortino 2.443 > prev 2.300137799824258, agg_dd 11.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.442697150351653
- validation_folds: 13
- per_fold_sortinos: [1.0208, 0.5187, -1.4344, 4.1303, 7.7206, 6.3566, 4.0076, 3.8785, 2.3988, 0.54, 1.882, 1.9235, -1.188]
- calmar_mean: 6.108321521134618
- hit_rate_mean: 0.487334403906802
- profit_factor_mean: 10.508992934189886
- trade_count_total: 157
- aggregate_max_dd: 0.11282995639016376
- worst_fold_max_dd: 0.0969699673578185
- max_position_frac_peak: 0.05173635002892044
- lower_quartile_fold_calmar: 1.2729208992000423
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.300 to 2.443 (+0.143). Aggregate DD was 11.3% versus previous kept 13.5%; negative folds were 2/13; trades=157. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.443 > prev 2.300137799824258, agg_dd 11.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-5d4d474 — REVERTED

**Hypothesis:** Adding a stock-specific downside capture penalty to the kept defensive low-volatility trend book will improve validation Sortino by avoiding names that still fall sharply on weak market days even when their average relative strength looks acceptable.

**Change:** I extended the existing down-market relative-strength calculation to include downside capture and penalized high-capture candidates in the scorer while preserving PIT universe filtering, fixed-slot sizing, biweekly rebalancing, and the 25% sector cap.

**Decision:** REVERTED — sortino 2.315 did not improve on prev 2.442697150351653

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.31450499568359
- validation_folds: 13
- per_fold_sortinos: [1.0876, 0.2791, -1.688, 3.7283, 7.3383, 6.308, 4.0012, 3.9355, 2.2482, 0.722, 1.834, 1.585, -1.2906]
- calmar_mean: 5.756364802943365
- hit_rate_mean: 0.4870301763014313
- profit_factor_mean: 6.455665918833829
- trade_count_total: 168
- aggregate_max_dd: 0.12158168923775926
- worst_fold_max_dd: 0.10071528407608109
- max_position_frac_peak: 0.05167173271540293
- lower_quartile_fold_calmar: 1.7979871182060123
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.443 to 2.315 (-0.128). Aggregate DD was 12.2% versus previous kept 11.3%; negative folds were 2/13; trades=168. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.315 did not improve on prev 2.442697150351653.

---

## Iteration 2026-05-16-4e044b9 — KEPT

**Hypothesis:** Adding a PIT-safe cross-sectional trend-breadth gate will improve validation Sortino by keeping the defensive low-volatility book invested when many liquid names qualify and automatically holding more cash when the opportunity set is thin.

**Change:** I changed selection to require a minimum ranked-candidate breadth before filling the fixed slots, using existing parameters so weak-market filters leave capital in cash without changing per-position sizing.

**Decision:** KEPT — sortino 2.453 > prev 2.442697150351653, agg_dd 11.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.453167311281237
- validation_folds: 13
- per_fold_sortinos: [1.1146, 0.5553, -1.4856, 4.1896, 7.7206, 6.3566, 4.0076, 3.8785, 2.3988, 0.54, 1.882, 1.9174, -1.1842]
- calmar_mean: 6.128424439192282
- hit_rate_mean: 0.487334403906802
- profit_factor_mean: 10.518089567500917
- trade_count_total: 157
- aggregate_max_dd: 0.11277254976556383
- worst_fold_max_dd: 0.09689754729864211
- max_position_frac_peak: 0.05173635002892044
- lower_quartile_fold_calmar: 1.2729208992000423
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.443 to 2.453 (+0.010). Aggregate DD was 11.3% versus previous kept 11.3%; negative folds were 2/13; trades=157. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.453 > prev 2.442697150351653, agg_dd 11.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-e61876f — KEPT

**Hypothesis:** Adding a PIT-safe trend-persistence term will improve validation Sortino by favoring stocks whose intermediate uptrend is built across multiple recent legs rather than one noisy jump, while preserving the kept defensive low-volatility construction.

**Change:** I added a multi-segment trend persistence scorer and a mild choppiness rejection inside the existing fixed-slot low-vol defensive ranking so selection prefers steadier trends without changing rebalance cadence, sizing, universe filtering, or sector caps.

**Decision:** KEPT — sortino 2.622 > prev 2.453167311281237, agg_dd 11.7%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.622326027486962
- validation_folds: 13
- per_fold_sortinos: [1.2091, 0.6032, -1.4789, 4.1896, 8.0178, 6.6497, 4.4499, 4.1487, 2.5153, 1.1231, 1.9903, 1.9082, -1.2356]
- calmar_mean: 6.540782394279262
- hit_rate_mean: 0.5481967253460466
- profit_factor_mean: 12.293469892056804
- trade_count_total: 153
- aggregate_max_dd: 0.117327930332949
- worst_fold_max_dd: 0.09750157367736607
- max_position_frac_peak: 0.0517795203579806
- lower_quartile_fold_calmar: 2.2274429325453626
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.453 to 2.622 (+0.169). Aggregate DD was 11.7% versus previous kept 11.3%; negative folds were 2/13; trades=153. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.622 > prev 2.453167311281237, agg_dd 11.7%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-87be2d3 — REVERTED

**Hypothesis:** Adding a path-efficiency quality term will improve validation Sortino by preferring positive-trend stocks whose gains were achieved with smoother daily progress rather than noisy two-way churn.

**Change:** I added a PIT-safe trend-efficiency scorer using existing trend-window returns, lightly rewarded efficient uptrends, and filtered extremely inefficient trends while preserving fixed-slot sizing, biweekly rebalancing, universe filtering, and sector caps.

**Decision:** REVERTED — sortino 2.512 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5124057519394247
- validation_folds: 13
- per_fold_sortinos: [1.2323, 0.6031, -1.4783, 4.1889, 7.6815, 6.301, 4.4447, 4.1145, 2.5391, 1.1628, 1.6843, 1.3438, -1.1566]
- calmar_mean: 6.118737421159365
- hit_rate_mean: 0.5163875089214455
- profit_factor_mean: 5.318496122260597
- trade_count_total: 154
- aggregate_max_dd: 0.12282510792311421
- worst_fold_max_dd: 0.10433675749191
- max_position_frac_peak: 0.05190773311401055
- lower_quartile_fold_calmar: 1.4733620394672513
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.512 (-0.110). Aggregate DD was 12.3% versus previous kept 11.7%; negative folds were 2/13; trades=154. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.512 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-0956b17 — REVERTED

**Hypothesis:** Adding a no-new-parameter market breadth exposure throttle will improve validation Sortino by retaining the kept stock ranking while cutting gross exposure only when the PIT opportunity set is barely above the existing breadth floor.

**Change:** I made target exposure depend on ranked-candidate breadth, so thin-but-tradable rebalance days use partial gross while broad opportunity sets keep the current 90% gross and all sizing remains fixed-slot based.

**Decision:** REVERTED — sortino 2.622 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.622326027486962
- validation_folds: 13
- per_fold_sortinos: [1.2091, 0.6032, -1.4789, 4.1896, 8.0178, 6.6497, 4.4499, 4.1487, 2.5153, 1.1231, 1.9903, 1.9082, -1.2356]
- calmar_mean: 6.540782394279262
- hit_rate_mean: 0.5481967253460466
- profit_factor_mean: 12.293469892056804
- trade_count_total: 153
- aggregate_max_dd: 0.117327930332949
- worst_fold_max_dd: 0.09750157367736607
- max_position_frac_peak: 0.0517795203579806
- lower_quartile_fold_calmar: 2.2274429325453626
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.622 (+0.000). Aggregate DD was 11.7% versus previous kept 11.7%; negative folds were 2/13; trades=153. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.622 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-ed59182 — REVERTED

**Hypothesis:** Adding a late-stage overextension guard will improve validation Sortino by keeping the persistent low-volatility trend book from buying names whose 21-day move has already become a short-term blow-off.

**Change:** I capped the contribution of recent momentum and rejected extreme recent extensions relative to the longer trend, preserving PIT filtering, fixed-slot sizing, biweekly cadence, and sector caps.

**Decision:** REVERTED — sortino 2.558 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5581285105098512
- validation_folds: 13
- per_fold_sortinos: [1.2362, 0.5634, -1.4783, 4.1889, 7.6815, 6.301, 4.4447, 4.1145, 2.5391, 1.1307, 1.8249, 1.9082, -1.199]
- calmar_mean: 6.21624261754215
- hit_rate_mean: 0.5262046148923976
- profit_factor_mean: 7.295844541266126
- trade_count_total: 153
- aggregate_max_dd: 0.11835886239226545
- worst_fold_max_dd: 0.09750157367736607
- max_position_frac_peak: 0.05162328793954709
- lower_quartile_fold_calmar: 2.2712234819791366
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.558 (-0.064). Aggregate DD was 11.8% versus previous kept 11.7%; negative folds were 2/13; trades=153. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.558 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-f675e52 — REVERTED

**Hypothesis:** Adding a cross-sectional median-relative trend term will improve validation Sortino by preferring low-volatility persistent uptrends that are also outperforming the current PIT liquid universe, without adding new hyperparameters or changing fixed-slot sizing.

**Change:** I added PIT-safe market-relative trend and recent return context from the active universe and lightly rewarded stocks with positive excess intermediate trend while preserving the kept defensive low-volatility persistence construction.

**Decision:** REVERTED — sortino 2.592 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5920505953200927
- validation_folds: 13
- per_fold_sortinos: [1.2362, 0.5634, -1.4783, 4.1889, 8.0178, 6.649, 4.4498, 4.1487, 2.5153, 1.1545, 1.8711, 1.6157, -1.2356]
- calmar_mean: 6.461206879013504
- hit_rate_mean: 0.5482415523139504
- profit_factor_mean: 11.81856961158141
- trade_count_total: 156
- aggregate_max_dd: 0.12198517277780663
- worst_fold_max_dd: 0.10174801046610864
- max_position_frac_peak: 0.0517795203579806
- lower_quartile_fold_calmar: 1.8812876744272047
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.592 (-0.030). Aggregate DD was 12.2% versus previous kept 11.7%; negative folds were 2/13; trades=156. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.592 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-443eebc — REVERTED

**Hypothesis:** Adding a no-new-parameter intraday range-risk penalty will improve validation Sortino by avoiding fragile low-close-volatility uptrends whose hidden high-low/gap volatility is more likely to produce downside shocks after costs.

**Change:** I added a PIT-safe true-range risk scorer over the existing volatility window, reject extreme range-risk names, and penalize range risk in the existing fixed-slot defensive trend ranking while preserving universe, sector-cap, biweekly rebalance, and order_target_percent-only sizing.

**Decision:** REVERTED — sortino 2.567 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5669852130945463
- validation_folds: 13
- per_fold_sortinos: [1.3639, 0.645, -1.6287, 4.2435, 7.6813, 6.3099, 4.4948, 4.1606, 2.4627, 0.8845, 1.8544, 1.6242, -0.7253]
- calmar_mean: 6.155435456280178
- hit_rate_mean: 0.5354120740998568
- profit_factor_mean: 5.390546288064362
- trade_count_total: 155
- aggregate_max_dd: 0.11354020634894656
- worst_fold_max_dd: 0.10023415246133957
- max_position_frac_peak: 0.05201452818970178
- lower_quartile_fold_calmar: 1.8667375347737465
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.567 (-0.055). Aggregate DD was 11.4% versus previous kept 11.7%; negative folds were 2/13; trades=155. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.567 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-0be2772 — REVERTED

**Hypothesis:** A no-new-data liquidity-confirmation term will improve validation Sortino by preferring low-volatility persistent uptrends whose recent gains are supported by rising traded volume rather than thin price drift.

**Change:** I added a PIT-safe relative volume score using existing OHLCV bars, lightly rewarded volume-confirmed trends, and filtered extreme recent volume droughts while preserving fixed-slot sizing, biweekly rebalance, universe filtering, and sector caps.

**Decision:** REVERTED — sortino 2.113 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.112699935207194
- validation_folds: 13
- per_fold_sortinos: [1.3157, 1.3762, -0.5129, 3.2534, 5.967, 5.3635, 3.1018, 2.2409, 1.7854, 0.4626, 1.3125, 1.5349, 0.2641]
- calmar_mean: 4.046093872219538
- hit_rate_mean: 0.49294613360760065
- profit_factor_mean: 2.031813627066274
- trade_count_total: 181
- aggregate_max_dd: 0.10401616867658177
- worst_fold_max_dd: 0.09899941607704243
- max_position_frac_peak: 0.05174988423741381
- lower_quartile_fold_calmar: 1.608153504097266
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.113 (-0.510). Aggregate DD was 10.4% versus previous kept 11.7%; negative folds were 1/13; trades=181. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.113 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-ef270e5 — REVERTED

**Hypothesis:** Adding a no-new-parameter incumbent score buffer will improve validation Sortino by reducing marginal biweekly turnover in the kept defensive trend book while still forcing held names through the same PIT universe, trend, risk, breadth, sector-cap, and fixed-slot constraints.

**Change:** I added a small incumbent bonus only during ranking so existing holdings have to remain fundamentally qualified but are less likely to be displaced by near-tie candidates, targeting DP-cost and churn drag without changing position count, gross exposure, cadence, or selection filters.

**Decision:** REVERTED — sortino 2.543 did not improve on prev 2.622326027486962

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5426836450358454
- validation_folds: 13
- per_fold_sortinos: [1.2136, 0.6032, -1.4789, 4.1896, 7.6814, 6.3015, 4.4447, 4.1145, 2.5391, 1.1307, 1.7546, 1.7963, -1.2353]
- calmar_mean: 6.189999978474575
- hit_rate_mean: 0.5238377509870722
- profit_factor_mean: 6.685679756146519
- trade_count_total: 152
- aggregate_max_dd: 0.11761957315855116
- worst_fold_max_dd: 0.09792778395634075
- max_position_frac_peak: 0.051645165462496326
- lower_quartile_fold_calmar: 2.232098237130038
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.543 (-0.080). Aggregate DD was 11.8% versus previous kept 11.7%; negative folds were 2/13; trades=152. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.543 did not improve on prev 2.622326027486962.

---

## Iteration 2026-05-16-7af92b9 — KEPT

**Hypothesis:** Adding a PIT-safe short-term mean-reversion qualifier to the existing persistent low-volatility trend book will improve validation Sortino by avoiding fresh entries that are extended above their own recent average while still retaining durable intermediate uptrends.

**Change:** I added a no-new-parameter moving-average distance term that rewards modest pullbacks within positive trends and filters only extreme near-term extensions, preserving fixed-slot sizing, sector caps, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** KEPT — sortino 2.754 > prev 2.622326027486962, agg_dd 10.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.754021639889776
- validation_folds: 13
- per_fold_sortinos: [1.0087, 0.2498, -1.4594, 4.3873, 8.5929, 6.3825, 5.3526, 4.9562, 2.8206, 0.4138, 1.8661, 1.6937, -0.4626]
- calmar_mean: 6.088612214405485
- hit_rate_mean: 0.5153541468586718
- profit_factor_mean: 7.80321803971302
- trade_count_total: 174
- aggregate_max_dd: 0.10319289101471445
- worst_fold_max_dd: 0.08831124654550537
- max_position_frac_peak: 0.051145423598898905
- lower_quartile_fold_calmar: 0.721942262761293
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.622 to 2.754 (+0.132). Aggregate DD was 10.3% versus previous kept 11.7%; negative folds were 2/13; trades=174. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.754 > prev 2.622326027486962, agg_dd 10.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-cbce9cd — REVERTED

**Hypothesis:** A PIT-safe macro-regime exposure brake will improve validation Sortino by keeping the current defensive pullback book unchanged in normal regimes while cutting gross exposure during India macro shock/risk-off states that disproportionately drive downside volatility.

**Change:** I imported macro_regime and added a rebalance-date gross exposure multiplier that halves fixed-slot exposure in risk_off and exits to cash in shock, preserving ranking, PIT universe enforcement, sector caps, and order_target_percent-only sizing.

**Decision:** REVERTED — sortino 2.746 did not improve on prev 2.754021639889776

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.745661604414121
- validation_folds: 13
- per_fold_sortinos: [1.0089, 0.2531, -1.3059, 4.4972, 8.5931, 6.315, 5.2776, 4.9355, 2.8231, 0.2166, 2.3967, 1.6852, -1.0025]
- calmar_mean: 5.970386632143898
- hit_rate_mean: 0.4886735436509191
- profit_factor_mean: 7.530936255856753
- trade_count_total: 169
- aggregate_max_dd: 0.10312578186124893
- worst_fold_max_dd: 0.08810226450221666
- max_position_frac_peak: 0.05159974028810194
- lower_quartile_fold_calmar: 0.20420316117876516
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.746 (-0.008). Aggregate DD was 10.3% versus previous kept 10.3%; negative folds were 2/13; trades=169. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.746 did not improve on prev 2.754021639889776.

---

## Iteration 2026-05-16-c8db88d — REVERTED

**Hypothesis:** Adding a PIT-safe long-horizon trend anchor will improve validation Sortino by keeping the current defensive pullback book out of short-lived 126-day rebounds that lack a durable 12-month uptrend.

**Change:** I added a no-new-parameter 252-day trend confirmation and a lightly weighted long-trend score term, preserving fixed-slot sizing, sector caps, PIT universe filtering, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.112 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1167 (need ≥ 0.20); sub-periods = [+3.217, -0.375])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.1118836684816413
- validation_folds: 13
- per_fold_sortinos: [1.1583, 0.161, -1.6051, 3.2888, 8.3105, 4.0821, 5.645, 4.8128, 3.1024, 0.3677, 1.2286, -0.1213, -2.9763]
- calmar_mean: 3.4923006358413082
- hit_rate_mean: 0.4832499702409204
- profit_factor_mean: 2.749346823637233
- trade_count_total: 172
- aggregate_max_dd: 0.11174093694984485
- worst_fold_max_dd: 0.08012884722010094
- max_position_frac_peak: 0.05206215990821996
- lower_quartile_fold_calmar: 0.0979787824799677
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.112 (-0.642). Aggregate DD was 11.2% versus previous kept 10.3%; negative folds were 3/13; trades=172. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.112 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1167 (need ≥ 0.20); sub-periods = [+3.217, -0.375]).

---

## Iteration 2026-05-16-16d6cd5 — REVERTED

**Hypothesis:** Adding a PIT-safe recent downside-asymmetry penalty will improve validation Sortino by avoiding low-volatility trend names whose last-month returns contain clustered downside shocks despite still passing the current trend and pullback filters.

**Change:** I added a no-new-parameter downside-cluster score from existing 21-day returns and lightly penalized names with repeated negative days, preserving PIT universe, fixed-slot sizing, sector caps, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.685 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1806 (need ≥ 0.20); sub-periods = [+3.591, +0.648])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6853370408047423
- validation_folds: 13
- per_fold_sortinos: [0.9648, -0.0265, -1.746, 4.3173, 8.4856, 6.1026, 5.5017, 5.7689, 2.9477, 0.4747, 1.9129, 0.6615, -0.4558]
- calmar_mean: 6.278952559433628
- hit_rate_mean: 0.5119088741826299
- profit_factor_mean: 6.568341232495221
- trade_count_total: 178
- aggregate_max_dd: 0.11631631838858461
- worst_fold_max_dd: 0.0905178131984517
- max_position_frac_peak: 0.051387906128825114
- lower_quartile_fold_calmar: 0.7755712020555005
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.685 (-0.069). Aggregate DD was 11.6% versus previous kept 10.3%; negative folds were 3/13; trades=178. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.685 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1806 (need ≥ 0.20); sub-periods = [+3.591, +0.648]).

---

## Iteration 2026-05-16-6a80518 — REVERTED

**Hypothesis:** Adding a PIT-safe overnight gap-risk penalty will improve validation Sortino by avoiding low-volatility uptrends whose close-to-close smoothness hides repeated adverse open gaps, which are especially costly because CNC rebalances fill at next open.

**Change:** I added a no-new-parameter recent gap-risk score from existing OHLC data and lightly penalized adverse overnight gap behavior while preserving fixed-slot sizing, PIT universe enforcement, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 1.750 did not improve on prev 2.754021639889776 | aggregate DD regressed: 45.8% > prev 10.3% + 10pp tolerance | catastrophe: gross exposure: max 164.1% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0750 >= alpha/N=0.0250) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5380 (need ≥ 0.20); sub-periods = [+3.322, -1.787])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.7499970813675003
- validation_folds: 13
- per_fold_sortinos: [1.0156, -0.0713, -1.7473, 4.3074, 8.4953, 5.798, 4.2132, 4.2455, 3.6424, -0.4618, -3.2724, -2.1324, -1.2824]
- calmar_mean: 4.647478498921201
- hit_rate_mean: 0.5223027161375577
- profit_factor_mean: 6.091665249617782
- trade_count_total: 182
- aggregate_max_dd: 0.4580809729620269
- worst_fold_max_dd: 0.28921257515755444
- max_position_frac_peak: 0.07333655441368499
- lower_quartile_fold_calmar: -0.8033146476603803
- n_negative_folds: 6/13
- risk.passed: False
- risk.violations: ['gross exposure: max 164.1% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 2.754 to 1.750 (-1.004). Aggregate DD was 45.8% versus previous kept 10.3%; negative folds were 6/13; trades=182. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 1.750 did not improve on prev 2.754021639889776 | aggregate DD regressed: 45.8% > prev 10.3% + 10pp tolerance | catastrophe: gross exposure: max 164.1% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0750 >= alpha/N=0.0250) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5380 (need ≥ 0.20); sub-periods = [+3.322, -1.787]).

---

## Iteration 2026-05-16-af80b47 — REVERTED

**Hypothesis:** Adding a PIT-safe cross-stock diversification penalty during selection will improve validation Sortino by reducing hidden same-trade clustering beyond the existing sector cap while preserving the kept low-volatility pullback ranking.

**Change:** I changed only the portfolio construction step to prefer high-ranked candidates whose recent returns are less correlated with already selected names, so fixed slots remain diversified without changing sizing, cadence, PIT universe handling, or signal data.

**Decision:** REVERTED — sortino 2.729 did not improve on prev 2.754021639889776

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7293556652197983
- validation_folds: 13
- per_fold_sortinos: [0.9648, 0.2526, -1.4607, 4.3524, 8.5622, 6.3446, 5.3526, 4.9562, 2.8206, 0.4138, 1.8661, 1.5134, -0.457]
- calmar_mean: 6.052289911317885
- hit_rate_mean: 0.5133430860240815
- profit_factor_mean: 7.7288867371980325
- trade_count_total: 175
- aggregate_max_dd: 0.10319289101471445
- worst_fold_max_dd: 0.08831124654550537
- max_position_frac_peak: 0.05123207190444486
- lower_quartile_fold_calmar: 0.721942262761293
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.729 (-0.025). Aggregate DD was 10.3% versus previous kept 10.3%; negative folds were 2/13; trades=175. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.729 did not improve on prev 2.754021639889776.

---

## Iteration 2026-05-16-6b0fc03 — REVERTED

**Hypothesis:** Adding a PIT-safe market-downside-beta penalty will improve validation Sortino by avoiding stocks whose recent returns are most exposed on broad weak days while preserving the existing low-volatility pullback trend thesis.

**Change:** I added a no-new-parameter downside-beta score derived from the same recent PIT market-return window and penalized high weak-day beta in ranking while leaving universe filtering, fixed-slot sizing, sector caps, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1650 (need ≥ 0.20); sub-periods = [+3.833, +0.632])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.8484327585099716
- validation_folds: 13
- per_fold_sortinos: [1.3396, 0.9454, -1.3783, 5.0173, 9.4173, 6.4583, 4.9259, 5.0529, 2.7212, 0.3319, 1.9208, 1.1881, -0.9109]
- calmar_mean: 6.279400294396682
- hit_rate_mean: 0.5302385648539496
- profit_factor_mean: 8.035607406236407
- trade_count_total: 171
- aggregate_max_dd: 0.11021150294113934
- worst_fold_max_dd: 0.08724882638089783
- max_position_frac_peak: 0.05075847197688741
- lower_quartile_fold_calmar: 1.046369010191462
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.848 (+0.094). Aggregate DD was 11.0% versus previous kept 10.3%; negative folds were 2/13; trades=171. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1650 (need ≥ 0.20); sub-periods = [+3.833, +0.632]).

---

## Iteration 2026-05-16-c296801 — REVERTED

**Hypothesis:** Adding a PIT-safe crash-recovery quality term will improve validation Sortino by favoring trend candidates that have recently recovered from drawdowns without relying on high downside beta or broad-market timing.

**Change:** I added a no-new-parameter recovery-efficiency score from the existing max-drawdown window and blended it into ranking to prefer resilient pullback recoveries while preserving fixed-slot sizing, sector caps, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.681 did not improve on prev 2.754021639889776

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.680631537700281
- validation_folds: 13
- per_fold_sortinos: [1.0156, 0.2599, -1.8173, 3.9181, 8.4853, 6.3552, 5.3779, 4.9214, 2.8206, 0.4138, 1.8661, 1.6937, -0.4621]
- calmar_mean: 5.9821756267994886
- hit_rate_mean: 0.5151790768306606
- profit_factor_mean: 7.731631864746049
- trade_count_total: 173
- aggregate_max_dd: 0.11708127234479175
- worst_fold_max_dd: 0.08831124654550537
- max_position_frac_peak: 0.05156587737869118
- lower_quartile_fold_calmar: 0.721942262761293
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.681 (-0.073). Aggregate DD was 11.7% versus previous kept 10.3%; negative folds were 2/13; trades=173. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.681 did not improve on prev 2.754021639889776.

---

## Iteration 2026-05-17-73e481d — REVERTED

**Hypothesis:** Adding a PIT-safe turnover-aware incumbent retention band will improve validation Sortino by reducing cost drag and unnecessary churn while only retaining held names that still satisfy the same trend, pullback, volatility, and universe constraints.

**Change:** I added an incumbent-aware selection pass that reserves a small rank buffer for currently held qualifying names before filling remaining slots by score, preserving fixed-slot sizing, the sector cap, PIT universe filtering, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.549 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1198 (need ≥ 0.20); sub-periods = [+3.495, +0.419])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.548787174672354
- validation_folds: 13
- per_fold_sortinos: [2.4976, 0.179, -1.3563, 4.5022, 10.7017, 4.6582, 3.0598, 4.7373, 2.4797, -0.0693, 0.8313, 0.4982, 0.4148]
- calmar_mean: 5.596867314246866
- hit_rate_mean: 0.5390831390831391
- profit_factor_mean: 5.333296653869302
- trade_count_total: 95
- aggregate_max_dd: 0.1385964521033646
- worst_fold_max_dd: 0.10174676439226024
- max_position_frac_peak: 0.06940331449884656
- lower_quartile_fold_calmar: 0.3733037598137194
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.549 (-0.205). Aggregate DD was 13.9% versus previous kept 10.3%; negative folds were 2/13; trades=95. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.549 did not improve on prev 2.754021639889776 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1198 (need ≥ 0.20); sub-periods = [+3.495, +0.419]).

---

## Iteration 2026-05-17-8010db2 — KEPT

**Hypothesis:** Adding a PIT-safe intermediate-trend confirmation will improve validation Sortino by removing stale 126-day winners whose most recent 63-day path has already rolled over, while preserving the kept low-volatility pullback ranking.

**Change:** I required the existing 63-day lookback return to be positive before a ticker can be ranked, using the already-present vol_days horizon so the book avoids fading trends without changing sizing, cadence, sector caps, or the order_target_percent-only contract.

**Decision:** KEPT — sortino 2.917 > prev 2.754021639889776, agg_dd 10.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.917301771816021
- validation_folds: 13
- per_fold_sortinos: [0.9663, 0.254, -0.9872, 4.6016, 8.7425, 7.1583, 5.8965, 5.016, 2.7056, 0.4846, 1.8647, 1.6846, -0.4626]
- calmar_mean: 5.794404386472798
- hit_rate_mean: 0.5261123868589931
- profit_factor_mean: 6.289285683999885
- trade_count_total: 176
- aggregate_max_dd: 0.10284383692506154
- worst_fold_max_dd: 0.0903523374819925
- max_position_frac_peak: 0.0522533700788161
- lower_quartile_fold_calmar: 0.9199305420789948
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.754 to 2.917 (+0.163). Aggregate DD was 10.3% versus previous kept 10.3%; negative folds were 2/13; trades=176. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.917 > prev 2.754021639889776, agg_dd 10.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-c349e61 — REVERTED

**Hypothesis:** Adding a PIT-safe short-term damage guard will improve validation Sortino by keeping the low-volatility trend book from buying names whose current pullback is a sharp recent breakdown rather than a mild mean-reversion entry.

**Change:** I added a no-new-parameter 21-day current drawdown check using the existing recent_days window, rejecting candidates more than 12% below their recent high while preserving the kept ranking, fixed-slot sizing, sector cap, PIT universe enforcement, and order_target_percent-only contract.

**Decision:** REVERTED — sortino 2.480 did not improve on prev 2.917301771816021

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.480038697619526
- validation_folds: 13
- per_fold_sortinos: [1.0864, -0.3021, -1.4445, 4.7693, 8.73, 5.4275, 3.3099, 4.0799, 2.4718, 0.5648, 1.7165, 2.4456, -0.6145]
- calmar_mean: 5.271195171120935
- hit_rate_mean: 0.5020329029944415
- profit_factor_mean: 4.935317025405898
- trade_count_total: 188
- aggregate_max_dd: 0.12857145160722971
- worst_fold_max_dd: 0.08785293631377954
- max_position_frac_peak: 0.07290922390876751
- lower_quartile_fold_calmar: 1.1161084134382897
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.917 to 2.480 (-0.437). Aggregate DD was 12.9% versus previous kept 10.3%; negative folds were 3/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.480 did not improve on prev 2.917301771816021.

---

## Iteration 2026-05-17-99dd244 — REVERTED

**Hypothesis:** Raising fixed risk slots from 18 to 20 will improve validation Sortino by reducing concentration-driven downside in weaker folds while preserving the kept PIT-safe ranking, cadence, sector cap, and gross exposure.

**Change:** I changed only n_positions from 18 to 20 so each selected name targets 4.5% instead of 5.0%, leaving unfilled or sector-blocked slots as cash under the existing fixed-slot sizing contract.

**Decision:** REVERTED — sortino 2.333 did not improve on prev 2.917301771816021

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.3333857990767877
- validation_folds: 13
- per_fold_sortinos: [0.3206, -0.6449, -2.1864, 3.785, 9.0783, 5.5106, 4.3623, 4.213, 2.2993, 0.5493, 1.7934, 1.6758, -0.4222]
- calmar_mean: 4.4602153310723
- hit_rate_mean: 0.5070620674871686
- profit_factor_mean: 4.053626390984514
- trade_count_total: 204
- aggregate_max_dd: 0.13054675135740987
- worst_fold_max_dd: 0.08736018016014678
- max_position_frac_peak: 0.04718599930677107
- lower_quartile_fold_calmar: 0.4853960923719036
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.917 to 2.333 (-0.584). Aggregate DD was 13.1% versus previous kept 10.3%; negative folds were 3/13; trades=204. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.333 did not improve on prev 2.917301771816021.

---

## Iteration 2026-05-17-9cbdf72 — KEPT

**Hypothesis:** Adding a PIT-safe five-day exhaustion penalty will improve validation Sortino by avoiding low-volatility intermediate uptrends that have just made a sharp one-week sprint and are more likely to mean-revert after entry.

**Change:** I added a no-new-parameter short-horizon return check derived from recent_days, lightly penalizing very strong last-week moves in the ranking while preserving all universe, fixed-slot sizing, sector cap, and order_target_percent-only constraints.

**Decision:** KEPT — sortino 3.105 > prev 2.917301771816021, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.104746404728241
- validation_folds: 13
- per_fold_sortinos: [3.6955, 0.3038, -1.0096, 4.4874, 8.6624, 6.8839, 5.7367, 5.0165, 2.669, 0.5512, 2.0011, 1.8138, -0.4501]
- calmar_mean: 5.9198451902319595
- hit_rate_mean: 0.5280149337841645
- profit_factor_mean: 5.182974787517902
- trade_count_total: 178
- aggregate_max_dd: 0.10394286477902075
- worst_fold_max_dd: 0.09112622188833276
- max_position_frac_peak: 0.051943429391906
- lower_quartile_fold_calmar: 1.0618749968035892
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.917 to 3.105 (+0.187). Aggregate DD was 10.4% versus previous kept 10.3%; negative folds were 2/13; trades=178. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.105 > prev 2.917301771816021, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-ae9eed8 — REVERTED

**Hypothesis:** Adding a PIT-safe one-week cooling bonus will improve validation Sortino by preferring persistent intermediate uptrends that have paused mildly rather than chased or broken down.

**Change:** I added a no-new-parameter fast-pullback quality term centered on a mild one-week dip while keeping the existing exhaustion penalty, universe enforcement, fixed-slot sizing, sector cap, and order_target_percent-only contract unchanged.

**Decision:** REVERTED — sortino 3.022 did not improve on prev 3.104746404728241

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0221745714129824
- validation_folds: 13
- per_fold_sortinos: [4.0275, -0.0302, -1.305, 4.5906, 8.8307, 6.4967, 5.4628, 4.9278, 2.6307, 0.452, 1.8509, 1.8107, -0.457]
- calmar_mean: 5.971657105068022
- hit_rate_mean: 0.5334430275606746
- profit_factor_mean: 6.600412708490394
- trade_count_total: 179
- aggregate_max_dd: 0.11167681440326849
- worst_fold_max_dd: 0.09053100146341213
- max_position_frac_peak: 0.05206448366251404
- lower_quartile_fold_calmar: 0.8371993008608819
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.105 to 3.022 (-0.083). Aggregate DD was 11.2% versus previous kept 10.4%; negative folds were 3/13; trades=179. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.022 did not improve on prev 3.104746404728241.

---

## Iteration 2026-05-17-a47fc2b — KEPT

**Hypothesis:** Adding a PIT-safe trend-efficiency quality term will improve validation Sortino by preferring persistent uptrends that advance with less two-way churn, without changing exposure, cadence, universe enforcement, or risk-slot sizing.

**Change:** I added a no-new-parameter 63-day efficiency ratio to the ranking score, lightly rewarding smoother intermediate trends and filtering only extremely choppy candidates while preserving all hard trading constraints.

**Decision:** KEPT — sortino 3.155 > prev 3.104746404728241, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.154924091916563
- validation_folds: 13
- per_fold_sortinos: [4.058, 0.2971, -1.0201, 4.4824, 8.6638, 6.8799, 5.9905, 5.0768, 2.6769, 0.5506, 2.0011, 1.8138, -0.4569]
- calmar_mean: 5.965498090654785
- hit_rate_mean: 0.5397083685545223
- profit_factor_mean: 5.442900781502686
- trade_count_total: 175
- aggregate_max_dd: 0.10353971981539965
- worst_fold_max_dd: 0.09078464134780861
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: 1.0613768244374644
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.105 to 3.155 (+0.050). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=175. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.155 > prev 3.104746404728241, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-d1dca99 — REVERTED

**Hypothesis:** Adding a PIT-safe two-leg trend balance term will improve validation Sortino by favoring names whose 126-day momentum is supported by both older and recent intermediate legs instead of a single late rebound or exhausted surge.

**Change:** I added a no-new-parameter prior-leg return check and balance score derived from existing trend_days and vol_days, lightly rewarding smoother two-leg momentum while preserving fixed-slot sizing, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.652 did not improve on prev 3.154924091916563

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.651824940585617
- validation_folds: 13
- per_fold_sortinos: [-0.5659, -1.7356, -2.717, 5.9505, 11.1706, 5.0414, 5.4554, 5.0713, 2.6769, 0.5506, 2.0137, 1.7727, -0.2109]
- calmar_mean: 4.3202054891287425
- hit_rate_mean: 0.4935511886303741
- profit_factor_mean: 3.59074575379289
- trade_count_total: 173
- aggregate_max_dd: 0.15779593311402842
- worst_fold_max_dd: 0.09078464134780861
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: -0.2574666978714852
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.155 to 2.652 (-0.503). Aggregate DD was 15.8% versus previous kept 10.4%; negative folds were 4/13; trades=173. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.652 did not improve on prev 3.154924091916563.

---

## Iteration 2026-05-17-0d69043 — REVERTED

**Hypothesis:** Adding a PIT-safe lower-tail volatility penalty will improve validation Sortino by avoiding trend candidates whose ordinary close-to-close volatility understates clustered downside shocks.

**Change:** I added a no-new-parameter downside semivolatility term to the existing ranking and a light hard filter for extreme lower-tail risk while preserving universe enforcement, fixed-slot sizing, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.033 did not improve on prev 3.154924091916563

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0333639394368523
- validation_folds: 13
- per_fold_sortinos: [4.1609, 0.2842, -0.9779, 4.4815, 8.6744, 6.225, 5.4467, 5.0786, 2.6803, 0.5564, 1.8145, 1.489, -0.4798]
- calmar_mean: 5.830437092546636
- hit_rate_mean: 0.5264792899408284
- profit_factor_mean: 5.01146152477042
- trade_count_total: 173
- aggregate_max_dd: 0.10376841606748052
- worst_fold_max_dd: 0.09096718242731779
- max_position_frac_peak: 0.05184191255763668
- lower_quartile_fold_calmar: 1.0752790384023958
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.155 to 3.033 (-0.122). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=173. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.033 did not improve on prev 3.154924091916563.

---
