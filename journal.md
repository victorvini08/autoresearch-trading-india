# Journal — mean-reversion-quant-strategy

**Fresh start 2026-05-16.** Prior history archived in
`journal_pre-2026-05-16_archive.md` — those REVERT verdicts were produced
by the broken evaluator (degenerate RW-MC null, 5-name-universe poisoning,
parsimony double-jeopardy) and are NOT reliable signals of which ideas are
bad. Evaluator now at `EVALUATOR_VERSION = 2026-05-16-univfloor`. Durable
structural learnings are codified in `program.md`. Explore freely.

---


## Iteration 2026-05-16-aaa0198 — REVERTED

**Hypothesis:** Sizing selected names by fixed risk slots instead of by the number of surviving selections will reduce concentration during filtered or risk-gated rebalances and improve validation Sortino after costs.

**Change:** Changed portfolio construction so target weights are always sized as 0.99 / n_positions, leaving unused slots in cash rather than reallocating them into fewer holdings.

**Decision:** REVERTED — sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.47401590365159174
- validation_folds: 13
- per_fold_sortinos: [-0.0507, -0.1823, -0.9221, 0.8855, 1.9349, 1.0582, 2.5221, 1.2567, 0.9335, 0.9919, -4.1248, -4.7992, -5.666]
- calmar_mean: 0.20615479178899687
- hit_rate_mean: 0.4893750846444665
- profit_factor_mean: 1.4137417995489208
- trade_count_total: 467
- aggregate_max_dd: 0.25455771984436343
- worst_fold_max_dd: 0.11197702429751788
- max_position_frac_peak: 0.04362859037008209
- lower_quartile_fold_calmar: -1.0128348349285454
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -0.474 with no prior kept baseline. Aggregate DD was 25.5%; negative folds were 6/13; trades=467. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400]).

---

## Iteration 2026-05-16-54f59d5 — REVERTED

**Hypothesis:** Requiring a positive latest factor residual before opening a residual-reversal position will avoid falling-knife entries and improve mean validation Sortino after Dhan delivery costs.

**Change:** Changed new-entry selection to require both top-tail oversold residual rank and one-bar residual rebound confirmation, while keeping fixed n_positions sizing and applying the 25% sector cap to the whole target book.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0500) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.8135 (need ≥ 0.20); sub-periods = [+1.069, -1.938])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.14351510273005158
- validation_folds: 13
- per_fold_sortinos: [1.6586, -1.4942, -2.2807, 4.1201, 1.3626, 1.0514, 2.0901, 1.8752, 1.235, -1.321, -0.1582, -2.6861, -3.5871]
- calmar_mean: 0.10720865174054772
- hit_rate_mean: 0.46030461732404315
- profit_factor_mean: 1.2440678417469095
- trade_count_total: 371
- aggregate_max_dd: 0.11866694142298664
- worst_fold_max_dd: 0.06273735373060813
- max_position_frac_peak: 0.04120512261634931
- lower_quartile_fold_calmar: -1.4816937387952767
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.144 with no prior kept baseline. Aggregate DD was 11.9%; negative folds were 6/13; trades=371. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0500) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.8135 (need ≥ 0.20); sub-periods = [+1.069, -1.938]).

---

## Iteration 2026-05-16-da1b6e1 — REVERTED

**Hypothesis:** Buying only bar-fresh residual losers that still have positive beta-window trend should avoid stale delayed off-universe fills and reduce falling-knife exposure, improving mean validation Sortino after costs.

**Change:** Rebuilt target construction around a same-day liquid-bar and beta-window uptrend qualifier, with fixed n_positions sizing and full-book sector-cap selection so blocked slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3518 (need ≥ 0.20); sub-periods = [+1.845, -0.649])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.077854057982982
- validation_folds: 13
- per_fold_sortinos: [2.2698, -0.5261, -2.2408, 1.836, 5.0729, 3.2292, 3.9161, 2.4114, 0.6407, 0.2728, -0.4109, -3.6893, 1.2303]
- calmar_mean: 1.7248658687123641
- hit_rate_mean: 0.4891617694046844
- profit_factor_mean: 1.5701761442470215
- trade_count_total: 318
- aggregate_max_dd: 0.1421478019979768
- worst_fold_max_dd: 0.08452758578544842
- max_position_frac_peak: 0.04114964780177637
- lower_quartile_fold_calmar: -0.32949852481616304
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.078 with no prior kept baseline. Aggregate DD was 14.2%; negative folds were 4/13; trades=318. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.3518 (need ≥ 0.20); sub-periods = [+1.845, -0.649]).

