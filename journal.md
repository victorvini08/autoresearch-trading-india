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

## Iteration 2026-05-16-3720275 — REVERTED

**Hypothesis:** Sector-neutralizing the residual-reversal score will improve validation Sortino because it keeps the bar-fresh idiosyncratic pullback edge while avoiding persistent broad sector drawdowns that caused weak sub-period behavior.

**Change:** I changed the traded score from raw market/size residual reversal to sector-demeaned residual reversal using existing sector assignments, while preserving the same universe, rebalance, low-volatility, retention, fixed-slot sizing, and sector-cap contracts.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1722 (need ≥ 0.20); sub-periods = [+2.584, +0.445])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.925507046345217
- validation_folds: 13
- per_fold_sortinos: [2.2197, 0.3924, 1.7871, 2.4484, 2.8376, 4.5506, 5.7004, 2.3951, 0.9205, 1.3835, 0.6698, -0.4603, 0.1869]
- calmar_mean: 0.6664022026346359
- hit_rate_mean: 0.5124729970883817
- profit_factor_mean: 2.650552672792422
- trade_count_total: 174
- aggregate_max_dd: 0.02049361109810689
- worst_fold_max_dd: 0.01556636734500266
- max_position_frac_peak: 0.039540610144284984
- lower_quartile_fold_calmar: 0.26802729947430937
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.926 with no prior kept baseline. Aggregate DD was 2.0%; negative folds were 1/13; trades=174. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1722 (need ≥ 0.20); sub-periods = [+2.584, +0.445]).

---

## Iteration 2026-05-17-c10a52c — REVERTED

**Hypothesis:** Sector-demeaning residual reversal scores before ranking should improve validation Sortino and stationarity by keeping the idiosyncratic oversold edge while reducing persistent sector drawdown exposure.

**Change:** I replaced raw residual-reversal ranking with sector-neutral residual score ranking and restored fixed-slot sizing at 0.99 / n_positions so blocked slots remain cash.

**Decision:** REVERTED — sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400])

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

**Learning:** Sortino scored -0.474 with no prior kept baseline. Aggregate DD was 25.5%; negative folds were 6/13; trades=467. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400]).

---

## Iteration 2026-05-17-d77c1da — REVERTED

**Hypothesis:** Ranking residual reversion within sectors and constructing the whole book with 35 fixed risk slots should preserve the prior idiosyncratic reversal edge while improving weak-subperiod stationarity and avoiding selected-count concentration.

**Change:** I sector-demeaned the residual-reversal scores, raised the fixed slot count to 35, enforced the 25% sector cap on retained plus new names together, and sized every selected name at 0.99 / n_positions so blocked slots stay cash.

**Decision:** REVERTED — sortino -1.139 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -27.2031 (need ≥ 0.20); sub-periods = [+0.148, -4.035])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: -1.1389774627217877
- validation_folds: 13
- per_fold_sortinos: [-1.9803, -1.0397, -1.5541, 0.0247, 2.4406, 1.8175, 1.7035, 0.2735, -0.3506, -0.7972, -5.852, -5.3815, -4.111]
- calmar_mean: -0.6055517155521337
- hit_rate_mean: 0.4603496837428188
- profit_factor_mean: 1.3447522914183365
- trade_count_total: 389
- aggregate_max_dd: 0.29126841144240584
- worst_fold_max_dd: 0.13861673561638466
- max_position_frac_peak: 0.030758837087903116
- lower_quartile_fold_calmar: -1.454016407298886
- n_negative_folds: 9/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored -1.139 with no prior kept baseline. Aggregate DD was 29.1%; negative folds were 9/13; trades=389. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -1.139 not positive — won't compound on losing baseline | anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -27.2031 (need ≥ 0.20); sub-periods = [+0.148, -4.035]).

---

## Iteration 2026-05-17-9c71331 — REVERTED

**Hypothesis:** Sizing every selected name by fixed risk slots instead of the number of selected names should improve validation Sortino by preventing concentration when regime, universe, or sector-cap filters leave some slots in cash.

**Change:** I changed only the final target sizing from 0.99 / len(selected) to 0.99 / n_positions so unfilled slots remain cash and the strategy satisfies the fixed-slot construction contract.

**Decision:** REVERTED — sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400])

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

