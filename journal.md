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

## Iteration 2026-05-17-df694cd — REVERTED

**Hypothesis:** Adding a no-new-parameter 21-day volatility-compression preference will improve validation Sortino by favoring momentum names whose recent risk is contracting rather than expanding, reducing fragile late-breakout entries while preserving fixed-slot diversification.

**Change:** I added a PIT-safe short-vol versus intermediate-vol comparison inside the existing score and vetoed names with sharply expanding recent volatility, so the ranker keeps the same universe, sector cap, cadence, and fixed-slot sizing contract.

**Decision:** REVERTED — sortino 3.139 did not improve on prev 3.4038275153908293

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.138560254511375
- validation_folds: 13
- per_fold_sortinos: [4.9399, -0.1144, -1.3088, 4.6144, 9.8261, 6.9791, 5.5324, 4.6266, 1.6721, 0.8763, 1.8062, 1.6269, -0.2754]
- calmar_mean: 7.578885591763408
- hit_rate_mean: 0.5402687496013288
- profit_factor_mean: 8.08570126303193
- trade_count_total: 192
- aggregate_max_dd: 0.14480516012956113
- worst_fold_max_dd: 0.12640104337863173
- max_position_frac_peak: 0.06548627587298662
- lower_quartile_fold_calmar: 1.9935283506633197
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.139 (-0.265). Aggregate DD was 14.5% versus previous kept 13.6%; negative folds were 3/13; trades=192. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.139 did not improve on prev 3.4038275153908293.

---

## Iteration 2026-05-17-7db6f7f — REVERTED

**Hypothesis:** Adding a PIT-safe continuous macro stress exposure gate should improve validation Sortino by cutting gross exposure only when India VIX percentile is elevated and Nifty is below its 200dma, using external market-state information not already captured by the stock ranker.

**Change:** I added optional llm.features macro scalars and a no-new-parameter gross-exposure multiplier in next(), preserving ranking, sector cap, fixed-slot sizing, and order_target_percent-only execution.

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

## Iteration 2026-05-17-b46e4dc — KEPT

**Hypothesis:** Using a fixed ISO-week parity for biweekly rebalances will improve validation Sortino by avoiding fold-start anchoring and testing the alternate Friday schedule without changing the stock-selection thesis or adding parameters.

**Change:** I changed the rebalance scheduler to honor the existing rebalance_week_parity parameter directly instead of resetting it to each fold's first eligible Friday, so the strategy trades the configured alternate-Friday calendar consistently.

**Decision:** KEPT — sortino 3.598 > prev 3.4038275153908293, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5982902404874557
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.8047, 5.9487, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, 2.0932]
- calmar_mean: 7.506087855062573
- hit_rate_mean: 0.5543471234647706
- profit_factor_mean: 6.175811542964128
- trade_count_total: 186
- aggregate_max_dd: 0.13582530924838732
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.624244030969848
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.404 to 3.598 (+0.194). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 1/13; trades=186. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.598 > prev 3.4038275153908293, agg_dd 13.6%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-b42426a — REVERTED

**Hypothesis:** Adding a PIT-safe prior-rebalance gap filter should improve validation Sortino by avoiding biweekly entries that already made an excessive two-week move since the last scheduled rebalance, reducing mean-reversion risk at the next-open fill while preserving the proven ranker and fixed-slot sizing.

**Change:** I added a no-new-parameter 10-trading-day exhaustion veto inside _score_for, using the existing biweekly cadence to reject names with an overly stretched prior-rebalance move without changing universe handling, sector caps, or order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.258 did not improve on prev 3.5982902404874557

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2580365587803906
- validation_folds: 13
- per_fold_sortinos: [3.9992, -0.0377, -1.0304, 3.4002, 7.1495, 7.4125, 5.601, 5.3014, 2.5973, 0.4681, 1.5225, 2.0589, 3.912]
- calmar_mean: 5.678226449417778
- hit_rate_mean: 0.5309731857294941
- profit_factor_mean: 7.211340601319114
- trade_count_total: 211
- aggregate_max_dd: 0.1237628200623666
- worst_fold_max_dd: 0.09944015098332096
- max_position_frac_peak: 0.08491364738798353
- lower_quartile_fold_calmar: 2.011939443791184
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 3.258 (-0.340). Aggregate DD was 12.4% versus previous kept 13.6%; negative folds were 2/13; trades=211. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.258 did not improve on prev 3.5982902404874557.

---

## Iteration 2026-05-17-36fa1f2 — REVERTED

**Hypothesis:** Adding a PIT-safe gap-adjusted fill-risk penalty will improve validation Sortino by favoring momentum names whose signal is less dependent on the current close being far above the prior close, reducing next-open reversal risk without changing gross exposure or fixed-slot sizing.

**Change:** I added a no-new-parameter close-gap quality term to the existing score, penalizing candidates with stretched current-close versus prior-close moves while preserving the existing universe, sector-cap, cadence, and order_target_percent-only contract.

**Decision:** REVERTED — sortino 3.430 did not improve on prev 3.5982902404874557

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4299851793194835
- validation_folds: 13
- per_fold_sortinos: [3.652, -0.0728, -0.9618, 5.5251, 9.7462, 6.6448, 5.9526, 5.2593, 2.3797, 0.6727, 2.0021, 1.7051, 2.0849]
- calmar_mean: 7.390763532787539
- hit_rate_mean: 0.5564991381167851
- profit_factor_mean: 5.869812237579589
- trade_count_total: 189
- aggregate_max_dd: 0.13582530924838682
- worst_fold_max_dd: 0.11728339561855498
- max_position_frac_peak: 0.0646215671969394
- lower_quartile_fold_calmar: 1.6224601257970628
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 3.430 (-0.168). Aggregate DD was 13.6% versus previous kept 13.6%; negative folds were 2/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.430 did not improve on prev 3.5982902404874557.

---

## Iteration 2026-05-17-4495103 — REVERTED

**Hypothesis:** Adding PIT-safe holding retention for already-held names that remain near the top of the current rank should improve net validation Sortino by reducing biweekly churn and DP-charge drag without changing the underlying momentum-quality signal or fixed-slot sizing.

**Change:** I changed sector-cap selection to retain eligible current holdings from the upper rank band before filling new names, preserving universe checks, the 25% sector cap, and gross/n_positions sizing.

**Decision:** REVERTED — sortino 2.893 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1299 (need ≥ 0.20); sub-periods = [+3.951, +0.513])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.8934819342554614
- validation_folds: 13
- per_fold_sortinos: [2.5126, -1.3587, -2.6843, 7.1605, 13.5638, 4.6315, 4.212, 5.1471, 2.3778, 0.2303, 1.0597, 0.2511, 0.512]
- calmar_mean: 6.246046969861258
- hit_rate_mean: 0.6673316000239077
- profit_factor_mean: 5.14238639198937
- trade_count_total: 107
- aggregate_max_dd: 0.17419511257602485
- worst_fold_max_dd: 0.13179492951198163
- max_position_frac_peak: 0.06560023052192407
- lower_quartile_fold_calmar: 0.26267705573324296
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 2.893 (-0.705). Aggregate DD was 17.4% versus previous kept 13.6%; negative folds were 2/13; trades=107. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.893 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1299 (need ≥ 0.20); sub-periods = [+3.951, +0.513]).

---

## Iteration 2026-05-17-e9d0262 — REVERTED

**Hypothesis:** Switching the fixed biweekly rebalance calendar to the opposite ISO-week parity will improve validation Sortino by testing the other persistent alternate-Friday execution path while leaving the proven selection, sizing, sector cap, and PIT universe mechanics unchanged.

**Change:** I changed rebalance_week_parity from 1 to 0 so the strategy trades the opposite alternate-Friday schedule without adding parameters or altering the stock-selection thesis.

**Decision:** REVERTED — sortino 2.669 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0413 (need ≥ 0.20); sub-periods = [+3.927, -0.162])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6689959025050856
- validation_folds: 13
- per_fold_sortinos: [3.1088, 1.3045, -0.7387, 5.0743, 9.8527, 6.6323, 3.9169, 4.1013, 2.093, -0.6713, 0.721, -0.2631, -0.4348]
- calmar_mean: 6.202075768841002
- hit_rate_mean: 0.48723914973914967
- profit_factor_mean: 3.990953801906124
- trade_count_total: 190
- aggregate_max_dd: 0.20835946656335097
- worst_fold_max_dd: 0.14196024438174965
- max_position_frac_peak: 0.07125204191064133
- lower_quartile_fold_calmar: -0.48176113741956855
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 2.669 (-0.929). Aggregate DD was 20.8% versus previous kept 13.6%; negative folds were 4/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.669 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0413 (need ≥ 0.20); sub-periods = [+3.927, -0.162]).

---

## Iteration 2026-05-17-5a64510 — REVERTED

**Hypothesis:** Adding a PIT-safe high-range extension veto will improve validation Sortino by avoiding momentum candidates whose intermediate trend is already too close to the top of its 63-day range, reducing late-breakout reversal risk while preserving the proven ranker and fixed-slot sizing.

**Change:** I added a no-new-parameter upper range-location filter inside _score_for, rejecting names above 0.92 of their 63-day close range while leaving cadence, universe, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 2.441 did not improve on prev 3.5982902404874557 | catastrophe: gross exposure: max 126.4% > 100% (cash account — leverage error)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.4408656415585295
- validation_folds: 13
- per_fold_sortinos: [1.3612, -0.6665, -1.4588, 3.5811, 10.2204, 8.5392, 3.1774, 1.6047, 1.5865, -0.1225, 0.2628, 2.8864, 0.7594]
- calmar_mean: 3.8487018171130485
- hit_rate_mean: 0.5284705207073628
- profit_factor_mean: 6.184962281575621
- trade_count_total: 239
- aggregate_max_dd: 0.1523102647540727
- worst_fold_max_dd: 0.12180404715175246
- max_position_frac_peak: 0.09549860876561397
- lower_quartile_fold_calmar: 0.2560281226861667
- n_negative_folds: 3/13
- risk.passed: False
- risk.violations: ['gross exposure: max 126.4% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 3.598 to 2.441 (-1.157). Aggregate DD was 15.2% versus previous kept 13.6%; negative folds were 3/13; trades=239. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 2.441 did not improve on prev 3.5982902404874557 | catastrophe: gross exposure: max 126.4% > 100% (cash account — leverage error).

---

## Iteration 2026-05-17-99c59e3 — REVERTED

**Hypothesis:** Adding a PIT-safe accumulation-volume confirmation will improve validation Sortino by favoring momentum leaders whose recent up moves are supported by stronger volume than down moves, reducing fragile price-only breakouts without changing cadence, gross exposure, or fixed-slot sizing.

**Change:** I added a no-new-parameter volume support term based on up-day versus down-day traded volume over the existing 63-day window, vetoing clear distribution patterns and softly rewarding accumulation while preserving all universe, sector-cap, and order_target_percent-only mechanics.

**Decision:** REVERTED — sortino 3.481 did not improve on prev 3.5982902404874557

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.481233094059728
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.432, -1.0257, 5.524, 9.7897, 6.3099, 5.6826, 5.239, 2.3074, 0.6708, 1.8987, 1.5364, 1.6987]
- calmar_mean: 7.559058194886154
- hit_rate_mean: 0.5430222680788291
- profit_factor_mean: 6.802027116372911
- trade_count_total: 186
- aggregate_max_dd: 0.13461287021793295
- worst_fold_max_dd: 0.11635960389629917
- max_position_frac_peak: 0.06452462771242871
- lower_quartile_fold_calmar: 1.2973899858766869
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 3.481 (-0.117). Aggregate DD was 13.5% versus previous kept 13.6%; negative folds were 1/13; trades=186. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.481 did not improve on prev 3.5982902404874557.

---

## Iteration 2026-05-17-25c082f — REVERTED

**Hypothesis:** Replacing the total realized-volatility penalty with downside realized volatility will improve validation Sortino by avoiding names with harmful downside variance while not penalizing orderly upside momentum.

**Change:** I added a PIT-safe downside-volatility computation and used it for the volatility veto and score penalty, leaving cadence, universe gating, sector cap, and fixed-slot order_target_percent sizing unchanged.

**Decision:** REVERTED — sortino 2.792 did not improve on prev 3.5982902404874557 | catastrophe: gross exposure: max 111.9% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0474 (need ≥ 0.20); sub-periods = [+3.950, +0.187])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7923104448422573
- validation_folds: 13
- per_fold_sortinos: [5.1076, -0.0237, -1.3022, 5.3211, 9.9782, 5.5461, 3.3863, 4.5627, 2.9757, -0.7875, 0.1546, -0.172, 1.5531]
- calmar_mean: 5.926659688493462
- hit_rate_mean: 0.5057862161785714
- profit_factor_mean: 5.538514196652321
- trade_count_total: 185
- aggregate_max_dd: 0.12554494517795162
- worst_fold_max_dd: 0.08720259757112449
- max_position_frac_peak: 0.0971980604331687
- lower_quartile_fold_calmar: -0.11926066932470222
- n_negative_folds: 4/13
- risk.passed: False
- risk.violations: ['gross exposure: max 111.9% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 3.598 to 2.792 (-0.806). Aggregate DD was 12.6% versus previous kept 13.6%; negative folds were 4/13; trades=185. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 2.792 did not improve on prev 3.5982902404874557 | catastrophe: gross exposure: max 111.9% > 100% (cash account — leverage error) | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0474 (need ≥ 0.20); sub-periods = [+3.950, +0.187]).

---

## Iteration 2026-05-17-c5af661 — REVERTED

**Hypothesis:** Replacing the primary 126-day momentum leg with skip-month momentum will improve validation Sortino by reducing short-term reversal exposure while preserving the proven intermediate trend, low-volatility, defensive-strength, sector-cap, and fixed-slot construction.

**Change:** I changed the main trend calculation and score term to use price at the 21-day lookback versus the 126-day lookback, keeping recent momentum only as a secondary confirmation so the ranker favors persistent 12-1 style momentum rather than stocks already extended into the rebalance close.

**Decision:** REVERTED — sortino 2.911 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0105 (need ≥ 0.20); sub-periods = [+4.186, +0.044])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.911461252992353
- validation_folds: 13
- per_fold_sortinos: [2.1857, -1.3622, -3.1226, 5.5841, 14.5893, 7.5371, 5.6374, 4.4268, 2.1982, 0.7394, 0.9085, -0.462, -1.0106]
- calmar_mean: 5.539443180414515
- hit_rate_mean: 0.5609873535212901
- profit_factor_mean: 5.738651015240075
- trade_count_total: 181
- aggregate_max_dd: 0.16556584647804043
- worst_fold_max_dd: 0.13240856944594556
- max_position_frac_peak: 0.06637761617380068
- lower_quartile_fold_calmar: -0.8231626845684792
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 2.911 (-0.687). Aggregate DD was 16.6% versus previous kept 13.6%; negative folds were 4/13; trades=181. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.911 did not improve on prev 3.5982902404874557 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0105 (need ≥ 0.20); sub-periods = [+4.186, +0.044]).

