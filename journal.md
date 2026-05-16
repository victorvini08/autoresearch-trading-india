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

## Iteration 2026-05-17-f2078a1 — REVERTED

**Hypothesis:** Adding a PIT-safe cross-sectional percentile rank term will improve validation Sortino by favoring names that are strong relative to the current liquid universe, not just positive on absolute standalone momentum.

**Change:** I added a no-new-parameter universe-relative ranking blend that percentile-ranks the existing stock scores at each rebalance and lightly mixes that rank into final ordering while preserving PIT universe enforcement, fixed-slot sizing, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.155 did not improve on prev 3.154924091916563

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

**Learning:** Sortino changed from 3.155 to 3.155 (+0.000). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=175. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.155 did not improve on prev 3.154924091916563.

---

## Iteration 2026-05-17-97567ab — KEPT

**Hypothesis:** Adding a PIT-safe close-location quality term will improve validation Sortino by preferring low-volatility uptrends that are recovering from recent pullbacks without sitting at the bottom of their 63-day range or chasing fresh range highs.

**Change:** I added a no-new-parameter 63-day range-location score centered on the upper-middle of the recent range, with only an extreme lower-range filter, while preserving fixed-slot sizing, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** KEPT — sortino 3.167 > prev 3.154924091916563, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.166988802108574
- validation_folds: 13
- per_fold_sortinos: [4.3254, 0.5307, -1.1343, 4.5019, 8.6645, 6.8784, 6.0011, 5.0786, 2.6804, 0.4525, 1.8395, 1.8091, -0.457]
- calmar_mean: 5.935216565906912
- hit_rate_mean: 0.5217361070302245
- profit_factor_mean: 5.357253858133188
- trade_count_total: 177
- aggregate_max_dd: 0.10360829429276239
- worst_fold_max_dd: 0.0909842627904907
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: 0.8372815842160365
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.155 to 3.167 (+0.012). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=177. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.167 > prev 3.154924091916563, agg_dd 10.4%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-86e9d65 — REVERTED

**Hypothesis:** Adding a PIT-safe price-volume accumulation term will improve validation Sortino by preferring low-volatility uptrends where recent volume is concentrated on advancing days rather than distribution days.

**Change:** I added a no-new-parameter 63-day volume-accumulation score, filtered only clear distribution patterns, and lightly rewarded accumulation while preserving fixed-slot sizing, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.142 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1993 (need ≥ 0.20); sub-periods = [+4.170, +0.831])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1423265821715587
- validation_folds: 13
- per_fold_sortinos: [4.3254, 0.5307, -1.1343, 4.5019, 8.6645, 6.8784, 6.0011, 5.0786, 2.6804, 0.4525, 1.7883, 1.6209, -0.5382]
- calmar_mean: 5.879515245071082
- hit_rate_mean: 0.511828386545581
- profit_factor_mean: 5.33261176080983
- trade_count_total: 179
- aggregate_max_dd: 0.10360829429276239
- worst_fold_max_dd: 0.0909842627904907
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: 0.8372815842160365
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.142 (-0.025). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=179. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.142 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1993 (need ≥ 0.20); sub-periods = [+4.170, +0.831]).

---

## Iteration 2026-05-17-789df87 — REVERTED

**Hypothesis:** Adding a PIT-safe intermediate overextension guard will improve validation Sortino by avoiding trend candidates that are already stretched far above their 63-day average, a different failure mode from one-week exhaustion or 21-day pullback distance.

**Change:** I added a 63-day moving-average distance check and penalty using the existing vol_days parameter so late-stage extended trends are demoted or filtered while preserving fixed-slot sizing, PIT universe enforcement, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.497 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.4968340998677645
- validation_folds: 13
- per_fold_sortinos: [0.8224, -1.3422, -3.2856, 5.2099, 11.4085, 5.8404, 5.6149, 2.8287, 0.7542, 0.595, 1.6329, 2.7763, -0.3966]
- calmar_mean: 2.6172640757132437
- hit_rate_mean: 0.47080701376367007
- profit_factor_mean: 4.0164135340197085
- trade_count_total: 214
- aggregate_max_dd: 0.11210595164542678
- worst_fold_max_dd: 0.061766555354544964
- max_position_frac_peak: 0.05224303767886598
- lower_quartile_fold_calmar: 0.5107465209576256
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 2.497 (-0.670). Aggregate DD was 11.2% versus previous kept 10.4%; negative folds were 3/13; trades=214. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.497 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-8f9a60e — REVERTED

**Hypothesis:** Adding a PIT-safe volatility-compression quality term will improve validation Sortino by preferring low-volatility uptrends whose recent risk is contracting rather than expanding into a fragile pullback.

**Change:** I added a no-new-parameter recent-versus-intermediate volatility compression score and mild expansion filter, preserving fixed-slot sizing, PIT universe enforcement, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.953 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.953311576598057
- validation_folds: 13
- per_fold_sortinos: [3.8965, 0.0152, -1.2847, 4.1068, 9.0005, 6.8186, 5.0977, 4.2814, 1.6503, 0.6915, 1.7337, 2.6625, -0.2769]
- calmar_mean: 5.859184536888104
- hit_rate_mean: 0.5077966716541378
- profit_factor_mean: 6.313410927823998
- trade_count_total: 180
- aggregate_max_dd: 0.12887098034636424
- worst_fold_max_dd: 0.11039726003874503
- max_position_frac_peak: 0.05338107792334286
- lower_quartile_fold_calmar: 1.5048246827099887
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 2.953 (-0.214). Aggregate DD was 12.9% versus previous kept 10.4%; negative folds were 3/13; trades=180. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.953 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-7c4f3bb — REVERTED

**Hypothesis:** Adding a PIT-safe broad-market risk throttle will improve validation Sortino by cutting exposure when Nifty 50 is below its 200DMA or India VIX is elevated, reducing downside in weak market folds without changing stock-selection ranking.

**Change:** I added a continuous macro exposure scaler in next(), using nifty_vs_200dma_pct and india_vix_percentile when available, while preserving fixed-slot sizing, PIT universe enforcement, sector cap, biweekly cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.099 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.099371294120833
- validation_folds: 13
- per_fold_sortinos: [3.6854, 0.063, -1.8322, 4.7524, 10.1142, 6.4402, 4.9971, 5.3222, 3.1905, 0.3433, 1.9545, 1.9909, -0.7297]
- calmar_mean: 4.723632748672527
- hit_rate_mean: 0.5144850624488633
- profit_factor_mean: 5.094821350104268
- trade_count_total: 170
- aggregate_max_dd: 0.09997512009787252
- worst_fold_max_dd: 0.06897358112085489
- max_position_frac_peak: 0.04847925404861312
- lower_quartile_fold_calmar: 0.5802892571955551
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.099 (-0.068). Aggregate DD was 10.0% versus previous kept 10.4%; negative folds were 2/13; trades=170. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.099 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-d729a95 — REVERTED

**Hypothesis:** Adding a PIT-safe longer-term trend-consistency guard will improve validation Sortino by filtering 126-day winners whose broader 252-day path is still weak or unstable, reducing rebound traps without adding exposure or cadence complexity.

**Change:** I added a 252-day trend-consistency check that requires modest positive longer-horizon momentum and mildly rewards durable long-term strength while preserving fixed-slot sizing, PIT universe enforcement, sector cap, biweekly cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.237 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0829 (need ≥ 0.20); sub-periods = [+3.355, -0.278])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2369755233536606
- validation_folds: 13
- per_fold_sortinos: [4.3254, 0.5307, -1.0591, 1.893, 6.221, 4.3719, 5.8548, 4.8928, 3.1622, 0.4443, 1.2217, 0.1983, -2.9763]
- calmar_mean: 3.414536194196548
- hit_rate_mean: 0.5015253725660965
- profit_factor_mean: 2.953877879946949
- trade_count_total: 163
- aggregate_max_dd: 0.09535007952671451
- worst_fold_max_dd: 0.07692429228352414
- max_position_frac_peak: 0.05213953433575263
- lower_quartile_fold_calmar: 0.5320727840205499
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 2.237 (-0.930). Aggregate DD was 9.5% versus previous kept 10.4%; negative folds were 2/13; trades=163. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.237 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0829 (need ≥ 0.20); sub-periods = [+3.355, -0.278]).

---

## Iteration 2026-05-17-1d3662c — REVERTED

**Hypothesis:** Adding a PIT-safe intraday range risk penalty will improve validation Sortino by avoiding trend candidates whose close-to-close smoothness hides unstable high-low trading ranges, while preserving the existing momentum-quality thesis.