**Learning:** Sortino scored -0.474 with no prior kept baseline. Aggregate DD was 25.5%; negative folds were 6/13; trades=467. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino -0.474 not positive — won't compound on losing baseline | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -4.1147 (need ≥ 0.20); sub-periods = [+0.826, -3.400]).

---

## Iteration 2026-05-17-336ce72 — REVERTED

**Hypothesis:** Replacing residual falling-knife entries with a downside-risk-normalized positive-drift rank, rather than the earlier raw trend-quality rank, should improve validation Sortino by selecting smoother NSE winners while leaving weak or choppy names in cash.

**Change:** I changed the ranking signal from residual mean reversion to defensive momentum-quality using positive intermediate drift divided by downside semideviation, trailing drawdown, and recent weakness penalty, while preserving PIT universe filtering, fixed-slot sizing, retention, regime gating, and the sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0375 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0565 (need ≥ 0.20); sub-periods = [+2.712, +0.153])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.9247422543950372
- validation_folds: 13
- per_fold_sortinos: [3.4473, -0.2778, -3.0183, -1.8531, 6.3652, 5.2644, 8.4996, 6.2857, -0.3042, -0.4298, 1.035, -0.1352, 0.1427]
- calmar_mean: 1.318386073972887
- hit_rate_mean: 0.49875850645081415
- profit_factor_mean: 3.4633169554079566
- trade_count_total: 118
- aggregate_max_dd: 0.13641858287275255
- worst_fold_max_dd: 0.07880842196602478
- max_position_frac_peak: 0.04114639000012282
- lower_quartile_fold_calmar: -0.43494672627403014
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.925 with no prior kept baseline. Aggregate DD was 13.6%; negative folds were 6/13; trades=118. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0375 >= alpha/N=0.0100) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.0565 (need ≥ 0.20); sub-periods = [+2.712, +0.153]).

---

## Iteration 2026-05-17-278d67a — REJECTED

**Hypothesis:** Replacing residual reversal with a breadth-gated defensive momentum and low-downside-volatility carry rank will improve validation Sortino by keeping long exposure in smoother NSE winners while automatically cutting gross in weak market breadth regimes.

**Change:** I changed the strategy to rank active PIT-universe names by intermediate momentum, downside stability, drawdown control and liquidity, scale gross by internal breadth plus macro stress, enforce the sector cap across retained and new names, and size by fixed slots.

**Decision:** REJECTED — prepare.py crashed: name 'ticker' is not defined

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: name 'ticker' is not defined.

---

## Iteration 2026-05-17-5e24a16 — REVERTED

**Hypothesis:** Replacing residual reversion with a market-breadth-gated low-downside-volatility momentum carry book should improve mean validation Sortino by staying diversified in smoother winners while cutting gross during weak internal breadth regimes.

**Change:** I changed the signal to rank PIT-universe names by intermediate momentum adjusted for downside volatility, drawdown, short-term reversal, and ADV, then scaled fixed-slot gross exposure by cross-sectional breadth instead of using selected-count sizing.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.2704 >= alpha/N=0.0100) · random_walk_mc(only 73.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.1068 (need ≥ 0.20); sub-periods = [+1.567, -1.735])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.5512795733663991
- validation_folds: 13
- per_fold_sortinos: [2.2073, 0.2701, -3.0459, -0.4035, 1.4457, 2.5477, 5.2065, 4.7466, 1.1313, 0.0722, -0.1109, -2.5271, -4.3732]
- calmar_mean: 0.20492583159019578
- hit_rate_mean: 0.4273520207928004
- profit_factor_mean: 1.6098714564073653
- trade_count_total: 368
- aggregate_max_dd: 0.09315537924723666
- worst_fold_max_dd: 0.04690954074605074
- max_position_frac_peak: 0.037125752873002925
- lower_quartile_fold_calmar: -0.14748638361521182
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.551 with no prior kept baseline. Aggregate DD was 9.3%; negative folds were 5/13; trades=368. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.2704 >= alpha/N=0.0100) · random_walk_mc(only 73.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.1068 (need ≥ 0.20); sub-periods = [+1.567, -1.735]).

---

## Iteration 2026-05-17-cb34110 — REVERTED