---

## Iteration 2026-05-17-0cd4108 — REVERTED

**Hypothesis:** Adding a PIT-safe market-internal breadth gate will improve validation Sortino by keeping the long-only book mostly in cash when fewer than half of the active liquid NSE universe has positive intermediate trend, reducing regime-wide drawdowns without adding new hyperparameters.

**Change:** I added a no-new-parameter breadth calculation over the active universe and require constructive intermediate breadth before selecting positions, while preserving the existing ranker, sector cap, fixed-slot sizing, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.141 did not improve on prev 3.5982902404874557

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.140984754072945
- validation_folds: 13
- per_fold_sortinos: [4.7508, -0.6318, -1.7418, 4.1437, 8.1077, 6.825, 6.1282, 5.3333, 2.4051, 0.738, 2.0021, 1.7095, 1.0632]
- calmar_mean: 6.926649547027119
- hit_rate_mean: 0.5081959706959706
- profit_factor_mean: 5.22045517475115
- trade_count_total: 175
- aggregate_max_dd: 0.16758152893298914
- worst_fold_max_dd: 0.11477420168687472
- max_position_frac_peak: 0.06441810841618469
- lower_quartile_fold_calmar: 1.4664961067964615
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 3.141 (-0.457). Aggregate DD was 16.8% versus previous kept 13.6%; negative folds were 2/13; trades=175. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.141 did not improve on prev 3.5982902404874557.

---

## Iteration 2026-05-17-6ec1ab7 — KEPT

**Hypothesis:** Tightening the 21-day recent-momentum floor from -8% to -4% will improve validation Sortino by avoiding deeper pullback candidates that have begun to break trend while preserving the existing intermediate-momentum thesis.

**Change:** I changed the recent-return entry veto in _score_for so candidates with worse than a 4% 21-day pullback are skipped, leaving cadence, fixed-slot sizing, sector caps, and ranking weights unchanged.

**Decision:** KEPT — sortino 3.628 > prev 3.5982902404874557, agg_dd 15.1%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.598 to 3.628 (+0.029). Aggregate DD was 15.1% versus previous kept 13.6%; negative folds were 1/13; trades=188. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.628 > prev 3.5982902404874557, agg_dd 15.1%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-231807c — REVERTED

**Hypothesis:** Tightening the one-day upside-exhaustion entry veto from 7.5% to 6.0% will improve validation Sortino by avoiding short-lived news-gap breakouts whose next-open fills are more reversal-prone while preserving the existing intermediate momentum thesis.

**Change:** I changed only the one-day return veto in _score_for so candidates up more than 6.0% on the signal close are skipped, leaving the ranker, fixed-slot sizing, sector cap, cadence, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.284 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1964 (need ≥ 0.20); sub-periods = [+4.363, +0.857])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2839774463038367
- validation_folds: 13
- per_fold_sortinos: [4.3595, 0.081, -1.2571, 5.4331, 9.7636, 6.6593, 5.9527, 5.9292, 2.3424, -0.1924, 0.958, 1.5477, 1.1148]
- calmar_mean: 6.989558997919898
- hit_rate_mean: 0.5457387849772941
- profit_factor_mean: 5.936199384266313
- trade_count_total: 191
- aggregate_max_dd: 0.16181858355494938
- worst_fold_max_dd: 0.13676595220299706
- max_position_frac_peak: 0.06546721193820755
- lower_quartile_fold_calmar: 0.8094643741462493
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.284 (-0.344). Aggregate DD was 16.2% versus previous kept 15.1%; negative folds were 2/13; trades=191. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.284 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1964 (need ≥ 0.20); sub-periods = [+4.363, +0.857]).

---

## Iteration 2026-05-17-ff22260 — REVERTED

**Hypothesis:** Adding a PIT-safe lower bound on 21-day moving-average distance will improve validation Sortino by filtering momentum candidates whose recent pullback has already broken below short-term trend support while preserving fixed-slot sizing and the existing ranker.

**Change:** I added a ma_distance < -0.025 entry veto inside _score_for so weak short-term breakdowns stay as cash rather than entering the long-only book.

**Decision:** REVERTED — sortino 3.541 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.541097513370888
- validation_folds: 13
- per_fold_sortinos: [5.2811, -0.4905, -2.2755, 5.3742, 10.1697, 7.5007, 5.9166, 5.5685, 2.3488, 0.4948, 1.9875, 1.5747, 2.5836]
- calmar_mean: 7.948975115274454
- hit_rate_mean: 0.5524938643667741
- profit_factor_mean: 6.342836179779393
- trade_count_total: 211
- aggregate_max_dd: 0.16388665116290688
- worst_fold_max_dd: 0.11679257822720988
- max_position_frac_peak: 0.06556790097520072
- lower_quartile_fold_calmar: 1.9888652397286233
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.541 (-0.087). Aggregate DD was 16.4% versus previous kept 15.1%; negative folds were 2/13; trades=211. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.541 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-43749ee — REVERTED

**Hypothesis:** Increasing the fixed risk slots from 16 to 18 will improve mean validation Sortino by reducing single-name concentration and downside variance while preserving the currently kept ranker, biweekly cadence, sector cap, and fixed-slot cash discipline.

**Change:** I changed only n_positions from 16 to 18 so each selected name receives a smaller fixed allocation while filtered or blocked slots still remain cash.

**Decision:** REVERTED — sortino 3.493 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4929560237790724
- validation_folds: 13
- per_fold_sortinos: [5.0599, 0.3699, -0.9253, 5.1848, 9.1198, 7.1093, 5.988, 5.5469, 2.3167, 0.1473, 1.6309, 2.0368, 1.8233]
- calmar_mean: 6.410372786880712
- hit_rate_mean: 0.541784685902333
- profit_factor_mean: 5.560345233822021
- trade_count_total: 184
- aggregate_max_dd: 0.14218645198740137
- worst_fold_max_dd: 0.11413589621282746
- max_position_frac_peak: 0.05682154318202802
- lower_quartile_fold_calmar: 1.3159926789426324
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.493 (-0.135). Aggregate DD was 14.2% versus previous kept 15.1%; negative folds were 1/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.493 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-cb0da60 — REVERTED

**Hypothesis:** Reducing fixed risk slots from 16 to 15 will improve validation Sortino by concentrating capital slightly more in the highest-ranked names while staying within the catastrophe and position-count constraints.

**Change:** I changed only n_positions from 16 to the allowed floor of 15, preserving fixed-slot sizing, sector caps, the biweekly calendar, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4515527078967096
- validation_folds: 13
- per_fold_sortinos: [4.7029, 0.287, -0.8222, 5.7739, 9.507, 7.1352, 6.3456, 5.8345, 2.5867, 0.3278, 1.6027, 0.6307, 0.9584]
- calmar_mean: 7.069279102100814
- hit_rate_mean: 0.5188420553805171
- profit_factor_mean: 5.352644492443058
- trade_count_total: 148
- aggregate_max_dd: 0.13438997596957955
- worst_fold_max_dd: 0.1084497308933861
- max_position_frac_peak: 0.06616960180051587
- lower_quartile_fold_calmar: 0.6568001675824231
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.452 (-0.176). Aggregate DD was 13.4% versus previous kept 15.1%; negative folds were 1/13; trades=148. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880]).

---

## Iteration 2026-05-17-ae8a1bd — REVERTED

**Hypothesis:** Adding a PIT-safe short-horizon reversal penalty for stocks whose last five trading days are sharply negative will improve validation Sortino by avoiding entries where the existing 21-day trend filter is too slow to catch fresh breakdowns.

**Change:** I added a five-day return check inside _score_for that vetoes candidates down more than 6.5% over the last week while leaving the kept ranker, fixed-slot sizing, sector cap, and biweekly cadence unchanged.

**Decision:** REVERTED — sortino 3.492 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.491899140249208
- validation_folds: 13
- per_fold_sortinos: [5.1923, -0.1872, -1.5134, 5.7202, 9.5354, 6.3467, 5.6887, 5.5987, 2.2564, 0.4697, 2.1237, 2.0555, 2.1081]
- calmar_mean: 7.531239098144147
- hit_rate_mean: 0.5476682003265714
- profit_factor_mean: 6.110895409529236
- trade_count_total: 199
- aggregate_max_dd: 0.15661771942508448
- worst_fold_max_dd: 0.12609570439934592
- max_position_frac_peak: 0.06436736691028637
- lower_quartile_fold_calmar: 1.6153860112574003
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.492 (-0.136). Aggregate DD was 15.7% versus previous kept 15.1%; negative folds were 2/13; trades=199. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.492 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-2f21a81 — REVERTED

**Hypothesis:** Adding a PIT-safe long-horizon trend alignment check will improve validation Sortino by keeping the existing intermediate momentum ranker out of short-lived rebounds that remain below their broader 9-month trend.

**Change:** I added a long_trend leg derived from existing trend_days and vol_days, requiring positive 189-day trend and lightly rewarding it in the score while preserving fixed-slot sizing, biweekly cadence, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.247 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.246727395264047
- validation_folds: 13
- per_fold_sortinos: [5.4791, 0.0641, -1.3244, 5.4779, 9.6308, 4.4203, 5.9474, 5.5079, 2.6243, 0.0514, 1.5526, 2.0775, 0.6984]
- calmar_mean: 6.349499764384325
- hit_rate_mean: 0.5290766763468597
- profit_factor_mean: 4.148053805692067
- trade_count_total: 186
- aggregate_max_dd: 0.12895083257269452
- worst_fold_max_dd: 0.11448392367737874
- max_position_frac_peak: 0.06427304359228458
- lower_quartile_fold_calmar: 0.5576090036121251
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.247 (-0.381). Aggregate DD was 12.9% versus previous kept 15.1%; negative folds were 3/13; trades=186. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.247 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-892da68 — REVERTED

**Hypothesis:** Adding a PIT-safe 63-day high-watermark breakout-quality reward will improve validation Sortino by preferring momentum names making fresh but not exhausted intermediate highs, distinct from prior range-location tuning because it rewards confirmed upside continuation instead of penalizing high range extension.

**Change:** I added a high-watermark confirmation helper and incorporated it as a modest score reward while preserving the existing filters, fixed-slot sizing, sector cap, and biweekly cadence.

**Decision:** REVERTED — sortino 3.556 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.555658603219305
- validation_folds: 13
- per_fold_sortinos: [4.6824, 0.0807, -0.9122, 5.725, 9.7918, 6.8079, 5.9473, 5.5363, 2.3905, 0.6988, 2.0246, 1.5842, 1.8663]
- calmar_mean: 7.495747660425219
- hit_rate_mean: 0.5538824109525466
- profit_factor_mean: 6.214332297334982
- trade_count_total: 190
- aggregate_max_dd: 0.14074839335855777
- worst_fold_max_dd: 0.11631014954299089
- max_position_frac_peak: 0.06340544234749454
- lower_quartile_fold_calmar: 1.4380730275186426
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.556 (-0.072). Aggregate DD was 14.1% versus previous kept 15.1%; negative folds were 1/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.556 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-9aaff00 — REVERTED

**Hypothesis:** Tightening the 21-day recent-momentum floor from -4% to -2% will improve validation Sortino by excluding weakening pullback candidates while preserving the kept intermediate momentum and low-volatility ranker.

**Change:** I changed only the recent return veto in _score_for from recent < -0.04 to recent < -0.02, leaving sizing, cadence, sector caps, PIT universe enforcement, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.289 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2891032923970567
- validation_folds: 13
- per_fold_sortinos: [5.1829, 0.1721, -1.2984, 4.7958, 8.2709, 6.1594, 6.4126, 5.6219, 2.2169, 0.581, 1.9133, 1.5254, 1.2044]
- calmar_mean: 6.811500654755514
- hit_rate_mean: 0.5332151006359152
- profit_factor_mean: 4.64521330054754
- trade_count_total: 198
- aggregate_max_dd: 0.15148804026040077
- worst_fold_max_dd: 0.12629381536230963
- max_position_frac_peak: 0.06440607341076221
- lower_quartile_fold_calmar: 0.9653800466218739
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.289 (-0.339). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=198. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.289 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-9643b82 — REVERTED

**Hypothesis:** Adding a PIT-safe liquidity/participation proxy through recent volume stability will improve validation Sortino by avoiding thin or irregularly traded momentum names whose price signals are more prone to gap and fill noise under Dhan delivery costs.

**Change:** I added a recent-volume consistency check and small score reward using only historical feed volume, preserving the existing fixed-slot sizing, sector cap, PIT universe enforcement, and biweekly cadence.

**Decision:** REVERTED — sortino 3.560 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5598000020285565
- validation_folds: 13
- per_fold_sortinos: [4.1867, 0.3336, -0.6419, 5.3946, 9.5453, 6.7233, 5.9474, 5.5469, 2.4743, 0.2098, 2.0183, 2.0364, 2.5029]
- calmar_mean: 7.3583735407734485
- hit_rate_mean: 0.5166057547279267
- profit_factor_mean: 4.3862068966635706
- trade_count_total: 195
- aggregate_max_dd: 0.14015843440115217
- worst_fold_max_dd: 0.10961957249255248
- max_position_frac_peak: 0.06326102937093966
- lower_quartile_fold_calmar: 1.780295602109625
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.560 (-0.068). Aggregate DD was 14.0% versus previous kept 15.1%; negative folds were 1/13; trades=195. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.560 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-0535cc6 — REVERTED

**Hypothesis:** Tightening the sector cap from 25% to about 20% will improve validation Sortino by reducing sector-cluster drawdowns while preserving the current proven stock-level momentum/quality ranker.

**Change:** I changed only the sector_cap parameter from 0.25 to 0.20 so the 16-slot book can hold at most three names per classified sector instead of four, leaving signal logic, cadence, fixed-slot sizing, and PIT universe enforcement unchanged.

**Decision:** REVERTED — sortino 3.472 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.471515850089183
- validation_folds: 13
- per_fold_sortinos: [4.538, 0.4419, -0.6488, 5.6777, 9.4277, 7.0434, 6.1965, 5.8416, 2.6299, 0.3194, 1.6735, 0.8808, 1.108]
- calmar_mean: 6.714571028828539
- hit_rate_mean: 0.520765132303594
- profit_factor_mean: 5.783511140101205
- trade_count_total: 147
- aggregate_max_dd: 0.13264550140641787
- worst_fold_max_dd: 0.10562025213945446
- max_position_frac_peak: 0.0615548420186634
- lower_quartile_fold_calmar: 0.6957270701772478
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.472 (-0.156). Aggregate DD was 13.3% versus previous kept 15.1%; negative folds were 1/13; trades=147. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.472 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-3dba668 — REVERTED