**Change:** I added a no-new-parameter high-low range risk score over the existing volatility window and mildly filter/penalize unstable candidates without changing universe enforcement, sector cap, fixed-slot sizing, cadence, or order_target_percent-only execution.

**Decision:** REVERTED — sortino 0.341 did not improve on prev 3.166988802108574 | anti-overfit FAILED: bonferroni(p=0.3118 >= alpha/N=0.0167) · random_walk_mc(only 68.85% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2620 (need ≥ 0.20); sub-periods = [+1.120, -1.414])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.34054451848421763
- validation_folds: 13
- per_fold_sortinos: [1.8552, -1.5308, -3.3723, -2.1863, 0.7497, 2.5241, 3.4025, 5.3702, 3.2695, -1.4258, -0.211, -2.6939, -1.3241]
- calmar_mean: 0.21804616992839215
- hit_rate_mean: 0.4269637612129872
- profit_factor_mean: 2.3273670571226783
- trade_count_total: 144
- aggregate_max_dd: 0.0930642638393917
- worst_fold_max_dd: 0.0472405255076339
- max_position_frac_peak: 0.05070974748260395
- lower_quartile_fold_calmar: -0.9015461483848464
- n_negative_folds: 7/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 0.341 (-2.826). Aggregate DD was 9.3% versus previous kept 10.4%; negative folds were 7/13; trades=144. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 0.341 did not improve on prev 3.166988802108574 | anti-overfit FAILED: bonferroni(p=0.3118 >= alpha/N=0.0167) · random_walk_mc(only 68.85% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2620 (need ≥ 0.20); sub-periods = [+1.120, -1.414]).

---

## Iteration 2026-05-17-a3cb311 — REVERTED

**Hypothesis:** Adding a PIT-safe short-horizon reversal confirmation will improve validation Sortino by favoring intermediate uptrends whose pullback has started to resolve over the last three sessions, avoiding entries that are still falling.

**Change:** I added a no-new-parameter three-day reversal confirmation score and guard inside the existing ranking, preserving fixed-slot sizing, PIT universe enforcement, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 1.981 did not improve on prev 3.166988802108574 | aggregate DD regressed: 46.5% > prev 10.4% + 10pp tolerance | catastrophe: gross exposure: max 170.3% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.1584 >= alpha/N=0.0143) · random_walk_mc(only 84.20% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5172 (need ≥ 0.20); sub-periods = [+3.715, -1.921])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.9807709573597876
- validation_folds: 13
- per_fold_sortinos: [4.2574, 0.0129, -2.1431, 3.691, 7.9879, 6.6432, 4.8074, 4.958, 3.2201, -0.5198, -2.8806, -3.2713, -1.0132]
- calmar_mean: 3.809187392069532
- hit_rate_mean: 0.48192787340203397
- profit_factor_mean: 4.59284589703397
- trade_count_total: 212
- aggregate_max_dd: 0.4651473464549601
- worst_fold_max_dd: 0.28976994744401663
- max_position_frac_peak: 0.07009135570449554
- lower_quartile_fold_calmar: -0.9613858673718835
- n_negative_folds: 6/13
- risk.passed: False
- risk.violations: ['gross exposure: max 170.3% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 3.167 to 1.981 (-1.186). Aggregate DD was 46.5% versus previous kept 10.4%; negative folds were 6/13; trades=212. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 1.981 did not improve on prev 3.166988802108574 | aggregate DD regressed: 46.5% > prev 10.4% + 10pp tolerance | catastrophe: gross exposure: max 170.3% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.1584 >= alpha/N=0.0143) · random_walk_mc(only 84.20% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.5172 (need ≥ 0.20); sub-periods = [+3.715, -1.921]).

---

## Iteration 2026-05-17-917227b — REVERTED

**Hypothesis:** Adding a PIT-safe turnover participation guard will improve validation Sortino by avoiding technically strong names whose recent advance is occurring on unusually thin volume, reducing stale-price and weak-follow-through entries without changing fixed-slot sizing or gross exposure.

**Change:** I added a no-new-import volume participation check that requires current 21-day average volume to remain at least 65% of the prior 63-day average and adds a small liquidity-continuity term to the existing score.

**Decision:** REVERTED — sortino 2.249 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0730 (need ≥ 0.20); sub-periods = [+3.146, +0.230])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2487471764057108
- validation_folds: 13
- per_fold_sortinos: [3.5691, 1.2641, -0.3365, 3.3437, 6.2543, 5.2413, 3.1779, 3.4183, 2.3835, -0.5627, 0.7754, 0.3978, 0.3077]
- calmar_mean: 4.066992250456557
- hit_rate_mean: 0.4997788589119859
- profit_factor_mean: 3.651123340910956
- trade_count_total: 205
- aggregate_max_dd: 0.06929822966231358
- worst_fold_max_dd: 0.06805550292864418
- max_position_frac_peak: 0.07458167192265612
- lower_quartile_fold_calmar: 0.2833283649988516
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 2.249 (-0.918). Aggregate DD was 6.9% versus previous kept 10.4%; negative folds were 2/13; trades=205. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.249 did not improve on prev 3.166988802108574 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0730 (need ≥ 0.20); sub-periods = [+3.146, +0.230]).

---

## Iteration 2026-05-17-98416aa — REVERTED

**Hypothesis:** Adding a PIT-safe asymmetric downside-volatility penalty will improve validation Sortino by distinguishing smooth compounders from trend names whose realized volatility is concentrated in negative sessions, without changing exposure, cadence, universe enforcement, or sector construction.

**Change:** I added a downside-volatility quality check over the existing volatility window and penalized candidates with high downside volatility relative to total volatility while preserving fixed-slot sizing and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.149 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1485729800220765
- validation_folds: 13
- per_fold_sortinos: [4.3254, 0.5307, -1.1343, 4.5019, 8.6645, 6.8784, 6.0011, 5.0786, 2.6804, 0.4525, 1.7883, 1.6209, -0.457]
- calmar_mean: 5.885340014209357
- hit_rate_mean: 0.511828386545581
- profit_factor_mean: 5.3325778280374205
- trade_count_total: 179
- aggregate_max_dd: 0.10360829429276239
- worst_fold_max_dd: 0.0909842627904907
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: 0.8372815842160365
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.149 (-0.018). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=179. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.149 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-7956392 — REVERTED

**Hypothesis:** Adding a PIT-safe LLM news-risk overlay will improve validation Sortino by avoiding otherwise attractive momentum names with fresh adverse sentiment or high-risk corporate event flags, while leaving no-news names unchanged.

**Change:** I added a defensive sentiment/event/news-volume adjustment to the ranking score so negative classified news can veto or penalize candidates without changing fixed-slot sizing, universe enforcement, sector cap, cadence, or order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.167 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.166988802108574
- validation_folds: 13
- per_fold_sortinos: [4.3254, 0.5307, -1.1343, 4.5019, 8.6645, 6.8784, 6.0011, 5.0786, 2.6804, 0.4525, 1.8395, 1.8091, -0.457]
- calmar_mean: 5.935216565906912
- hit_rate_mean: 0.5217361070302245
- profit_factor_mean: 5.357253858133188
- trade_count_total: 177
- aggregate_max_dd: 0.10360829429276239
- worst_fold_max_dd: 0.0909842627904907
- max_position_frac_peak: 0.05222323354869495
- lower_quartile_fold_calmar: 0.8372815842160365
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.167 (+0.000). Aggregate DD was 10.4% versus previous kept 10.4%; negative folds were 2/13; trades=177. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.167 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-5d15d95 — REVERTED

**Hypothesis:** Adding a no-new-parameter off-universe exposure reserve will improve validation Sortino by preventing stale holdings that leave the PIT universe from combining with new buys into excess gross exposure, while preserving fixed-slot sizing for eligible names.

**Change:** I changed rebalance sizing so active selections only receive unused gross budget after accounting for currently held off-universe positions, reducing leverage-like drift without trading off-universe tickers or changing the ranking signal.

**Decision:** REVERTED — sortino 3.032 did not improve on prev 3.166988802108574

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.031735786405346
- validation_folds: 13
- per_fold_sortinos: [4.3995, 0.7945, -0.7988, 4.1624, 7.9305, 6.9571, 4.7835, 4.7652, 2.4136, 0.3415, 2.2054, 2.0626, -0.6045]
- calmar_mean: 4.885258427453613
- hit_rate_mean: 0.5104743672616976
- profit_factor_mean: 6.0082371228797395
- trade_count_total: 173
- aggregate_max_dd: 0.08563369663578183
- worst_fold_max_dd: 0.07596572130001682
- max_position_frac_peak: 0.04742946605435194
- lower_quartile_fold_calmar: 0.8395467139772771
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.032 (-0.135). Aggregate DD was 8.6% versus previous kept 10.4%; negative folds were 2/13; trades=173. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.032 did not improve on prev 3.166988802108574.