**Hypothesis:** Replacing residual reversal with an absolute-trend, high-proximity, downside-risk-adjusted carry rank will improve validation Sortino by owning persistent NSE uptrends instead of oversold falling-knife names.

**Change:** I replaced the residual mean-reversion core with a fixed-slot biweekly quality-trend selector that ranks active PIT-universe names by six-month momentum, trend confirmation, proximity to highs, and low downside drawdown while enforcing the sector cap across the whole selected book.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.4268 >= alpha/N=0.0100) · random_walk_mc(only 57.35% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.6462 (need ≥ 0.20); sub-periods = [+1.589, -2.615])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.29512913724072565
- validation_folds: 13
- per_fold_sortinos: [1.5954, -1.0623, -3.8311, 1.4434, 7.4773, 4.3328, 5.441, 2.2763, -3.3762, -3.0818, -3.609, -1.8447, -1.9245]
- calmar_mean: 0.24107862095022956
- hit_rate_mean: 0.4805860805860806
- profit_factor_mean: 1.5174605329799
- trade_count_total: 99
- aggregate_max_dd: 0.1578157273005845
- worst_fold_max_dd: 0.06393475593949861
- max_position_frac_peak: 0.05072109559433393
- lower_quartile_fold_calmar: -2.0783267237428804
- n_negative_folds: 7/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.295 with no prior kept baseline. Aggregate DD was 15.8%; negative folds were 7/13; trades=99. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.4268 >= alpha/N=0.0100) · random_walk_mc(only 57.35% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.6462 (need ≥ 0.20); sub-periods = [+1.589, -2.615]).

---

## Iteration 2026-05-17-03d9b97 — REVERTED

**Hypothesis:** Replacing pure residual falling-knife entries with news-clean pullbacks inside established intermediate uptrends will improve validation Sortino by buying temporary weakness in proven winners while avoiding event-driven crashes and weak breadth regimes.

**Change:** I changed the strategy to rank PIT-universe names by trend, normalized pullback, downside stability, drawdown control, high proximity, liquidity, and optional LLM news vetoes, with fixed-slot gross scaled by breadth and macro regime stress while preserving order_target_percent sizing and the 25% sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0235 >= alpha/N=0.0100)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.0452539617389713
- validation_folds: 13
- per_fold_sortinos: [2.7668, -1.5466, -2.7314, 0.503, 4.6025, 4.5095, 3.8011, 6.8001, 4.1214, 0.0607, 3.561, 1.5684, -1.4282]
- calmar_mean: 0.8257992143267074
- hit_rate_mean: 0.6257256844083543
- profit_factor_mean: 3.9554471390164734
- trade_count_total: 307
- aggregate_max_dd: 0.08201846474655111
- worst_fold_max_dd: 0.04128222287435777
- max_position_frac_peak: 0.04043791699789258
- lower_quartile_fold_calmar: 0.025566346538434814
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.045 with no prior kept baseline. Aggregate DD was 8.2%; negative folds were 3/13; trades=307. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0235 >= alpha/N=0.0100).

---

## Iteration 2026-05-17-ac5b502 — REVERTED

**Hypothesis:** A confirmed pullback-with-recovery rank inside established intermediate uptrends will improve mean validation Sortino by avoiding residual falling knives while still buying temporary weakness in liquid NSE winners.

**Change:** I replaced the residual-reversal entry with a price-only trend-pullback recovery selector, retained optional bad-news vetoes, enforced whole-book sector caps, and sized every selected name by fixed gross-over-n_positions slots so blocked slots remain cash.

**Decision:** REVERTED — catastrophe: gross exposure: max 128.3% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.9505 >= alpha/N=0.0100) · random_walk_mc(only 4.95% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2873 (need ≥ 0.20); sub-periods = [+1.134, -1.459])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.33583632958180776
- validation_folds: 13
- per_fold_sortinos: [1.9553, -2.294, -3.9647, 3.387, 8.2138, 4.1555, 0.7824, -1.9845, -0.0474, -0.8843, -4.5015, -2.3378, 1.8861]
- calmar_mean: -0.010303175588227397
- hit_rate_mean: 0.4526252809675366
- profit_factor_mean: 1.6740524345892298
- trade_count_total: 507
- aggregate_max_dd: 0.47581957607352426
- worst_fold_max_dd: 0.26520325766283065
- max_position_frac_peak: 0.12326521932088604
- lower_quartile_fold_calmar: -1.476238693349695
- n_negative_folds: 7/13
- risk.passed: False
- risk.violations: ['gross exposure: max 128.3% > 100% (cash account — leverage error)']