**Hypothesis:** Adding a PIT-safe continuous macro de-risking overlay will improve validation Sortino by cutting fixed-slot gross exposure during broad-market trend stress or high India VIX regimes while leaving the proven stock ranker unchanged.

**Change:** I imported continuous macro signals from llm.features and added a gross-exposure scaler in next() that keeps fixed n_positions sizing but leaves more cash when Nifty is below its 200DMA or India VIX percentile is elevated.

**Decision:** REVERTED — sortino 3.525 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.525274663287535
- validation_folds: 13
- per_fold_sortinos: [5.1239, 0.3219, -1.0144, 5.1648, 9.2383, 6.6554, 5.946, 6.0395, 3.1008, 0.3713, 1.7173, 1.4879, 1.6758]
- calmar_mean: 7.192951165900895
- hit_rate_mean: 0.5468037806838713
- profit_factor_mean: 6.000826735278253
- trade_count_total: 182
- aggregate_max_dd: 0.11811032778721371
- worst_fold_max_dd: 0.10080245794519255
- max_position_frac_peak: 0.061569788217822996
- lower_quartile_fold_calmar: 1.39197619235361
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.525 (-0.102). Aggregate DD was 11.8% versus previous kept 15.1%; negative folds were 1/13; trades=182. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.525 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-962bfe2 — REVERTED

**Hypothesis:** Adding the already-computed 63-day intermediate momentum as a primary score leg while modestly reducing the 126-day trend weight will improve validation Sortino by selecting fresher continuation leaders without adding another filter or hyperparameter.

**Change:** I changed only the rank score formula to blend intermediate momentum into the existing trend score, preserving all PIT universe checks, fixed-slot sizing, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.138 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1378325820258826
- validation_folds: 13
- per_fold_sortinos: [4.5705, 0.1143, -1.3078, 4.6315, 9.0413, 6.2816, 5.2547, 5.0306, 2.2968, 0.3241, 1.1554, 1.2169, 2.1819]
- calmar_mean: 6.6282151163848
- hit_rate_mean: 0.5269624926686132
- profit_factor_mean: 4.351289532706356
- trade_count_total: 206
- aggregate_max_dd: 0.14612185686961876
- worst_fold_max_dd: 0.1185597268560483
- max_position_frac_peak: 0.083107691439385
- lower_quartile_fold_calmar: 1.6882861194446352
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.138 (-0.490). Aggregate DD was 14.6% versus previous kept 15.1%; negative folds were 1/13; trades=206. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.138 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-2a9b231 — REVERTED

**Hypothesis:** Switching from biweekly to four-week rebalancing will improve validation Sortino by cutting Dhan fixed sell-charge turnover while preserving the slow 126-day momentum edge.

**Change:** I changed only the rebalance cadence from every 2 weeks to every 4 weeks and updated the strategy docstring, leaving ranking, fixed-slot sizing, PIT universe enforcement, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.179 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1654 (need ≥ 0.20); sub-periods = [+4.277, +0.708])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.17852872274392
- validation_folds: 13
- per_fold_sortinos: [3.5111, 0.763, 0.0659, 5.446, 8.4035, 6.2404, 4.3657, 6.4037, 3.2916, -0.4569, 0.3375, 1.3454, 1.604]
- calmar_mean: 6.812767543390047
- hit_rate_mean: 0.5492338857723472
- profit_factor_mean: 9.499666736702022
- trade_count_total: 121
- aggregate_max_dd: 0.14450312775576404
- worst_fold_max_dd: 0.11836473947775542
- max_position_frac_peak: 0.06190281015663274
- lower_quartile_fold_calmar: 0.9395874728413957
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.179 (-0.449). Aggregate DD was 14.5% versus previous kept 15.1%; negative folds were 2/13; trades=121. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.179 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1654 (need ≥ 0.20); sub-periods = [+4.277, +0.708]).

---

## Iteration 2026-05-17-c843544 — REVERTED

**Hypothesis:** Adding a small incumbent-retention score bonus will improve validation Sortino by reducing marginal biweekly churn and Dhan sell-charge drag while still requiring every retained name to pass the existing PIT-safe trend, volatility, drawdown, range, and sector-cap filters.

**Change:** I added a turnover-aware holding retention adjustment inside ranking so already-held qualified names get a modest score boost near the selection cutoff, preserving fixed-slot sizing, biweekly cadence, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.388 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3876582986680015
- validation_folds: 13
- per_fold_sortinos: [4.7136, -0.0527, -1.0464, 5.5345, 9.4141, 6.449, 5.8422, 5.4827, 2.3384, 0.5744, 1.7781, 1.5487, 1.463]
- calmar_mean: 7.520035094251288
- hit_rate_mean: 0.5502465483234714
- profit_factor_mean: 8.236946874663339
- trade_count_total: 172
- aggregate_max_dd: 0.14883592861276154
- worst_fold_max_dd: 0.12408256686858746
- max_position_frac_peak: 0.06443682432271629
- lower_quartile_fold_calmar: 1.1918074507768628
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.388 (-0.240). Aggregate DD was 14.9% versus previous kept 15.1%; negative folds were 2/13; trades=172. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.388 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-90c9093 — REVERTED

**Hypothesis:** Replacing raw 126-day momentum scoring with a clipped momentum score will improve validation Sortino by reducing overextended winner concentration while preserving the existing PIT-safe trend-selection thesis.

**Change:** I capped the trend contribution used in ranking at 55% so extreme long-horizon moves no longer dominate otherwise similar candidates, leaving filters, cadence, fixed-slot sizing, universe enforcement, and sector caps unchanged.

**Decision:** REVERTED — sortino 1.671 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0825 >= alpha/N=0.0100)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.6713303090546465
- validation_folds: 13
- per_fold_sortinos: [1.9452, -2.5904, -3.4947, -0.3881, 5.8072, 3.6193, 3.7989, 7.5868, 3.1158, 3.7127, 2.6007, -1.2065, -2.7796]
- calmar_mean: 0.8585187201244922
- hit_rate_mean: 0.5023523736193419
- profit_factor_mean: 5.126823896745308
- trade_count_total: 188
- aggregate_max_dd: 0.13925440847463974
- worst_fold_max_dd: 0.07631101755882859
- max_position_frac_peak: 0.06278953113133047
- lower_quartile_fold_calmar: -0.6862474605268165
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 1.671 (-1.956). Aggregate DD was 13.9% versus previous kept 15.1%; negative folds were 5/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.671 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0825 >= alpha/N=0.0100).

---

## Iteration 2026-05-17-25655c0 — REVERTED

**Hypothesis:** Adding a PIT-safe minimum trend-efficiency floor will improve validation Sortino by excluding choppy positive-momentum names whose gains came through unstable paths rather than persistent accumulation.

**Change:** I tightened the existing 63-day trend-efficiency eligibility check from -0.05 to 0.02 while leaving cadence, ranking weights, fixed-slot sizing, PIT universe enforcement, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.613 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6125821636152526
- validation_folds: 13
- per_fold_sortinos: [5.1914, 0.3163, -0.9846, 5.6849, 9.6958, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.450367572413736
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.159421839754112
- trade_count_total: 188
- aggregate_max_dd: 0.1511863714656785
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.613 (-0.015). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.613 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-54da3c4 — REVERTED

**Hypothesis:** Increasing gross exposure modestly from 97% to 99% will improve validation Sortino by raising the return earned by the already-kept signal while staying below the 100% gross hard limit and diluting fixed Dhan DP-charge drag per unit of exposure.

**Change:** I changed only the fixed gross_exposure parameter from 0.97 to 0.99, leaving ranking, filters, PIT universe enforcement, fixed-slot sizing, sector cap, cadence, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.577 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5767343719361246
- validation_folds: 13
- per_fold_sortinos: [5.1293, 0.2405, -1.0565, 5.7338, 9.7684, 6.8162, 5.8977, 5.5247, 2.3379, 0.5446, 1.9562, 1.7198, 1.885]
- calmar_mean: 7.589787539688569
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 5.862186739158906
- trade_count_total: 188
- aggregate_max_dd: 0.15299987299366946
- worst_fold_max_dd: 0.12778446537563545
- max_position_frac_peak: 0.0657038888845818
- lower_quartile_fold_calmar: 1.4964132590230728
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.577 (-0.051). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.577 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-8eee07e — REVERTED

**Hypothesis:** Adding a PIT-safe shallow-liquidity-stress veto based on recent zero-or-near-zero price movement will improve validation Sortino by avoiding stale or mechanically pinned names whose momentum scores are unreliable despite passing ADV universe membership.

**Change:** I added a flat-price-day fraction check over the 63-day volatility window and reject candidates with excessive near-zero daily movement, preserving the existing ranker, fixed-slot sizing, biweekly cadence, universe enforcement, and sector cap.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-f6abdf5 — REVERTED

**Hypothesis:** Shifting the biweekly rebalance schedule to the opposite Friday parity will improve mean validation Sortino by reducing unlucky entry/exit timing while preserving the proven signal, fixed-slot sizing, sector cap, and Dhan delivery turnover profile.

**Change:** I changed only rebalance_week_parity from 1 to 0, leaving the ranking model, filters, fixed-slot sizing, PIT universe enforcement, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 2.244 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0366 (need ≥ 0.20); sub-periods = [+3.295, -0.120])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2440424353655413
- validation_folds: 13
- per_fold_sortinos: [2.9924, 0.4341, -1.3196, 4.4775, 8.9584, 5.9583, 3.301, 3.2972, 1.5552, -0.3932, 0.7183, -0.3562, -0.4509]
- calmar_mean: 5.3341989922552715
- hit_rate_mean: 0.45521924656540036
- profit_factor_mean: 2.8308507741343223
- trade_count_total: 200
- aggregate_max_dd: 0.20225691346389785
- worst_fold_max_dd: 0.14316940109491239
- max_position_frac_peak: 0.07325720077384909
- lower_quartile_fold_calmar: -0.4973263939642089
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.244 (-1.384). Aggregate DD was 20.2% versus previous kept 15.1%; negative folds were 4/13; trades=200. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.244 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0366 (need ≥ 0.20); sub-periods = [+3.295, -0.120]).

---

## Iteration 2026-05-17-4f89902 — REVERTED

**Hypothesis:** Adding a PIT-safe sector-momentum confirmation term will improve validation Sortino by favoring strong stocks whose intermediate momentum is aligned with their sector while the existing 25% sector cap prevents over-concentration.

**Change:** I added an active-universe sector median return helper and a modest sector-relative score component, leaving fixed-slot sizing, PIT universe enforcement, biweekly cadence, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-21ca3b1 — REVERTED

**Hypothesis:** Replacing part of the raw trend ranking with volatility-adjusted trend will improve validation Sortino by favoring steadier momentum leaders without changing universe membership, cadence, sector cap, or fixed-slot sizing.

**Change:** I added a capped risk_adjusted_trend score inside _score_for and shifted some weight from raw 126-day trend to this steadier momentum measure.

**Decision:** REVERTED — sortino 3.494 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4941463338215963
- validation_folds: 13
- per_fold_sortinos: [4.369, -0.1224, -1.2142, 5.7203, 9.7201, 6.5994, 5.9527, 5.4473, 2.4332, 0.5616, 1.9919, 1.851, 2.114]
- calmar_mean: 7.4547770146971555
- hit_rate_mean: 0.5187889159608616
- profit_factor_mean: 5.266702953249273
- trade_count_total: 191
- aggregate_max_dd: 0.14537173852373736
- worst_fold_max_dd: 0.11979466387698916
- max_position_frac_peak: 0.0652791769917805
- lower_quartile_fold_calmar: 1.670654588306082
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.494 (-0.134). Aggregate DD was 14.5% versus previous kept 15.1%; negative folds were 2/13; trades=191. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.494 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-eb482c9 — REVERTED

**Hypothesis:** Adding an active-universe breadth confirmation gate will improve validation Sortino by holding cash on rebalance dates when too few PIT universe names have positive 63-day momentum, avoiding broad-market drawdown regimes without using external macro labels.

**Change:** I added a PIT-safe median 63-day breadth calculation from the active universe and require at least 52% positive intermediate momentum before ranking, preserving the existing stock score, fixed-slot sizing, sector cap, cadence, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.090 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: parsimony(baseline params=8, strategy=9; +1 param(s) need Sortino +0.10, has -0.54)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.089512926676443
- validation_folds: 13
- per_fold_sortinos: [4.7508, -0.7174, -1.5785, 4.2843, 7.6511, 6.3325, 6.0772, 5.517, 2.5096, 0.5545, 1.9883, 1.7316, 1.0626]
- calmar_mean: 6.392082046767415
- hit_rate_mean: 0.5036171470560611
- profit_factor_mean: 5.396638360321149
- trade_count_total: 169
- aggregate_max_dd: 0.16971774086650526
- worst_fold_max_dd: 0.12158873478469112
- max_position_frac_peak: 0.06450034369066955
- lower_quartile_fold_calmar: 0.8981107094562876
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.090 (-0.538). Aggregate DD was 17.0% versus previous kept 15.1%; negative folds were 2/13; trades=169. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.090 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: parsimony(baseline params=8, strategy=9; +1 param(s) need Sortino +0.10, has -0.54).

---

## Iteration 2026-05-17-457b51e — REVERTED

**Hypothesis:** Replacing the volatility penalty with downside-only realized volatility will improve validation Sortino by no longer penalizing upside momentum variance while still avoiding names with unstable drawdowns.

**Change:** I changed the realized-volatility calculation used by the existing filter and rank penalty to annualized downside semi-volatility, preserving all current parameters, PIT universe enforcement, fixed-slot sizing, cadence, and sector cap.

**Decision:** REVERTED — sortino 3.059 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1804 (need ≥ 0.20); sub-periods = [+4.090, +0.738])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0585798753915374
- validation_folds: 13
- per_fold_sortinos: [4.924, -0.3117, -1.523, 5.3557, 10.0012, 5.9855, 3.7797, 5.1233, 3.4763, -0.3899, 1.1998, 0.7872, 1.3536]
- calmar_mean: 6.217223092559187
- hit_rate_mean: 0.5185527624977493
- profit_factor_mean: 4.6407579753196435
- trade_count_total: 191
- aggregate_max_dd: 0.13485148831708155
- worst_fold_max_dd: 0.088188550893691
- max_position_frac_peak: 0.09412910390253837
- lower_quartile_fold_calmar: 1.0361169417551208
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.059 (-0.569). Aggregate DD was 13.5% versus previous kept 15.1%; negative folds were 3/13; trades=191. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.059 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1804 (need ≥ 0.20); sub-periods = [+4.090, +0.738]).