---

## Iteration 2026-05-17-31c5658 — KEPT

**Hypothesis:** Reducing fixed risk slots from 18 to 16 will improve validation Sortino by modestly concentrating the already-filtered low-volatility trend book while staying above the 15-position catastrophe floor and preserving cash-account gross exposure.

**Change:** I changed only n_positions from 18 to 16 so each selected name receives a slightly larger fixed-slot allocation without altering the signal family, sector cap, cadence, PIT universe enforcement, or order_target_percent-only contract.

**Decision:** KEPT — sortino 3.189 > prev 3.166988802108574, agg_dd 13.1%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1886060453978216
- validation_folds: 13
- per_fold_sortinos: [4.4333, 0.3609, -1.2611, 4.9952, 9.4464, 6.4798, 5.8356, 5.2912, 2.3826, 0.5833, 1.6846, 1.5673, -0.3472]
- calmar_mean: 6.651082478965423
- hit_rate_mean: 0.5448684799363532
- profit_factor_mean: 5.554754096037808
- trade_count_total: 185
- aggregate_max_dd: 0.13131784710367803
- worst_fold_max_dd: 0.10794863528070474
- max_position_frac_peak: 0.05958597657503148
- lower_quartile_fold_calmar: 1.0409400675456437
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.167 to 3.189 (+0.022). Aggregate DD was 13.1% versus previous kept 10.4%; negative folds were 2/13; trades=185. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.189 > prev 3.166988802108574, agg_dd 13.1%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-0bdb2d2 — REVERTED

**Hypothesis:** Reducing fixed risk slots from 16 to the allowed floor of 15 will improve validation Sortino by giving the already-filtered low-volatility trend book slightly more exposure per selected name while still respecting the catastrophe floor, sector cap, and cash-account gross limit.

**Change:** I changed only n_positions from 16 to 15, preserving the kept signal, PIT universe enforcement, biweekly cadence, sector construction, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.055 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0773 (need ≥ 0.20); sub-periods = [+4.267, +0.330])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0553939207456344
- validation_folds: 13
- per_fold_sortinos: [4.2284, 0.5414, -1.0319, 5.2298, 9.3795, 6.8032, 4.0936, 5.8728, 3.2832, 0.364, 1.4877, -0.2957, -0.2359]
- calmar_mean: 5.843494034237411
- hit_rate_mean: 0.49720237027929337
- profit_factor_mean: 5.395776587742234
- trade_count_total: 138
- aggregate_max_dd: 0.09180650656079174
- worst_fold_max_dd: 0.08245543386011837
- max_position_frac_peak: 0.06315935954671427
- lower_quartile_fold_calmar: 0.5548245861680744
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.189 to 3.055 (-0.133). Aggregate DD was 9.2% versus previous kept 13.1%; negative folds were 3/13; trades=138. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.055 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0773 (need ≥ 0.20); sub-periods = [+4.267, +0.330]).

---

## Iteration 2026-05-17-d7d4809 — REVERTED

**Hypothesis:** Adding a PIT-safe incumbent retention band will improve validation Sortino by reducing unnecessary biweekly churn and DP-charge drag while still forcing exits from weakened names that fall outside the ranked breadth buffer.

**Change:** I changed sector-capped selection to prefer currently held names that remain eligible within the existing breadth buffer before filling open slots from new candidates, preserving fixed-slot sizing and all universe and sector constraints.

**Decision:** REVERTED — sortino 2.590 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0720 (need ≥ 0.20); sub-periods = [+3.626, +0.261])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5903475503341977
- validation_folds: 13
- per_fold_sortinos: [2.5159, -1.2765, -2.829, 6.27, 13.5321, 4.5099, 3.2634, 4.5296, 2.1149, 0.0954, 1.1357, -0.119, -0.0677]
- calmar_mean: 5.264495879284751
- hit_rate_mean: 0.6601951467336082
- profit_factor_mean: 19.91927037174704
- trade_count_total: 109
- aggregate_max_dd: 0.17536489836317157
- worst_fold_max_dd: 0.12239054578065398
- max_position_frac_peak: 0.07601698054211263
- lower_quartile_fold_calmar: -0.16581184856394948
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.189 to 2.590 (-0.598). Aggregate DD was 17.5% versus previous kept 13.1%; negative folds were 5/13; trades=109. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.590 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0720 (need ≥ 0.20); sub-periods = [+3.626, +0.261]).

---

## Iteration 2026-05-17-ecb8ce8 — REVERTED

**Hypothesis:** Honoring the fixed biweekly parity instead of resetting it to each fold's first Friday will improve validation Sortino by making rebalance timing stable across walk-forward folds rather than anchoring to an arbitrary fold start date.

**Change:** I changed the rebalance scheduler to use the existing rebalance_week_parity parameter directly, preserving the signal, sizing, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.783 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0205 (need ≥ 0.20); sub-periods = [+4.057, -0.083])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7831872691070023
- validation_folds: 13
- per_fold_sortinos: [3.3213, 1.3614, -0.6871, 4.9545, 9.7599, 6.6964, 4.2314, 4.7675, 2.1087, -0.773, 0.6999, 0.0876, -0.3472]
- calmar_mean: 6.15236885677381
- hit_rate_mean: 0.4671304572620362
- profit_factor_mean: 3.802009065876988
- trade_count_total: 184
- aggregate_max_dd: 0.1992222112334123
- worst_fold_max_dd: 0.1378507051521372
- max_position_frac_peak: 0.06689237898505679
- lower_quartile_fold_calmar: -0.034586705228880986
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.189 to 2.783 (-0.405). Aggregate DD was 19.9% versus previous kept 13.1%; negative folds were 4/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.783 did not improve on prev 3.1886060453978216 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0205 (need ≥ 0.20); sub-periods = [+4.057, -0.083]).

---

## Iteration 2026-05-17-efffc1a — KEPT

**Hypothesis:** Increasing gross exposure from 0.90 to 0.94 will improve validation Sortino by modestly scaling the already-kept positive-edge 16-slot book while keeping enough cash buffer to avoid gross-exposure and drawdown gate failures.

**Change:** I changed only the existing gross_exposure parameter from 0.90 to 0.94, preserving the signal, fixed-slot sizing, PIT universe enforcement, sector cap, cadence, and order_target_percent-only contract.

**Decision:** KEPT — sortino 3.196 > prev 3.1886060453978216, agg_dd 13.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1961034722967954
- validation_folds: 13
- per_fold_sortinos: [4.3252, 0.3703, -1.2931, 5.0814, 9.5358, 6.4199, 5.9126, 5.2645, 2.4212, 0.7317, 1.6713, 1.5678, -0.4592]
- calmar_mean: 6.859307307150354
- hit_rate_mean: 0.5503348084796048
- profit_factor_mean: 5.582353391911711
- trade_count_total: 187
- aggregate_max_dd: 0.13293904457698819
- worst_fold_max_dd: 0.11046936884937757
- max_position_frac_peak: 0.06225166736518536
- lower_quartile_fold_calmar: 1.4564174397588183
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.189 to 3.196 (+0.007). Aggregate DD was 13.3% versus previous kept 13.1%; negative folds were 2/13; trades=187. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.196 > prev 3.1886060453978216, agg_dd 13.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-af232b5 — KEPT

**Hypothesis:** Increasing the existing gross exposure from 0.94 to 0.97 should improve validation Sortino by continuing the kept positive-edge exposure scaling while preserving a cash buffer below the 100% gross catastrophe constraint.

**Change:** I changed only the existing gross_exposure parameter from 0.94 to 0.97, leaving the signal, fixed 16-slot sizing, PIT universe filter, sector cap, cadence, and order_target_percent-only execution unchanged.

**Decision:** KEPT — sortino 3.254 > prev 3.1961034722967954, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2541190820225
- validation_folds: 13
- per_fold_sortinos: [4.4191, 0.3754, -1.319, 5.205, 9.7907, 6.3789, 5.8569, 5.3026, 2.3662, 0.6732, 1.9802, 1.7034, -0.4291]
- calmar_mean: 7.212599846726907
- hit_rate_mean: 0.5528989110437074
- profit_factor_mean: 5.567950813091967
- trade_count_total: 188
- aggregate_max_dd: 0.13610743175496356
- worst_fold_max_dd: 0.11696078762693822
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 1.2507269695551222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.196 to 3.254 (+0.058). Aggregate DD was 13.6% versus previous kept 13.3%; negative folds were 2/13; trades=188. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.254 > prev 3.1961034722967954, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-dc3a845 — REVERTED