**Learning:** Sortino scored 0.336 with no prior kept baseline. Aggregate DD was 47.6%; negative folds were 7/13; trades=507. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: gross exposure: max 128.3% > 100% (cash account — leverage error) | anti-overfit FAILED: bonferroni(p=0.9505 >= alpha/N=0.0100) · random_walk_mc(only 4.95% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2873 (need ≥ 0.20); sub-periods = [+1.134, -1.459]).

---

## Iteration 2026-05-17-a9c490b — REVERTED

**Hypothesis:** A cross-sectional trend-pullback strategy that only buys positive intermediate-trend stocks after a controlled short-term pullback, with fixed-slot sizing and continuous macro stress de-risking, will improve validation Sortino by avoiding both residual falling knives and late-stage momentum chases.

**Change:** I replaced the residual-reversal ranking with a price-only trend-pullback recovery rank, added continuous VIX/Nifty stress gross scaling, and corrected sizing to fixed gross-over-n_positions slots so filtered slots remain cash.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.9488918962407665
- validation_folds: 13
- per_fold_sortinos: [1.2044, -2.6058, -4.2961, 2.1195, 12.2304, 3.117, 1.0411, -1.2269, -0.7983, -2.5522, 0.1312, 4.6591, -0.6877]
- calmar_mean: 0.39130317720407815
- hit_rate_mean: 0.4536464443317713
- profit_factor_mean: 2.033508502902848
- trade_count_total: 515
- aggregate_max_dd: 0.21311321245738507
- worst_fold_max_dd: 0.11839721863427453
- max_position_frac_peak: 0.05975095485757484
- lower_quartile_fold_calmar: -1.8863032033949874
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.949 with no prior kept baseline. Aggregate DD was 21.3%; negative folds were 6/13; trades=515. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0100) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-17-e66bf70 — REVERTED

**Hypothesis:** Buying volume-confirmed volatility-compression breakouts in positive intermediate trends will improve validation Sortino by replacing residual falling-knife entries with fresh strength while staying diversified and cost-aware.

**Change:** I replaced residual reversion with an equal-rank price-volume breakout selector and constructed the book with fixed gross-over-n_positions slots plus a whole-book sector cap.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.3428 >= alpha/N=0.0100) · random_walk_mc(only 65.75% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2325 (need ≥ 0.20); sub-periods = [+0.164, -0.202])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 0.05140203258067428
- validation_folds: 13
- per_fold_sortinos: [0.1333, -1.8673, -4.3114, 0.9278, 1.6917, 1.1008, 1.6424, 1.9, 0.2603, -1.081, 2.2211, 1.6384, -3.5879]
- calmar_mean: 0.20788838609846355
- hit_rate_mean: 0.4886521935104931
- profit_factor_mean: 1.2772041888901653
- trade_count_total: 169
- aggregate_max_dd: 0.10639720681640978
- worst_fold_max_dd: 0.055887050520111635
- max_position_frac_peak: 0.048969992153432874
- lower_quartile_fold_calmar: -1.2603770991449492
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 0.051 with no prior kept baseline. Aggregate DD was 10.6%; negative folds were 4/13; trades=169. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.3428 >= alpha/N=0.0100) · random_walk_mc(only 65.75% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -1.2325 (need ≥ 0.20); sub-periods = [+0.164, -0.202]).

---

## Iteration 2026-05-17-c792756 — KEPT

**Hypothesis:** Replacing residual falling-knife reversion with 12-1 momentum-quality carry plus breadth-scaled fixed-slot exposure will improve mean validation Sortino by owning smoother persistent NSE winners while leaving weak-market and sector-blocked slots in cash.

**Change:** I changed strategy.py from residual reversal to a PIT-universe momentum-quality rank with whole-book sector-cap construction and gross/n_positions sizing so selection filters reduce exposure instead of concentrating it.