---

## Iteration 2026-05-17-058c786 — REVERTED

**Hypothesis:** Adding a PIT-safe single-name gap-risk veto will improve validation Sortino by avoiding momentum names whose recent path contains large downside gaps that the current volatility and drawdown filters under-penalize.

**Change:** I added a recent worst one-day loss check inside the existing score filter, with no new params, to reject stocks showing abrupt gap-down behavior while preserving the kept ranking, fixed-slot sizing, sector cap, and rebalance cadence.

**Decision:** REVERTED — sortino 2.750 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1353 (need ≥ 0.20); sub-periods = [+3.747, +0.507])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7499604786754386
- validation_folds: 13
- per_fold_sortinos: [1.2989, 0.3159, -1.4468, 5.2719, 9.5286, 5.6838, 4.5833, 5.6852, 2.8011, -0.1063, 0.4024, 0.5929, 1.1384]
- calmar_mean: 6.4735342408939225
- hit_rate_mean: 0.5161490470313999
- profit_factor_mean: 5.153425817899615
- trade_count_total: 189
- aggregate_max_dd: 0.11658830289513698
- worst_fold_max_dd: 0.08745308142777315
- max_position_frac_peak: 0.06515805136069924
- lower_quartile_fold_calmar: 0.4747571328983913
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.750 (-0.878). Aggregate DD was 11.7% versus previous kept 15.1%; negative folds were 2/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.750 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1353 (need ≥ 0.20); sub-periods = [+3.747, +0.507]).

---

## Iteration 2026-05-17-d283a0d — REVERTED

**Hypothesis:** Adding a PIT-safe adverse-news veto will improve validation Sortino by avoiding momentum names with recent negative sentiment or risk-event flags that price-only volatility and drawdown filters miss.

**Change:** I imported the existing point-in-time LLM sentiment/events/news_volume features and added a conservative adverse-news adjustment inside scoring, with no new strategy parameters and preserving fixed-slot sizing, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-ee6e52a — REVERTED

**Hypothesis:** Increasing fixed risk slots from 16 to 18 will improve validation Sortino by reducing single-name concentration and fold drawdown without changing the proven PIT-safe momentum-quality ranking thesis.

**Change:** I changed only the existing n_positions parameter from 16 to 18, preserving fixed-slot sizing, biweekly cadence, sector cap, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.493 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4929560237790724
- validation_folds: 13
- per_fold_sortinos: [5.0599, 0.3699, -0.9253, 5.1848, 9.1198, 7.1093, 5.988, 5.5469, 2.3167, 0.1473, 1.6309, 2.0368, 1.8233]
- calmar_mean: 6.410372786880712
- hit_rate_mean: 0.541784685902333
- profit_factor_mean: 5.560345233822021
- trade_count_total: 184
- aggregate_max_dd: 0.14218645198740137
- worst_fold_max_dd: 0.11413589621282746
- max_position_frac_peak: 0.05682154318202802
- lower_quartile_fold_calmar: 1.3159926789426324
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.493 (-0.135). Aggregate DD was 14.2% versus previous kept 15.1%; negative folds were 1/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.493 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-c092a39 — REVERTED

**Hypothesis:** Reducing fixed risk slots from 16 to the allowed minimum of 15 will improve mean validation Sortino by concentrating the already-filtered momentum-quality edge while keeping gross exposure, sector cap, PIT universe enforcement, and drawdown controls unchanged.

**Change:** I changed only the existing n_positions parameter from 16 to 15 so sizing remains fixed-slot and all filtered/blocked slots still stay cash.

**Decision:** REVERTED — sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4515527078967096
- validation_folds: 13
- per_fold_sortinos: [4.7029, 0.287, -0.8222, 5.7739, 9.507, 7.1352, 6.3456, 5.8345, 2.5867, 0.3278, 1.6027, 0.6307, 0.9584]
- calmar_mean: 7.069279102100814
- hit_rate_mean: 0.5188420553805171
- profit_factor_mean: 5.352644492443058
- trade_count_total: 148
- aggregate_max_dd: 0.13438997596957955
- worst_fold_max_dd: 0.1084497308933861
- max_position_frac_peak: 0.06616960180051587
- lower_quartile_fold_calmar: 0.6568001675824231
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.452 (-0.176). Aggregate DD was 13.4% versus previous kept 15.1%; negative folds were 1/13; trades=148. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880]).

---

## Iteration 2026-05-17-a152377 — REVERTED

**Hypothesis:** Adding a PIT-safe market-correlation penalty will improve validation Sortino by preferring idiosyncratic momentum leaders that are less exposed to broad-market drawdown regimes while preserving the existing fixed-slot momentum-quality construction.

**Change:** I added a no-new-parameter rolling correlation-to-market score using the existing defensive window and median active-universe returns, then lightly penalized highly index-like names in the ranking.

**Decision:** REVERTED — sortino 3.510 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5104055388595676
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.3332, 5.6827, 5.4913, 2.2947, 0.5532, 1.9361, 1.5488, 1.6947]
- calmar_mean: 7.599557109457933
- hit_rate_mean: 0.556474276100973
- profit_factor_mean: 6.710501609273385
- trade_count_total: 186
- aggregate_max_dd: 0.1501003457800104
- worst_fold_max_dd: 0.12507613102150425
- max_position_frac_peak: 0.06461734605147335
- lower_quartile_fold_calmar: 1.3569063625337874
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.510 (-0.117). Aggregate DD was 15.0% versus previous kept 15.1%; negative folds were 1/13; trades=186. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.510 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-48e1a49 — REVERTED

**Hypothesis:** Using canonical skip-month momentum for the primary trend leg will improve validation Sortino by avoiding short-term reversal and overextension while preserving the existing recent-strength confirmation.

**Change:** I changed the main 126-day trend calculation to exclude the most recent 21 trading days, leaving the existing filters, fixed-slot sizing, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.172 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0296 (need ≥ 0.20); sub-periods = [+4.523, +0.134])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.172180266753134
- validation_folds: 13
- per_fold_sortinos: [2.5037, -1.192, -2.9658, 5.2435, 12.9584, 8.5449, 6.8852, 6.0194, 2.706, 0.0356, 0.8606, 0.1184, -0.4795]
- calmar_mean: 5.734708546822079
- hit_rate_mean: 0.5306813849800276
- profit_factor_mean: 4.861883870888473
- trade_count_total: 192
- aggregate_max_dd: 0.16045538136391663
- worst_fold_max_dd: 0.13043510315711548
- max_position_frac_peak: 0.06641238608789221
- lower_quartile_fold_calmar: -0.16892503969950276
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.172 (-0.456). Aggregate DD was 16.0% versus previous kept 15.1%; negative folds were 4/13; trades=192. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.172 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0296 (need ≥ 0.20); sub-periods = [+4.523, +0.134]).

---

## Iteration 2026-05-17-d0df633 — REVERTED

**Hypothesis:** Adding a PIT-safe volume-accumulation confirmation will improve validation Sortino by favoring momentum names whose trend is supported by recent participation rather than thin price drift.

**Change:** I added a no-new-parameter recent-versus-intermediate volume ratio score using existing recent_days and vol_days, with a mild penalty for volume contraction and a capped reward for constructive accumulation.

**Decision:** REVERTED — sortino 3.387 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3873149600808166
- validation_folds: 13
- per_fold_sortinos: [5.0725, 0.4805, -1.5147, 4.8689, 9.7651, 6.6567, 5.3403, 5.2118, 2.471, 0.5928, 1.9435, 1.2476, 1.8991]
- calmar_mean: 7.085350051555053
- hit_rate_mean: 0.5227604095251154
- profit_factor_mean: 5.657595605535775
- trade_count_total: 196
- aggregate_max_dd: 0.14202664315912114
- worst_fold_max_dd: 0.11799622281326275
- max_position_frac_peak: 0.06583544398098763
- lower_quartile_fold_calmar: 1.2845083026989013
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.387 (-0.240). Aggregate DD was 14.2% versus previous kept 15.1%; negative folds were 1/13; trades=196. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.387 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-d344d13 — REVERTED

**Hypothesis:** Replacing score-level retention with a final-selection incumbent hysteresis pass will improve validation Sortino by cutting avoidable Dhan sell-charge turnover while retaining only names that still pass the existing PIT-safe filters and near-cutoff rank window.

**Change:** I added stateful last-selection tracking and changed sector-capped selection to retain previously selected tickers that remain in the qualified near-cutoff pool before filling remaining fixed slots by rank.

**Decision:** REVERTED — sortino 3.072 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.0717204851143203
- validation_folds: 13
- per_fold_sortinos: [2.3153, -1.0933, -2.122, 5.8402, 13.696, 4.7752, 4.3068, 5.5098, 2.4016, -0.3217, 1.7058, 1.5802, 1.3384]
- calmar_mean: 6.21650718289598
- hit_rate_mean: 0.591993903532365
- profit_factor_mean: 7.241895820049664
- trade_count_total: 104
- aggregate_max_dd: 0.1707203449112662
- worst_fold_max_dd: 0.1326177110761884
- max_position_frac_peak: 0.06700391049130472
- lower_quartile_fold_calmar: 1.4873447632430414
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.072 (-0.556). Aggregate DD was 17.1% versus previous kept 15.1%; negative folds were 3/13; trades=104. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.072 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-de5c528 — REVERTED

**Hypothesis:** Adding a PIT-safe macro-regime exposure throttle will improve validation Sortino by moving the book partially or fully to cash during India risk-off and shock regimes while leaving the existing stock-selection edge unchanged in neutral and risk-on regimes.

**Change:** I imported macro_regime and added a no-new-parameter gross-exposure multiplier in next: shock liquidates, risk_off carries half gross using the same fixed-slot sizing, and neutral/risk_on preserve the current construction.

**Decision:** REVERTED — sortino 3.541 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5412293935081114
- validation_folds: 13
- per_fold_sortinos: [5.2073, 0.3327, -1.0303, 5.6019, 9.6922, 6.8289, 5.9487, 5.5379, 2.3802, 0.0299, 2.1549, 1.6828, 1.6689]
- calmar_mean: 7.2128979108891835
- hit_rate_mean: 0.5091709760827408
- profit_factor_mean: 6.0280732169529765
- trade_count_total: 182
- aggregate_max_dd: 0.15124544304167936
- worst_fold_max_dd: 0.12605256109817975
- max_position_frac_peak: 0.06435838110043943
- lower_quartile_fold_calmar: 1.2744669037112022
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.541 (-0.086). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 2/13; trades=182. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.541 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-26ccc20 — REVERTED

**Hypothesis:** Replacing the binary macro-regime throttle with a continuous Nifty-50 200-DMA exposure scaler will improve validation Sortino by cutting gross exposure only during objectively weak index regimes while preserving the stock-selection edge in normal markets.

**Change:** I imported nifty_vs_200dma_pct and added a smooth PIT-safe gross-exposure multiplier in next, using current gross when Nifty is above its 200-DMA, partial cash below it, and full liquidation only in deep index weakness.

**Decision:** REVERTED — sortino 3.282 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.281981275995771
- validation_folds: 13
- per_fold_sortinos: [4.7508, 0.229, -1.0148, 3.8509, 8.104, 6.8218, 5.9828, 5.459, 2.4, 0.5854, 1.9883, 1.7262, 1.7823]
- calmar_mean: 6.868120261519881
- hit_rate_mean: 0.5371162334397629
- profit_factor_mean: 5.015173124368818
- trade_count_total: 183
- aggregate_max_dd: 0.15138796047723346
- worst_fold_max_dd: 0.12404537217213206
- max_position_frac_peak: 0.06441513019779876
- lower_quartile_fold_calmar: 1.3521146378327087
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.282 (-0.346). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=183. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.282 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-41009a9 — REVERTED

**Hypothesis:** Replacing the raw linear stock score with a cross-sectional rank-normalized composite will improve validation Sortino by making selection less sensitive to regime-dependent feature scale shifts while preserving the existing PIT-safe momentum-quality thesis.

**Change:** I changed ranking to compute feature components once per ticker, then rank-normalize each component across the active universe before applying the existing directional preferences, sector cap, fixed-slot sizing, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 1.973 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0330 >= alpha/N=0.0100)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.9727572379282978
- validation_folds: 13
- per_fold_sortinos: [0.4415, -1.2511, -2.6927, 0.4041, 4.284, 4.4159, 6.9314, 7.5866, 3.008, 0.0223, 1.412, 1.8512, -0.7671]
- calmar_mean: 1.076191694429991
- hit_rate_mean: 0.5305073131996209
- profit_factor_mean: 4.964059980466778
- trade_count_total: 182
- aggregate_max_dd: 0.10812375397677464
- worst_fold_max_dd: 0.06506354647654959
- max_position_frac_peak: 0.06166576945148685
- lower_quartile_fold_calmar: -0.0074855542813612175
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 1.973 (-1.655). Aggregate DD was 10.8% versus previous kept 15.1%; negative folds were 4/13; trades=182. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.973 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0330 >= alpha/N=0.0100).

---

## Iteration 2026-05-17-f1eb652 — REVERTED

**Hypothesis:** Adding a PIT-safe medium-term acceleration confirmation will improve validation Sortino by preferring names whose 63-day trend is stronger than their older 126-day trend instead of buying decelerating long-horizon winners.

**Change:** I added a no-new-parameter trend-acceleration term and veto inside _score_for, using existing 63-day and 126-day price anchors to penalize stale momentum and reward improving intermediate trend strength.

**Decision:** REVERTED — sortino 2.971 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1546 (need ≥ 0.20); sub-periods = [+4.016, +0.621])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.971392581638597
- validation_folds: 13
- per_fold_sortinos: [5.9482, 0.426, -1.6468, 4.0801, 8.5765, 6.1299, 5.2896, 5.5782, 1.7632, -0.5086, 1.1724, 1.0764, 0.7432]
- calmar_mean: 6.367388421446052
- hit_rate_mean: 0.5642794303814785
- profit_factor_mean: 5.860106958377431
- trade_count_total: 200
- aggregate_max_dd: 0.17444768622095014
- worst_fold_max_dd: 0.13645762623925814
- max_position_frac_peak: 0.06666111768111285
- lower_quartile_fold_calmar: 0.9334462062100942
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.971 (-0.656). Aggregate DD was 17.4% versus previous kept 15.1%; negative folds were 2/13; trades=200. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.971 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1546 (need ≥ 0.20); sub-periods = [+4.016, +0.621]).