**Hypothesis:** Raising the existing gross exposure from 0.97 to 0.99 will improve mean validation Sortino by capturing more of the already-kept positive-edge 16-slot book while still leaving a small cash buffer below the 100% gross catastrophe limit.

**Change:** I changed only the existing gross_exposure parameter from 0.97 to 0.99, preserving the signal, fixed-slot sizing, PIT universe enforcement, 25% sector cap, biweekly cadence, and order_target_percent-only contract.

**Decision:** REVERTED — sortino 3.254 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.253657904016755
- validation_folds: 13
- per_fold_sortinos: [4.3788, 0.3677, -1.3269, 5.1759, 9.6664, 6.5865, 5.9438, 5.2513, 2.3689, 0.6641, 1.9468, 1.704, -0.4297]
- calmar_mean: 7.272033316887366
- hit_rate_mean: 0.5528989110437074
- profit_factor_mean: 5.519196806908193
- trade_count_total: 188
- aggregate_max_dd: 0.1359140919684902
- worst_fold_max_dd: 0.11826308175920162
- max_position_frac_peak: 0.06565660872104556
- lower_quartile_fold_calmar: 1.2319278174910728
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.254 (-0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.254 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-54092e6 — REVERTED

**Hypothesis:** Reducing the existing sector cap from 25% to 20% should improve validation Sortino by reducing sector-cluster drawdowns in the current high-gross 16-slot book while preserving the same PIT-safe ranking signal and fixed-slot sizing.

**Change:** I changed only the existing sector_cap parameter from 0.25 to 0.20 so the 16-position portfolio can hold at most three names per classified sector instead of four.

**Decision:** REVERTED — sortino 3.055 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0748 (need ≥ 0.20); sub-periods = [+4.271, +0.319])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0549824757782797
- validation_folds: 13
- per_fold_sortinos: [4.2284, 0.5465, -1.0337, 5.2221, 9.3952, 6.8227, 4.0959, 5.854, 3.3066, 0.3252, 1.4695, -0.2878, -0.2297]
- calmar_mean: 5.838184610485873
- hit_rate_mean: 0.4929288660057891
- profit_factor_mean: 5.348829670696274
- trade_count_total: 139
- aggregate_max_dd: 0.09304506775658686
- worst_fold_max_dd: 0.08333596823610154
- max_position_frac_peak: 0.06317545019881267
- lower_quartile_fold_calmar: 0.5282426604806515
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.055 (-0.199). Aggregate DD was 9.3% versus previous kept 13.6%; negative folds were 3/13; trades=139. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.055 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0748 (need ≥ 0.20); sub-periods = [+4.271, +0.319]).

---

## Iteration 2026-05-17-206f1d5 — REVERTED

**Hypothesis:** Requiring a small positive fast trend confirmation before ranking will improve validation Sortino by avoiding candidates whose intermediate momentum is already rolling over, while preserving the existing pullback and exhaustion controls.

**Change:** I added a no-new-parameter fast-momentum floor using the existing recent_days-derived fast window, filtering names with fast return below -1% before scoring.

**Decision:** REVERTED — sortino 2.884 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1519 (need ≥ 0.20); sub-periods = [+3.902, +0.593])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.883700386529976
- validation_folds: 13
- per_fold_sortinos: [4.122, -0.7626, -2.3859, 4.7699, 10.8543, 7.9308, 3.7273, 4.5846, 2.2763, 0.158, 1.8917, 0.3761, -0.0545]
- calmar_mean: 6.628834468188392
- hit_rate_mean: 0.47914666239267334
- profit_factor_mean: 4.431166218421739
- trade_count_total: 244
- aggregate_max_dd: 0.16778225161446922
- worst_fold_max_dd: 0.10220715521646323
- max_position_frac_peak: 0.06395231404420543
- lower_quartile_fold_calmar: 0.1321998600398857
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 2.884 (-0.370). Aggregate DD was 16.8% versus previous kept 13.6%; negative folds were 3/13; trades=244. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.884 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1519 (need ≥ 0.20); sub-periods = [+3.902, +0.593]).

---

## Iteration 2026-05-17-73576cf — REVERTED

**Hypothesis:** Reducing the existing one-week exhaustion penalty should improve mean validation Sortino by letting strong intermediate trend winners remain eligible when short-term strength is constructive rather than treating all >5.5% fast moves as excessive.

**Change:** I changed only the fast_exhaustion penalty coefficient from 0.70 to 0.55, preserving the existing PIT universe filter, fixed 16-slot sizing, 25% sector cap, biweekly cadence, and order_target_percent-only execution contract.

**Decision:** REVERTED — sortino 3.254 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.25369045282884
- validation_folds: 13
- per_fold_sortinos: [4.4191, 0.3754, -1.319, 5.205, 9.7907, 6.3789, 5.8569, 5.3026, 2.3662, 0.6732, 1.9802, 1.7034, -0.4347]
- calmar_mean: 7.2122435732915555
- hit_rate_mean: 0.5528989110437074
- profit_factor_mean: 5.567321165042504
- trade_count_total: 188
- aggregate_max_dd: 0.13610743175496356
- worst_fold_max_dd: 0.11696078762693822
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 1.2507269695551222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.254 (-0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.254 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-56d97ec — REVERTED

**Hypothesis:** Adding a PIT-safe cross-sectional trend-relative score should improve validation Sortino by favoring stocks with true leadership over broad-market beta while keeping the existing absolute uptrend, volatility, pullback, sector-cap, and fixed-slot controls intact.

**Change:** I added an active-universe median 126-day trend benchmark and passed it into scoring so each candidate receives a capped leadership bonus/penalty based on excess intermediate trend, without changing sizing or rebalance mechanics.

**Decision:** REVERTED — sortino 3.174 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.174291594803495
- validation_folds: 13
- per_fold_sortinos: [4.1041, -0.0537, -1.5402, 5.1861, 9.763, 6.3696, 5.8547, 5.2939, 2.3662, 0.6732, 1.9802, 1.7034, -0.4348]
- calmar_mean: 7.1681948671306035
- hit_rate_mean: 0.560852335328401
- profit_factor_mean: 5.571197657886653
- trade_count_total: 190
- aggregate_max_dd: 0.13610743175496431
- worst_fold_max_dd: 0.11696078762693822
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 1.2507269695551222
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.174 (-0.080). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 3/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.174 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-a0323b8 — REVERTED

**Hypothesis:** Switching from biweekly to four-week rebalancing will improve validation Sortino by reducing DP-charge churn and letting the existing intermediate-trend winners compound longer without changing the PIT universe, ranking signal, fixed-slot sizing, or sector cap.

**Change:** I changed the existing rebalance cadence from 2 to 4 weeks and generalized the rebalance scheduler so it honors rebalance_period_weeks instead of hard-coding two-week parity.

**Decision:** REVERTED — sortino 2.215 did not improve on prev 3.2541190820225 | aggregate DD regressed: 26.7% > prev 13.6% + 10pp tolerance | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3039 (need ≥ 0.20); sub-periods = [+3.699, -1.124])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.215089170718996
- validation_folds: 13
- per_fold_sortinos: [3.2944, 1.3912, -0.3366, 5.1538, 9.3859, 4.4556, 3.4016, 5.1559, 1.3915, -0.6614, -1.4809, -2.6343, 0.2795]
- calmar_mean: 6.055407753559132
- hit_rate_mean: 0.6161283161283161
- profit_factor_mean: 7.562505857175625
- trade_count_total: 116
- aggregate_max_dd: 0.2670055269093262
- worst_fold_max_dd: 0.11586064294106208
- max_position_frac_peak: 0.06715182711714682
- lower_quartile_fold_calmar: -0.526212654715667
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 2.215 (-1.039). Aggregate DD was 26.7% versus previous kept 13.6%; negative folds were 4/13; trades=116. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.215 did not improve on prev 3.2541190820225 | aggregate DD regressed: 26.7% > prev 13.6% + 10pp tolerance | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3039 (need ≥ 0.20); sub-periods = [+3.699, -1.124]).

---

## Iteration 2026-05-17-63a8fbc — REVERTED

**Hypothesis:** Adding a PIT-safe high-watermark breakout participation score will improve validation Sortino by favoring trend candidates that are close to confirming fresh multi-month highs while avoiding late, overextended one-week moves.