---

## Iteration 2026-05-16-ecd89b9 — REVERTED

**Hypothesis:** A residual-reversal book should be fully in cash when Indian market stress is explicit (risk_off/shock, India VIX above the existing regime_pct threshold, or Nifty below its 200-DMA), because avoiding falling-knife regimes should improve mean validation Sortino more than the missed rebounds cost.

**Change:** Changed the regime gate into a continuous macro gross-budget gate that liquidates in hostile states, and applied fixed n_positions slot sizing with full-book sector-cap selection so unused slots remain cash.

**Decision:** REVERTED — sortino -0.132 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -2.8383 (need ≥ 0.20); sub-periods = [+0.728, -2.067])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.1318440786271441
- validation_folds: 13
- per_fold_sortinos: [-0.3047, -0.7264, -2.1459, 0.5358, 2.2568, 0.7761, 2.0885, 1.7787, 2.2967, 0.0913, -4.0772, -2.2423, -2.0415]
- calmar_mean: 0.10190336308604858
- hit_rate_mean: 0.49594328309471225
- profit_factor_mean: 1.5169411329176248
- trade_count_total: 347
- aggregate_max_dd: 0.37259158159732286
- worst_fold_max_dd: 0.20627373015486622
- max_position_frac_peak: 0.08236746888516923
- lower_quartile_fold_calmar: -1.4295255469592216
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -0.132 with no prior kept baseline. Aggregate DD was 37.3%; negative folds were 6/13; trades=347. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.132 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -2.8383 (need ≥ 0.20); sub-periods = [+0.728, -2.067]).

---

## Iteration 2026-05-16-e34c0eb — REVERTED

**Hypothesis:** Ranking residual-reversal entries by idiosyncratic residual t-stat instead of raw cumulative residual z-score will reduce high-volatility falling-knife selection and improve mean validation Sortino after Dhan delivery costs.

**Change:** Changed the reversion score to normalize each cumulative residual selloff by that ticker's own residual volatility, while preserving the PIT universe, fixed-slot sizing, biweekly cadence, and 25% sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.4483 >= alpha/N=0.0200) · random_walk_mc(only 55.20% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.9395 (need ≥ 0.20); sub-periods = [+0.237, -0.222])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.09539762287608483
- validation_folds: 13
- per_fold_sortinos: [-1.1698, 0.0504, -0.0306, 1.7542, 0.5347, 0.1853, 1.5166, -1.3962, 0.6846, 2.8871, 2.7301, -1.0814, -5.4249]
- calmar_mean: 0.08223192956194482
- hit_rate_mean: 0.47321159842711563
- profit_factor_mean: 1.220675896507058
- trade_count_total: 376
- aggregate_max_dd: 0.06230185069078692
- worst_fold_max_dd: 0.03970488181369905
- max_position_frac_peak: 0.0436638677122356
- lower_quartile_fold_calmar: -0.4624116871805328
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.095 with no prior kept baseline. Aggregate DD was 6.2%; negative folds were 5/13; trades=376. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.4483 >= alpha/N=0.0200) · random_walk_mc(only 55.20% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.9395 (need ≥ 0.20); sub-periods = [+0.237, -0.222]).

---

## Iteration 2026-05-16-128274a — REVERTED

**Hypothesis:** Replacing falling-knife residual reversal with positive residual continuation over the beta window, while skipping the latest formation bars and preserving fixed risk slots, should improve validation Sortino by capturing idiosyncratic persistence instead of unstable short-horizon rebounds.

**Change:** Changed the traded score to a positive market-and-size residual momentum t-stat with latest-bar skip, retained the seven-parameter footprint, enforced full-book sector caps, and sized selected names at 0.99 / n_positions so blocked slots remain cash.