---

## Iteration 2026-05-17-f0115ee — REVERTED

**Hypothesis:** Adding PIT-safe recent close-location accumulation will improve validation Sortino by favoring momentum names that consistently finish near the upper part of their daily ranges, a price-action quality signal not captured by close-to-close trend or volatility.

**Change:** I added a recent OHLC close-strength helper and folded it into the existing score with a mild veto and reward, preserving fixed-slot sizing, sector caps, PIT universe enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.481 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.4807880166597127
- validation_folds: 13
- per_fold_sortinos: [0.8309, 0.9129, -0.9266, 3.9746, 7.4764, 4.6108, 4.7777, 5.259, 2.0908, 0.3266, 1.3571, 0.4414, 1.1186]
- calmar_mean: 5.264538303450926
- hit_rate_mean: 0.5437399588715378
- profit_factor_mean: 6.002896576076447
- trade_count_total: 200
- aggregate_max_dd: 0.14133606605219504
- worst_fold_max_dd: 0.12231826859302491
- max_position_frac_peak: 0.06393327232880203
- lower_quartile_fold_calmar: 0.7809506990616777
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.481 (-1.147). Aggregate DD was 14.1% versus previous kept 15.1%; negative folds were 1/13; trades=200. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.481 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-ca89660 — REVERTED

**Hypothesis:** Adding a PIT-safe active-universe relative-momentum confirmation will improve validation Sortino by selecting stocks whose 63-day advance beats the contemporaneous median NSE universe move, separating true leaders from names merely lifted by broad beta.

**Change:** I added cross-sectional median market return over the volatility window and require/reward excess intermediate momentum, while preserving the existing fixed-slot sizing, sector cap, PIT universe filter, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.555 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5551330947298427
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 6.3851, 2.7064, -0.1527, 0.9547, 1.6296, 1.8159]
- calmar_mean: 7.306364464094143
- hit_rate_mean: 0.5542518881319787
- profit_factor_mean: 6.282076887690187
- trade_count_total: 188
- aggregate_max_dd: 0.1527179362166496
- worst_fold_max_dd: 0.13140516072296712
- max_position_frac_peak: 0.06544632741637497
- lower_quartile_fold_calmar: 1.433601542442653
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.555 (-0.073). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 2/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.555 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-dc0a5c7 — REVERTED

**Hypothesis:** Adding a PIT-safe turnover hysteresis buffer for currently held names will improve validation Sortino by reducing avoidable Dhan DP-charge churn while only retaining incumbents that still rank near the fixed-slot cutoff.

**Change:** I added incumbent-aware final selection that seeds eligible current holdings from the top retention band before filling remaining slots by score, preserving fixed-slot sizing, PIT universe enforcement, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.977 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1555 (need ≥ 0.20); sub-periods = [+4.023, +0.626])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.9774731584846843
- validation_folds: 13
- per_fold_sortinos: [2.3153, -1.0933, -2.1093, 6.1726, 13.6958, 4.907, 4.3038, 5.6034, 2.4091, -0.1455, 1.0647, 1.1132, 0.4702]
- calmar_mean: 6.1432749112377145
- hit_rate_mean: 0.597376128145359
- profit_factor_mean: 6.024466265031993
- trade_count_total: 122
- aggregate_max_dd: 0.16986485258677864
- worst_fold_max_dd: 0.13286325243404437
- max_position_frac_peak: 0.06682105958757667
- lower_quartile_fold_calmar: 0.5200957848910502
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.977 (-0.650). Aggregate DD was 17.0% versus previous kept 15.1%; negative folds were 3/13; trades=122. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.977 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1555 (need ≥ 0.20); sub-periods = [+4.023, +0.626]).

---

## Iteration 2026-05-17-470e15c — REVERTED

**Hypothesis:** Adding a PIT-safe low-beta defensive participation term will improve validation Sortino by favoring momentum leaders that advance without relying heavily on broad-market up days, reducing drawdown sensitivity while preserving the existing stock-selection edge.

**Change:** I added a market-beta helper over the existing defensive window and used it as a mild score penalty for high-beta names plus a small reward for positive stock returns on weak market days.

**Decision:** REVERTED — sortino 3.280 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.280010791992617
- validation_folds: 13
- per_fold_sortinos: [1.318, 0.3758, -1.1554, 5.1807, 9.624, 6.65, 5.9471, 5.5215, 2.3654, 0.5568, 1.9883, 1.7712, 2.4967]
- calmar_mean: 7.348448834005286
- hit_rate_mean: 0.5496901979368043
- profit_factor_mean: 5.4470982591722095
- trade_count_total: 193
- aggregate_max_dd: 0.1511009225985191
- worst_fold_max_dd: 0.12518919206626114
- max_position_frac_peak: 0.0640483028531064
- lower_quartile_fold_calmar: 1.983102822248246
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.280 (-0.348). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=193. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.280 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-60196a4 — REVERTED

**Hypothesis:** Adding a PIT-safe long-horizon trend smoothness veto will improve validation Sortino by avoiding extended winners whose 126-day return is dominated by a small number of jump days rather than persistent accumulation.

**Change:** I added a 126-day return concentration helper and lightly veto/penalize jump-dominated trends while preserving fixed-slot sizing, PIT universe enforcement, sector caps, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.605 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6049266290537285
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.4646, 2.3561, 0.557, 1.9868, 1.7283, 1.8935]
- calmar_mean: 7.487771564639833
- hit_rate_mean: 0.540765625776938
- profit_factor_mean: 5.812394175730228
- trade_count_total: 188
- aggregate_max_dd: 0.15130025262259741
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 1.4875243016053252
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.605 (-0.023). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.605 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-410e80d — REVERTED

**Hypothesis:** Replacing greedy sector-cap selection with sector-balanced round-robin selection will improve validation Sortino by reducing hot-sector clustering while preserving the proven stock-level momentum-quality ranking and fixed-slot sizing.

**Change:** I changed only the final sector-cap selector so it fills positions in score-ordered sector rounds, keeping the same scoring model, PIT universe enforcement, 25% sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-e777bfe — REVERTED

**Hypothesis:** Adding a PIT-safe downside tail-risk penalty will improve validation Sortino by avoiding momentum names whose recent return distribution contains clustered large negative days that are not fully captured by realized volatility or max drawdown.

**Change:** I added a left-tail return quality helper over the existing volatility window and use it as a veto plus score penalty, preserving fixed-slot sizing, PIT universe filtering, sector cap enforcement, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 0.966 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0790 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0873 (need ≥ 0.20); sub-periods = [+1.451, -0.127])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.9656887845391945
- validation_folds: 13
- per_fold_sortinos: [1.675, -2.0698, -3.2462, -0.9881, 1.3508, 3.1287, 4.1513, 5.1944, 3.8647, 0.5382, 0.2467, -1.7061, 0.4145]
- calmar_mean: 0.7491119115903293
- hit_rate_mean: 0.4813130245822554
- profit_factor_mean: 3.209471002477341
- trade_count_total: 149
- aggregate_max_dd: 0.08811084320197661
- worst_fold_max_dd: 0.048261250214893144
- max_position_frac_peak: 0.06199747517987977
- lower_quartile_fold_calmar: -0.42090460304385013
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 0.966 (-2.662). Aggregate DD was 8.8% versus previous kept 15.1%; negative folds were 4/13; trades=149. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 0.966 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0790 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0873 (need ≥ 0.20); sub-periods = [+1.451, -0.127]).

---

## Iteration 2026-05-17-62ff9dc — REVERTED

**Hypothesis:** Adding a PIT-safe 126-day range-location anchor will improve validation Sortino by preferring momentum names trading in the upper part of their full trend window, distinguishing durable breakouts from shorter intermediate rebounds already captured by the 63-day range signal.

**Change:** I added a long-window range-location check and mild score term using the existing trend window, requiring candidates to sit above the midpoint of their 126-day close range while favoring names near but not excessively beyond the upper range.

**Decision:** REVERTED — sortino 3.550 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5497888018017485
- validation_folds: 13
- per_fold_sortinos: [5.0725, 0.0028, -1.3155, 5.7259, 9.7905, 6.6539, 5.9472, 5.5158, 2.3815, 0.5568, 1.9883, 1.7262, 2.1014]
- calmar_mean: 7.501536347631426
- hit_rate_mean: 0.5467404516047051
- profit_factor_mean: 6.042273659786421
- trade_count_total: 192
- aggregate_max_dd: 0.15118637146567918
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6117105253899844
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.550 (-0.078). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 2/13; trades=192. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.550 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-e580dda — REVERTED

**Hypothesis:** Adding a PIT-safe short-term reversal risk check will improve validation Sortino by avoiding momentum candidates that have just printed an unusually large 5-day advance relative to their own recent daily volatility, which current raw fast-return exhaustion does not volatility-normalize.

**Change:** I added a 5-day z-scored surge helper and use it as a mild veto plus score penalty so the strategy keeps buying intermediate uptrends but avoids volatility-adjusted blow-off entries.

**Decision:** REVERTED — sortino 3.579 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5787061120452504
- validation_folds: 13
- per_fold_sortinos: [5.0682, 0.3146, -0.9867, 5.682, 9.6746, 6.8048, 5.9485, 5.3203, 2.3301, 0.557, 1.9868, 1.7283, 2.0947]
- calmar_mean: 7.418553112760083
- hit_rate_mean: 0.5500147100260222
- profit_factor_mean: 6.0632813611500795
- trade_count_total: 190
- aggregate_max_dd: 0.15265634392862487
- worst_fold_max_dd: 0.12739062749370667
- max_position_frac_peak: 0.06432477621632594
- lower_quartile_fold_calmar: 1.6082769161341615
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.579 (-0.049). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 1/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.579 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-d4598d7 — REVERTED

**Hypothesis:** Adding a PIT-safe overnight gap fragility penalty will improve validation Sortino by avoiding momentum candidates whose trend has been driven by unstable overnight gaps rather than intraday follow-through, which should matter for CNC fills at the next open.

**Change:** I added an open-to-prior-close gap quality helper and use it as a mild veto plus score term while preserving the existing fixed-slot sizing, PIT universe filter, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.820 did not improve on prev 3.6277126896862444 | aggregate DD regressed: 48.7% > prev 15.1% + 10pp tolerance | catastrophe: gross exposure: max 183.6% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0340 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1857 (need ≥ 0.20); sub-periods = [+4.439, -0.824])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.819508799107724
- validation_folds: 13
- per_fold_sortinos: [4.3595, -0.2682, -1.318, 5.7174, 9.7629, 6.6853, 5.8233, 5.9778, 3.2107, -0.2848, -2.5707, -2.5341, 2.0927]
- calmar_mean: 6.311341207842769
- hit_rate_mean: 0.5408941485864562
- profit_factor_mean: 5.76820728291538
- trade_count_total: 194
- aggregate_max_dd: 0.48681762525174654
- worst_fold_max_dd: 0.3232739247937124
- max_position_frac_peak: 0.08177033921017364
- lower_quartile_fold_calmar: -0.7647158852340372
- n_negative_folds: 5/13
- risk.passed: False
- risk.violations: ['gross exposure: max 183.6% > 100% (cash account — leverage error)']

**Learning:** Sortino changed from 3.628 to 2.820 (-0.808). Aggregate DD was 48.7% versus previous kept 15.1%; negative folds were 5/13; trades=194. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: sortino 2.820 did not improve on prev 3.6277126896862444 | aggregate DD regressed: 48.7% > prev 15.1% + 10pp tolerance | catastrophe: gross exposure: max 183.6% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.0340 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.1857 (need ≥ 0.20); sub-periods = [+4.439, -0.824]).

---

## Iteration 2026-05-17-6894b6d — REVERTED

**Hypothesis:** Adding a PIT-safe cross-sectional breadth gate will improve validation Sortino by keeping the book invested only when enough active NSE names have positive intermediate trends, avoiding weak-market momentum traps without relying on coarse macro labels.

**Change:** I added an active-universe 63-day positive-trend breadth calculation and use it to require constructive market participation before ranking candidates, while preserving fixed-slot sizing, sector caps, PIT filtering, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.159 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: parsimony(baseline params=8, strategy=10; +2 param(s) need Sortino +0.20, has -0.47)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1592703992044564
- validation_folds: 13
- per_fold_sortinos: [4.7508, -0.7174, -1.6764, 4.3243, 8.1086, 6.824, 6.1365, 5.6354, 2.3169, 0.5854, 1.9883, 1.7316, 1.0626]
- calmar_mean: 6.91112004482518
- hit_rate_mean: 0.5025359632825697
- profit_factor_mean: 5.310556469255042
- trade_count_total: 177
- aggregate_max_dd: 0.16971774086650526
- worst_fold_max_dd: 0.1267144863370063
- max_position_frac_peak: 0.06441513019779876
- lower_quartile_fold_calmar: 0.9731764478147087
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.159 (-0.468). Aggregate DD was 17.0% versus previous kept 15.1%; negative folds were 2/13; trades=177. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.159 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: parsimony(baseline params=8, strategy=10; +2 param(s) need Sortino +0.20, has -0.47).

---

## Iteration 2026-05-17-b0cdde2 — REVERTED

**Hypothesis:** Adding a PIT-safe liquidity participation quality term will improve validation Sortino by preferring momentum candidates whose recent advances are supported by volume expansion rather than low-participation price drift.

**Change:** I added a volume-trend helper that compares recent volume to the longer trend-window average, lightly vetoes collapsing participation, and rewards moderate accumulation without changing fixed-slot sizing or universe/sector constraints.

**Decision:** REVERTED — sortino 2.823 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1470 (need ≥ 0.20); sub-periods = [+3.828, +0.563])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.823093148521248
- validation_folds: 13
- per_fold_sortinos: [1.0155, 0.4876, -0.6521, 5.5739, 9.5277, 5.7822, 4.782, 5.4807, 2.4523, -0.8463, -0.3825, 0.9226, 2.5567]
- calmar_mean: 6.26451439302543
- hit_rate_mean: 0.5526504326426926
- profit_factor_mean: 7.263973761166134
- trade_count_total: 193
- aggregate_max_dd: 0.16412033434499249
- worst_fold_max_dd: 0.10119349131183407
- max_position_frac_peak: 0.06534550010899906
- lower_quartile_fold_calmar: 0.45630840438921805
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.823 (-0.805). Aggregate DD was 16.4% versus previous kept 15.1%; negative folds were 3/13; trades=193. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.823 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1470 (need ≥ 0.20); sub-periods = [+3.828, +0.563]).

---

## Iteration 2026-05-17-7989a82 — REVERTED