**Change:** I added a no-new-parameter breakout proximity component using the existing 63-day range location, rewarding names near the upper half of their intermediate range but penalizing only extreme range-extension that coincides with fast exhaustion.

**Decision:** REVERTED — sortino 3.173 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1732662346826617
- validation_folds: 13
- per_fold_sortinos: [4.4191, 0.0403, -1.8434, 5.0039, 9.746, 6.3777, 5.8547, 5.2668, 2.363, 0.8052, 2.045, 1.7545, -0.5803]
- calmar_mean: 7.218120484525972
- hit_rate_mean: 0.542793799238786
- profit_factor_mean: 5.5074281609054685
- trade_count_total: 190
- aggregate_max_dd: 0.13753878101907477
- worst_fold_max_dd: 0.11751153150364708
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 1.5452770285010309
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.173 (-0.081). Aggregate DD was 13.8% versus previous kept 13.6%; negative folds were 3/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.173 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-1c3b407 — REVERTED

**Hypothesis:** Adding a no-new-parameter macro-regime exposure throttle should improve validation Sortino by keeping the proven fixed-slot momentum book mostly intact while reducing downside participation during India risk_off and shock regimes.

**Change:** I imported macro_regime and applied a conservative rebalance-day gross exposure multiplier for risk_off and shock states, with neutral fallback when macro data is unavailable.

**Decision:** REVERTED — sortino 3.185 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1888 (need ≥ 0.20); sub-periods = [+4.244, +0.801])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.184835169768132
- validation_folds: 13
- per_fold_sortinos: [4.4217, 0.3571, -1.3543, 5.1701, 9.6989, 6.3789, 5.8569, 5.3026, 2.3662, 0.3186, 1.9044, 1.6515, -0.6698]
- calmar_mean: 6.977295528246336
- hit_rate_mean: 0.5300051381499344
- profit_factor_mean: 5.438056508081877
- trade_count_total: 184
- aggregate_max_dd: 0.13610993172332547
- worst_fold_max_dd: 0.11696785858567071
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 0.38903776723080535
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.185 (-0.069). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.185 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1888 (need ≥ 0.20); sub-periods = [+4.244, +0.801]).

---

## Iteration 2026-05-17-8768349 — REVERTED

**Hypothesis:** Adding a PIT-safe active-universe breadth exposure throttle will improve validation Sortino by reducing gross only during broad cross-sectional selloffs where a long-only momentum book has poor payoff asymmetry, while leaving the proven ranker unchanged in healthy markets.

**Change:** I added a rebalance-day gross multiplier derived from active-universe 63-day and 126-day breadth plus median recent returns, so fixed-slot sizing is preserved but exposure is cut to 86% or 72% of normal during deteriorating market breadth.

**Decision:** REVERTED — sortino 3.184 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1843726327071327
- validation_folds: 13
- per_fold_sortinos: [4.412, 0.3644, -1.3637, 4.9253, 9.4843, 6.3831, 5.8559, 5.3049, 2.3631, 0.6739, 1.9802, 1.7054, -0.6921]
- calmar_mean: 7.042833043589114
- hit_rate_mean: 0.5528989110437074
- profit_factor_mean: 5.448347498994543
- trade_count_total: 188
- aggregate_max_dd: 0.13659806557072265
- worst_fold_max_dd: 0.11757416280646198
- max_position_frac_peak: 0.06441897761519673
- lower_quartile_fold_calmar: 1.2521682549806241
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.184 (-0.070). Aggregate DD was 13.7% versus previous kept 13.6%; negative folds were 2/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.184 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-95a099c — REVERTED

**Hypothesis:** Replacing part of the raw 126-day momentum score with risk-adjusted intermediate momentum will improve validation Sortino by favoring smoother leaders whose trend return is large relative to realized volatility, without changing fixed-slot sizing, cadence, or exposure.

**Change:** I added a PIT-safe volatility-adjusted momentum component inside the existing score, using already-computed 63-day return and volatility to reward efficient intermediate trends while leaving the universe, filters, sector cap, and order contract unchanged.

**Decision:** REVERTED — sortino 3.076 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1656 (need ≥ 0.20); sub-periods = [+4.138, +0.685])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.075526188510484
- validation_folds: 13
- per_fold_sortinos: [4.3155, 0.5112, -1.304, 5.1731, 9.5455, 6.4429, 5.2362, 4.9771, 2.3433, 0.3138, 1.7321, 1.3132, -0.618]
- calmar_mean: 6.637512061122621
- hit_rate_mean: 0.5383782507085674
- profit_factor_mean: 4.3281798991201805
- trade_count_total: 187
- aggregate_max_dd: 0.142457658635003
- worst_fold_max_dd: 0.11641945045108872
- max_position_frac_peak: 0.06400171103853698
- lower_quartile_fold_calmar: 0.5069175476452304
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.076 (-0.179). Aggregate DD was 14.2% versus previous kept 13.6%; negative folds were 2/13; trades=187. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.076 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1656 (need ≥ 0.20); sub-periods = [+4.138, +0.685]).

---

## Iteration 2026-05-17-082419c — REVERTED

**Hypothesis:** Adding a PIT-safe one-day downside shock guard will improve validation Sortino by excluding momentum names that just printed an abnormal down day, where short-horizon reversal risk is high for a biweekly long-only book.

**Change:** I added a no-new-parameter latest daily return check inside the existing score filter, rejecting candidates with a same-close one-day loss worse than 6% while leaving ranking, sizing, cadence, universe, and sector construction unchanged.

**Decision:** REVERTED — sortino 3.197 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.196667004738205
- validation_folds: 13
- per_fold_sortinos: [4.4191, 0.0352, -1.6787, 5.1853, 9.7639, 6.3852, 5.8548, 5.298, 2.3662, 0.6732, 1.9802, 1.7034, -0.4291]
- calmar_mean: 7.2089332486959234
- hit_rate_mean: 0.5535022292940844
- profit_factor_mean: 5.501221888371343
- trade_count_total: 194
- aggregate_max_dd: 0.13693869681641216
- worst_fold_max_dd: 0.11696078762693822
- max_position_frac_peak: 0.0645603776989541
- lower_quartile_fold_calmar: 1.2507269695551222
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.197 (-0.057). Aggregate DD was 13.7% versus previous kept 13.6%; negative folds were 3/13; trades=194. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.197 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-54dd0e1 — REVERTED

**Hypothesis:** Replacing the primary trend leg with 12-1 skip-month momentum should improve validation Sortino by ranking stocks on persistent intermediate leadership while reducing exposure to short-term reversal from the most recent month.

**Change:** I changed the main trend calculation in _score_for to use the price from recent_days ago versus trend_days ago, while keeping current-price gates, sizing, cadence, universe, and sector construction unchanged.

**Decision:** REVERTED — sortino 2.764 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0240 (need ≥ 0.20); sub-periods = [+3.950, +0.095])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.763944418808472
- validation_folds: 13
- per_fold_sortinos: [2.0714, -1.3133, -3.2948, 5.0744, 14.588, 7.6003, 3.921, 4.2197, 2.6849, 0.8562, 0.6759, -1.3411, 0.1888]
- calmar_mean: 4.921937819175705
- hit_rate_mean: 0.5818069750762058
- profit_factor_mean: 6.614254392505164
- trade_count_total: 175
- aggregate_max_dd: 0.17358144082126173
- worst_fold_max_dd: 0.10285784528411096
- max_position_frac_peak: 0.06546356486323437
- lower_quartile_fold_calmar: 0.13250382107300895
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 2.764 (-0.490). Aggregate DD was 17.4% versus previous kept 13.6%; negative folds were 3/13; trades=175. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.764 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0240 (need ≥ 0.20); sub-periods = [+3.950, +0.095]).

---

## Iteration 2026-05-17-3e148f9 — REVERTED

**Hypothesis:** Replacing the total-volatility penalty with downside semivolatility will improve validation Sortino by penalizing choppy downside risk while no longer discarding leaders whose realized volatility is mostly upside participation.

**Change:** I changed the risk leg inside the existing score to compute and use downside annualized semivolatility from the same 63-day return window, leaving cadence, universe, filters, sector cap, fixed-slot sizing, and order contract unchanged.