**Decision:** KEPT — sortino 2.055 > prev None, agg_dd 4.9%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.05528277047027
- validation_folds: 13
- per_fold_sortinos: [-0.3348, -0.4188, -1.2878, 4.696, 6.9874, 1.2114, 4.3214, 6.6055, 2.352, 0.6559, 0.9666, 1.5153, -0.5513]
- calmar_mean: 1.214468415945593
- hit_rate_mean: 0.4540293040293039
- profit_factor_mean: 4.442047813537827
- trade_count_total: 59
- aggregate_max_dd: 0.049198045262431676
- worst_fold_max_dd: 0.032707975813494314
- max_position_frac_peak: 0.03965068504588806
- lower_quartile_fold_calmar: -0.18260900646095202
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 2.055 with no prior kept baseline. Aggregate DD was 4.9%; negative folds were 4/13; trades=59. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.055 > prev None, agg_dd 4.9%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-89e95d1 — REVERTED

**Hypothesis:** Scaling gross exposure down when the existing momentum-quality screen finds too few positive-momentum names will improve mean validation Sortino by cutting weak-regime downside without changing the kept signal thesis.

**Change:** I added an opportunity-breadth gross adjustment that uses the existing entry_pct as the desired candidate breadth, then funds fixed slots less when the scoreable PIT universe is thinner than that.

**Decision:** REVERTED — sortino 1.879 did not improve on prev 2.05528277047027

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.8792236332074201
- validation_folds: 13
- per_fold_sortinos: [-0.467, -1.2135, -2.2676, 4.1588, 6.8874, 1.2029, 4.5848, 6.6055, 2.352, 0.6559, 0.9666, 1.5153, -0.5513]
- calmar_mean: 1.1457677108959643
- hit_rate_mean: 0.43150183150183147
- profit_factor_mean: 4.751562803418205
- trade_count_total: 62
- aggregate_max_dd: 0.06640389170137881
- worst_fold_max_dd: 0.034362107964349096
- max_position_frac_peak: 0.03965068504588806
- lower_quartile_fold_calmar: -0.18260900646095202
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 1.879 (-0.176). Aggregate DD was 6.6% versus previous kept 4.9%; negative folds were 4/13; trades=62. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.879 did not improve on prev 2.05528277047027.

---

## Iteration 2026-05-17-7d6212e — REVERTED

**Hypothesis:** Adding a point-in-time India macro stress gross cap to the kept momentum-quality book will improve mean validation Sortino by preserving the stock-selection edge while cutting exposure during high-VIX or below-200DMA market stress.

**Change:** I kept the current momentum-quality ranking unchanged and capped breadth-scaled gross with existing macro_regime, India VIX percentile, and Nifty-vs-200DMA signals using the existing regime_pct parameter, so no new strategy parameter is added.

**Decision:** REVERTED — sortino 1.804 did not improve on prev 2.05528277047027 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0645 (need ≥ 0.20); sub-periods = [+2.683, -0.173])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.8043593634759956
- validation_folds: 13
- per_fold_sortinos: [-0.3348, -0.4188, -1.2878, 4.696, 6.9874, 1.2114, 4.3214, 6.3489, 2.6259, 0.9466, 0.5513, -0.5656, -1.6251]
- calmar_mean: 1.0720449162141992
- hit_rate_mean: 0.47291042291042285
- profit_factor_mean: 3.592969654767306
- trade_count_total: 74
- aggregate_max_dd: 0.049198045262431676
- worst_fold_max_dd: 0.032707975813494314
- max_position_frac_peak: 0.04186298553873122
- lower_quartile_fold_calmar: -0.3001551453759954
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 1.804 (-0.251). Aggregate DD was 4.9% versus previous kept 4.9%; negative folds were 5/13; trades=74. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.804 did not improve on prev 2.05528277047027 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.0645 (need ≥ 0.20); sub-periods = [+2.683, -0.173]).

---

## Iteration 2026-05-17-4ebe1d3 — REVERTED

**Hypothesis:** Penalizing large absolute moves in the existing 21-day skip window inside the kept momentum-quality rank will improve validation Sortino by preserving the 12-1 carry edge while avoiding newly stretched or breaking winners.

**Change:** I added a recent_abs_move percentile component to momentum_quality_scores, ranked lower-is-better, so the existing fixed-slot momentum book favors smooth winners without changing sizing, cadence, universe handling, or strategy parameters.