**Hypothesis:** Adding a PIT-safe adverse-news and event-risk overlay will improve validation Sortino by avoiding momentum candidates whose recent classifier-confirmed negative headlines create idiosyncratic gap risk not captured by price-only volatility and drawdown filters.

**Change:** I imported the existing LLM feature accessors and added a five-session news/event adjustment that vetoes severe negative sentiment or adverse events while only lightly nudging ranks for ordinary sentiment, leaving fixed-slot sizing, PIT universe filtering, sector caps, and rebalance cadence unchanged.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-740e840 — REVERTED

**Hypothesis:** Increasing fixed risk slots from 16 to 18 will improve validation Sortino by reducing single-name concentration and drawdown drag while preserving the existing proven ranking signal, sector cap, and cash-aware fixed-slot sizing.

**Change:** Changed only the existing n_positions parameter from 16 to 18 so each selected name receives a smaller fixed allocation without adding new hyperparameters or altering the signal family.

**Decision:** REVERTED — sortino 3.493 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4929560237790724
- validation_folds: 13
- per_fold_sortinos: [5.0599, 0.3699, -0.9253, 5.1848, 9.1198, 7.1093, 5.988, 5.5469, 2.3167, 0.1473, 1.6309, 2.0368, 1.8233]
- calmar_mean: 6.410372786880712
- hit_rate_mean: 0.541784685902333
- profit_factor_mean: 5.560345233822021
- trade_count_total: 184
- aggregate_max_dd: 0.14218645198740137
- worst_fold_max_dd: 0.11413589621282746
- max_position_frac_peak: 0.05682154318202802
- lower_quartile_fold_calmar: 1.3159926789426324
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.493 (-0.135). Aggregate DD was 14.2% versus previous kept 15.1%; negative folds were 1/13; trades=184. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.493 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-f8c1bf2 — REVERTED

**Hypothesis:** Reducing fixed risk slots from 16 to 15 will improve validation Sortino by concentrating slightly more capital in the strongest already-filtered momentum-quality names while staying inside the catastrophe and sector-cap constraints.

**Change:** Changed only the existing n_positions parameter from 16 to 15, preserving the proven PIT ranking, fixed-slot sizing, sector cap, and order_target_percent-only execution without adding hyperparameters.

**Decision:** REVERTED — sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4515527078967096
- validation_folds: 13
- per_fold_sortinos: [4.7029, 0.287, -0.8222, 5.7739, 9.507, 7.1352, 6.3456, 5.8345, 2.5867, 0.3278, 1.6027, 0.6307, 0.9584]
- calmar_mean: 7.069279102100814
- hit_rate_mean: 0.5188420553805171
- profit_factor_mean: 5.352644492443058
- trade_count_total: 148
- aggregate_max_dd: 0.13438997596957955
- worst_fold_max_dd: 0.1084497308933861
- max_position_frac_peak: 0.06616960180051587
- lower_quartile_fold_calmar: 0.6568001675824231
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.452 (-0.176). Aggregate DD was 13.4% versus previous kept 15.1%; negative folds were 1/13; trades=148. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.452 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1915 (need ≥ 0.20); sub-periods = [+4.595, +0.880]).

---

## Iteration 2026-05-17-12af9cb — REVERTED

**Hypothesis:** Raising fixed-slot gross exposure from 0.97 to 0.99 will improve validation Sortino by diluting fixed per-scrip Dhan DP charges while keeping target gross below the 100% catastrophe gate.

**Change:** I changed only the existing gross_exposure parameter from 0.97 to 0.99, preserving the proven PIT ranking, fixed-slot sizing, sector cap, and rebalance cadence without adding parameters.

**Decision:** REVERTED — sortino 3.577 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5767343719361246
- validation_folds: 13
- per_fold_sortinos: [5.1293, 0.2405, -1.0565, 5.7338, 9.7684, 6.8162, 5.8977, 5.5247, 2.3379, 0.5446, 1.9562, 1.7198, 1.885]
- calmar_mean: 7.589787539688569
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 5.862186739158906
- trade_count_total: 188
- aggregate_max_dd: 0.15299987299366946
- worst_fold_max_dd: 0.12778446537563545
- max_position_frac_peak: 0.0657038888845818
- lower_quartile_fold_calmar: 1.4964132590230728
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.577 (-0.051). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.577 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-fc52d3f — REVERTED

**Hypothesis:** Adding a PIT-safe minimum score margin for selected names will improve validation Sortino by keeping weakly qualified momentum candidates as cash instead of forcing every fixed slot to hold a marginal name.

**Change:** I added a no-new-parameter score-quality cutoff inside sector-cap selection, using the ranked universe's own score distribution to require selected names to have positive absolute score and remain near the upper cross-sectional tail while preserving fixed-slot sizing.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-a569e34 — REVERTED

**Hypothesis:** Replacing the primary momentum leg with a one-week-lagged trend score will improve validation Sortino by reducing rank reward for names whose apparent 126-day momentum is mostly a just-printed short-term surge, while preserving the existing fixed-slot construction.

**Change:** I changed only _score_for so the main trend threshold and weighted trend score use the close five sessions ago versus trend_days ago, with current full-window trend still required positive and all sizing, sector-cap, and universe rules unchanged.

**Decision:** REVERTED — sortino 2.958 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1229 (need ≥ 0.20); sub-periods = [+4.051, +0.498])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.957796279672531
- validation_folds: 13
- per_fold_sortinos: [2.9995, -0.4219, -1.2463, 5.2507, 9.3387, 6.9314, 6.5824, 4.9537, 2.072, 0.2852, 1.1061, 0.1075, 0.4922]
- calmar_mean: 6.726494258717063
- hit_rate_mean: 0.5296922848393436
- profit_factor_mean: 4.656013915009388
- trade_count_total: 206
- aggregate_max_dd: 0.15346720961716487
- worst_fold_max_dd: 0.1298411277507001
- max_position_frac_peak: 0.0647021346917195
- lower_quartile_fold_calmar: 0.39511166374154116
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.958 (-0.670). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 3/13; trades=206. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.958 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1229 (need ≥ 0.20); sub-periods = [+4.051, +0.498]).

---

## Iteration 2026-05-17-10a5086 — REVERTED

**Hypothesis:** Adding a no-new-parameter macro stress throttle will improve validation Sortino by cutting gross exposure only when India VIX stress and Nifty 50 trend deterioration coincide, reducing downside folds without changing the proven stock-ranking signal.

**Change:** I imported the PIT-safe continuous macro helpers and added a gross-exposure multiplier in next so fixed-slot target weights are reduced during broad-market stress while ranking, universe membership, sector caps, and order_target_percent-only execution remain unchanged.

**Decision:** REVERTED — sortino 3.530 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.530384116656502
- validation_folds: 13
- per_fold_sortinos: [5.1666, 0.3327, -1.0081, 5.2429, 9.3243, 6.6544, 5.9474, 5.5226, 2.3481, 0.5583, 1.9883, 1.7262, 2.0915]
- calmar_mean: 7.289828307411558
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 5.973127827401834
- trade_count_total: 188
- aggregate_max_dd: 0.15190348090517095
- worst_fold_max_dd: 0.12564220082077235
- max_position_frac_peak: 0.06449473238090761
- lower_quartile_fold_calmar: 1.6069110377672802
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.530 (-0.097). Aggregate DD was 15.2% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.530 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-58f2856 — REVERTED

**Hypothesis:** Replacing the current absolute 126-day momentum score with a sector-neutral momentum residual will improve validation Sortino by selecting leaders that are strong versus their own industry group rather than simply chasing whichever sector has recently dominated.

**Change:** I added PIT-safe sector median trend adjustment inside ranking, preserving the existing filters, fixed-slot sizing, sector cap, and rebalance cadence while changing only the ranking score used to choose among qualified names.

**Decision:** REVERTED — sortino 3.401 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0380 (need ≥ 0.20); sub-periods = [+4.832, +0.183])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4014946587489425
- validation_folds: 13
- per_fold_sortinos: [4.2544, -0.249, -1.4228, 5.7175, 9.8804, 8.5561, 6.0237, 10.2314, 0.4942, -1.0122, 0.266, 0.0142, 1.4655]
- calmar_mean: 4.7307838021758295
- hit_rate_mean: 0.5458823003357416
- profit_factor_mean: 21.795696374201917
- trade_count_total: 175
- aggregate_max_dd: 0.13290415952109333
- worst_fold_max_dd: 0.08915051137737556
- max_position_frac_peak: 0.06298553083332248
- lower_quartile_fold_calmar: -0.019509057819613318
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.401 (-0.226). Aggregate DD was 13.3% versus previous kept 15.1%; negative folds were 4/13; trades=175. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.401 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0380 (need ≥ 0.20); sub-periods = [+4.832, +0.183]).

---

## Iteration 2026-05-17-3f71fee — REVERTED

**Hypothesis:** Conditioning the existing momentum-quality ranking on active-universe weakness will improve validation Sortino by rotating defensive relative-strength and low-risk names into the fixed slots during broad NSE drawdowns without reducing gross exposure across all regimes.

**Change:** I added a PIT-safe market-pressure score derived from the active universe's recent median return stream and used it only to increase the defensive-strength reward and volatility/drawdown penalties when that broad return stream is negative.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-d98449a — REVERTED

**Hypothesis:** Switching the biweekly rebalance to the opposite Friday cohort will improve mean validation Sortino by changing execution timing without adding signal parameters or increasing concentration.

**Change:** I changed only the default rebalance_week_parity from 1 to 0, preserving the existing ranking, universe, fixed-slot sizing, sector cap, and order_target_percent-only execution contract.

**Decision:** REVERTED — sortino 2.244 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0366 (need ≥ 0.20); sub-periods = [+3.295, -0.120])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2440424353655413
- validation_folds: 13
- per_fold_sortinos: [2.9924, 0.4341, -1.3196, 4.4775, 8.9584, 5.9583, 3.301, 3.2972, 1.5552, -0.3932, 0.7183, -0.3562, -0.4509]
- calmar_mean: 5.3341989922552715
- hit_rate_mean: 0.45521924656540036
- profit_factor_mean: 2.8308507741343223
- trade_count_total: 200
- aggregate_max_dd: 0.20225691346389785
- worst_fold_max_dd: 0.14316940109491239
- max_position_frac_peak: 0.07325720077384909
- lower_quartile_fold_calmar: -0.4973263939642089
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.244 (-1.384). Aggregate DD was 20.2% versus previous kept 15.1%; negative folds were 4/13; trades=200. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.244 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0366 (need ≥ 0.20); sub-periods = [+3.295, -0.120]).

---

## Iteration 2026-05-17-d13d1c2 — REVERTED

**Hypothesis:** Tightening the existing sector cap from 25% to roughly 20% will improve validation Sortino by reducing concentration in hot NSE sector clusters while preserving the proven stock-level momentum-quality ranking and fixed-slot sizing.

**Change:** I changed only the existing sector_cap default from 0.25 to 0.20 so a 16-slot book can hold at most three names per classified sector instead of four, leaving all ranking, universe, rebalance, and order_target_percent-only execution logic unchanged.

**Decision:** REVERTED — sortino 3.472 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.471515850089183
- validation_folds: 13
- per_fold_sortinos: [4.538, 0.4419, -0.6488, 5.6777, 9.4277, 7.0434, 6.1965, 5.8416, 2.6299, 0.3194, 1.6735, 0.8808, 1.108]
- calmar_mean: 6.714571028828539
- hit_rate_mean: 0.520765132303594
- profit_factor_mean: 5.783511140101205
- trade_count_total: 147
- aggregate_max_dd: 0.13264550140641787
- worst_fold_max_dd: 0.10562025213945446
- max_position_frac_peak: 0.0615548420186634
- lower_quartile_fold_calmar: 0.6957270701772478
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.472 (-0.156). Aggregate DD was 13.3% versus previous kept 15.1%; negative folds were 1/13; trades=147. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.472 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-0d0f5bd — REVERTED

**Hypothesis:** Adding score-rank retention for current holdings will improve validation Sortino by reducing biweekly churn and Dhan DP-cost drag while keeping the same signal family, fixed-slot sizing, universe gate, and 25% sector cap.

**Change:** I changed selection to retain currently held names that still qualify within the existing ranked breadth window before filling open slots with new candidates, using the same sector-cap logic and no selected-count sizing.

**Decision:** REVERTED — sortino 2.946 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1318 (need ≥ 0.20); sub-periods = [+4.020, +0.530])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.946437103053602
- validation_folds: 13
- per_fold_sortinos: [2.3153, -1.0933, -2.1093, 6.1726, 13.6958, 4.907, 4.258, 5.5538, 2.4842, -0.1466, 0.9369, 0.8144, 0.5149]
- calmar_mean: 6.147345345000831
- hit_rate_mean: 0.603720638336023
- profit_factor_mean: 12.494441608192364
- trade_count_total: 118
- aggregate_max_dd: 0.1691191410230415
- worst_fold_max_dd: 0.13240546899680705
- max_position_frac_peak: 0.06698590489269049
- lower_quartile_fold_calmar: 0.5783245280336672
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.946 (-0.681). Aggregate DD was 16.9% versus previous kept 15.1%; negative folds were 3/13; trades=118. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.946 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1318 (need ≥ 0.20); sub-periods = [+4.020, +0.530]).

---

## Iteration 2026-05-17-421ae8b — REVERTED

**Hypothesis:** Adding a PIT-safe downside-asymmetry quality term will improve validation Sortino by preferring momentum names whose recent gains are earned with smaller downside moves rather than merely lower total volatility.

**Change:** I added a no-new-parameter downside capture helper over the existing 63-day return window and blended it into the score while vetoing strongly negative downside asymmetry, aiming to reduce validation downside without changing slots, gross, cadence, or sector-cap construction.

**Decision:** REVERTED — sortino 3.393 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.393162979647798
- validation_folds: 13
- per_fold_sortinos: [4.3653, -0.0371, -1.1992, 5.2412, 9.6472, 6.2426, 5.6802, 5.4943, 2.3488, 0.5532, 1.9361, 1.737, 2.1014]
- calmar_mean: 7.469450891548508
- hit_rate_mean: 0.5590410720501219
- profit_factor_mean: 6.460081412442973
- trade_count_total: 190
- aggregate_max_dd: 0.14995563600023562
- worst_fold_max_dd: 0.12419342858867241
- max_position_frac_peak: 0.06427902679387894
- lower_quartile_fold_calmar: 1.6117105253899844
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.393 (-0.235). Aggregate DD was 15.0% versus previous kept 15.1%; negative folds were 2/13; trades=190. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.393 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-ad77252 — REVERTED