**Decision:** REVERTED — sortino 2.750 did not improve on prev 3.2541190820225 | catastrophe: gross exposure: max 150.2% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0003 (need ≥ 0.20); sub-periods = [+3.972, +0.001])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7498721903473506
- validation_folds: 13
- per_fold_sortinos: [4.0582, 0.0171, -1.4843, 4.9034, 10.0501, 5.4521, 4.973, 5.1973, 2.5767, -0.7754, 0.6462, 0.9223, -0.7883]
- calmar_mean: 6.509277526258239
- hit_rate_mean: 0.5304884343911493
- profit_factor_mean: 4.7028243251289705
- trade_count_total: 188
- aggregate_max_dd: 0.1509801945665166
- worst_fold_max_dd: 0.11340002119562521
- max_position_frac_peak: 0.22547424247971182
- lower_quartile_fold_calmar: -0.07205798003599895
- n_negative_folds: 4/13
- risk.passed: False
- risk.violations: ['gross exposure: max 150.2% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 3.254 to 2.750 (-0.504). Aggregate DD was 15.1% versus previous kept 13.6%; negative folds were 4/13; trades=188. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 2.750 did not improve on prev 3.2541190820225 | catastrophe: gross exposure: max 150.2% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0003 (need ≥ 0.20); sub-periods = [+3.972, +0.001]).

---

## Iteration 2026-05-17-41f6d53 — REVERTED

**Hypothesis:** Adding PIT-safe volume accumulation confirmation will improve validation Sortino by preferring momentum leaders whose recent up days carry stronger participation than down days, while avoiding distribution-heavy names that price-only trend filters miss.

**Change:** I added a recent up-volume versus down-volume accumulation score and a modest distribution filter inside the existing fixed-slot ranking, leaving universe handling, cadence, sector cap, gross exposure, and order_target_percent sizing unchanged.

**Decision:** REVERTED — sortino 2.608 did not improve on prev 3.2541190820225

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.608437368899362
- validation_folds: 13
- per_fold_sortinos: [2.6805, -0.5104, -1.786, 4.3876, 8.5563, 5.4966, 4.9806, 4.7991, 2.0083, 0.9128, 1.8829, 1.3728, -0.8714]
- calmar_mean: 6.646250222072049
- hit_rate_mean: 0.5517947051228783
- profit_factor_mean: 9.368016428174418
- trade_count_total: 193
- aggregate_max_dd: 0.1473823033655838
- worst_fold_max_dd: 0.12803376641435213
- max_position_frac_peak: 0.06476910750007901
- lower_quartile_fold_calmar: 1.917386998167208
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 2.608 (-0.646). Aggregate DD was 14.7% versus previous kept 13.6%; negative folds were 3/13; trades=193. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.608 did not improve on prev 3.2541190820225.

---

## Iteration 2026-05-17-8597241 — REVERTED

**Hypothesis:** Adding a same-universe median trend hurdle will improve validation Sortino by requiring selected momentum names to show leadership versus the current liquid NSE opportunity set, not just positive absolute momentum.

**Change:** I added a PIT-safe cross-sectional median trend filter at each rebalance and require candidates to clear it before scoring, preserving sizing, cadence, sector cap, and the order_target_percent-only contract.

**Decision:** REVERTED — sortino 2.744 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0464 (need ≥ 0.20); sub-periods = [+4.048, -0.188])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7443264524783997
- validation_folds: 13
- per_fold_sortinos: [1.9183, 0.8345, -0.6727, 4.3088, 8.789, 7.9732, 7.5807, 4.3845, 1.3115, -1.1638, 0.205, 0.0978, 0.1094]
- calmar_mean: 5.890320996757391
- hit_rate_mean: 0.553342170649863
- profit_factor_mean: 6.846463558119089
- trade_count_total: 165
- aggregate_max_dd: 0.21108915453811605
- worst_fold_max_dd: 0.14482130924463735
- max_position_frac_peak: 0.08410691545752931
- lower_quartile_fold_calmar: -0.020821230432043477
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 2.744 (-0.510). Aggregate DD was 21.1% versus previous kept 13.6%; negative folds were 4/13; trades=165. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.744 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0464 (need ≥ 0.20); sub-periods = [+4.048, -0.188]).

---

## Iteration 2026-05-17-2a3e3ee — REVERTED

**Hypothesis:** Adding a drawdown-recovery quality leg should improve validation Sortino by preferring momentum names that have already repaired recent damage rather than names still sitting in deep intermediate drawdowns.

**Change:** I added a PIT-safe recovery ratio from the 63-day low to current price relative to the 63-day drawdown depth, rewarding resilient recoveries while keeping the existing fixed-slot sizing, sector cap, cadence, and order_target_percent-only contract unchanged.

**Decision:** REVERTED — sortino 3.000 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1759 (need ≥ 0.20); sub-periods = [+4.019, +0.707])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.9999454861926953
- validation_folds: 13
- per_fold_sortinos: [3.9073, 0.0488, -1.6107, 4.4266, 9.9059, 6.5134, 5.5524, 5.2597, 2.1683, 0.3272, 1.7487, 1.2438, -0.4922]
- calmar_mean: 7.207415484536865
- hit_rate_mean: 0.5015650011125123
- profit_factor_mean: 5.722607555575282
- trade_count_total: 191
- aggregate_max_dd: 0.14488428154311897
- worst_fold_max_dd: 0.11425500088549759
- max_position_frac_peak: 0.06552217314317627
- lower_quartile_fold_calmar: 0.49311195224318116
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.000 (-0.254). Aggregate DD was 14.5% versus previous kept 13.6%; negative folds were 3/13; trades=191. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.000 did not improve on prev 3.2541190820225 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1759 (need ≥ 0.20); sub-periods = [+4.019, +0.707]).

---

## Iteration 2026-05-17-0e26f39 — KEPT

**Hypothesis:** Adding a no-new-parameter gap-risk filter will improve validation Sortino by avoiding momentum names whose latest close is too far above the prior close, where next-open delivery fills are most exposed to short-term mean reversion and poor entry prices.

**Change:** I added a PIT-safe one-day upside gap/exhaustion exclusion inside the existing score, leaving cadence, fixed-slot sizing, sector cap, gross exposure, and the order_target_percent-only contract unchanged.

**Decision:** KEPT — sortino 3.404 > prev 3.2541190820225, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4038275153908293
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.3440874574941555
- hit_rate_mean: 0.5433581124757595
- profit_factor_mean: 5.780037413995571
- trade_count_total: 190
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.254 to 3.404 (+0.150). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.404 > prev 3.2541190820225, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-e3b8db4 — REVERTED

**Hypothesis:** Adding a no-new-parameter holding-retention pass will improve validation Sortino by reducing biweekly DP-charge churn when existing holdings still rank inside the near-top candidate band.

**Change:** I changed sector-cap selection to retain currently held names that remain in the top breadth band before filling new slots, while preserving PIT universe filtering, fixed-slot sizing, 25% sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.846 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0907 (need ≥ 0.20); sub-periods = [+3.951, +0.358])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.8458228752554415
- validation_folds: 13
- per_fold_sortinos: [2.5126, -1.3587, -2.6843, 7.1605, 13.5638, 4.6315, 4.212, 5.1471, 2.3778, 0.2303, 1.0597, 0.2511, -0.1076]
- calmar_mean: 6.186802097305973
- hit_rate_mean: 0.656647839340147
- profit_factor_mean: 4.5981596311335435
- trade_count_total: 110
- aggregate_max_dd: 0.17419511257602485
- worst_fold_max_dd: 0.13179492951198163
- max_position_frac_peak: 0.06560023052192407
- lower_quartile_fold_calmar: 0.2057772329669568
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 2.846 (-0.558). Aggregate DD was 17.4% versus previous kept 13.6%; negative folds were 3/13; trades=110. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.846 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0907 (need ≥ 0.20); sub-periods = [+3.951, +0.358]).

---

## Iteration 2026-05-17-550cc7a — REVERTED

**Hypothesis:** Adding a PIT-safe downside tail filter will improve validation Sortino by excluding momentum candidates whose recent path includes a large single-day loss, a common precursor to fragile rebounds and next-open downside slippage in a CNC book.

**Change:** I added a no-new-import recent tail-loss guard inside the existing score path, preserving PIT universe filtering, biweekly cadence, fixed-slot sizing, 25% sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.320 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1931 (need ≥ 0.20); sub-periods = [+4.417, +0.853])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.320098980549461
- validation_folds: 13
- per_fold_sortinos: [5.0924, 0.162, -1.0887, 5.696, 9.718, 6.4703, 5.926, 5.2861, 2.4884, 0.7693, 1.7772, 1.4059, -0.5415]
- calmar_mean: 7.345759352208794
- hit_rate_mean: 0.5460519118890159
- profit_factor_mean: 5.754888942483027
- trade_count_total: 186
- aggregate_max_dd: 0.12683663202366852
- worst_fold_max_dd: 0.10849577185030654
- max_position_frac_peak: 0.06515761487943814
- lower_quartile_fold_calmar: 1.575051018724876
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.320 (-0.084). Aggregate DD was 12.7% versus previous kept 13.6%; negative folds were 2/13; trades=186. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.320 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1931 (need ≥ 0.20); sub-periods = [+4.417, +0.853]).