**Decision:** REVERTED — sortino 1.692 did not improve on prev 2.05528277047027 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1433 (need ≥ 0.20); sub-periods = [+2.298, +0.329])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.692427717927515
- validation_folds: 13
- per_fold_sortinos: [-0.1872, -0.6225, -2.2301, 3.9467, 6.4493, 1.4035, 2.1729, 7.29, 2.4617, 0.2448, 1.032, 1.2595, -1.2191]
- calmar_mean: 0.883925793057345
- hit_rate_mean: 0.6239316239316239
- profit_factor_mean: 15.977691241875695
- trade_count_total: 61
- aggregate_max_dd: 0.05285204986499085
- worst_fold_max_dd: 0.03791730326322974
- max_position_frac_peak: 0.04048623287935838
- lower_quartile_fold_calmar: -0.2677604597700478
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 1.692 (-0.363). Aggregate DD was 5.3% versus previous kept 4.9%; negative folds were 4/13; trades=61. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.692 did not improve on prev 2.05528277047027 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1433 (need ≥ 0.20); sub-periods = [+2.298, +0.329]).

---

## Iteration 2026-05-17-afb94b3 — REVERTED

**Hypothesis:** Adding a latest-skip-window directional confirmation component to the kept 12-1 momentum-quality rank will improve validation Sortino by avoiding stale winners whose historical momentum has already started unwinding, unlike the reverted low-absolute-move penalty that removed both upside and downside continuation.

**Change:** I added a recent_mom cross-sectional percentile to momentum_quality_scores, using the existing skip window and no new strategy parameter, while leaving fixed-slot sizing, breadth gross, PIT universe handling, cadence, and sector cap unchanged.

**Decision:** REVERTED — sortino 1.562 did not improve on prev 2.05528277047027 | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2456 (need ≥ 0.20); sub-periods = [+2.532, -0.622])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.5616757192758
- validation_folds: 13
- per_fold_sortinos: [-0.2316, -1.214, -1.2387, 4.302, 9.6355, 2.6872, 4.0365, 2.8832, 1.9295, 0.1607, -0.5388, -1.1875, -0.9222]
- calmar_mean: 0.7644334818094773
- hit_rate_mean: 0.4746336996336996
- profit_factor_mean: 3.870916890310192
- trade_count_total: 81
- aggregate_max_dd: 0.0730610558264766
- worst_fold_max_dd: 0.03875090522209683
- max_position_frac_peak: 0.03998896693583783
- lower_quartile_fold_calmar: -0.5687028040563602
- n_negative_folds: 6/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 1.562 (-0.494). Aggregate DD was 7.3% versus previous kept 4.9%; negative folds were 6/13; trades=81. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.562 did not improve on prev 2.05528277047027 | anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = -0.2456 (need ≥ 0.20); sub-periods = [+2.532, -0.622]).

---

## Iteration 2026-05-17-ecc4916 — REVERTED

**Hypothesis:** Adding a down-market resilience component to the kept 12-1 momentum-quality rank will improve mean validation Sortino by favoring winners that historically lose less on broad NSE down days without changing fixed-slot sizing or gross exposure rules.

**Change:** I compute each candidate's average loss on negative cross-sectional market-return days inside the existing lookback and add its lower-is-better percentile rank to the momentum-quality score, leaving cadence, PIT universe handling, breadth gross, fixed slots, and sector cap unchanged.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0200) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6938744465936084
- validation_folds: 13
- per_fold_sortinos: [-0.3182, -0.0554, -0.682, 5.2161, 8.0735, 2.5176, 8.6029, 2.8076, 1.9472, -0.0391, 1.0695, 4.7357, 1.1449]
- calmar_mean: 1.1685864597213462
- hit_rate_mean: 0.53992673992674
- profit_factor_mean: 11.126845738851955
- trade_count_total: 48
- aggregate_max_dd: 0.04636971690051842
- worst_fold_max_dd: 0.035489191430151217
- max_position_frac_peak: 0.0399012286344789
- lower_quartile_fold_calmar: -0.02795767728663856
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 2.694 (+0.639). Aggregate DD was 4.6% versus previous kept 4.9%; negative folds were 4/13; trades=48. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0200) · random_walk_mc(only 0.00% percentile vs RW null).

---