**Hypothesis:** Adding a PIT-safe downside market-beta guard will improve validation Sortino by avoiding momentum names that amplify active-universe down days, reducing downside volatility without changing cadence, gross exposure, fixed-slot sizing, or sector caps.

**Change:** I added a downside-beta helper using the existing active-universe median return series, vetoed extreme high-downside-beta names only when they lack defensive relative strength, and applied a small score penalty to high downside beta.

**Decision:** REVERTED — sortino 2.614 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1035 (need ≥ 0.20); sub-periods = [+3.610, +0.374])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6140051743309716
- validation_folds: 13
- per_fold_sortinos: [1.211, 0.0787, -1.508, 4.1128, 7.5247, 6.0127, 4.3714, 6.8397, 3.8447, -0.563, 0.2358, 0.1424, 1.6791]
- calmar_mean: 5.762429537857258
- hit_rate_mean: 0.5346494499388046
- profit_factor_mean: 5.377495587121473
- trade_count_total: 188
- aggregate_max_dd: 0.13291790701509007
- worst_fold_max_dd: 0.09034261827835745
- max_position_frac_peak: 0.062102490751569484
- lower_quartile_fold_calmar: 0.018173013826576812
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.614 (-1.014). Aggregate DD was 13.3% versus previous kept 15.1%; negative folds were 2/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.614 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1035 (need ≥ 0.20); sub-periods = [+3.610, +0.374]).

---

## Iteration 2026-05-17-2d106b4 — REVERTED

**Hypothesis:** Adding a PIT-safe long-horizon trend confirmation veto will improve validation Sortino by avoiding intermediate momentum names whose 126-day trend is positive but still below their slower 252-day trend anchor, reducing weak-cycle false breakouts without changing sizing, cadence, or sector caps.

**Change:** I added a 252-day moving-average distance check to require selected names to trade above their slow trend anchor and mildly reward cleaner slow-trend confirmation in the existing score.

**Decision:** REVERTED — sortino 3.329 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3290084093658305
- validation_folds: 13
- per_fold_sortinos: [5.1914, 0.3163, -1.1111, 6.7334, 9.604, 4.5252, 5.9472, 5.5693, 2.5747, 0.4444, 1.0995, 0.1801, 2.2027]
- calmar_mean: 4.9395935876810535
- hit_rate_mean: 0.537408424908425
- profit_factor_mean: 3.7174492121532103
- trade_count_total: 178
- aggregate_max_dd: 0.11781672875716129
- worst_fold_max_dd: 0.10879049595856977
- max_position_frac_peak: 0.06328859322024043
- lower_quartile_fold_calmar: 0.8428887013618696
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.329 (-0.299). Aggregate DD was 11.8% versus previous kept 15.1%; negative folds were 1/13; trades=178. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.329 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-7474ccd — REVERTED

**Hypothesis:** Adding a PIT-safe recent close-strength term will improve validation Sortino by preferring momentum candidates that repeatedly finish near the upper part of their daily ranges, capturing persistent demand without adding a new parameter or changing sizing, cadence, gross exposure, or sector caps.

**Change:** I added a recent daily close-location helper using existing OHLC bars, vetoed weak close-strength candidates, and blended a modest close-strength quality reward into the existing momentum-quality score.

**Decision:** REVERTED — sortino 1.270 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0565 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0405 (need ≥ 0.20); sub-periods = [+1.868, -0.076])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.2700836928718184
- validation_folds: 13
- per_fold_sortinos: [0.6405, -0.5969, -2.8569, 1.1016, 4.0274, 2.0547, 4.6137, 5.9024, 1.9274, -0.6402, 0.0749, 0.44, -0.1774]
- calmar_mean: 2.59117464071012
- hit_rate_mean: 0.4593915888033535
- profit_factor_mean: 2.982272408669907
- trade_count_total: 213
- aggregate_max_dd: 0.17630234634604955
- worst_fold_max_dd: 0.12277806752863928
- max_position_frac_peak: 0.06434878162475309
- lower_quartile_fold_calmar: -0.13009090503686593
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 1.270 (-2.358). Aggregate DD was 17.6% versus previous kept 15.1%; negative folds were 5/13; trades=213. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.270 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: bonferroni(p=0.0565 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0405 (need ≥ 0.20); sub-periods = [+1.868, -0.076]).

---

## Iteration 2026-05-17-ff1f4cb — REVERTED

**Hypothesis:** Adding a PIT-safe liquidity stability guard will improve validation Sortino by avoiding momentum candidates whose recent volume is too erratic or thin relative to their own history, reducing fragile breakouts without changing cadence, slots, gross exposure, or sector caps.

**Change:** I added a no-new-parameter volume-stability helper using existing OHLCV bars, vetoed candidates with extreme recent volume instability, and blended a small stability reward into the existing momentum-quality score.

**Decision:** REVERTED — sortino 3.450 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.449701795430389
- validation_folds: 13
- per_fold_sortinos: [4.3595, -0.1256, -1.1748, 5.7001, 9.7642, 6.6574, 5.9528, 5.448, 2.3561, 0.6891, 1.9996, 1.4873, 1.7324]
- calmar_mean: 7.393490524324283
- hit_rate_mean: 0.5243501345311301
- profit_factor_mean: 5.765443827551256
- trade_count_total: 189
- aggregate_max_dd: 0.15130025262259666
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 1.3266759663746042
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.450 (-0.178). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 2/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.450 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-6a723a1 — REVERTED

**Hypothesis:** Switching the proven momentum-quality book from biweekly to four-week rebalancing will improve validation Sortino by reducing Dhan DP-cost drag and rank-churn whipsaw while keeping the same PIT universe gate, fixed-slot sizing, sector cap, and stock-selection thesis.

**Change:** I changed only the default rebalance cadence from every 2 weeks to every 4 weeks, leaving ranking, filters, gross exposure, fixed-slot sizing, and sector construction unchanged.

**Decision:** REVERTED — sortino 3.179 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1654 (need ≥ 0.20); sub-periods = [+4.277, +0.708])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.17852872274392
- validation_folds: 13
- per_fold_sortinos: [3.5111, 0.763, 0.0659, 5.446, 8.4035, 6.2404, 4.3657, 6.4037, 3.2916, -0.4569, 0.3375, 1.3454, 1.604]
- calmar_mean: 6.812767543390047
- hit_rate_mean: 0.5492338857723472
- profit_factor_mean: 9.499666736702022
- trade_count_total: 121
- aggregate_max_dd: 0.14450312775576404
- worst_fold_max_dd: 0.11836473947775542
- max_position_frac_peak: 0.06190281015663274
- lower_quartile_fold_calmar: 0.9395874728413957
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.179 (-0.449). Aggregate DD was 14.5% versus previous kept 15.1%; negative folds were 2/13; trades=121. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.179 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1654 (need ≥ 0.20); sub-periods = [+4.277, +0.708]).

---

## Iteration 2026-05-17-597c303 — REVERTED

**Hypothesis:** Replacing the primary current-to-126-day momentum leg with classic one-month-skipped intermediate momentum will improve validation Sortino by ranking persistent seasoned winners instead of names whose score is dominated by very recent surge/reversal noise.

**Change:** I changed the core trend calculation and score to use price from 126 days ago to 21 days ago as the primary momentum leg, while keeping recent strength only as a secondary confirmation and leaving sizing, cadence, sector caps, and universe handling unchanged.

**Decision:** REVERTED — sortino 2.988 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0798 (need ≥ 0.20); sub-periods = [+4.168, +0.333])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.988123456834664
- validation_folds: 13
- per_fold_sortinos: [3.5816, -0.3487, -1.3477, 4.8425, 9.9115, 7.0239, 5.4956, 5.8519, 2.5047, 0.1109, 0.9008, 0.1323, 0.1862]
- calmar_mean: 6.781890304590799
- hit_rate_mean: 0.5097696672357306
- profit_factor_mean: 4.698590477372972
- trade_count_total: 193
- aggregate_max_dd: 0.15415517106804416
- worst_fold_max_dd: 0.13177226762560107
- max_position_frac_peak: 0.06690183108921664
- lower_quartile_fold_calmar: 0.08306796052464982
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 2.988 (-0.640). Aggregate DD was 15.4% versus previous kept 15.1%; negative folds were 2/13; trades=193. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.988 did not improve on prev 3.6277126896862444 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0798 (need ≥ 0.20); sub-periods = [+4.168, +0.333]).

---

## Iteration 2026-05-17-72bfecd — REVERTED

**Hypothesis:** Adding a PIT-safe breadth participation gate will improve validation Sortino by holding cash on rebalance days when the active universe's own intermediate trend participation is weak, reducing broad-market drawdown exposure without changing the stock-level ranking family.

**Change:** I added an active-universe breadth estimator and require at least 52% of sufficiently seasoned active names to have positive 63-day returns before deploying the fixed-slot momentum book, leaving sizing, cadence, sector cap, and ranking unchanged.

**Decision:** REVERTED — sortino 3.090 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.089512926676443
- validation_folds: 13
- per_fold_sortinos: [4.7508, -0.7174, -1.5785, 4.2843, 7.6511, 6.3325, 6.0772, 5.517, 2.5096, 0.5545, 1.9883, 1.7316, 1.0626]
- calmar_mean: 6.392082046767415
- hit_rate_mean: 0.5036171470560611
- profit_factor_mean: 5.396638360321149
- trade_count_total: 169
- aggregate_max_dd: 0.16971774086650526
- worst_fold_max_dd: 0.12158873478469112
- max_position_frac_peak: 0.06450034369066955
- lower_quartile_fold_calmar: 0.8981107094562876
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.090 (-0.538). Aggregate DD was 17.0% versus previous kept 15.1%; negative folds were 2/13; trades=169. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.090 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-a818f88 — REVERTED

**Hypothesis:** Adding a PIT-safe intra-book correlation guard will improve validation Sortino by preventing the fixed-slot momentum book from filling multiple slots with near-duplicate price paths, reducing clustered drawdowns while preserving the proven stock-level ranking thesis.

**Change:** I added rolling-return correlation checks during sector-capped selection so highly correlated candidates are skipped only when enough ranked alternatives exist, leaving universe handling, scoring, cadence, gross exposure, and fixed-slot sizing unchanged.

**Decision:** REVERTED — sortino 3.628 did not improve on prev 3.6277126896862444

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6277126896862444
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.5371, 2.3815, 0.5568, 1.9883, 1.7262, 2.0927]
- calmar_mean: 7.507118314640582
- hit_rate_mean: 0.5513883363996487
- profit_factor_mean: 6.028189846151534
- trade_count_total: 188
- aggregate_max_dd: 0.15118637146567923
- worst_fold_max_dd: 0.12589683175444755
- max_position_frac_peak: 0.06427130110377423
- lower_quartile_fold_calmar: 1.6078656238728861
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.628 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.628 did not improve on prev 3.6277126896862444.

---

## Iteration 2026-05-17-7eb1b82 — KEPT

**Hypothesis:** Adding a PIT-safe volume-confirmed accumulation term will improve validation Sortino by preferring momentum names whose advance is supported by heavier up-day participation rather than fragile price-only moves.

**Change:** I added an up-volume versus down-volume accumulation score to the existing ranking and veto only clearly distribution-heavy candidates while leaving cadence, sizing, universe gating, and sector caps unchanged.

**Decision:** KEPT — sortino 3.646 > prev 3.6277126896862444, agg_dd 15.1%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.645505465789117
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.4646, 2.3561, 0.557, 1.9529, 1.5828, 2.6003]
- calmar_mean: 7.485932309318195
- hit_rate_mean: 0.5324614299727422
- profit_factor_mean: 5.883363948825357
- trade_count_total: 189
- aggregate_max_dd: 0.15130025262259741
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 2.0192331288161514
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.628 to 3.646 (+0.018). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=189. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.646 > prev 3.6277126896862444, agg_dd 15.1%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-0e272a9 — REVERTED

**Hypothesis:** Adding a PIT-safe volatility compression term will improve validation Sortino by favoring momentum names whose recent advance is becoming less noisy rather than increasingly unstable.

**Change:** I added a 21-day versus 63-day realized-volatility compression score and veto only sharp recent volatility expansions while leaving universe handling, cadence, sizing, sector caps, and the existing accumulation signal unchanged.

**Decision:** REVERTED — sortino 3.629 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.6293118938676137
- validation_folds: 13
- per_fold_sortinos: [5.4828, 0.4365, -1.0343, 5.5588, 9.897, 6.5361, 5.6376, 5.77, 2.5662, 0.697, 1.8854, 1.3854, 2.3626]
- calmar_mean: 7.461465399097744
- hit_rate_mean: 0.5528808798039567
- profit_factor_mean: 6.6446376264383
- trade_count_total: 188
- aggregate_max_dd: 0.14294282607087558
- worst_fold_max_dd: 0.1215659733934479
- max_position_frac_peak: 0.06600805098001256
- lower_quartile_fold_calmar: 1.8723087002923
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.629 (-0.016). Aggregate DD was 14.3% versus previous kept 15.1%; negative folds were 1/13; trades=188. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.629 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-fc601cc — REVERTED

**Hypothesis:** Adding a PIT-safe recent gap-follow-through quality term will improve validation Sortino by avoiding momentum names whose gains are being driven by repeated gap-up opens that fade intraday, which are fragile for next-open CNC fills.

**Change:** I added open-price based gap follow-through scoring, vetoed only strongly gap-fade candidates, and gave a modest rank reward to names whose recent gaps are absorbed constructively while leaving universe handling, cadence, fixed-slot sizing, sector caps, and the kept accumulation signal unchanged.

**Decision:** REVERTED — sortino 3.598 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5977263146635314
- validation_folds: 13
- per_fold_sortinos: [5.095, 1.25, -0.3952, 5.6243, 10.4846, 6.6727, 5.0758, 4.4599, 1.6977, 0.6018, 1.9016, 1.3505, 2.9518]
- calmar_mean: 7.763336912438318
- hit_rate_mean: 0.540509645153608
- profit_factor_mean: 6.851020200746711
- trade_count_total: 202
- aggregate_max_dd: 0.16141283039296672
- worst_fold_max_dd: 0.13274459468415506
- max_position_frac_peak: 0.08184631530750877
- lower_quartile_fold_calmar: 1.6973706403478062
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.598 (-0.048). Aggregate DD was 16.1% versus previous kept 15.1%; negative folds were 1/13; trades=202. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.598 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-8db0ff3 — REVERTED

**Hypothesis:** Adding a narrow PIT news-risk veto will improve validation Sortino by avoiding otherwise strong momentum names when unusually negative current news and event context raise next-open gap risk.