---

## Iteration 2026-05-17-4a06d05 — REVERTED

**Hypothesis:** Adding a no-new-parameter liquidity participation guard should improve validation Sortino by avoiding momentum candidates whose recent advance is not supported by above-normal trading volume, which should reduce fragile entries and next-open slippage risk in the Dhan CNC book.

**Change:** I added PIT-safe volume-ratio scoring and filtering inside the existing rank path, requiring recent participation to be at least near its intermediate average while lightly rewarding healthier accumulation without changing cadence, sizing, sector caps, or imports.

**Decision:** REVERTED — sortino 1.926 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: bonferroni(p=0.0390 >= alpha/N=0.0333) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0391 (need ≥ 0.20); sub-periods = [+2.735, +0.107])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.9264134769484083
- validation_folds: 13
- per_fold_sortinos: [-0.2309, -0.0482, -3.0716, 2.344, 8.312, 4.9805, 5.2196, 3.9521, 3.1585, 0.5237, 0.2246, -0.9616, 0.6406]
- calmar_mean: 2.341248422598977
- hit_rate_mean: 0.5242046931925475
- profit_factor_mean: 3.242808483762074
- trade_count_total: 242
- aggregate_max_dd: 0.1319303203605249
- worst_fold_max_dd: 0.08074555887620871
- max_position_frac_peak: 0.08909672802411207
- lower_quartile_fold_calmar: -0.12330465168009397
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 1.926 (-1.477). Aggregate DD was 13.2% versus previous kept 13.6%; negative folds were 4/13; trades=242. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.926 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: bonferroni(p=0.0390 >= alpha/N=0.0333) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0391 (need ≥ 0.20); sub-periods = [+2.735, +0.107]).

---

## Iteration 2026-05-17-09f62a6 — REVERTED

**Hypothesis:** Increasing the fixed risk-slot count from 16 to 18 will improve mean validation Sortino by reducing single-name downside concentration while keeping the same proven PIT-safe momentum-quality ranker, gross exposure, cadence, and sector cap.

**Change:** I changed only n_positions from 16 to 18 so sizing remains fixed-slot gross/n_positions, blocked slots stay cash, and the existing sector-capped rank logic is preserved with slightly broader diversification.

**Decision:** REVERTED — sortino 3.291 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1918 (need ≥ 0.20); sub-periods = [+4.380, +0.840])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.291077957571126
- validation_folds: 13
- per_fold_sortinos: [5.0599, 0.4502, -0.9942, 5.0488, 9.1193, 7.1102, 5.9866, 5.3186, 2.3238, 0.2685, 1.6292, 2.0164, -0.5531]
- calmar_mean: 6.25792524673147
- hit_rate_mean: 0.5291208791208791
- profit_factor_mean: 5.1220991830380465
- trade_count_total: 186
- aggregate_max_dd: 0.12851044818909405
- worst_fold_max_dd: 0.10640587790176012
- max_position_frac_peak: 0.056886302844854485
- lower_quartile_fold_calmar: 0.4319876032285726
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.291 (-0.113). Aggregate DD was 12.9% versus previous kept 13.6%; negative folds were 2/13; trades=186. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.291 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1918 (need ≥ 0.20); sub-periods = [+4.380, +0.840]).

---

## Iteration 2026-05-17-4981859 — REVERTED

**Hypothesis:** Adding a PIT-safe recent downside-skew preference will improve validation Sortino by favoring momentum leaders whose recent volatility is more upside-driven than downside-driven, reducing fragile long entries without adding a new sizing or cadence parameter.

**Change:** I added a downside/upside semivolatility balance term using existing recent_days data, filtering only strongly downside-skewed candidates and lightly rewarding upside-skewed recent paths while preserving fixed-slot sizing, PIT universe filtering, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.263 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.262973336372913
- validation_folds: 13
- per_fold_sortinos: [4.5621, 0.1542, -0.9811, 5.5331, 9.7905, 6.2403, 5.6814, 5.2382, 2.3074, 0.6708, 1.9325, 1.7267, -0.4376]
- calmar_mean: 7.4143582371765655
- hit_rate_mean: 0.5516815010027678
- profit_factor_mean: 6.3065222550253015
- trade_count_total: 192
- aggregate_max_dd: 0.13461287021793353
- worst_fold_max_dd: 0.11635960389629917
- max_position_frac_peak: 0.06452462771242871
- lower_quartile_fold_calmar: 1.2475965156065907
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.263 (-0.141). Aggregate DD was 13.5% versus previous kept 13.6%; negative folds were 2/13; trades=192. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.263 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-3273648 — REVERTED

**Hypothesis:** Adding a no-new-parameter weak-market absolute trend guard will improve validation Sortino by avoiding long entries when the current liquid NSE universe median intermediate trend is negative, while preserving the proven stock-level ranker and fixed-slot sizing.

**Change:** I added a PIT-safe universe median intermediate-trend check at rebalance time and return an empty selection when fewer than half of active liquid stocks have positive 63-day trend, leaving blocked slots in cash instead of forcing long exposure during broad selloffs.

**Decision:** REVERTED — sortino 2.979 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.9785179543241354
- validation_folds: 13
- per_fold_sortinos: [4.7508, -0.6318, -1.7418, 4.1437, 8.1077, 6.825, 6.1282, 5.3333, 2.4051, 0.738, 2.0021, 1.7095, -1.0489]
- calmar_mean: 6.796625833647988
- hit_rate_mean: 0.49110195360195347
- profit_factor_mean: 4.460162796846111
- trade_count_total: 178
- aggregate_max_dd: 0.16758152893298914
- worst_fold_max_dd: 0.11477420168687472
- max_position_frac_peak: 0.06441810841618469
- lower_quartile_fold_calmar: 1.4664961067964615
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 2.979 (-0.425). Aggregate DD was 16.8% versus previous kept 13.6%; negative folds were 3/13; trades=178. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.979 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-edb1f36 — REVERTED

**Hypothesis:** Adding a PIT-safe same-day adverse news and event overlay will improve mean validation Sortino by avoiding momentum entries exposed to fresh negative company-specific catalysts while leaving the proven price ranker unchanged when no news evidence exists.

**Change:** I imported the existing llm.features accessors and added a guarded news/event adjustment that vetoes severe adverse catalyst days, mildly penalizes event risk, and lightly rewards confident positive sentiment without adding strategy params or changing sizing, cadence, sector caps, or execution contract.