**Decision:** REVERTED — sortino -0.281 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -8.4414 (need ≥ 0.20); sub-periods = [+0.147, -1.243])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.2805620197472993
- validation_folds: 13
- per_fold_sortinos: [-1.3926, 0.0173, 0.1747, 2.6737, 0.7616, 0.0163, 1.245, -2.2947, 0.1242, 2.1102, 0.1746, -2.2496, -5.0081]
- calmar_mean: -0.08669912022570102
- hit_rate_mean: 0.4590240009622531
- profit_factor_mean: 1.0835671677633023
- trade_count_total: 366
- aggregate_max_dd: 0.06704930258730889
- worst_fold_max_dd: 0.038201137096860176
- max_position_frac_peak: 0.04372214183783921
- lower_quartile_fold_calmar: -0.5512604980265068
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -0.281 with no prior kept baseline. Aggregate DD was 6.7%; negative folds were 6/13; trades=366. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.281 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0167) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -8.4414 (need ≥ 0.20); sub-periods = [+0.147, -1.243]).

---

## Iteration 2026-05-16-cef5663 — REVERTED

**Hypothesis:** Replacing the unstable residual-reversal entry with a positive intermediate-term trend-quality rank should improve validation Sortino because it buys persistent NSE winners with lower downside volatility while leaving weak or sector-blocked slots in cash.

**Change:** Changed the traded signal to 126-day momentum skipping the latest 10 bars, filtered by current 20-day trend and 50-day average, ranked by downside-volatility-adjusted momentum, with fixed-slot sizing and full-book sector-cap enforcement.

**Decision:** REVERTED — sortino -0.641 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -18.8912 (need ≥ 0.20); sub-periods = [+0.125, -2.367])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -0.6414774245018737
- validation_folds: 13
- per_fold_sortinos: [0.6065, -1.7591, -3.1598, 0.0368, 4.7246, 2.9242, 1.9827, -1.8205, -2.4079, -3.4014, -4.5627, -1.4764, -0.0261]
- calmar_mean: -0.4879297155280317
- hit_rate_mean: 0.4489024186515825
- profit_factor_mean: 2.1569865792495913
- trade_count_total: 194
- aggregate_max_dd: 0.32942009305898096
- worst_fold_max_dd: 0.15986121609589637
- max_position_frac_peak: 0.12055641878927284
- lower_quartile_fold_calmar: -2.3102334010144325
- n_negative_folds: 8/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -0.641 with no prior kept baseline. Aggregate DD was 32.9%; negative folds were 8/13; trades=194. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.641 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0143) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -18.8912 (need ≥ 0.20); sub-periods = [+0.125, -2.367]).

---

## Iteration 2026-05-16-0e1cfa7 — REVERTED

**Hypothesis:** Ranking liquid NSE names by short-term pullback within positively trending sectors, with low downside-volatility tie-breaks, will capture sector momentum dips more consistently than market-size residual reversal and improve mean validation Sortino after Dhan costs.

**Change:** Replaced the residual-reversal score with a price-only sector-pullback rank that buys underperformers inside positive-trend sectors, enforces the sector cap on the whole target book, and sizes at 0.99 / n_positions so blocked slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2047 (need ≥ 0.20); sub-periods = [+2.147, -2.586])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.6904435777085941
- validation_folds: 13
- per_fold_sortinos: [0.4025, 2.4238, 2.9908, 4.5785, 1.7122, 1.0532, 1.7884, 3.1749, 1.1956, -0.2621, -3.7938, -4.3991, -1.8889]
- calmar_mean: 0.27709152168780904
- hit_rate_mean: 0.5706613157422875
- profit_factor_mean: 2.2767857654449113
- trade_count_total: 291
- aggregate_max_dd: 0.24424875223785694
- worst_fold_max_dd: 0.1275033547947217
- max_position_frac_peak: 0.041727134942368745
- lower_quartile_fold_calmar: -0.2714483945150281
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.690 with no prior kept baseline. Aggregate DD was 24.4%; negative folds were 4/13; trades=291. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2047 (need ≥ 0.20); sub-periods = [+2.147, -2.586]).

---