**Change:** I imported the existing LLM news feature accessors, threaded the rebalance date into scoring, and added a conservative adverse-news block plus small score penalty while leaving cadence, sizing, sector caps, and the kept accumulation signal unchanged.

**Decision:** REVERTED — sortino 3.646 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.645505465789117
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.4646, 2.3561, 0.557, 1.9529, 1.5828, 2.6003]
- calmar_mean: 7.485932309318195
- hit_rate_mean: 0.5324614299727422
- profit_factor_mean: 5.883363948825357
- trade_count_total: 189
- aggregate_max_dd: 0.15130025262259741
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 2.0192331288161514
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.646 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.646 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-b59bf36 — REVERTED

**Hypothesis:** Adding a PIT-safe short-term mean-reversion entry term will improve validation Sortino by preferring established intermediate momentum names that are not extended over the last week and are therefore less exposed to next-open reversal.

**Change:** I added a five-day pullback-from-fast-MA quality score and veto only sharp one-week extensions while leaving the kept accumulation signal, fixed-slot sizing, universe gate, cadence, and sector cap unchanged.

**Decision:** REVERTED — sortino 3.115 did not improve on prev 3.645505465789117 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1892 (need ≥ 0.20); sub-periods = [+4.150, +0.785])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.114830649430181
- validation_folds: 13
- per_fold_sortinos: [4.1867, 0.0687, -1.221, 5.4015, 10.5273, 6.7247, 4.9012, 4.8328, 1.9306, 0.5545, 1.1362, 0.445, 1.0045]
- calmar_mean: 6.619744401178514
- hit_rate_mean: 0.5054044461135435
- profit_factor_mean: 5.295306532641481
- trade_count_total: 195
- aggregate_max_dd: 0.15813710733825098
- worst_fold_max_dd: 0.1320536494320646
- max_position_frac_peak: 0.0646845577892097
- lower_quartile_fold_calmar: 0.8813741822295028
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.115 (-0.531). Aggregate DD was 15.8% versus previous kept 15.1%; negative folds were 2/13; trades=195. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.115 did not improve on prev 3.645505465789117 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1892 (need ≥ 0.20); sub-periods = [+4.150, +0.785]).

---

## Iteration 2026-05-17-9f6bf8d — REVERTED

**Hypothesis:** Adding a PIT-safe early trend-break veto will improve validation Sortino by exiting otherwise high-ranked momentum names when their short-horizon moving-average structure has already rolled over, reducing left-tail continuation losses without changing cadence, sizing, universe gating, or sector caps.

**Change:** I added a no-new-import 21-day slope confirmation inside the existing score filter, requiring the current short moving-average distance to be at least as strong as its five-day-prior value minus a small tolerance so deteriorating trends are blocked before ranking.

**Decision:** REVERTED — sortino 3.194 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.19412961187123
- validation_folds: 13
- per_fold_sortinos: [4.2283, -0.9003, -1.7789, 5.2962, 10.054, 8.6637, 6.1803, 4.428, 1.6492, 0.8274, 2.0606, 0.4319, 0.3832]
- calmar_mean: 6.979482917025655
- hit_rate_mean: 0.506880294590619
- profit_factor_mean: 13.073054015715664
- trade_count_total: 241
- aggregate_max_dd: 0.14286523979280105
- worst_fold_max_dd: 0.09317454919467956
- max_position_frac_peak: 0.06353887674627179
- lower_quartile_fold_calmar: 0.38149251921848837
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.194 (-0.451). Aggregate DD was 14.3% versus previous kept 15.1%; negative folds were 2/13; trades=241. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.194 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-e613e56 — REVERTED

**Hypothesis:** Adding a PIT-safe broad-market stress overlay will improve validation Sortino by keeping the proven accumulation/momentum stock ranking intact while cutting gross exposure only when continuous India VIX and Nifty trend signals indicate elevated index-level downside risk.

**Change:** I imported continuous macro feature accessors and added a defensive gross-exposure scaler in next(), so selected names and fixed-slot sizing remain unchanged but each slot is proportionally de-risked during macro stress.

**Decision:** REVERTED — sortino 3.565 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5648330112272104
- validation_folds: 13
- per_fold_sortinos: [5.1666, 0.3327, -1.0081, 5.2429, 9.3243, 6.6544, 5.9474, 5.8284, 3.0308, 0.3661, 1.7162, 1.3754, 2.3659]
- calmar_mean: 7.23544879838324
- hit_rate_mean: 0.5274542199881566
- profit_factor_mean: 5.880715696025072
- trade_count_total: 183
- aggregate_max_dd: 0.11966301817637877
- worst_fold_max_dd: 0.10305753002746726
- max_position_frac_peak: 0.061644523373131845
- lower_quartile_fold_calmar: 1.9043203458730007
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.565 (-0.081). Aggregate DD was 12.0% versus previous kept 15.1%; negative folds were 1/13; trades=183. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.565 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-f823563 — REVERTED

**Hypothesis:** Adding a PIT-safe volatility-normalized momentum score will improve validation Sortino by ranking persistent winners by return earned per unit of realized risk instead of raw return alone, reducing noisy high-beta momentum exposure without changing universe handling, cadence, sector caps, or fixed-slot sizing.

**Change:** I changed only the stock scoring formula to use a clipped trend-over-vol component alongside the kept accumulation signal, so high raw momentum must also be efficient relative to its own realized volatility.

**Decision:** REVERTED — sortino 3.384 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3837107403812343
- validation_folds: 13
- per_fold_sortinos: [4.2019, -0.5989, -1.5999, 5.6968, 9.8745, 6.6994, 6.0205, 5.5355, 2.4189, 0.3126, 1.701, 1.7545, 1.9716]
- calmar_mean: 7.366513910897753
- hit_rate_mean: 0.5291805443240308
- profit_factor_mean: 5.165827531665503
- trade_count_total: 197
- aggregate_max_dd: 0.15346806825475603
- worst_fold_max_dd: 0.11950747311615671
- max_position_frac_peak: 0.06509851056463076
- lower_quartile_fold_calmar: 1.5444057681063672
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.384 (-0.262). Aggregate DD was 15.3% versus previous kept 15.1%; negative folds were 2/13; trades=197. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.384 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-d33108f — REVERTED

**Hypothesis:** Increasing fixed risk slots from 16 to 20 will improve mean validation Sortino by reducing single-name concentration and drawdown volatility while preserving the kept accumulation-based ranking, PIT universe gate, biweekly cadence, and 25% sector cap.

**Change:** I changed only n_positions from 16 to 20 so sizing remains fixed-slot but each selected name carries less portfolio risk and sector exposure is spread across more names.

**Decision:** REVERTED — sortino 2.969 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.9687075896231048
- validation_folds: 13
- per_fold_sortinos: [4.5079, -0.0862, -1.3536, 4.19, 8.3726, 6.048, 4.6618, 4.724, 2.3467, 0.1947, 1.4541, 1.3032, 2.23]
- calmar_mean: 6.140951664526128
- hit_rate_mean: 0.5270029909229719
- profit_factor_mean: 5.2879193147252685
- trade_count_total: 221
- aggregate_max_dd: 0.11991873047754473
- worst_fold_max_dd: 0.10059498005749819
- max_position_frac_peak: 0.05161222941431126
- lower_quartile_fold_calmar: 1.2847388809464766
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 2.969 (-0.677). Aggregate DD was 12.0% versus previous kept 15.1%; negative folds were 2/13; trades=221. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.969 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-49b7561 — REVERTED

**Hypothesis:** Reducing fixed risk slots from 16 to 15 will improve validation Sortino by concentrating the already-kept accumulation/momentum ranking in the strongest names while still satisfying the minimum position-count and sector-cap constraints.

**Change:** I changed only n_positions from 16 to 15, preserving PIT universe gating, biweekly cadence, fixed-slot sizing, order_target_percent-only execution, and the 25% sector cap.

**Decision:** REVERTED — sortino 3.516 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.516319138080914
- validation_folds: 13
- per_fold_sortinos: [4.7029, 0.287, -0.8222, 5.7739, 9.507, 7.0859, 6.2289, 5.8209, 2.5312, 0.4473, 1.0732, 1.1759, 1.9003]
- calmar_mean: 6.963803000299243
- hit_rate_mean: 0.5342371303909765
- profit_factor_mean: 5.497135505673179
- trade_count_total: 149
- aggregate_max_dd: 0.12429985655682445
- worst_fold_max_dd: 0.10348353259061487
- max_position_frac_peak: 0.08944723663962523
- lower_quartile_fold_calmar: 1.476191651455303
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.516 (-0.129). Aggregate DD was 12.4% versus previous kept 15.1%; negative folds were 1/13; trades=149. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.516 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-7e714c5 — REVERTED

**Hypothesis:** Adding a two-pass sector diversification fill will improve validation Sortino by reducing hot-sector cluster risk while preserving the kept stock-level momentum/accumulation ranking, fixed-slot sizing, PIT universe gate, biweekly cadence, and the hard 25% sector cap.

**Change:** I changed only sector-cap selection so the book first takes a softer cross-sector pass before filling remaining slots up to the existing hard sector cap, keeping weaker duplicate sector exposure as cash only when breadth is insufficient.

**Decision:** REVERTED — sortino 3.646 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.645505465789117
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.4646, 2.3561, 0.557, 1.9529, 1.5828, 2.6003]
- calmar_mean: 7.485932309318195
- hit_rate_mean: 0.5324614299727422
- profit_factor_mean: 5.883363948825357
- trade_count_total: 189
- aggregate_max_dd: 0.15130025262259741
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 2.0192331288161514
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.646 (+0.000). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.646 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-698f0a2 — REVERTED

**Hypothesis:** Adding a PIT-safe rebalance retention band will improve validation Sortino by reducing cost-heavy churn and short-horizon whipsaw while keeping only currently qualified holdings that remain strong enough under the existing score.

**Change:** I changed selection to retain existing holdings that still rank within a fixed top-2x-position band before filling new names, preserving the sector cap, PIT universe gate, fixed-slot sizing, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 2.720 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.719723367831772
- validation_folds: 13
- per_fold_sortinos: [2.243, -0.2948, -1.3606, 4.6958, 11.0083, 4.4841, 4.2403, 5.0877, 2.299, -0.3406, 0.8999, 1.0629, 1.3313]
- calmar_mean: 5.6521416580861885
- hit_rate_mean: 0.6233744887591042
- profit_factor_mean: 7.192704571235105
- trade_count_total: 112
- aggregate_max_dd: 0.1778929762978217
- worst_fold_max_dd: 0.12784255863605956
- max_position_frac_peak: 0.06514114332152747
- lower_quartile_fold_calmar: 1.509892283515551
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 2.720 (-0.926). Aggregate DD was 17.8% versus previous kept 15.1%; negative folds were 3/13; trades=112. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.720 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-65d67af — REVERTED

**Hypothesis:** Adding PIT-safe market-adjusted trend strength will improve validation Sortino by preferring momentum names whose 126-day advance exceeds the active universe median rather than simply riding broad market beta.

**Change:** I changed only the ranking context to compute active-universe 126-day median market returns and added a bounded excess-trend term to the stock score while preserving PIT universe gating, fixed-slot sizing, biweekly cadence, and the sector cap.

**Decision:** REVERTED — sortino 3.597 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.597360077365871
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.067, -1.3004, 5.6596, 9.7912, 6.6527, 5.9472, 5.5358, 2.4352, 0.5615, 2.0453, 1.8299, 2.3483]
- calmar_mean: 7.549963245443205
- hit_rate_mean: 0.5335939602193471
- profit_factor_mean: 5.963757858834018
- trade_count_total: 197
- aggregate_max_dd: 0.14523688056113787
- worst_fold_max_dd: 0.11961465166289413
- max_position_frac_peak: 0.06516264343664915
- lower_quartile_fold_calmar: 1.8518592449884874
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.597 (-0.048). Aggregate DD was 14.5% versus previous kept 15.1%; negative folds were 2/13; trades=197. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.597 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-4a6bb8a — REVERTED

**Hypothesis:** Adding a PIT-safe negative overnight gap risk penalty will improve validation Sortino by avoiding momentum names whose recent path includes repeated adverse open gaps, reducing next-open fill risk and downside tails without changing the kept accumulation ranking thesis.

**Change:** I added a close-to-next-open gap fragility metric over the existing volatility window, vetoed severe adverse gap histories, and penalized milder gap risk in the score while preserving PIT universe gating, fixed-slot sizing, biweekly cadence, sector cap, and order_target_percent-only execution.

**Decision:** REVERTED — sortino 3.642 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.642301064169784
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.8286, 5.9485, 5.4646, 2.3561, 0.6891, 2.0157, 1.5822, 2.3645]
- calmar_mean: 7.516300780463253
- hit_rate_mean: 0.5381755499402557
- profit_factor_mean: 5.824578165497031
- trade_count_total: 187
- aggregate_max_dd: 0.15130025262259741
- worst_fold_max_dd: 0.12598967743333822
- max_position_frac_peak: 0.06432321564169123
- lower_quartile_fold_calmar: 1.8667731361873807
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.642 (-0.003). Aggregate DD was 15.1% versus previous kept 15.1%; negative folds were 1/13; trades=187. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.642 did not improve on prev 3.645505465789117.

---

## Iteration 2026-05-17-7424e28 — REVERTED

**Hypothesis:** Adding a PIT-safe downside semivolatility asymmetry term will improve validation Sortino by favoring momentum names whose recent volatility is upside-led rather than left-tail dominated, directly targeting downside-risk quality without changing the kept accumulation thesis.

**Change:** I added a 63-day semivolatility balance metric, softly rewarded upside-led paths, penalized and vetoed strongly downside-led paths, and left PIT universe gating, fixed-slot sizing, biweekly cadence, sector cap, and order_target_percent-only execution unchanged.

**Decision:** REVERTED — sortino 3.582 did not improve on prev 3.645505465789117

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.5821307922801133
- validation_folds: 13
- per_fold_sortinos: [5.1923, 0.3537, -0.9762, 5.6907, 9.8402, 6.3332, 5.6827, 5.4214, 2.2803, 0.5533, 1.9927, 1.8391, 2.3644]
- calmar_mean: 7.6687161648513715
- hit_rate_mean: 0.5430418751685719
- profit_factor_mean: 6.515884936156468
- trade_count_total: 189
- aggregate_max_dd: 0.1502110111616633
- worst_fold_max_dd: 0.12517053582101767
- max_position_frac_peak: 0.0646707238235426
- lower_quartile_fold_calmar: 1.8657281430506245
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.646 to 3.582 (-0.063). Aggregate DD was 15.0% versus previous kept 15.1%; negative folds were 1/13; trades=189. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.582 did not improve on prev 3.645505465789117.

---