**Decision:** REVERTED — sortino 3.404 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4038275153908293
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.3440874574941555
- hit_rate_mean: 0.5433581124757595
- profit_factor_mean: 5.780037413995571
- trade_count_total: 190
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.404 (+0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.404 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-c39f740 — REVERTED

**Hypothesis:** Adding a PIT-safe return-correlation diversification pass should improve validation Sortino by reducing clustered long exposure among otherwise high-ranked momentum candidates without changing the underlying price signal, cadence, or fixed-slot sizing.

**Change:** I changed the sector-cap selector into a greedy diversification selector that preserves the ranked signal but penalizes candidates whose recent returns are highly correlated with already selected names, leaving blocked slots as cash and keeping order_target_percent-only sizing.

**Decision:** REVERTED — sortino 3.359 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3586248578873974
- validation_folds: 13
- per_fold_sortinos: [5.4724, 0.4444, -0.9943, 5.4965, 9.8406, 6.3327, 5.713, 5.2382, 2.3074, 0.7007, 1.8529, 1.7115, -0.4541]
- calmar_mean: 7.432473429394244
- hit_rate_mean: 0.5517636209943901
- profit_factor_mean: 6.452153157128369
- trade_count_total: 181
- aggregate_max_dd: 0.13461287021793325
- worst_fold_max_dd: 0.11635960389629917
- max_position_frac_peak: 0.06452462771242871
- lower_quartile_fold_calmar: 1.319250113547918
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.359 (-0.045). Aggregate DD was 13.5% versus previous kept 13.6%; negative folds were 2/13; trades=181. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.359 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-cc7b992 — REVERTED

**Hypothesis:** Adding a PIT-safe sector-relative breadth tailwind to the existing ranker will improve validation Sortino by favoring momentum names whose whole sector is leading the current universe, without changing gross exposure, cadence, or fixed-slot sizing.

**Change:** I added a sector median trend context at rebalance time and used its centered sector tailwind as a small ranking term so selection tilts toward broad sector leadership while preserving PIT universe filtering, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.404 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4038275153908293
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.3440874574941555
- hit_rate_mean: 0.5433581124757595
- profit_factor_mean: 5.780037413995571
- trade_count_total: 190
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.404 (+0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.404 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-1b85e13 — REVERTED

**Hypothesis:** Adding a PIT-safe stale-price continuity filter will improve validation Sortino by excluding momentum candidates whose recent path contains too many zero-return or near-zero-return days, which are often suspended, illiquid, or mechanically stale despite passing the ADV universe screen.

**Change:** I added a no-new-parameter price-continuity quality check over the existing recent and volatility windows and veto candidates with excessive flat closes while preserving PIT universe filtering, fixed-slot sizing, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.404 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4038275153908293
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.3440874574941555
- hit_rate_mean: 0.5433581124757595
- profit_factor_mean: 5.780037413995571
- trade_count_total: 190
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.404 (+0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.404 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-960b61f — REVERTED

**Hypothesis:** Reducing the fixed slot count from 16 to 15 should improve validation Sortino by slightly concentrating the already filtered momentum-quality book while still satisfying the catastrophe-control minimum position count and leaving blocked slots as cash.

**Change:** I changed only n_positions from 16 to 15, preserving the existing PIT universe filter, biweekly cadence, sector cap, gap-risk filter, fixed-slot sizing, and order_target_percent-only execution contract.

**Decision:** REVERTED — sortino 3.328 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1267 (need ≥ 0.20); sub-periods = [+4.550, +0.576])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.32756740003344
- validation_folds: 13
- per_fold_sortinos: [4.7029, 0.3607, -0.963, 5.5837, 9.5299, 7.1377, 6.3434, 5.7485, 2.5091, 0.3288, 1.6053, 0.6325, -0.2611]
- calmar_mean: 6.93348717530831
- hit_rate_mean: 0.48749306249306257
- profit_factor_mean: 5.32221917923662
- trade_count_total: 143
- aggregate_max_dd: 0.13474134058418663
- worst_fold_max_dd: 0.10871705898432783
- max_position_frac_peak: 0.06660567569538296
- lower_quartile_fold_calmar: 0.458372623615363
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.328 (-0.076). Aggregate DD was 13.5% versus previous kept 13.6%; negative folds were 2/13; trades=143. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.328 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1267 (need ≥ 0.20); sub-periods = [+4.550, +0.576]).

---

## Iteration 2026-05-17-12557e8 — REVERTED

**Hypothesis:** Adding a PIT-safe post-rank trend-decay veto should improve validation Sortino by avoiding leaders whose 63-day intermediate momentum is positive but materially weaker than their 126-day trend, a common late-cycle fade pattern for biweekly long-only entries.

**Change:** I added one no-new-parameter acceleration check that rejects candidates whose intermediate return has fallen below half the per-day pace of the longer trend, preserving the existing ranker, sector cap, fixed-slot sizing, and order_target_percent-only contract.

**Decision:** REVERTED — sortino 3.150 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1547 (need ≥ 0.20); sub-periods = [+4.257, +0.658])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.149997595876274
- validation_folds: 13
- per_fold_sortinos: [5.9162, 0.6348, -1.1775, 4.0371, 8.3991, 6.6349, 5.998, 5.6614, 2.2122, -0.0528, 0.9602, 1.6141, 0.1123]
- calmar_mean: 6.2939364968450455
- hit_rate_mean: 0.5480274376201978
- profit_factor_mean: 5.417692870534991
- trade_count_total: 193
- aggregate_max_dd: 0.1471814837446827
- worst_fold_max_dd: 0.12822953483760025
- max_position_frac_peak: 0.0653016016220799
- lower_quartile_fold_calmar: 0.6286966709725401
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.150 (-0.254). Aggregate DD was 14.7% versus previous kept 13.6%; negative folds were 2/13; trades=193. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.150 did not improve on prev 3.4038275153908293 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1547 (need ≥ 0.20); sub-periods = [+4.257, +0.658]).

---

## Iteration 2026-05-17-60a640b — REVERTED

**Hypothesis:** Replacing the binary all-or-nothing selection with score-spread gated fixed-slot exposure will improve validation Sortino by keeping weak top-ranked names as cash when the candidate edge is shallow while preserving diversification, PIT universe filtering, and fixed-slot sizing.

**Change:** I added a no-new-parameter selection quality gate based on each candidate's score relative to the ranked universe median, so only names with clear cross-sectional edge receive the existing fixed-slot target and unfilled slots remain cash.

**Decision:** REVERTED — sortino 3.078 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.077605964667462
- validation_folds: 13
- per_fold_sortinos: [4.236, 0.0872, -0.7273, 4.1167, 8.1038, 6.822, 5.9826, 5.2388, 2.4051, 0.738, 2.0021, 1.7095, -0.7055]
- calmar_mean: 6.753361497750238
- hit_rate_mean: 0.5215506715506715
- profit_factor_mean: 4.452784284133417
- trade_count_total: 182
- aggregate_max_dd: 0.1326190989380106
- worst_fold_max_dd: 0.11477420168687472
- max_position_frac_peak: 0.06441810841618469
- lower_quartile_fold_calmar: 1.4664961067964615
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.078 (-0.326). Aggregate DD was 13.3% versus previous kept 13.6%; negative folds were 2/13; trades=182. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.078 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-63b847d — REVERTED

**Hypothesis:** Adding a sector-neutral rank adjustment will improve validation Sortino by preferring momentum leaders that are strong within their own sector rather than only riding crowded sector-wide beta, while preserving the existing 25% sector cap and fixed-slot sizing.

**Change:** I changed the ranking step to compute each ticker's raw score minus half of its sector median raw score, keeping sector-level tailwinds from dominating selection without adding a new hyperparameter.

**Decision:** REVERTED — sortino 3.404 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4038275153908293
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.3440874574941555
- hit_rate_mean: 0.5433581124757595
- profit_factor_mean: 5.780037413995571
- trade_count_total: 190
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.404 (+0.000). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.404 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-18c678e — REVERTED

**Hypothesis:** Adding a PIT-safe portfolio exposure haircut during broad-market stress should improve mean validation Sortino by reducing downside participation in weak NSE regimes while preserving the proven stock ranker and fixed-slot construction.

**Change:** I added a no-new-parameter market-stress multiplier that cuts gross exposure when the active universe has weak 63-day breadth and negative median trend, leaving selection, sector cap, PIT filtering, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.192 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.191569364222781
- validation_folds: 13
- per_fold_sortinos: [4.9178, 0.221, -1.1496, 4.8258, 8.8569, 6.5403, 6.0217, 5.237, 2.3849, 0.6771, 2.0021, 1.708, -0.7524]
- calmar_mean: 6.896216688644638
- hit_rate_mean: 0.5235735418427725
- profit_factor_mean: 5.294498254967012
- trade_count_total: 187
- aggregate_max_dd: 0.13417393664607882
- worst_fold_max_dd: 0.11571297308319804
- max_position_frac_peak: 0.06438980758096938
- lower_quartile_fold_calmar: 1.2834969077492755
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.192 (-0.212). Aggregate DD was 13.4% versus previous kept 13.6%; negative folds were 2/13; trades=187. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.192 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-f45e324 — REVERTED

**Hypothesis:** Softly rewarding PIT-safe excess 126-day trend versus the current filtered candidate median will improve validation Sortino by preferring idiosyncratic momentum leaders over broad-beta participants without leaving risk slots empty.

**Change:** I added a cross-sectional median-trend adjustment inside ranking only, preserving the existing filters, sector cap, fixed-slot sizing, and order_target_percent-only execution contract.

**Decision:** REVERTED — sortino 3.333 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.333417601728466
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.3607, 5.045, 9.7906, 6.6538, 5.946, 5.3258, 2.3645, 0.6727, 2.0021, 1.7051, -0.4348]
- calmar_mean: 7.282774935877682
- hit_rate_mean: 0.5340255332902392
- profit_factor_mean: 5.482181123193068
- trade_count_total: 190
- aggregate_max_dd: 0.13590021260108895
- worst_fold_max_dd: 0.1169849321117141
- max_position_frac_peak: 0.06453601287255391
- lower_quartile_fold_calmar: 1.250582384667222
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.333 (-0.070). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.333 did not improve on prev 3.4038275153908293.

---
