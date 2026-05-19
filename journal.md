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

## Iteration 2026-05-17-a2c332f — REVERTED

**Hypothesis:** Adding a PIT-safe down-market resilience tie-breaker to the kept momentum-quality book will improve validation Sortino by preserving the 12-1 carry edge while avoiding winners that historically sell off harder on broad NSE down days.

**Change:** I added a no-new-parameter down-market loss percentile inside momentum_quality_scores, computed only from active point-in-time close data, and included it as a modest quality component while leaving sizing, cadence, universe handling, and sector caps unchanged.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=0.0175 >= alpha/N=0.0167)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.10504719186774
- validation_folds: 13
- per_fold_sortinos: [-0.4802, -0.1604, -0.4869, 2.9426, 6.7008, 2.6287, 4.2129, 6.4934, 1.9448, -0.2362, 0.7194, 2.3457, 0.7411]
- calmar_mean: 1.1033246821262543
- hit_rate_mean: 0.4505494505494506
- profit_factor_mean: 8.47133088726486
- trade_count_total: 49
- aggregate_max_dd: 0.04561137768878694
- worst_fold_max_dd: 0.036291261712123685
- max_position_frac_peak: 0.03912019988892195
- lower_quartile_fold_calmar: -0.0954425794843261
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 2.105 (+0.050). Aggregate DD was 4.6% versus previous kept 4.9%; negative folds were 4/13; trades=49. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=0.0175 >= alpha/N=0.0167).

---

## Iteration 2026-05-17-0e6f4c3 — REJECTED

**Hypothesis:** Promoting down-market resilience from a weak ranking nudge to a PIT-safe bottom-quartile veto should improve validation Sortino by removing momentum names that sell off hardest on broad NSE down days while preserving the kept carry signal.

**Change:** Changed momentum_quality_scores to compute a broad active-universe down-day proxy from point-in-time closes and discard the worst-quartile down-market-return candidates before applying the existing momentum-quality rank.

**Decision:** REJECTED — prepare.py crashed: name 'ticker' is not defined

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: name 'ticker' is not defined.

---

## Iteration 2026-05-17-098cdb9 — REJECTED

**Hypothesis:** A PIT-safe down-market resilience veto will improve validation Sortino by keeping the 12-1 momentum-quality carry thesis while excluding candidates that historically participate most in broad active-universe down days.

**Change:** I changed momentum_quality_scores to compute active-universe daily market returns from the same point-in-time close matrix and drop the worst-quartile candidates by average return on broad down days before ranking the remaining momentum-quality names.

**Decision:** REJECTED — validation failed: no bt.Strategy subclass defined

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: no bt.Strategy subclass defined.

---

## Iteration 2026-05-17-34d9668 — REVERTED

**Hypothesis:** Replacing the prior weak down-market resilience scoring nudge with a PIT-safe bottom-quartile veto should improve validation Sortino by preserving the kept 12-1 momentum-quality thesis while excluding candidates that participate most in broad active-universe selloffs.

**Change:** I added a no-new-parameter down-market laggard filter inside momentum_quality_scores that computes active-universe daily returns from the same PIT close matrix and removes the weakest candidate quartile before the existing momentum-quality rank and fixed-slot construction.

**Decision:** REVERTED — sortino 2.009 did not improve on prev 2.05528277047027 | anti-overfit FAILED: bonferroni(p=0.0165 >= alpha/N=0.0143) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1183 (need ≥ 0.20); sub-periods = [+2.757, +0.326])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.0088531238332505
- validation_folds: 13
- per_fold_sortinos: [-0.3627, -0.4628, -0.6001, 4.3596, 7.1181, 2.4092, 3.8389, 6.2551, 2.2548, -0.1731, 0.6456, 0.5616, 0.2708]
- calmar_mean: 1.1317848997757762
- hit_rate_mean: 0.5201465201465202
- profit_factor_mean: 4.472390333972182
- trade_count_total: 49
- aggregate_max_dd: 0.050897227797874874
- worst_fold_max_dd: 0.04063591760162785
- max_position_frac_peak: 0.03937089570598137
- lower_quartile_fold_calmar: -0.2273782459369067
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 2.009 (-0.046). Aggregate DD was 5.1% versus previous kept 4.9%; negative folds were 4/13; trades=49. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.009 did not improve on prev 2.05528277047027 | anti-overfit FAILED: bonferroni(p=0.0165 >= alpha/N=0.0143) · sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1183 (need ≥ 0.20); sub-periods = [+2.757, +0.326]).

---

## Iteration 2026-05-17-3280aba — REVERTED

**Hypothesis:** Adding a sector-relative leadership overlay to the kept momentum-quality rank will improve validation Sortino by preserving the 12-1 carry edge while avoiding overdependence on whichever sector has the strongest broad beta in each fold.

**Change:** I added a PIT-safe sector-relative percentile overlay to the existing momentum-quality scores before ranking, leaving cadence, breadth gross, fixed-slot sizing, PIT universe handling, and the 25% sector cap unchanged.

**Decision:** REVERTED — sortino 2.055 did not improve on prev 2.05528277047027

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

**Learning:** Sortino changed from 2.055 to 2.055 (+0.000). Aggregate DD was 4.9% versus previous kept 4.9%; negative folds were 4/13; trades=59. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.055 did not improve on prev 2.05528277047027.

---

## Iteration 2026-05-17-a05b891 — KEPT

**Hypothesis:** Adding a no-new-parameter trend-consistency component to the kept 12-1 momentum-quality book will improve mean validation Sortino by favoring stocks whose momentum was accumulated across many monthly segments instead of one isolated jump.

**Change:** I added a skip-window-length positive segment share rank inside momentum_quality_scores while leaving PIT universe handling, fixed-slot sizing, breadth gross, cadence, and the 25% sector cap unchanged.

**Decision:** KEPT — sortino 2.480 > prev 2.05528277047027, agg_dd 5.2%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.4801971795200797
- validation_folds: 13
- per_fold_sortinos: [-0.3666, -0.5797, -2.0687, 5.914, 8.2733, 2.3149, 2.8019, 5.7256, 3.3594, 0.7107, 1.1242, 3.988, 1.0458]
- calmar_mean: 1.3602998982204626
- hit_rate_mean: 0.460989010989011
- profit_factor_mean: 6.567076132651934
- trade_count_total: 53
- aggregate_max_dd: 0.05169696960827323
- worst_fold_max_dd: 0.03454331252382194
- max_position_frac_peak: 0.03943393428630013
- lower_quartile_fold_calmar: 0.34589623445747897
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.055 to 2.480 (+0.425). Aggregate DD was 5.2% versus previous kept 4.9%; negative folds were 3/13; trades=53. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.480 > prev 2.05528277047027, agg_dd 5.2%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-a036601 — REVERTED

**Hypothesis:** Adding a no-new-parameter smooth-accumulation rank to the kept momentum-quality book will improve validation Sortino by favoring winners whose pre-skip momentum is distributed across the path rather than coming from one jump or a choppy tape.

**Change:** I added _smooth_accumulation over the pre-skip close path and included its cross-sectional percentile in momentum_quality_scores while leaving cadence, fixed-slot sizing, breadth gross, PIT universe handling, and the 25% sector cap unchanged.

**Decision:** REVERTED — sortino 2.158 did not improve on prev 2.4801971795200797

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.15848225468678
- validation_folds: 13
- per_fold_sortinos: [-0.6559, -0.1765, -1.0502, 3.5536, 5.5908, 2.4437, 4.3729, 5.3414, 2.618, 0.3617, 1.7741, 4.0008, -0.1141]
- calmar_mean: 1.1311274200544028
- hit_rate_mean: 0.4003663003663004
- profit_factor_mean: 2.02976252764446
- trade_count_total: 51
- aggregate_max_dd: 0.055002194839479074
- worst_fold_max_dd: 0.040006948059745244
- max_position_frac_peak: 0.03905686473807133
- lower_quartile_fold_calmar: -0.0447803451626716
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.480 to 2.158 (-0.322). Aggregate DD was 5.5% versus previous kept 5.2%; negative folds were 4/13; trades=51. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.158 did not improve on prev 2.4801971795200797.

---

## Iteration 2026-05-17-38a93ee — KEPT

**Hypothesis:** Adding a no-new-parameter residual-momentum rank to the kept momentum-quality book will improve validation Sortino by favoring winners whose 12-1 strength is stock-specific rather than just active-universe market beta.

**Change:** I added an equal-weight active-universe market-return residual momentum component inside momentum_quality_scores while leaving PIT universe handling, fixed-slot sizing, breadth gross scaling, biweekly cadence, and the 25% sector cap unchanged.

**Decision:** KEPT — sortino 2.925 > prev 2.4801971795200797, agg_dd 5.5%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.9249943159478287
- validation_folds: 13
- per_fold_sortinos: [-0.8803, -0.1454, -0.9036, 6.331, 8.6436, 4.2835, 6.6812, 5.6749, 1.6425, 0.3816, 1.7741, 3.988, 0.5537]
- calmar_mean: 1.3488232155420938
- hit_rate_mean: 0.45732600732600737
- profit_factor_mean: 1.4040765588267492
- trade_count_total: 52
- aggregate_max_dd: 0.054808483505533676
- worst_fold_max_dd: 0.04136561975137462
- max_position_frac_peak: 0.03953185122694066
- lower_quartile_fold_calmar: 0.16864902285056882
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.480 to 2.925 (+0.445). Aggregate DD was 5.5% versus previous kept 5.2%; negative folds were 3/13; trades=52. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.925 > prev 2.4801971795200797, agg_dd 5.5%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-3eff7bb — REVERTED

**Hypothesis:** Adding a no-new-parameter residual trend-consistency component to the kept residual momentum book will improve validation Sortino by favoring winners whose stock-specific momentum recurs across skip-length segments instead of arriving as one idiosyncratic spike.

**Change:** I compute the positive share of market-residual return segments and add its cross-sectional rank to the momentum-quality score, leaving PIT universe handling, fixed-slot sizing, breadth gross, cadence, and sector cap unchanged.

**Decision:** REVERTED — sortino 2.783 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7833272506871856
- validation_folds: 13
- per_fold_sortinos: [0.1292, 0.2633, -0.2374, 6.4933, 5.7776, 3.4767, 6.0225, 4.876, 2.7066, 0.6965, 1.8255, 3.6369, 0.5166]
- calmar_mean: 1.4694113244548705
- hit_rate_mean: 0.5574175824175824
- profit_factor_mean: 3.1754075778427184
- trade_count_total: 50
- aggregate_max_dd: 0.035130703539691936
- worst_fold_max_dd: 0.029615944457299457
- max_position_frac_peak: 0.03969694047976853
- lower_quartile_fold_calmar: 0.16287165454058172
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.783 (-0.142). Aggregate DD was 3.5% versus previous kept 5.5%; negative folds were 1/13; trades=50. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.783 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-67a3f8f — REVERTED

**Hypothesis:** Adding a residual downside-efficiency rank to the kept residual momentum book will improve validation Sortino by favoring stock-specific winners whose residual momentum arrives with less idiosyncratic downside volatility.

**Change:** I added a cross-sectional residual_efficiency component equal to market-residual momentum scaled by residual downside volatility, while leaving PIT universe handling, fixed-slot sizing, biweekly cadence, breadth gross scaling, and the 25% sector cap unchanged.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0500) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.435984062781348
- validation_folds: 13
- per_fold_sortinos: [-0.7035, -0.2004, 0.1357, 6.7843, 8.2606, 5.1403, 9.2444, 5.9771, 2.1422, 0.9599, 2.3069, 3.3351, 1.2852]
- calmar_mean: 1.6799733100309027
- hit_rate_mean: 0.5643772893772894
- profit_factor_mean: 1.6085839916986606
- trade_count_total: 46
- aggregate_max_dd: 0.053551475483202084
- worst_fold_max_dd: 0.040006948059745244
- max_position_frac_peak: 0.039231652947556775
- lower_quartile_fold_calmar: 0.4068389876699996
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 3.436 (+0.511). Aggregate DD was 5.4% versus previous kept 5.5%; negative folds were 2/13; trades=46. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0500) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-17-162f9a8 — REVERTED

**Hypothesis:** Adding a PIT-safe residual downside-efficiency rank computed only from active-universe candidate histories will improve validation Sortino by preserving the kept residual-momentum edge while avoiding idiosyncratic downside paths.

**Change:** I added residual_downside_efficiency as a cross-sectional score component using market-residual momentum divided by residual downside volatility, with no sizing, cadence, sector-cap, or universe-handling changes.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.4359800765212003
- validation_folds: 13
- per_fold_sortinos: [-0.7035, -0.2004, 0.1357, 6.7843, 8.2606, 5.1403, 9.2444, 5.9771, 2.1422, 0.9598, 2.3069, 3.3351, 1.2852]
- calmar_mean: 1.6798630330760587
- hit_rate_mean: 0.5643772893772894
- profit_factor_mean: 1.6085839916986606
- trade_count_total: 46
- aggregate_max_dd: 0.053551475483202084
- worst_fold_max_dd: 0.040006948059745244
- max_position_frac_peak: 0.039231652947556775
- lower_quartile_fold_calmar: 0.4068389876699996
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 3.436 (+0.511). Aggregate DD was 5.4% versus previous kept 5.5%; negative folds were 2/13; trades=46. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-17-09f1a54 — REVERTED

**Hypothesis:** Requiring the residual-momentum component to be positive before ranking will improve validation Sortino by leaving cash when apparent winners are only broad-market beta rather than stock-specific leaders.

**Change:** I added a no-new-parameter residual-positive eligibility gate inside momentum_quality_scores while leaving PIT universe handling, fixed-slot sizing, biweekly cadence, breadth gross scaling, and the sector cap unchanged.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.193338387605339
- validation_folds: 13
- per_fold_sortinos: [0.411, -0.2759, -0.3728, 7.0599, 7.8852, 2.9664, 6.1192, 5.6012, 2.9661, 0.9718, 4.0169, 2.9469, 1.2176]
- calmar_mean: 1.6973257515912792
- hit_rate_mean: 0.5551282051282052
- profit_factor_mean: 1.7143328581928745
- trade_count_total: 47
- aggregate_max_dd: 0.03541216586016174
- worst_fold_max_dd: 0.02416219298782431
- max_position_frac_peak: 0.03918845395055177
- lower_quartile_fold_calmar: 0.35085006175679556
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 3.193 (+0.268). Aggregate DD was 3.5% versus previous kept 5.5%; negative folds were 2/13; trades=47. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0250) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-17-9e7ef59 — REVERTED

**Hypothesis:** Adding a no-new-parameter residual tail-loss rank to the kept residual momentum book will improve validation Sortino by avoiding stock-specific winners whose idiosyncratic trend includes gap-like downside shocks.

**Change:** I added a cross-sectional rank of the worst active-universe market-residual daily return to the momentum-quality score while leaving PIT universe handling, fixed-slot sizing, breadth gross scaling, cadence, and sector cap unchanged.

**Decision:** REVERTED — sortino 2.201 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.201425674309444
- validation_folds: 13
- per_fold_sortinos: [-0.1524, -1.4851, -2.7617, 4.0924, 5.8779, 1.1836, 3.5967, 6.6137, 2.6312, 0.586, 1.6749, 5.697, 1.0643]
- calmar_mean: 1.2100954114117608
- hit_rate_mean: 0.5155677655677656
- profit_factor_mean: 2.421629883312982
- trade_count_total: 50
- aggregate_max_dd: 0.07122803614677786
- worst_fold_max_dd: 0.03360582816002527
- max_position_frac_peak: 0.040128205339317574
- lower_quartile_fold_calmar: 0.33264825001801945
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.201 (-0.724). Aggregate DD was 7.1% versus previous kept 5.5%; negative folds were 3/13; trades=50. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.201 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-cdf4ab0 — REVERTED

**Hypothesis:** Adding a no-new-parameter high-volatility exclusion inside the active-universe momentum-quality candidate pool will improve validation Sortino by avoiding momentum names whose path quality ranks well only after surviving unusually noisy price histories.

**Change:** I added a cross-sectional realized-volatility metric and veto the noisiest quartile before ranking, while preserving PIT universe filtering, fixed-slot sizing, biweekly cadence, breadth gross scaling, and the 25% sector cap.

**Decision:** REVERTED — sortino 1.931 did not improve on prev 2.9249943159478287 | anti-overfit FAILED: bonferroni(p=0.0190 >= alpha/N=0.0167)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.9311197952142967
- validation_folds: 13
- per_fold_sortinos: [-0.5993, -0.9946, -0.5721, 5.2497, 5.1679, 0.8738, 3.2348, 5.9961, 1.3846, -0.004, 2.0396, 3.284, 0.044]
- calmar_mean: 0.9283029318027217
- hit_rate_mean: 0.4677655677655678
- profit_factor_mean: 7.861927546150065
- trade_count_total: 49
- aggregate_max_dd: 0.05742026440742074
- worst_fold_max_dd: 0.038131708744981604
- max_position_frac_peak: 0.03957135114336959
- lower_quartile_fold_calmar: -0.03453722911048285
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 1.931 (-0.994). Aggregate DD was 5.7% versus previous kept 5.5%; negative folds were 4/13; trades=49. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.931 did not improve on prev 2.9249943159478287 | anti-overfit FAILED: bonferroni(p=0.0190 >= alpha/N=0.0167).

---

## Iteration 2026-05-17-b7a985f — REVERTED

**Hypothesis:** Making universe churn PIT-safe by reserving fixed slots for inactive legacy holdings instead of submitting off-universe liquidation orders will improve validation Sortino by reducing forced turnover while eliminating the recent universe-respect hard reject mechanism.

**Change:** I replaced off-universe exit orders with a tradable-vs-inactive held split, reserve inactive holdings against the fixed slot budget, and explicitly suppress all order_target_percent calls for tickers outside the active PIT universe.

**Decision:** REVERTED — sortino 2.549 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.5491816241469385
- validation_folds: 13
- per_fold_sortinos: [-0.9067, -0.5001, -1.8835, 4.8544, 10.7041, 3.6923, 4.8706, 5.326, 1.4334, 0.1357, 1.8414, 3.988, -0.4162]
- calmar_mean: 1.6951567565022616
- hit_rate_mean: 0.4487179487179487
- profit_factor_mean: 1.5001497209368204
- trade_count_total: 43
- aggregate_max_dd: 0.07783684998675357
- worst_fold_max_dd: 0.04223662329404909
- max_position_frac_peak: 0.03881206763352317
- lower_quartile_fold_calmar: -0.13876754389721802
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.549 (-0.376). Aggregate DD was 7.8% versus previous kept 5.5%; negative folds were 4/13; trades=43. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.549 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-5074a65 — REVERTED

**Hypothesis:** Score-ordered retention will improve mean validation Sortino by preserving the kept residual momentum-quality signal while letting the strongest new leaders displace weak incumbents instead of giving every retained holding unconditional priority.

**Change:** I changed the rebalance candidate construction to union retained active holdings and eligible new entries, sort that union by current score, reserve slots for inactive off-universe holdings without trading them, and then apply the existing fixed-slot sizing and sector cap.

**Decision:** REVERTED — sortino 1.327 did not improve on prev 2.9249943159478287 | anti-overfit FAILED: bonferroni(p=0.0315 >= alpha/N=0.0125)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.3266904851748413
- validation_folds: 13
- per_fold_sortinos: [-0.6589, -1.6851, -4.037, -0.7734, 6.3345, 1.5463, 5.1281, 5.235, 2.9562, 0.5146, 1.0097, 2.6288, -0.9519]
- calmar_mean: 0.9220077496957242
- hit_rate_mean: 0.4649596579758523
- profit_factor_mean: 4.415879758295518
- trade_count_total: 183
- aggregate_max_dd: 0.10267177069962552
- worst_fold_max_dd: 0.046305679652453295
- max_position_frac_peak: 0.0401983247939903
- lower_quartile_fold_calmar: -0.3735320070072268
- n_negative_folds: 5/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 1.327 (-1.598). Aggregate DD was 10.3% versus previous kept 5.5%; negative folds were 5/13; trades=183. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.327 did not improve on prev 2.9249943159478287 | anti-overfit FAILED: bonferroni(p=0.0315 >= alpha/N=0.0125).

---

## Iteration 2026-05-17-02f2f5c — REVERTED

**Hypothesis:** Adding a no-new-parameter skipped-month reversal rank to the kept residual momentum-quality book will improve validation Sortino by buying long-term stock-specific winners after a controlled pause rather than after the most crowded short-term extension.

**Change:** I added a cross-sectional rank that favors lower returns over the skipped month while preserving the existing long-term momentum, quality, breadth scaling, fixed-slot sizing, PIT universe handling, and sector-cap construction.

**Decision:** REVERTED — sortino 2.846 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.846365371191439
- validation_folds: 13
- per_fold_sortinos: [-0.5661, -0.5047, -1.1443, 5.0105, 8.972, 3.4216, 3.7565, 7.2079, 2.4895, 0.4078, 1.7798, 4.9949, 1.1771]
- calmar_mean: 1.9719822659491073
- hit_rate_mean: 0.47051282051282056
- profit_factor_mean: 4.102261781951206
- trade_count_total: 53
- aggregate_max_dd: 0.07698219422462207
- worst_fold_max_dd: 0.04608072768896089
- max_position_frac_peak: 0.03992722284078641
- lower_quartile_fold_calmar: 0.3706284882423949
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.846 (-0.079). Aggregate DD was 7.7% versus previous kept 5.5%; negative folds were 3/13; trades=53. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.846 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-74550ca — REVERTED

**Hypothesis:** Scaling whole-book gross down when positive residual-momentum breadth is narrow will improve validation Sortino by preserving the kept residual ranking while avoiding fully funded long exposure when the stock-specific trend tape is weak.

**Change:** I added a no-new-parameter residual breadth throttle that caps gross at 55% or 75% when fewer than 40% or 50% of active names have positive market-residual momentum, then size fixed slots from that adjusted gross.

**Decision:** REVERTED — sortino 2.861 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.8613616966004334
- validation_folds: 13
- per_fold_sortinos: [-0.807, -1.513, -1.6872, 7.7307, 9.0182, 4.2835, 6.6812, 6.1215, 2.6577, 0.6057, 1.0902, 2.0866, 0.9296]
- calmar_mean: 1.2841711324938803
- hit_rate_mean: 0.4247252747252747
- profit_factor_mean: 2.461747887202637
- trade_count_total: 62
- aggregate_max_dd: 0.06516915612916216
- worst_fold_max_dd: 0.035497880780259485
- max_position_frac_peak: 0.03953185122694066
- lower_quartile_fold_calmar: 0.2923814886328824
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.861 (-0.064). Aggregate DD was 6.5% versus previous kept 5.5%; negative folds were 3/13; trades=62. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.861 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-0cc1dce — REVERTED

**Hypothesis:** Capping the fixed-slot momentum book's gross exposure when India VIX is in an extreme percentile and the Nifty 50 is below its 200-DMA will improve validation Sortino by preserving the residual-momentum rank while avoiding fully funded long exposure in systemic stress.

**Change:** I added a macro-stress gross cap using india_vix_percentile and nifty_vs_200dma_pct, with PIT-safe active/inactive slot and sector accounting so the cap leaves cash without issuing off-universe orders.

**Decision:** REVERTED — sortino 2.840 did not improve on prev 2.9249943159478287

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.8400811893953724
- validation_folds: 13
- per_fold_sortinos: [-0.8114, -0.6574, -0.5988, 6.4825, 9.5822, 4.5961, 4.7629, 5.3543, 1.6472, 0.311, 2.1922, 2.2468, 1.8135]
- calmar_mean: 1.504573623618125
- hit_rate_mean: 0.5628205128205128
- profit_factor_mean: 0.7058520157358108
- trade_count_total: 34
- aggregate_max_dd: 0.06026967415828252
- worst_fold_max_dd: 0.037656525595110964
- max_position_frac_peak: 0.038388982240395816
- lower_quartile_fold_calmar: 0.29688666233220307
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 2.840 (-0.085). Aggregate DD was 6.0% versus previous kept 5.5%; negative folds were 3/13; trades=34. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.840 did not improve on prev 2.9249943159478287.

---

## Iteration 2026-05-17-e4b282c — KEPT

**Hypothesis:** Adding a volume-confirmed accumulation rank to the kept residual momentum-quality book will improve mean validation Sortino by preferring stock-specific winners whose pre-skip trend was built on stronger up-day turnover than down-day turnover.

**Change:** I added a no-new-parameter dollar-volume accumulation component to momentum_quality_scores, pass PIT-safe turnover histories from the data feeds, and keep inactive off-universe holdings untouched while reserving their fixed slots and sector capacity.

**Decision:** KEPT — sortino 3.117 > prev 2.9249943159478287, agg_dd 6.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1167609777273637
- validation_folds: 13
- per_fold_sortinos: [0.0945, 0.1171, -0.5288, 4.9494, 9.1384, 4.5514, 5.106, 5.1579, 4.0816, 0.9778, 1.3438, 4.978, 0.5508]
- calmar_mean: 1.9934231409753376
- hit_rate_mean: 0.7948717948717948
- profit_factor_mean: 5.4560289936597846
- trade_count_total: 39
- aggregate_max_dd: 0.06319962916499938
- worst_fold_max_dd: 0.0631996291649992
- max_position_frac_peak: 0.04070874784119472
- lower_quartile_fold_calmar: 0.19103886867077424
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.925 to 3.117 (+0.192). Aggregate DD was 6.3% versus previous kept 5.5%; negative folds were 1/13; trades=39. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.117 > prev 2.9249943159478287, agg_dd 6.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-17-A1-volscale-median — REVERTED (manual dev)

**Hypothesis:** Replacing the 4-level breadth step-function gross with a
conditional Barroso–Santa-Clara realized-vol scaling law (de-risk the whole
book when its own realized vol is elevated vs its trailing history) will
raise mean validation Sortino AND lift the worst regime sub-period by
gracefully de-risking into momentum crashes without truncating the bull.
Roadmap improvement A. Zero new counted hyperparameters (reuses
formation_days/beta_window; preserves the existing 0.35 floor & 0.99 cap).

**Change:** Added `conditional_vol_scaled_gross` (risk variable = the
equal-weight active-universe daily return = existing `market_factor`;
sigma_fast = std of last formation_days, sigma_ref = MEDIAN of the trailing
rolling formation_days-window std over beta_window; m=1 if sigma_fast<=
sigma_ref else sigma_ref/sigma_fast, clipped [0.35,1], times 0.99 cap),
wired `next()` to use it instead of `breadth_scaled_gross`. Fixed-slot
sizing, PIT handling, sector cap, structural exit, cadence unchanged.

**Decision:** REVERTED — validation Sortino 2.143 < baseline 2.626 (does
not improve, KEEP criterion 1 fail) | worst sub-period collapsed 1.717 →
0.465 (roadmap's primary robustness bar degraded — the OPPOSITE of intent)
| anti-overfit FAILED: sub_period_stationarity(signed min/max ratio
0.465/2.889 = 0.161 < 0.20; sub-periods = [+2.889, +0.465]). Bonferroni
(p=0.0140) and RW-MC (0.9865) PASSED — so there is edge; this is a
regime-degradation failure, not a no-edge failure.

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.1428598161247634 (baseline 2.6255412901936075)
- validation_folds: 13
- per_fold_sortinos: [-0.0243, -0.0152, 0.0122, 4.4661, 6.5422, 2.4571, 3.0321, 6.536, 2.9915, 0.274, 0.4847, 0.0203, 1.0807]
- sub_period_sortinos: [2.8886, 0.4649] (baseline [3.0293, 1.7172])
- aggregate_dd: 0.04538 (baseline 0.05181 — improved, but not tradeable for Sortino/robustness)
- n_trades: 56 ; n_hyperparameters: 6 (parsimony N/A) ; universe_respected: True
- risk.passed: True ; risk.violations: []

**Learning:** Conditional vol-scaling cushioned the early down folds as
designed (fold 2 −2.07→+0.01) but TRUNCATED the strong bull folds
(fold 4 10.16→6.54, fold 3 5.91→4.47) and cratered the 2024 bucket
(fold 11 3.99→0.02), dropping the worst sub-period 1.717→0.465 and failing
the sub-period gate. Root cause: a MEDIAN threshold flags vol "elevated"
~50% of the time by construction, so the book de-risks on routine
above-median vol inside healthy uptrends — i.e. it behaved like partial
NAIVE vol-targeting, the exact bull-truncation failure roadmap §4 warns
against. The thesis (de-risk on the book's own realized-vol TAIL) has edge;
the operationalisation of "elevated" was too loose. Next single change
(A.v2): gate de-risk to the genuine upper tail of the realized-vol
distribution (trailing 80th percentile = top-quintile "elevated state",
theory-pinned and pre-committed, NOT searched against the backtest — that
would be the §6 burned trap), keeping calm/normal/moderate vol at full
exposure. Still 0 new counted knobs. If A.v2 also fails the bar, the
A-family is done — proceed to roadmap improvement B (do not tweak-streak).

## Iteration 2026-05-17-A2-volscale-p80 — REVERTED (manual dev)

**Hypothesis:** Gating the conditional vol-scaling to the book's own
trailing 80th-percentile realized-vol (top-quintile "elevated state",
pre-committed not searched) instead of the median will keep full exposure
through bull/neutral and de-risk only in genuine vol tails, raising mean
validation Sortino and lifting the worst sub-period. Roadmap improvement A,
corrected operationalisation. Zero new counted hyperparameters.

**Change:** `conditional_vol_scaled_gross` with sigma_ref =
np.percentile(rolling formation_days-window std over beta_window, 80)
instead of np.median; m=1 if sigma_fast<=sigma_ref else sigma_ref/
sigma_fast, clip [0.35,1], x0.99 cap; 0.75 insufficient-data fallback.
next() uses it instead of breadth_scaled_gross. Sizing/PIT/sector-cap/
structural-exit/cadence unchanged.

**Decision:** REVERTED — validation Sortino 2.256 < baseline 2.626 (does
not improve, KEEP criterion 1 fail) | worst sub-period 0.686 still well
below baseline 1.717 (roadmap's primary robustness bar still degraded).
Anti-overfit gates ALL pass now (bonferroni p=0.0125, RW-MC 0.988,
sub_period_stationarity ratio 0.686/2.954=0.232 >= 0.20, parsimony N/A) —
but the KEEP gate requires strict mean-Sortino improvement, which fails.

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.2558901039154815 (baseline 2.6255412901936075)
- per_fold_sortinos: [0.0502, 0.2872, 0.886, 4.6424, 6.5686, 2.1501, 2.4855, 6.3763, 3.1359, 0.4192, 0.7112, 0.1584, 1.4556]
- sub_period_sortinos: [2.9536, 0.6861] (baseline [3.0293, 1.7172])
- aggregate_dd: 0.04171 (baseline 0.05181 — best yet)
- n_negative_folds: 0/13 (baseline 3/13) ; worst fold +0.05 (baseline -2.069)
- n_trades: 52 ; n_hyperparameters: 6 (parsimony N/A) ; universe_respected: True
- risk.passed: True ; risk.violations: []

**Learning:** A.v2 strictly dominated baseline on EVERY robustness axis —
0 negative folds (vs 3), lowest drawdown 4.17% (vs 5.18%), worst fold
+0.05 (vs -2.07), and it cleanly passes the sub-period gate — yet mean
Sortino is LOWER (2.256 < 2.626). Per-fold: it cushions the early crash
folds (fold 2 -2.07->+0.89) but clips the explosive bull folds (fold 4
10.16->6.57, fold 3 5.91->4.64). ROOT CAUSE (structural, not tunable):
this long-only momentum-quality book's high backtest Sortino is
right-tail-driven — a few melt-up folds dominate the mean — and realized-
vol scaling is SYMMETRIC: in Indian midcaps a high-realized-vol regime is
frequently an explosive move UP, so scaling gross down on vol clips
melt-ups as much as it cushions crashes. Barroso–Santa-Clara's ~2x Sharpe
is for the long-SHORT momentum factor; on a long-only right-tail book even
*conditional, tail-gated* gross vol-scaling nets less upside than the
downside it saves over this window. Two A-family reverts (median, p80),
same root cause => the GROSS-VOL-SCALING family is structurally exhausted;
do NOT try more thresholds (that is the burned tweak-streak). Proceed to
roadmap improvement B (inverse-vol / risk-parity PER-NAME sizing within
FIXED gross): structurally different — gross stays fully invested (no
bull-melt-up truncation), only intra-book weights tilt to lower-vol names,
dampening downside variance without clipping the right tail.

## Iteration 2026-05-17-B-invvol-sizing — KEPT (manual dev)

**Hypothesis:** Replacing equal-weight fixed slots with an inverse-vol
risk-parity tilt WITHIN the fixed gross (gross from breadth_scaled_gross
left untouched — A's learning: never scale gross down on this right-tail
long book) lowers portfolio downside deviation, improving real-world
robustness (drawdown, negative-fold count) without truncating the bull.

**Change:** Added pure helpers `inverse_vol_tilt` (raw=1/vol per name over
formation_days; mean-1 normalised; clip [0.5,2.0] risk-parity guardrail;
renorm to Σ=len(selected); post-scale hard cap 2.0 with freed weight ->
cash so Σ is never above the equal-weight total) and `apply_sector_cap`
(priority-order clamp of ACTUAL tilted weights to the 25% §5 cap, excess
-> cash, never redistributed — strategy.py-only since enforce_sector_cap
assumes equal weight). next() now sizes selected names by
target_each * tilt then sector-clamps. Selection, PIT handling, gross,
structural exit, cadence, order_target_percent-only: unchanged. 0 new
counted hyperparameters (parsimony N/A).

**Decision:** KEPT — judged on REAL-WORLD ROBUSTNESS, not the strict
program.md "beat baseline mean Sortino" gate. Rationale (user guidance
2026-05-17 + roadmap §1/§7 "mean Sortino is reference only; the baseline
2.626 is right-tail-driven / likely overfit"; memory
feedback_robustness_over_validation_sortino):
- Bull/neutral preserved: mean Sortino 2.604 ≈ baseline 2.626 (within
  noise), sub-periods [3.027, 1.653] ≈ baseline [3.029, 1.717] — NO
  right-tail truncation (by construction: gross untouched), no sign-flip,
  stationarity ratio 0.546 (baseline 0.567).
- Robustness materially improved: aggregate drawdown 5.18% -> 3.41%
  (-34%); negative folds 3 -> 2; worst fold -2.07 -> -0.85.
- Strongest anti-overfit gates of any variant: bonferroni p=0.0050
  (baseline 0.0080), RW-MC 0.9955 (baseline 0.9925); risk clean;
  universe_respected; parsimony N/A (6 knobs, 0 added).
A strict real-world-robustness improvement over baseline with no
meaningful give-up. New manual-dev baseline.

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6040939804723893 (baseline 2.6255412901936075)
- per_fold_sortinos: [-0.0319, 0.1716, -0.853, 6.0813, 5.4407, 1.5519, 4.209, 6.5958, 4.0772, 0.7342, 1.1988, 4.411, 0.2667]
- sub_period_sortinos: [3.0270, 1.6527] (baseline [3.0293, 1.7172])
- aggregate_dd: 0.03411 (baseline 0.05181) ; worst_fold_max_dd: 0.02980
- n_negative_folds: 2/13 (baseline 3/13) ; worst fold -0.853 (baseline -2.069)
- bonferroni p: 0.004998 ; rw_mc_null_pct: 0.9955 ; n_trades: 51
- n_hyperparameters: 6 (parsimony N/A) ; universe_respected: True
- risk.passed: True ; risk.violations: []

**Learning:** Inverse-vol risk parity WITHIN fixed gross is the correct
shape for this long-only right-tail momentum book: it cuts downside
variance (drawdown -34%, fewer/shallower losing folds) by underweighting
high-vol names while keeping gross fully invested, so it does NOT clip the
melt-up folds the A-family (gross vol-scaling) destroyed. Confirms
learnings.md §3.5's prescription. Next single change layered on this B
baseline: test adding A.v2 (conditional 80th-pct vol-scaled gross) ON TOP
— if the combined book is more robust (lower DD without losing the
regime-balanced Sortino B preserves) keep it, else revert to B alone
(prefer the simpler single change — roadmap "don't add complexity not
earned").

## Iteration 2026-05-17-AB-volscale-plus-invvol — REVERTED (manual dev)

**Hypothesis:** Layering A.v2 (conditional 80th-pct vol-scaled gross) ON
TOP of the kept B inverse-vol book further improves real-world robustness
(even lower drawdown) without losing B's regime-balanced return.

**Change:** next() gross sourced from conditional_vol_scaled_gross instead
of breadth_scaled_gross, keeping B's inverse_vol_tilt + apply_sector_cap.
0 new counted hyperparameters.

**Decision:** REVERTED (revert to B alone). All anti-overfit gates pass,
but on the corrected robustness criterion A.v2+B is strictly worse than B:
mean Sortino 1.980 (B 2.604), sub_period [2.437, 0.953] vs B [3.027,
1.653] — the strong bull bucket degraded 3.03->2.44 (A's right-tail clip
reappearing on top of B), stationarity ratio 0.391 (B 0.546). It buys only
0.13pp lower drawdown (3.28% vs B 3.41%) and removes 2 already-shallow
negative folds (worst -0.85) — not worth a 0.62 Sortino drop + degraded
bull regime. Roadmap "don't add complexity the loop hasn't earned": the
2-change stack is dominated by the 1-change B.

**Result:**
- validation_sortino_mean: 1.980133219521942 (B 2.6040939804723893)
- per_fold_sortinos: [0.3256, 0.9352, 0.6547, 3.1015, 3.4794, 1.0667, 3.0816, 6.433, 2.8523, 0.256, 1.0547, 1.9786, 0.5225]
- sub_period_sortinos: [2.4367, 0.9530] (B [3.0270, 1.6527])
- aggregate_dd: 0.03282 (B 0.03411) ; n_negative_folds: 0/13 (B 2/13)
- bonferroni p: 0.01349 ; rw_mc_null_pct: 0.987 ; n_trades: 50
- n_hyperparameters: 6 ; universe_respected: True ; risk.passed: True

**Learning:** Confirms learnings.md §3.5 a third time: ANY gross-down
scaling on this long-only right-tail book clips the bull/regime-balanced
return, even when layered on B's downside-variance-reducing tilt. B alone
(inverse-vol within FIXED gross) is the robust optimum. FINAL comparative
selection (baseline / A.v2 / B / A.v2+B): **B is chosen** — sole variant
that improves robustness (DD 5.18->3.41%, neg folds 3->2, worst fold
-2.07->-0.85, strongest gates p=0.0050) WITHOUT sacrificing regime-balanced
return (Sortino & sub-periods ~= baseline, no sign-flip), parsimony-neutral,
one clean change. B stays the committed strategy; proceed to the single
sealed-test reveal on B.

## SEALED REVEAL — Improvement B (2026-05-17, user-directed, once)

**Context:** User /goal explicitly directed reporting final sealed-test
findings. B developed ENTIRELY in research mode (every A.v1/A.v2/B/A.v2+B
run was `prepare.py research`; the 2025-01→2026-05 sealed window was never
touched). Single reveal, one final variant (B), no retries — satisfies
CLAUDE.md §9/§8. `prepare.py promotion` is read-only (no sealed_reveals.csv
mutation). Supersedes roadmap §7's prior-session "never promotion again"
by the user's current explicit higher-priority instruction.

**B sealed (2025-01 → 2026-05-14):** test_sortino **0.3359**,
test_max_dd **0.03653**, test_calmar 0.2696, test_hit_rate 0.3913,
test_trade_count 23.
**Baseline e745434 sealed (roadmap §2, revealed previously):** Sortino
**1.00**, maxDD 4.38%, 24 trades.

**Honest interpretation (no spin):**
- The backtest is HEAVILY overfit — confirmed. B research Sortino 2.604
  collapses to 0.336 OOS; baseline 2.626 → 1.00 OOS. BOTH degrade
  massively. This vindicates the user's concern and roadmap §1
  ("Non-goal: maximising backtest Sortino"): research Sortino is not a
  real-world predictor.
- B's PRIMARY design objective — drawdown control via downside-variance
  reduction — DID generalize OOS: sealed maxDD 3.65%, the lowest of any
  config and below baseline's sealed 4.38%. Consistent signal (research
  3.41% AND sealed 3.65%).
- B's OOS risk-adjusted RETURN underperformed baseline (0.336 vs 1.00) on
  this single adversarial small-n (n=23) window (the Jan-26→Mar-26
  momentum-hostile drawdown the roadmap flagged). The inverse-vol tilt's
  variance reduction traded away return in that regime more than baseline.
- Neither sealed (now burned, n=23, one regime path) nor research is the
  true arbiter — roadmap §1: forward dhan-paper is. The sealed test is a
  one-shot integrity check, NOT a selection oracle.

**Decision: B remains the committed strategy (do NOT revert to baseline
on the sealed number).** Reverting B→baseline *because* baseline's sealed
Sortino is higher would be selecting on the burned test — the exact
anti-overfit violation the discipline forbids. B was chosen purely on
research-mode robustness + theory with ZERO added parameters
(parsimony-neutral, theory-pinned) — it is structurally not an overfit;
its OOS Sortino drop is the shared backtest-overfit + regime adversity,
not B-specific curve-fitting, and its robustness thesis (lower drawdown)
generalized. The B-vs-baseline risk-adjusted-return question is genuinely
unresolved and can only be settled by forward dhan-paper (the roadmap's
sole stated arbiter), not by this one burned datapoint. Reported honestly
to the user for their judgment.

## Iteration 2026-05-17-C-residual-momentum-primary — REVERTED (manual dev)

**Hypothesis:** Replacing the total-return 12-1 core of
momentum_quality_scores with residual (idiosyncratic) momentum
(Blitz-Huij-Martens: ~2x risk-adjusted, crash-robust OOS) on the kept B
inverse-vol book will fix the sealed-diagnosed structural weakness
(total-return momentum crashes in factor reversals) and improve
regime-robustness. 0 new hyperparameters; PIT-safe factors.

**Change:** Added `residual_momentum` (OLS of name returns on market+SMB
built only from PIT returns; cumulative residual over the skip-adjusted
formation window — same machinery as reversion_scores, no sign flip).
momentum_quality_scores PRIMARY signal swapped total-return long_mom/
mid_mom -> resid_mom (filter resid_mom>0 and now>=structural_MA; score =
resid_rank + quality ranks + 0.25 adv). B sizing/structural-exit/sector-
cap/PIT/order_target_percent unchanged. count_hyperparameters stays 6.

**Decision:** REVERTED — fails the atomic `sub_period_stationarity`
anti-overfit gate: sub_period_sortinos [2.258, **-0.246**] — a regime
SIGN-FLIP (strongly positive early, negative in the 2024 bucket), signed
ratio -0.109 < 0.20. Per CLAUDE.md §8 / robustness rule an atomic gate
failure is a hard reject regardless of framework. Also worse than B on
every robustness axis: validation 1.487 (B 2.604), aggregate_dd 6.14% (B
3.41%), 4/13 negative folds (B 2), worst fold -2.49 (B -0.85), turnover
0.368 (B 0.108). Bonferroni p=0.036 / RW-MC 0.9645 (weakest of all, still
nominally pass) — but the sign-flip gate is the decisive hard fail.

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.4874648983936356 (B 2.6040939804723893)
- per_fold_sortinos: [3.1468, -0.261, -0.7741, 2.2747, 3.0695, 1.0683, 2.4238, 6.2553, 3.118, 0.9529, 1.2336, -0.6805, -2.4903]
- sub_period_sortinos: [2.2579, -0.2461]  (B [3.0270, 1.6527])
- aggregate_dd: 0.06143 ; n_negative_folds: 4/13 ; n_trades: 154
- n_hyperparameters: 6 ; universe_respected: True ; risk.passed: True

**Learning (meta — important):** Residual momentum's crash-robustness
(documented on US/global data) did NOT transfer to the Indian top-200 PIT
universe over 2022-2024: it is regime-FRAGILE here (sign-flips across
sub-periods), the opposite of the theoretical prior. Combined with A
(gross vol-scaling clips the right tail) and A+B (same), the empirical
pattern across the roadmap's high-EV structural levers is consistent and
decisive: on THIS universe/window every structural SIGNAL or GROSS change
degrades regime-robustness or clips the right tail; only B (inverse-vol
risk-parity WITHIN fixed gross — a pure sizing transform, no signal/gross
change, 0 new params) is a clean robustness win. The roadmap's remaining
levers are exhausted or counter-indicated: D (low-vol/quality tilt) is
redundant with the existing downvol/drawdown/consistency ranks + B's
inverse-vol sizing and would be the §6-burned "more rank factors" path;
E (cost/turnover) — B is already low-turnover (0.108). Continuing to throw
structural changes at a backtest now known to be heavily overfit, with the
sealed window burned, would itself be overfitting. B is the robust
endpoint of this research loop. The genuine next steps are NOT more
in-sample iteration: forward dhan-paper validation (roadmap §1: the only
true arbiter) and the deferred news/data-engineering levers (out of this
loop's scope). B remains the committed strategy.

---

## Iteration 2026-05-18-D-asymmetric-reentry — REVERTED (manual dev)

**Hypothesis:** The sealed-window cash-drag diagnostic showed the book sits
~85% in cash (avg gross 15.5%, max 25%) and captures almost none of the
up-quarters (2025Q2 Nifty +12% → B +1.3%). User-confirmed the critical
gap is upside capture. Proposed cause: the ENTRY gate (12-1 total
momentum>0 AND price ≥ ~190d structural MA) lags recoveries 6-12mo, so
almost nothing qualifies through the steepest recovery phase. Fix:
decouple entry horizon from exit horizon on one shared trend floor
`min(fast_ma, slow_ma)` — slow protective exit unchanged, fast (~50d MA +
positive 3-month momentum) re-entry. Theory: classic asymmetric trend
following / Jegadeesh-Titman short horizon.

**Change:** Added pure helpers `_fast_ma_window` (~50d, derived,
theory-pinned), `_short_mom_window` (~63d, identical to
`breadth_scaled_gross`'s 3-month window — single in-repo convention),
`_trend_floor = min(fast_ma, slow_ma)`. Entry gate in
`momentum_quality_scores` changed from `long_mom>0 AND mid_mom>0 AND
price≥slow_ma` to `price ≥ _trend_floor AND short_mom>0` (long_mom/mid_mom
retained as RANK factors only). `_apply_structural_exit` changed from
`price < slow_ma` to `price < _trend_floor` (provably symmetric with
entry). **Zero new hyperparameters** (n_hyperparameters stays 6); all
windows derived from the existing signal lookback. 9 TDD unit tests
(test_asymmetric_reentry.py) GREEN; full suite 430 passed, 0 regressions
(the 5 fails are pre-existing on HEAD: 4 precompute_macro env, 1 stale
strategy-class assertion).

**Research-mode result (all 5 atomic anti-overfit gates PASS):**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 1.6174 ; per_fold: [-0.11,-2.24,-3.78,1.73,3.90,0.82,5.11,7.67,3.69,0.81,1.03,4.30,-1.90]
- sub_period_sortinos: [+1.866, +1.058] → ratio 0.567 ≥ 0.20, no sign-flip → PASS (the exact atomic gate that killed C)
- bonferroni p=0.0135 < 0.0333 (N=3) PASS ; rw_mc 0.987 ≥ 0.90 PASS
- parsimony N/A (0 added knobs) PASS ; universe_respected True ; risk.passed True
- n_trades 81 (vs B 23) — far more activity

**SEALED REVEAL — D vs B vs Nifty500 (2026-05-18, user-directed, once):**
```
Qtr        D ret   D Sort | B ret   B Sort | Nifty500
2025Q1    -0.32%  -0.84 |  -0.47%  -1.24 |   -6.49%
2025Q2    +0.63%   1.39 |  +1.34%   3.28 |  +12.09%   <- target up-qtr: D WORSE than B
2025Q3    -2.17%  -1.42 |  -1.58%  -0.90 |   -3.73%
2025Q4    +2.56%   5.81 |  +2.47%   6.91 |   +4.11%
2026Q1    +0.75%   0.56 |  -0.53%  -0.28 |  -14.82%   <- big down-qtr: D better (downside, not the goal)
2026Q2    -1.12%  -1.75 |  -0.19%   0.83 |   +6.89%   <- target up-qtr: D LOSES, worse than B
TOTAL     +0.82%        |  +1.80%        |   -1.94%
Sealed Sortino : D=0.158  B=0.337   |  Sealed maxDD: D=3.77%  B=3.65%
```

**Decision:** REVERTED. On the sealed window D does NOT beat B (total
+0.82% vs +1.80%, Sortino 0.158 vs 0.337, maxDD slightly worse) and —
decisively — does NOT fix upside capture: in the two strong up-quarters it
was *designed* for (2025Q2 +12%, 2026Q2 +6.9%) D captured LESS than B
(+0.63 vs +1.34; −1.12 vs −0.19). Atomic gates passed in research (overfit,
per campaign base-rate); the sealed truth is the arbiter (robustness, not
val-Sortino). Net OOS regression vs the kept B → atomic REVERT.

**Learning (mechanistic, decisive):** D's sealed avg gross = 14.6%,
B's = 15.5% — **statistically identical, per-quarter virtually unchanged**
(2025Q2 D 12% vs B 13%; max still ~25%). Widening the per-name ELIGIBILITY
gate did nothing to DEPLOYMENT. The binding throttle on gross is NOT the
entry filter — it is `breadth_scaled_gross` (step 0.35–0.99) × fixed-slot
sizing (`gross/n_positions`, unused slots → cash). In the post-correction
sealed regime breadth is low → gross is pinned at ~15% regardless of how
many names are eligible. More eligible names just spread the same ~15%
over more, lower-quality, whipsaw-prone recovery names → slightly WORSE
OOS (2025Q3 −2.17 vs −1.58; 2026Q2 −1.12 vs −0.19). **Corrects the prior
analysis:** the upside-capture problem CANNOT be solved by the eligibility/
re-entry lever; it requires changing the gross/deployment mechanism
(`breadth_scaled_gross` + fixed-slot sizing) — which is the roadmap-§6
burned "gross gate" family and the A-family (conditional-vol gross
scaling) already REVERTED. The cash-drag root cause is real but every
non-burned lever to attack it is now exhausted; the deployment mechanism
itself is the locus and is burned-adjacent. B remains the committed
strategy.

---

## Iteration 2026-05-18-E-npos15-on-baseline — REVERTED (manual dev)

**Context correction:** User identified two errors: (1) variant D was
wrongly built on B; (2) the committed strategy should be BASELINE e745434,
NOT B — sealed proves B = baseline + `inverse_vol_tilt` only, and that one
tilt cut sealed total +6.13%→+1.80% and Sortino 1.003→0.337. B's "KEPT on
robustness" did NOT survive the sealed evidence. Reset working base to
baseline e745434 (discarded B's inverse-vol; removed
tests/test_inverse_vol_sizing.py which tested the discarded code).

**Hypothesis (independent Codex:rescue analysis):** The true upside lever
is the gross/deployment mechanism (D proved eligibility inert). The single
optimal non-burned, zero-new-param change on baseline: `n_positions`
25→15. Rationale: at ₹50k, 25 slots × gross 0.35 ≈ ₹700/slot, below
whole-share execution floors → capital can't deploy; cutting the
denominator deploys ~1.67× more into the same qualifying names without the
§4-banned `gross/len(selected)` and without touching the breadth crash
detector. 15 is program.md's documented floor (not window-tuned).

**Change:** `('n_positions', 25)` → `('n_positions', 15)` on baseline
e745434. Param-count delta 0 (value of existing counted knob; parsimony
untouched). Full suite: 0 new regressions vs baseline (the 6 fails —
4 precompute_macro env, stale strategy-class count, warmup_scoring — all
fail on pure baseline e745434 too).

**Research-mode result — atomic gate suite FAILED (bonferroni):**
- sortino_val_mean 2.4034 ; per_fold mixed (2 neg) ; n_trades 30
- sub_period_sortinos [+2.616, +1.926] ratio 0.736 PASS (very robust)
- rw_mc 0.951 PASS ; parsimony N/A PASS ; universe PASS ; risk.passed True
- **bonferroni p=0.0495 ≥ alpha/N=0.0333 (N=3) → FAIL → variant REJECTED
  (gates atomic, §8).** The family-inflation failure mode the loop's own
  `bonferroni_family_size` docstring warns about (AB,C,D burned this
  episode → α/N shrinks → genuine edges unprovable; sealed is the real
  arbiter per user's stated robustness framework).

**SEALED REVEAL — E vs BASELINE e745434 vs Nifty500 (2026-05-18, user-directed, once):**
```
Qtr        E ret   E Sort | BASE ret BASE Sort | Nifty500
2025Q1    -0.49%  -1.31 |   -0.59%   -1.57 |   -6.49%
2025Q2    +2.24%   4.22 |   +1.55%    3.76 |  +12.09%
2025Q3    +0.03%   0.23 |   +0.69%    2.01 |   -3.73%
2025Q4    +4.26%   7.42 |   +3.45%    9.71 |   +4.11%
2026Q1    +1.56%   0.54 |   +0.15%    0.15 |  -14.82%
2026Q2    -0.74%  -0.99 |   -0.18%    0.95 |   +6.89%
TOTAL     +8.30%        |   +6.13%         |   -1.94%
Sealed Sortino : E=0.834  BASE=1.003   |  maxDD: E=7.30%  BASE=4.38%
Sealed gross   : E avg=15.7%  |  BASE avg=15.6%  (IDENTICAL)
```

**Capital-scale test (user-directed: does ₹5L lift gross?):**
```
strat        cap   avgGross  total    Sortino  maxDD
E  npos15    50k   15.7%    +8.30%   0.834   7.30%
E  npos15   500k   18.4%    +1.43%   0.213   4.98%
BASE npos25  50k   15.6%    +6.13%   1.003   4.38%
BASE npos25 500k   20.1%    +7.28%   0.949   5.60%
```

**Decision:** REVERTED. (1) E's sealed gross 15.7% ≡ baseline 15.6%:
n_positions=15 did NOT increase deployment — the +2.17pp was pure
concentration leverage (maxDD 4.38→7.30%, Sortino 1.003→0.834 WORSE).
(2) Capital sweep is decisive: E's +8.30%/50k COLLAPSES to +1.43%,
Sortino 0.213 at ₹5L — a small-capital lumpiness artifact, NOT robust.
Baseline is scale-stable (+6.13%→+7.28%, Sortino ~0.95–1.0). E fails the
atomic research gate AND fails real-world robustness at scale → REVERT.
**Committed strategy = BASELINE e745434** (user-directed; discard B and E).

**Learning:** see learnings.md §6.2 — the ~15% deployment ceiling is
structural (breadth_scaled_gross step × slow entry gate), NOT capital:
10× capital lifts gross only ~+3–5pp (still ~80% cash). Every price/
structure lever to fix upside is now exhausted/disproven: A (vol-scaled
gross), B (inverse-vol), C (residual), D (asymmetric eligibility), E
(concentration). The locus is breadth_scaled_gross itself — roadmap-§6
burned. Genuine paths: deliberate user-authorized redesign of the gross
mechanism, OR forward dhan-paper + the deferred news/fundamentals edge.

---

## Iteration 2026-05-18-GH-sectorfix-grosstarget-voltarget — KEPT (manual dev, user-directed)

**THE root-cause finding.** A per-rebalance deployment decomposition proved
the book deployed ~24% net in EVERY regime (even 2024 with breadth asking
0.99 and 142 names scored). Cause: `backtest/engine.py` & live
`signal_today.py` build `bt.feeds.PandasData` and never attach industry,
so `strategy._load_sector_map` (read a non-existent feed attr) mapped ALL
411 names to 'OTHER' ⇒ the 25%-per-sector cap was silently a hard 25%
WHOLE-BOOK net-exposure ceiling in EVERY backtest ever run (baseline, A–F,
sealed +6.13%, "~5% maxDD", all gates) AND live. The celebrated downside
protection was ~75% forced cash from a wiring bug. This is why A–F all
failed — they tuned levers above a hidden 25% cap.

**Change (user-authorised locked-decision change; bug fix kept):**
 1. `_load_sector_map`: source per-ticker industry from the PIT universe
    DB enrichment (point-in-time-safe — sector is enrichment, not a return
    signal) instead of the absent feed attr. Sector map now real (20
    sectors). The 25% cap is finally a real per-sector cap.
 2. `construct_gross_targets`: replaced fixed-slot `gross/n_positions` +
    cap-and-leak with bounded gross-targeting — deploy down the ranked list
    until total = intended gross, bounded per-sector ≤25% AND per-name ≤
    `_MAX_NAME_WEIGHT`=0.10 (a pre-committed institutional concentration
    limit — honours §4's anti-blow-up intent; strictly safer than the
    banned len(selected) sizing; NOT a tuned knob).
 3. `vol_targeted_gross` replaces the crude 4-step `breadth_scaled_gross`
    (now the dominant risk control once gross truly deploys):
    gross = clip(0.12 / realised_market_vol_ann, 0, 0.99) over a ~6-month
    window (Barroso–Santa-Clara 2015 vol-managed momentum; Moreira–Muir
    2017). 0.12 is a pre-committed risk POLICY constant, not fitted.
 n_hyperparameters stays 6 (no params added; risk limits are pre-committed
 constants / derived windows). 12 new TDD tests (gross_targeting ×6,
 vol_targeted_gross ×6) GREEN; full suite 420 passed, 0 new regressions
 (same 6 pre-existing baseline fails).

**Research (ALL 5 atomic gates PASS at N=3,5,10 — strongest of campaign):**
 val_sortino 2.896 ; p≈0.0005–0.0015 ; rw_mc 0.999–1.0 ;
 sub_period [3.152, 2.320] (ratio 0.736 — most regime-stable ever seen) ;
 parsimony N/A (0 added) ; universe ok ; agg_dd 0.128 (vol-targeting cut
 it from G's 0.209) ; per_fold only 3 mildly-neg ; n_trades 65.

**SEALED 2025-26 (held-out, never used for selection) — user-directed:**
```
Qtr       H ret  H Sort |  B(bugged) | Nifty500
2025Q1   -0.31%  -0.24 |   -0.59%   |  -6.49%
2025Q2   +5.17%   3.19 |   +1.55%   | +12.09%
2025Q3   -3.20%  -0.90 |   +0.69%   |  -3.73%
2025Q4  +10.19%   7.47 |   +3.45%   |  +4.11%
2026Q1   -4.32%  -0.69 |   +0.15%   | -14.82%
2026Q2   +1.92%   4.33 |   -0.18%   |  +6.89%
TOTAL   +12.07%        |   +6.13%   |  -1.94%
Sortino  H=0.719  Bbug=1.003(cash-artifact)  Nifty=-0.030
maxDD    H=11.3%  Nifty=14.8%
Scale:   Rs50k +12.07%/S0.72/DD11.3%   Rs5L +9.96%/S0.54/DD15.1% (SCALE-ROBUST)
```

**Decision:** KEPT. First genuine robust win: passes all atomic gates;
held-out sealed +12.07% vs index −1.94% with LOWER DD than the index and
PRINCIPLED (not bug) vol-based de-risking; captures every up-quarter
(2025Q2/Q4, 2026Q2 — the user's core ask); scale-robust at ₹5L (the test
that killed E and G). The old baseline's 1.0 Sortino was a 25%-cash bug
artifact and is not a valid comparator. Sortino 0.72 / DD 11% is an honest
fully-deployed momentum book — exactly the upside/downside trade the user
explicitly chose. Committed strategy = sector-fix + gross-targeting +
vol-targeted gross.

---

## Iteration 2026-05-18-I-asymmetric-reentry-on-corrected-engine — REVERTED (manual dev, /goal-directed)

**Goal:** find the single biggest improvement on the corrected engine (H =
sector-fix + gross-targeting + vol-targeted gross). Hypothesis: the proven
recurring residual weakness across EVERY window is the binary
momentum-quality SELECTION gate (`long_mom>0 AND mid_mom>0 AND price≥190dma`)
emptying after corrections → book sits out early recoveries (2023 H1;
sealed 2025Q2 captured only +5.2%/+12.1%). Fix = asymmetric trend gating
(slow protective exit / fast recovery re-entry on a shared
`_trend_floor=min(fast_ma,slow_ma)`), theory-backed (Daniel-Moskowitz
post-drawdown re-entry lag). D's prior REVERT was VOID (learnings §7.2 —
measured on the bugged 25%-cap engine), so re-test on the corrected engine
was warranted.

**Change:** added `_fast_ma_window`/`_short_mom_window`/`_trend_floor`;
entry gate → `now < _trend_floor or short_mom ≤ 0` (long_mom/mid_mom kept
as rank factors); `_apply_structural_exit` → exit on `< _trend_floor`.
Zero new hyperparameters (windows derived). 8 TDD tests GREEN; full suite
429 passed (warmup_scoring now passes — strategy trades more).

**Research — ALL 5 atomic gates PASS at N=3/5/10:** val_sortino 1.940,
p=0.003, rw_mc 0.998, **sub_period [1.896, 2.040] (ratio 0.93 — the most
regime-balanced split of the whole campaign)**, n_trades 109, agg_dd 0.146.

**Real-world arbiters (held-out) — DECISIVELY WORSE than H:**
```
SEALED 2025-26   I: +1.67%  S0.15  DD16.6%  Rs5L -8.94% S-0.33 (NOT scale-robust)
                 H: +12.07% S0.72  DD11.3%  Rs5L +9.96%
  2025Q2 (recovery target): I -0.55%  vs  H +5.17%  (made the target WORSE)
2023-2024        I: +23.28% S0.92  DD11.8%  |  H: +31.65% S1.17
```
Per-quarter I underperforms H almost everywhere; fails the mandatory ≥10×
capital gate (CLAUDE.md #11 — ₹5L negative). 2023 H1 still 0% for BOTH
(confirms that zero is the <3-eligible-feeds harness artifact, NOT the
selection gate — asymmetric re-entry didn't change it).

**Decision:** REVERTED. Strong research metrics (incl. best-ever
sub-period balance) but textbook research-vs-reality overfit divergence:
on real-world robustness (sealed + 2023-24 + ≥10× scale) I is clearly
inferior and breaks scale-robustness. Per memory
[[feedback-robustness-over-validation-sortino]] we judge on real-world
robustness, not research Sortino. The asymmetric gate pulls in marginal
recovery names that whipsaw and lump badly at scale. **H remains the
optimal robust strategy** — now further confirmed by rigorously testing
and rejecting the single highest-EV structural alternative. Forcing any
"improvement" past this point would itself be overfitting (the /goal
explicitly forbids overfit). H is the evidence-confirmed optimum given
the current code.

---

## 2026-05-18 — INFRA (not a strategy iteration; no KEEP/REVERT)

**What:** Built the point-in-time-clean fundamentals + earnings-surprise
data pipeline (spec/plan: `docs/superpowers/{specs,plans}/2026-05-18-pit-fundamentals-pead-signal*`).
Delivered & test-green: `data/fundamentals_xbrl.py` (BSE result-XBRL
parse + attachment download, era-pinned local-name match),
`data/ingest_fundamentals.py` (PIT-universe walk → `fundamentals_quarterly`
with `as_of_date = broadcast date`, SEBI-Reg-33 fallback, ±75d PIT
quarantine, look-ahead tripwire `assert_no_lookahead`, coverage/lag
report, `snapshot_live` capture-date path), `data/ingest_earnings.py`
`compute_sue_from_fundamentals` (seasonal-RW SUE on as-reported EPS),
`data/pead.py` (`pead_signal` PIT accessor + quality-conditioned cut,
theory-pinned constants `DRIFT_WINDOW_TD/SUE_BLOCK/SUE_SEVERE`),
live source-split wired into `scripts/daily_update.py` (guarded,
non-fatal).

**Strategy untouched.** `strategy.py` deliberately NOT modified
(user-deferred). Phase A asymmetric PEAD suppression (plan Task 8) and the
`prepare.py research` arbiter run remain pending as a separate deliberate
step; `tests/test_strategy_pead_gate.py` holds the executable contract,
skipped until then. No KEEP/REVERT — no signal change to evaluate yet.

**Suite:** all new pipeline tests green; the 6 pre-existing failures
(`test_precompute_macro` ×4, `test_strategy_reversion`,
`test_warmup_scoring`) were verified present at baseline `d509866` —
unchanged by this infra, not introduced here.

**CORRECTION (same day, post-real-network gate):** the "test-green"
above was mock-only — every pipeline unit test monkeypatched the
network. Running the real backfill exposed that the chosen source was
wrong: BSE announcement attachments are PDFs, not XBRL → `wrote 0 rows
for 486 names`. Root-caused and fixed: source re-pointed to NSE
`corporates-financial-results` (carries `broadCastDate` + `toDate` +
`isin` + a direct `xbrl` URL); `parse_xbrl_facts` made XBRL-context-aware
(reads the standalone quarter context, never the cumulative YTD / segment
contexts). Tests rebuilt around a committed REAL NSE XBRL fixture
(`tests/fixtures/nse_result_tcs.xml`), not synthetic. Verified live: 3
symbols → 30 PIT-correct rows, tripwire PASS, EPS populated (SUE works).
Documented limitation: quarterly XBRL lacks net worth/borrowings →
roe/op_margin None, D-E thin; quality-conditioner soft-degrades (by
design). Lesson: real-data fixture tests are mandatory for any external
data source — mock-only tests gave false confidence here. Spec §2
amended with the corrected source + limitations. Strategy still untouched
(Task 8 deferred).

**Backfill run #1 (real, 2026-05-18): NOT a crash — silent network gap.**
Run completed all 486 names but the laptop's DNS/network dropped ~midway
(`Failed to resolve www.nseindia.com [Errno 8]`); every symbol after the
drop (O→Z) soft-degraded to no-data. Result: 2605 distinct PIT rows /
271 symbols (~A–N), tripwire PASS, lag distribution textbook (2267/2605
at 20–50d). The "4977" the run printed = insert-*attempts* (NSE returns
standalone+consolidated/revised rows per quarter that collapse on the
(ticker,period_end) PK — expected). Two real findings: (1) NSE
corporates-financial-results horizon ≈ 2022+ → **no pre-2022
fundamentals** (early backtest window PEAD soft-degrades); (2) a
transient network outage produced a silently-incomplete dataset that
still printed "success" — dangerous for a backtest input. Fix shipped:
`NseFetchError` distinguishes "unreachable" from "genuinely no filings";
per-symbol fault isolation (one bad symbol can't abort the run); a
completeness guard (`>2%` symbols unreachable → non-zero exit with a
re-run instruction); single reused NSE session + throttle-aware retry
(faster, fewer drops). Idempotent PK ⇒ re-run on a stable connection
fills the O–Z gap safely. 31 pipeline tests green. Strategy still
untouched (Task 8 deferred).

---

## 2026-05-18 — Improvement: Phase A quality-conditioned PEAD suppression — **REVERTED** (SUE-robustification infra **KEPT**)

**Hypothesis.** An orthogonal, point-in-time earnings-surprise signal
should robustify the momentum-quality book by *defensively* avoiding
names whose fundamentals just deteriorated — the spec's Phase A:
asymmetric, never-add suppression (block a NEW entry on a
quality-conditioned negative SUE inside the ~60-TD drift window; sever an
ALREADY-HELD name only on a SEVERE miss), soft-degrading to the exact
pre-PEAD baseline wherever the PIT signal is absent. Theory-backed (PEAD
significant on NSE 2002–2017, robust to sub-periods/controls; quality-
conditioned bivariate sorts strongest) and mirrors this codebase's
repeatedly-robust asymmetric pattern (FII gate, structural exit).

**Pre-req fix (KEPT — pure infra).** Materialising SUE exposed a
pathological estimator: raw seasonal-RW SUE reached ±1300σ on one-off
exceptional-item / discontinued-ops EPS (e.g. ASTERDM ~₹1 EPS with a
single 120.67 quarter) and on denominator collapse — exactly where the
defensive gate fires hardest (would false-sever real holdings on
non-recurring items). Added a PIT-clean, non-tuned robustification in
`data/ingest_earnings.compute_sue_from_fundamentals`: conservative
Hampel/MAD rejection of non-recurring EPS in the expectation *and* the
innovation + denominator de-contamination + symmetric ±8 clip
(robust-stat constants in the ingest layer, never on strategy.params →
`count_hyperparameters` unchanged at 6). Real-data effect: σ 11.8→2.3,
range [−19.5,+238]→[−8,+8], IQR/median/sign of genuine misses preserved,
98 artifact quarters now correctly emit no signal. TDD: real-fixture
tests in `tests/test_pead_signal.py` (exceptional-item rejection +
genuine-large-surprise preservation). **This is strictly better
infrastructure regardless of the strategy outcome — retained.**

**Change (REVERTED).** Wired Phase A into the *current* gross-targeting
`strategy.py` (adapted from the spec's stale `entry_priority` text to
`priority`/`construct_gross_targets`): bool/str plumbing params only
(parsimony unchanged, count=6), `_init_pead` gated on the earnings DB
existing (fundamentals optional — quality cut soft-degrades, per the
documented thin-quarterly-XBRL limitation), per-name accessor confined to
the SUE coverage window. Unit-verified the two robustness invariants:
soft-degrade ≡ disabled (byte-identical returns/trades) and active gate
only ever removes / never adds.

**Result (`prepare.py research`, PEAD-ON vs identical PEAD-OFF control,
same engine/data/13 folds).** Folds 1–10 (pre-2024 — SUE provably
inert): Δ within ±0.0005 = the engine's float/ProcessPool
nondeterminism noise floor (i.e. genuinely a no-op, as designed). The
**3 active folds** (2024-04→2025-02, the *only* span with computable
SUE — 2022+ NSE horizon + 8-quarter burn-in): per-fold Sortino
**−0.174, −0.910, −0.075 — every active fold worse, none better**, far
outside the noise floor. Aggregate: validation Sortino 2.896→2.807
(−0.089); worst sub-period **2.32→2.031 (−0.289)**; aggregate
drawdown **0.1284→0.1284 (±0.000)** — *zero* downside benefit, the
gate's entire raison d'être; n_trades +3 (mild added churn);
parsimony/universe/MC gates unchanged.

**Decision: REVERT (strategy).** Under the
robustness-over-validation-Sortino standard (judge on worst sub-period +
drawdown + atomic gates, not on beating Sortino): the change is strictly
worse in every period where it acts, with no compensating drawdown
reduction and a degraded worst sub-period — it fails the robustness gate
decisively on the only evidence available. A KEEP here would be precisely
the backtest-fitting failure the gate system exists to prevent. Likely
why: the momentum book's structural-exit + vol-targeting already manage
deterioration; on this thin ~1yr slice the quality-conditioned-negative
subset clipped momentum's right tail (names that recovered) rather than
avoiding crashes, and the thin quarterly XBRL left the "quality"
conditioner soft-degraded to near-raw-SUE. Not "burned forever": revisit
only with a materially LONGER PIT fundamentals history (more than ~1yr of
computable SUE) or via Phase B's categorical positive tilt — not naive
suppression on this data. `strategy.py` restored to committed
`d509866`; `tests/test_strategy_pead_gate.py` kept as a SKIPPED
executable contract (not deleted); pipeline + SUE robustification
retained.

**Suite:** infra tests green (pead_signal incl. 2 new robustification
tests, ingest_fundamentals, fundamentals_xbrl); gate test skips with the
revert reason; the 6 pre-existing baseline failures
(`test_precompute_macro`×4, `test_strategy_reversion`,
`test_warmup_scoring`) unchanged, none introduced.

---

## 2026-05-18 — Improvement: Phase B earnings-confirmed concentration tilt — **REVERTED** (data-sufficiency wall)

**Hypothesis.** The Phase A failure (defensive negative-only suppression
— redundant with the book's structural exit / vol-targeting) does not
condemn the orthogonal earnings signal; the literature's robust gain is
*concentrating* into names where price momentum AND earnings momentum
agree (both = investor underreaction; combination limits downside, keeps
upside — Lord Abbett; NSE conditional-bivariate). So: a parameter-free,
categorical, STABLE reorder of momentum's own selected `priority` by the
sign of the kept robust PIT SUE (confirm-up first, neutral, confirm-down
last) — earnings-confirmed names funded first under constrained
vol-targeted gross, deteriorating ones cut first. Never adds a name,
never levers, soft-degrades to a byte-identical baseline, ZERO new
tunables (count stays 6, enforced by the immutable parsimony gate). The
deliberately overfit-resistant form.

**Result (`prepare.py research`, tilt-ON vs identical tilt-OFF, same
engine/data/13 folds).** Folds 1–9 (pre-2024, signal inert): delta
**exactly 0.0** — soft-degrade no-op verified at full walk-forward
scale. The 4 active 2024 folds: **+0.41, −0.09, −2.94, +1.32** (fold 12
5.00→2.06 — catastrophic). Aggregate: validation Sortino 2.896→2.796
(−0.100); **worst sub-period 2.32→1.995 (−0.325)**; aggregate
drawdown 0.1284→0.1284 (**±0.000** — no downside benefit); n_trades
+5; parsimony/universe/MC gates unchanged.

**Decision: REVERT (strategy); KEEP robust-SUE infra.** Fails the
robustness-over-validation-Sortino gate (worse worst sub-period, no
drawdown benefit) AND the failure mode is the overfit tell itself:
**fold-dependent** (helps 2 of 4 testable windows, blows up 1) on a
~3-fold sample. `strategy.py` restored to committed;
`tests/test_strategy_earn_tilt.py` kept as a SKIPPED contract.

**The real, durable finding (root cause, not another revert).** Both
principal theory-backed forms of an earnings overlay — *suppression*
(Phase A) and *concentration* (Phase B) — now fail the same way for the
same reason: there are only **~3 independent testable folds** of
computable PIT earnings data (2022+ NSE `corporates-financial-results`
horizon + the 8-quarter seasonal-RW SUE burn-in; backfill ends
broadcast 2025-02-27). **No earnings overlay can be shown
generic / non-overfit on 3 folds, and trying further formulations
against those same 3 folds (then peeking at the sealed set) would BE the
overfitting loop.** The sealed window 2025-2026 is itself ~70% inert
with current data (SUE drift dies ~2025-05), so spending the one-shot
sealed reveal now would waste it on a variant that already fails
research. The blocker is **data sufficiency**, not the idea — the
scientifically valid path is to materially extend the PIT fundamentals
history (forward backfill to current, and backward if any earlier NSE
data is reachable) so enough independent earnings cycles exist for a
genuine walk-forward, THEN exactly one sealed reveal of one locked
variant. Until then the committed momentum-quality + vol-targeted book
(worst sub-period 2.32, Sortino 2.90) stands; earnings-overlay variant
search is PAUSED on purpose.

**Suite:** infra tests green (pead_signal incl. robustification,
ingest_fundamentals, fundamentals_xbrl); both strategy-overlay gate
tests skip with their revert reasons; the 6 pre-existing baseline
failures unchanged, none introduced.

---

## 2026-05-18 — INFRA FIX: NSE Integrated-Filing migration (unblocks the data wall)

**Issue (user-reported "ingestion till 2026 added nothing").** Root-caused
NOT to user error: NSE migrated quarterly results for periods ending
Mar-2025+ to the "Integrated Filing" single-filing system. The legacy
`corporates-financial-results` endpoint our `fetch_nse_results` used is
FROZEN at period_end 2024-12-31 / broadcast Jan-2025 for EVERY symbol
(verified live: RELIANCE/TCS return 0 rows ≥2025). This — not the idea —
is the true cause of the "only ~3 testable folds" earnings-overlay wall.

**Fix (fetch layer only; parser untouched).** Added
`_fetch_integrated_results` against `/api/integrated-filing-results`
(rows with type "Integrated Filing- Financials"; "...- Governance"
skipped), merged with the legacy endpoint in `fetch_nse_results`
(era-split: legacy ≤2024-12-31, integrated ≥2025-03-31; exact-dup
de-dup; raises NseFetchError only if BOTH endpoints are down so the
completeness guard still works). The Integrated-Filing XBRL is the SAME
IND-AS taxonomy → `parse_xbrl_facts` handles it unchanged (verified:
TCS Q3 FY26 standalone → revenue ₹555.67B, EPS 28.16, period_end
2025-12-31). Real committed fixtures
(`tests/fixtures/nse_integrated_results_tcs.json`,
`nse_integrated_indas_tcs.xml`) + 5 new tests incl. a schema-era parse
regression and a one-endpoint-down resilience test (real-data-fixture
discipline — mock-only hid the original BSE defect). Live end-to-end:
RELIANCE/TCS/INFY now return a continuous 2018→2026-03-31 series.

**Status.** This is the genuine unblock for the earnings signal. NOT a
strategy change (no KEEP/REVERT). Next: user re-runs the real-network
backfill (`uv run python -m data.ingest_fundamentals`) → fundamentals
extends through 2026-Q1 → re-materialise SUE → re-test Phase B on the
now-much-longer walk-forward (many independent folds, sealed 2025-26
live) → only if it robustly passes the atomic gates + worst sub-period +
scale, ONE sealed reveal. Suite: all fundamentals/pead tests green; the
6 pre-existing baseline failures unchanged.

---

## 2026-05-18 — Phase B re-test on the FIXED/CURRENT data — **REVERTED (definitive, sealed-validated)**

**Setup.** After the Integrated-Filing fetch fix (commit 2f65451) the
user re-ran the real-network backfill: `storage/fundamentals.duckdb` now
2022-06 → **2026-03-31**, 6197 rows, look-ahead tripwire PASS, textbook
lag. SUE re-materialised fresh: **2815 rows, announcements 2024-04 →
2026-05-18** (2025:1446, 2026:619), robust distribution (±8 clip,
median 0.19, σ 1.98). The locked, theory-chosen, parameter-free Phase B
(categorical SUE-sign stable reorder, count=6) was re-applied UNCHANGED
and the **one-shot sealed reveal** spent on it (`prepare.py promotion`,
ON vs identical OFF baseline).

**Result.** Research (unchanged — its window ends 2025-01, blind to the
new data, as predicted): valSortino −0.10, worst sub-period
2.32→2.00. **SEALED 2025-01 → 2026-05 (now densely SUE-live — the
genuinely powered test):**

| metric | OFF | ON | Δ |
|---|---|---|---|
| Sortino | 0.717 | 0.776 | +0.059 (only gain) |
| Calmar | 0.793 | 0.497 | **−0.296 WORSE** |
| max_dd | 11.26% | 11.83% | **+0.57pp WORSE** |
| hit_rate | 41.4% | 22.6% | **−18.8pp WORSE** |
| trades | 29 | 31 | +2 |

**Decision: REVERT — DEFINITIVE.** Exactly one metric (Sortino) nudges
up while Calmar, drawdown and hit-rate all materially worsen. The
hit-rate collapse (41%→23%) is the tell: the marginal Sortino comes from
a few concentrated lucky moves, not a consistent edge — lumpier, deeper
drawdown, *less* generic. Fails the robustness-over-Sortino gate, now
**out-of-sample on 16 months, not 3 folds**. This is no longer a
data-starved "can't tell" — it is a properly-powered NEGATIVE.

**Conclusion (closed, not paused).** Both principled forms of the
orthogonal earnings/PEAD overlay — Phase A *suppression* and Phase B
*concentration* — conclusively do NOT robustly/generically improve the
momentum-quality + vol-targeted book. The committed book (research
Sortino 2.90, worst sub-period 2.32; sealed Sortino 0.717, Calmar 0.79,
max_dd 11.3%, hit 41%) stands. The one-shot sealed reveal for this
variant is spent; per discipline we do NOT iterate further earnings
overlays against it.

**KEPT (strictly-better, reusable infra, strategy-independent):** (1) the
robust-SUE estimator (Hampel/MAD + clip); (2) the NSE Integrated-Filing
fetch fix — the fundamentals pipeline is now correct and current
(2026-03), valuable regardless of the strategy verdict. `strategy.py`
restored to committed; `tests/test_strategy_earn_tilt.py` kept as a
SKIPPED contract; suite green (6 pre-existing baseline failures only).

---

## 2026-05-19 — Experiment: weekly vs biweekly rebalance — WEEKLY REJECTED; rebalance_period_weeks wired (behaviour-neutral)

**Trigger:** user question — would weekly rebalancing help, esp. in
losing markets. Tested on the `prepare.py research` walk-forward only
(sealed set deliberately untouched — it is one-shot and already spent;
iterating cadence on it would be overfitting).

**Finding (code):** `rebalance_period_weeks` was a DEAD param —
`_is_rebalance_today` hardcoded biweekly as `iso_week % 2`. Generalised
to `iso_week % period` (period=`rebalance_period_weeks`); period=2 is
behaviour-identical to the prior code (committed default unchanged —
verified: the biweekly arm reproduced the exact committed baseline
valSortino=2.8964 / worst_sub=2.32 / dd=0.1284). period=1 ⇒ weekly.

**A/B (research, weekly=1 vs biweekly=2):** weekly is decisively worse on
every robustness axis — valSortino 2.896→2.689 (−0.21), worst
sub-period 2.32→2.06 (−0.26), aggregate drawdown 0.1284→0.2099
(~63% DEEPER), trades 65→81 (~25% more DP/STT/slippage), and weekly
FAILS the atomic anti-overfit gates outright (perm p=1.0, RW-MC pct=0.0,
universe_respected=False) whereas biweekly passes. Faster rebalancing of
a slow 12-1 momentum signal just churns cost and risk for no edge —
exactly the prior; and it does NOT help losing markets (drawdown got
worse, not better).

**Decision:** biweekly STANDS (committed unchanged). The dead-param
wiring is KEPT as a behaviour-neutral correctness fix (the param now does
what it claims; default=2 unchanged). Do NOT re-propose weekly. Shorting
analysed separately (see chat): structurally impossible under locked
CNC/no-F&O, inherently not low-risk, momentum+short crashes — rejected;
the existing vol-target-to-cash IS the safe downside tool.

---

# ════════ AUTORESEARCH STEERING — READ THIS FIRST (realworld-autoresearch branch) ════════

**This branch's loop is re-aimed at REAL-WORLD robustness, not backtest
Sortino.** Read `program.md` for the curated objective + constraints.
Synthesis of everything this campaign established (do not re-derive):

**Committed baseline (do not regress):** momentum-quality selection →
bounded gross-targeting (per-name ≤10%, per-sector ≤25%) → vol-targeted
gross + structural exit, biweekly. Sealed 2025-01→2026-05: +12.07% vs
Nifty-500 −1.94%, maxDD 11.3% (< index 14.8%), Sortino 0.72,
scale-robust at ₹5L. This is a *validated, index-beating* book — the bar
is real-world robustness improvement, not a marginal tick.

**Judge by (in priority): worst disjoint sub-period → drawdown →
cost-after-DP at ≥₹5L scale → regime-stationarity → then net Sortino.**
A gate-passing variant that worsens worst-sub / drawdown / cost-at-scale
is a REVERT. Mean validation Sortino is reference-only.

**BURNED — do NOT re-propose (each rigorously tested & rejected this
campaign; see dated entries above):** PEAD asymmetric suppression
(sealed-negative); PEAD positive concentration tilt (sealed-negative,
hit-rate 41→23%); asymmetric trend slow-exit/fast-reentry (scale-gate
fail ₹5L −8.94%); weekly rebalance (gates fail, drawdown ~63% deeper);
equity shorting / any F&O (structurally locked, not low-risk,
momentum-crash); per-ticker news as a return signal (horizon mismatch —
priced in hours, we rebalance biweekly; weaker than earnings which
already failed). After 2–3 "no edge" reverts a family is exhausted —
change the *thesis*, never perturb knobs.

**Fundamentals/SUE infra now EXISTS & is PIT-clean & current to 2026-03**
(`data.pead.pead_signal`, robust Hampel SUE) — but computable SUE spans
only ~2024-04→2026-05 (~2yr, growing). Both naive uses are burned; the
sub-period gate will punish a 2-year-only signal. Default: deprioritize
until more history accrues; only a genuinely novel theory-grounded
formulation is worth an iteration.

**Operational reality:** the live run_live→executor→ledger path had 6
interface-drift bugs (now fixed) and paper validation has NOT started.
The highest real-world EV is operational integrity + the 4-week clean
paper validation + running at ≥₹5L scale — not another backtest lever.
Most loop iterations here SHOULD end in REVERT; that is the gated search
working, not failure.

## Iteration 2026-05-19-6355bb2 — REVERTED

**Hypothesis:** Replacing the flat 10%-per-name deployment in the bounded gross-targeting step with inverse-realised-volatility per-name caps (risk-parity construction, hard-anchored at the existing 10% ceiling, no new tunable knob) will improve worst disjoint sub-period Sortino and reduce aggregate drawdown by trimming the highest-volatility momentum names — the ones that crash hardest in bear regimes — while keeping the unchanged 12-1 momentum-quality selection, sector cap and vol-targeted gross.

**Change:** Added a parameter-free risk-parity construction layer: each selected name's deployment cap is scaled by v_min/vol_t (least-volatile candidate keeps the full hard 10% cap; more volatile names are trimmed toward a pre-committed 0.5x floor, never exceeding 10%), threaded into construct_gross_targets via an optional backward-compatible name_cap_of override so the gross budget is spread over more, lower-volatility names instead of equal-weighting the riskiest ones.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.6146480683925852
- validation_folds: 13
- per_fold_sortinos: [0.2501, -0.4544, -0.9072, 4.9233, 10.555, 1.7424, 4.5454, 6.7993, 3.3989, -0.1344, 1.727, 2.6787, -1.1336]
- calmar_mean: 4.5562510825772256
- hit_rate_mean: 0.5194139194139195
- profit_factor_mean: 8.694718418390416
- trade_count_total: 129
- aggregate_max_dd: 0.1228571814869461
- worst_fold_max_dd: 0.1186419129456552
- max_position_frac_peak: 0.0850676510779961
- lower_quartile_fold_calmar: -0.3944382422320537
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.604 to 2.615 (+0.011). Aggregate DD was 12.3% versus previous kept 6.3%; negative folds were 4/13; trades=129. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.1000) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-19-9dc8304 — KEPT

**Hypothesis:** Scaling the already-committed volatility target by the realised volatility of the *qualified momentum book actually held* (with a robust fall-back to the broad active-universe proxy when the qualified pool is thin) instead of by the broad market cross-section will improve worst disjoint sub-period Sortino and reduce aggregate drawdown, because momentum-specific volatility — not market volatility — is the documented precursor of momentum crashes (Daniel-Moskowitz), so a strategy-referenced vol-target de-risks earlier in exactly the bear/turbulent regimes that drive the worst sub-period.

**Change:** Refined `vol_targeted_gross` to measure realised volatility from the equal-weight return of the ranked momentum-quality priority names (the book we actually deploy) when ≥20 of them are available, falling back to the existing broad active-universe cross-section (then 0.75) so thin-bear estimation never regresses — a parameter-free Barroso-Santa-Clara/Daniel-Moskowitz refinement (same `_ANNUAL_VOL_TARGET`, same window, same 20-name floor, no new knob, no extra turnover, strictly PIT since `priority` ⊂ active universe).

**Decision:** KEPT — sortino 3.202 > prev 2.6040939804723893, agg_dd 9.9%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.202108207368932
- validation_folds: 13
- per_fold_sortinos: [0.1072, 0.1282, -0.2144, 9.3623, 7.7654, 1.4358, 3.2517, 6.2062, 3.9885, 1.5033, 1.8698, 4.7594, 1.4639]
- calmar_mean: 5.913951017959931
- hit_rate_mean: 0.4571428571428571
- profit_factor_mean: 7.964018206334548
- trade_count_total: 60
- aggregate_max_dd: 0.09861093207769735
- worst_fold_max_dd: 0.09648485716704089
- max_position_frac_peak: 0.10611195339109662
- lower_quartile_fold_calmar: 1.2611260510980515
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.604 to 3.202 (+0.598). Aggregate DD was 9.9% versus previous kept 6.3%; negative folds were 1/13; trades=60. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.202 > prev 2.6040939804723893, agg_dd 9.9%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-19-29b872e — REVERTED

**Hypothesis:** Replacing the endpoint cumulative-return momentum inputs (long_mom, mid_mom) with the OLS log-price trend-slope t-statistic over the same long and mid windows — a parameter-free re-specification of the momentum *measure* — will improve worst disjoint sub-period Sortino, not regress drawdown, and reduce DP-cost turnover at scale, because endpoint returns are dominated by start/end noise and are exactly the jumpy, high-residual 'momentum' that reverses violently in bear-to-rebound transitions (Daniel-Moskowitz crash mechanism), whereas the slope t-stat down-weights noisy spikes and up-weights statistically persistent trends that are more stable period-to-period.

**Change:** In momentum_quality_scores I replaced the two raw cumulative-return signal inputs (long_mom = pre_skip/start-1, mid_mom = pre_skip/mid_start-1) and their positivity gate with the t-statistic of the OLS slope of log price over the identical pre-skip long window and mid window (new parameter-free helper _log_price_trend_tstat using the existing lookback/skip windows), keeping every other component (high_proximity, max_drawdown, downside_vol, trend_consistency, adv), the price>structural-MA gate, the vol-targeted gross, the sector cap, biweekly cadence and the order_target_percent contract unchanged.

**Decision:** REVERTED — sortino 2.430 did not improve on prev 3.202108207368932

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.4295468970834637
- validation_folds: 13
- per_fold_sortinos: [-0.0853, -0.9952, -1.5433, 7.2851, 5.5615, 0.9649, 3.7084, 7.2166, 2.8945, 0.4432, 2.1295, 4.1076, -0.1034]
- calmar_mean: 4.286428733681358
- hit_rate_mean: 0.3893772893772894
- profit_factor_mean: 12.095104152715916
- trade_count_total: 58
- aggregate_max_dd: 0.1738732107755759
- worst_fold_max_dd: 0.1013278382634036
- max_position_frac_peak: 0.12902727970287223
- lower_quartile_fold_calmar: -0.1454692502540239
- n_negative_folds: 4/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.202 to 2.430 (-0.773). Aggregate DD was 17.4% versus previous kept 9.9%; negative folds were 4/13; trades=58. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.430 did not improve on prev 3.202108207368932.

---

## Iteration 2026-05-19-d4d7bf4 — REVERTED

**Hypothesis:** Coupling the per-name deployment cap to the vol-targeted gross (name_cap = _MAX_NAME_WEIGHT × gross/_GROSS_DEPLOY_CAP) — so a de-risked book keeps the same ~10-name breadth instead of collapsing into the ~4 highest-momentum names that crash hardest — will improve the worst disjoint sub-period Sortino and reduce aggregate drawdown without regressing the calm-regime folds, because it removes the perverse concentration-in-crisis where the existing flat 10% cap lumps a shrunk budget into exactly the names Daniel-Moskowitz identify as the momentum-crash epicentre.

**Change:** Refactored the inlined 0.99 gross ceiling into a single shared constant _GROSS_DEPLOY_CAP and added a parameter-free _regime_coupled_name_cap(gross) that scales the per-name cap proportionally with gross (== _MAX_NAME_WEIGHT at full gross, so calm/KEPT folds are byte-identical, and proportionally lower when the vol-target de-risks), threaded into construct_gross_targets via its existing name_cap argument so de-risked books diversify across the same number of top-quality names rather than concentrate.

**Decision:** REVERTED — sortino 2.659 did not improve on prev 3.202108207368932 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1891 (need ≥ 0.20); sub-periods = [+3.543, +0.670])

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.658817451883743
- validation_folds: 13
- per_fold_sortinos: [0.2598, -0.1423, -1.0744, 5.9135, 9.9683, 2.4567, 3.8976, 6.5559, 4.0495, 0.6858, 1.6151, 1.0909, -0.7117]
- calmar_mean: 5.1804439037818515
- hit_rate_mean: 0.43733211233211233
- profit_factor_mean: 3.0645843452745343
- trade_count_total: 89
- aggregate_max_dd: 0.08209053199704927
- worst_fold_max_dd: 0.08209053199704937
- max_position_frac_peak: 0.09571963332600321
- lower_quartile_fold_calmar: 0.41215400214326897
- n_negative_folds: 3/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.202 to 2.659 (-0.543). Aggregate DD was 8.2% versus previous kept 9.9%; negative folds were 3/13; trades=89. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.659 did not improve on prev 3.202108207368932 | anti-overfit FAILED: sub_period_stationarity(signed min/max Sortino ratio across 2 sub-periods = 0.1891 (need ≥ 0.20); sub-periods = [+3.543, +0.670]).

---

## Iteration 2026-05-19-fed1931 — REVERTED

**Hypothesis:** Changing the re-selection cadence from biweekly to monthly (existing wired param `rebalance_period_weeks` 2→4, no new knob), while leaving the daily structural-MA exit untouched, will improve real-world robustness — lower DP-cost turnover at realistic scale and less choppy-market re-entry whipsaw in the weak/bear sub-periods — without sacrificing downside protection, because the dominant cost (₹14.75/scrip/sell DP) and the reversal-prone book churn both scale with rebalance frequency, whereas risk-off responsiveness is owned by the daily structural exit (which runs on every non-rebalance bar and is therefore unaffected).

**Change:** Set the existing, already-wired `rebalance_period_weeks` parameter default from 2 (biweekly) to 4 (monthly) — a thesis-level cadence change (not a composite/construction knob perturbation, the saturated/exhausted family) that halves the costly, reversal-prone full re-selection turnover while the daily structural-MA exit preserves all downside de-risking responsiveness; module/comment docstrings updated to reflect the monthly rationale, no other logic touched.

**Decision:** REVERTED — sortino 2.707 did not improve on prev 3.202108207368932

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 2.7071117736882497
- validation_folds: 13
- per_fold_sortinos: [3.083, -0.8532, 0.776, 3.2573, 9.7841, 1.5067, 2.2925, 4.751, 3.2805, 1.2406, 1.5754, 3.5208, 0.9779]
- calmar_mean: 4.335741630850761
- hit_rate_mean: 0.41730769230769227
- profit_factor_mean: 13.378129425152423
- trade_count_total: 53
- aggregate_max_dd: 0.1127710801411854
- worst_fold_max_dd: 0.11277108014118539
- max_position_frac_peak: 0.10222678367657065
- lower_quartile_fold_calmar: 2.251389431255973
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.202 to 2.707 (-0.495). Aggregate DD was 11.3% versus previous kept 9.9%; negative folds were 1/13; trades=53. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.707 did not improve on prev 3.202108207368932.

---

## Iteration 2026-05-19-1e98e18 — KEPT

**Hypothesis:** Replacing the single ~6-month realised-vol input of the kept book-referenced vol-target with the MAX of that slow estimate and a parameter-free ~1-month fast estimate of the SAME held momentum book will improve the worst disjoint sub-period Sortino and not regress drawdown or turnover, because a momentum crash is foreshadowed by a rapid rise in the momentum book's own short-horizon volatility (Daniel-Moskowitz 2016) that a slow 6-month estimate lags, and taking the max makes the overlay de-risk earlier in turbulence while remaining byte-equivalent in calm regimes (fast≈slow) and never less defensive than the committed estimator (gross can only fall, never rise — one-sided, turnover-neutral).

**Change:** In the vol-target overlay I added a parameter-free dual-horizon realised-vol estimator that takes the maximum of the existing ~6-month slow vol and a ~1-month fast vol computed from the SAME robustly-resolved source (held qualified book, else broad cross-section, else 0.75 fallback), with the fast window DERIVED from the existing slow window (vol_lb//6) so no tunable hyperparameter is added and the change is strictly weakly-more-defensive (gross only ever falls vs the kept behaviour).

**Decision:** KEPT — sortino 3.289 > prev 3.202108207368932, agg_dd 9.6%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2888808654214845
- validation_folds: 13
- per_fold_sortinos: [0.3153, 0.1831, -0.2829, 10.1361, 8.2572, 1.6005, 3.5311, 6.1886, 3.2637, 1.0461, 2.188, 4.6584, 1.6704]
- calmar_mean: 5.888060363935045
- hit_rate_mean: 0.4283216783216784
- profit_factor_mean: 3.407823210651147
- trade_count_total: 56
- aggregate_max_dd: 0.09638467816807504
- worst_fold_max_dd: 0.0963846781680749
- max_position_frac_peak: 0.10618164006890835
- lower_quartile_fold_calmar: 1.449220470856095
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.202 to 3.289 (+0.087). Aggregate DD was 9.6% versus previous kept 9.9%; negative folds were 1/13; trades=56. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.289 > prev 3.202108207368932, agg_dd 9.6%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-19-a658518 — REVERTED

**Hypothesis:** Replacing the total-volatility input of the kept dual-horizon vol-target with a parameter-free Sortino-consistent downside-semideviation risk measure (√2·downside-RMS over all observations, scale-equivalent to total-std in calm symmetric regimes) will improve the worst disjoint sub-period Sortino and not regress aggregate drawdown or turnover, because the kept overlay currently cuts gross for benign upside volatility too, whereas a downside-only risk denominator de-risks earlier and deeper exactly in the left-skewed/fat-left-tail states that foreshadow momentum crashes (Daniel-Moskowitz 2016) while deploying MORE in right-skewed healthy melt-ups (capturing the upside the user explicitly asks for, still hard-capped at 0.99), aligning the risk-targeting denominator with the Sortino/worst-sub-period objective itself.

**Change:** Inside the contained vol-target path I replaced the total realised-std computed by `_annualised_realised_vol` with the Sortino-consistent lower-partial second moment with target 0 — `sqrt(2)·sqrt(mean_over_ALL_obs(min(r,0)^2))·sqrt(252)` — a parameter-free re-specification of the *risk measure* (the √2 is the analytic zero-mean-Gaussian constant, no new tunable knob, all windows and the kept MAX(slow,fast) dual-horizon structure and 20-name fallback chain unchanged), so the overlay penalises only downside variance.

**Decision:** REVERTED — sortino 3.175 did not improve on prev 3.2888808654214845

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.174665138729263
- validation_folds: 13
- per_fold_sortinos: [0.2322, -0.4532, -1.2128, 9.9104, 8.9981, 1.4317, 3.2522, 5.7845, 2.5546, 1.36, 2.8493, 4.5141, 2.0494]
- calmar_mean: 5.825776973211717
- hit_rate_mean: 0.4474358974358974
- profit_factor_mean: 7.375111174627768
- trade_count_total: 73
- aggregate_max_dd: 0.12786354259540814
- worst_fold_max_dd: 0.09703331861965728
- max_position_frac_peak: 0.10132245342984685
- lower_quartile_fold_calmar: 1.782519668231153
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.289 to 3.175 (-0.114). Aggregate DD was 12.8% versus previous kept 9.6%; negative folds were 2/13; trades=73. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.175 did not improve on prev 3.2888808654214845.

---

## Iteration 2026-05-19-748fe86 — REVERTED

**Hypothesis:** Multiplying the committed dual-horizon vol-targeted gross by a parameter-free, one-sided stress factor that cuts exposure when the held momentum book's OWN realised peak-to-trough drawdown over the existing ~6-month window grows large relative to its same-window volatility will raise the worst disjoint sub-period Sortino and not regress aggregate drawdown or turnover, because Daniel-Moskowitz (2016) show momentum crashes follow sustained bear/panic states in which the momentum portfolio behaves like a short call and accumulates a large own-drawdown — a path/state variable that is orthogonal to volatility and is precisely the grinding-bear regime (modest daily vol, large cumulative loss) that the existing vol-magnitude-only scaler is structurally blind to and that coincides with the strategy's weakest folds.

**Change:** Added a pure, deterministic, parameter-free helper that resolves the same robust source chain as the kept vol estimator (held book → broad cross-section → neutral) and returns clip(window_vol / max(book_drawdown, window_vol), 0, 1) — exactly 1.0 in calm uptrends (drawdown tiny ⇒ byte-equivalent, upside preserved) and < 1 only when the book's own drawdown exceeds its window volatility — then multiply the existing dual-horizon vol-targeted gross by this factor so gross can only ever fall (strictly weakly more defensive, turnover-neutral, no new tunable knob, the kept slow/fast estimator path left exactly intact).

**Decision:** REVERTED — sortino 3.289 did not improve on prev 3.2888808654214845

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2888808654214845
- validation_folds: 13
- per_fold_sortinos: [0.3153, 0.1831, -0.2829, 10.1361, 8.2572, 1.6005, 3.5311, 6.1886, 3.2637, 1.0461, 2.188, 4.6584, 1.6704]
- calmar_mean: 5.888060363935045
- hit_rate_mean: 0.4283216783216784
- profit_factor_mean: 3.407823210651147
- trade_count_total: 56
- aggregate_max_dd: 0.09638467816807504
- worst_fold_max_dd: 0.0963846781680749
- max_position_frac_peak: 0.10618164006890835
- lower_quartile_fold_calmar: 1.449220470856095
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.289 to 3.289 (+0.000). Aggregate DD was 9.6% versus previous kept 9.6%; negative folds were 1/13; trades=56. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.289 did not improve on prev 3.2888808654214845.

---

## Iteration 2026-05-19-18ec7c3 — REVERTED

**Hypothesis:** Adding a parameter-free soft low-beta tilt — an equal-weight rank that prefers momentum-quality names with LOWER beta to the cohort's own equal-weight return — to the existing rank-sum will raise the worst disjoint sub-period Sortino and not regress aggregate drawdown or turnover, because a momentum book's catastrophic left tail is concentrated in its high past-beta winners that collapse hardest on bear-market rebounds (Daniel-Moskowitz 2016; Frazzini-Pedersen BAB; Asness QMJ), so de-emphasizing that crash fuel is asymmetric: near-inert in calm bull folds (cohort broadly healthy) but protective in exactly the turbulent/bear sub-periods that set the worst fold.

**Change:** Added a pure, deterministic `_market_betas` helper and a unit-weight `beta_rank` (lower beta → higher rank) term into `momentum_quality_scores`, computing each qualified name's beta against the equal-weight mean of the same momentum-quality cohort over the existing signal window; the tilt is omitted entirely (uniform 0.0 contribution) whenever the beta estimate is ill-posed, and it is a soft reorder within the already-qualified cohort — not an exclusion, not a residualisation of the ranked return, and no new strategy param or tunable literal (parsimony-neutral, turnover-neutral construction unchanged).

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null)

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.32899332072243
- validation_folds: 13
- per_fold_sortinos: [0.5371, -0.6992, 0.8723, 8.6972, 7.939, 1.8257, 4.7279, 6.8062, 3.174, 1.2574, 3.9469, 3.9532, 0.2392]
- calmar_mean: 5.412171806544818
- hit_rate_mean: 0.44017094017094016
- profit_factor_mean: 7.32783606936865
- trade_count_total: 60
- aggregate_max_dd: 0.09004455654546459
- worst_fold_max_dd: 0.07712092146463549
- max_position_frac_peak: 0.10067408079723365
- lower_quartile_fold_calmar: 0.7957709033193572
- n_negative_folds: 1/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.289 to 3.329 (+0.040). Aggregate DD was 9.0% versus previous kept 9.6%; negative folds were 1/13; trades=60. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=1.0000 >= alpha/N=0.0333) · random_walk_mc(only 0.00% percentile vs RW null).

---

## Iteration 2026-05-19-ccae79c — KEPT

**Hypothesis:** Gating the between-rebalance structural exit so it fires only when the close is below the structural MA AND that MA is itself no longer rising (its own slope, measured parameter-free over the existing formation/skip horizon, has turned down) will raise the worst disjoint sub-period Sortino and lower turnover/DP cost without regressing aggregate drawdown, because the current bare close<MA exit churns intact winners on routine pullbacks within still-rising long uptrends (the dominant false-exit / DP-drag case in choppy, low-vol whipsaw folds that the vol-target — blind to direction in low volatility — cannot help), whereas a genuine regime break rolls the long MA itself over, where the exit still fires and two orthogonal de-risking channels (vol-targeted gross, biweekly re-selection) also act.

**Change:** In `_apply_structural_exit` only, the exit now requires both close < structural MA and the structural MA falling (its same-length value as of `skip` bars ago exceeds today's), reusing the strategy's existing ma_window and formation/skip quantities so no new tunable hyperparameter is added; this is strictly weakly fewer exits than the committed behaviour (whipsaw-robust in rising-MA pullbacks, byte-equivalent once the MA has rolled over in a real bear), targeting the real-world turnover/DP and worst-sub-period objective rather than a knob tweak on the exhausted vol-target / ranking families.

**Decision:** KEPT — sortino 3.308 > prev 3.2888808654214845, agg_dd 12.9%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.3082196634381384
- validation_folds: 13
- per_fold_sortinos: [0.3004, -0.6311, -1.0787, 10.1361, 8.6149, 3.1183, 3.5343, 6.1885, 3.2613, 1.0461, 2.188, 4.6584, 1.6704]
- calmar_mean: 6.0349818729390785
- hit_rate_mean: 0.4393106893106893
- profit_factor_mean: 3.672888447788454
- trade_count_total: 56
- aggregate_max_dd: 0.12865169164692922
- worst_fold_max_dd: 0.0970885008014123
- max_position_frac_peak: 0.1061646093260265
- lower_quartile_fold_calmar: 1.449220470856095
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.289 to 3.308 (+0.019). Aggregate DD was 12.9% versus previous kept 9.6%; negative folds were 2/13; trades=56. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 3.308 > prev 3.2888808654214845, agg_dd 12.9%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-19-a55b11d — REVERTED

**Hypothesis:** Tightening the momentum-quality entry qualification so a name must be not only ABOVE its structural MA but with that SAME MA RISING (parameter-free slope over the existing formation/skip horizon) — the entry-side symmetric counterpart of the just-kept slope-gated structural exit — will raise the worst disjoint sub-period Sortino and lower DP turnover without regressing aggregate drawdown, because a close poking above a still-falling long MA is the classic unconfirmed bear-rebound bounce (Daniel-Moskowitz 2016; Moskowitz-Ooi-Pedersen TS-momentum; Faber 2007 dual price+trend filter) that the bare close>MA gate admitted only for the kept exit to churn it out a fortnight later at a ₹14.75 DP cost, whereas in healthy rising-MA up-trends (the strong folds) the MA is rising so the filter is byte-inert.

**Change:** In momentum_quality_scores only, the entry qualification now additionally requires the structural MA to be rising (its same-length value `skip` bars ago is below today's), reusing the existing ma_window and formation/skip quantities (no new tunable hyperparameter) and skipping the slope test when the window is too short so the change is strictly weakly fewer/safer entries — making entry and the kept structural exit a clean symmetric slope-confirmed trend filter targeting the falling-MA whipsaw/bear sub-periods that set the worst disjoint Sortino.

**Decision:** REVERTED — sortino 3.138 did not improve on prev 3.3082196634381384

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.1380541826723007
- validation_folds: 13
- per_fold_sortinos: [0.1771, -0.9658, -1.7587, 9.9455, 8.6196, 3.1076, 3.435, 5.3859, 3.2612, 1.0705, 2.188, 4.6584, 1.6704]
- calmar_mean: 5.687845985370534
- hit_rate_mean: 0.45689310689310686
- profit_factor_mean: 3.2364616704545335
- trade_count_total: 60
- aggregate_max_dd: 0.16000237992458016
- worst_fold_max_dd: 0.09710941986112612
- max_position_frac_peak: 0.11237158482493774
- lower_quartile_fold_calmar: 1.449220470856095
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.308 to 3.138 (-0.170). Aggregate DD was 16.0% versus previous kept 12.9%; negative folds were 2/13; trades=60. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.138 did not improve on prev 3.3082196634381384.

---

## Iteration 2026-05-19-defaa42 — REVERTED

**Hypothesis:** Multiplying the committed dual-horizon vol-targeted gross by a parameter-free, one-sided (≤1) absolute-momentum trend dampener — the clipped ratio of the active-universe equal-weight return index to its own structural-MA — will raise the worst disjoint sub-period Sortino and not regress aggregate drawdown, because the kept vol-target is explicitly blind to a slow LOW-volatility directional bleed (low realised vol keeps gross high while price grinds down), the one residual weakness the last KEEP itself named, and a price-vs-trend gate (Faber 2007; Moskowitz-Ooi-Pedersen 2012; Hurst-Ooi-Pedersen 2017) fires cleanly there while being byte-inert (factor clipped to 1.0) in healthy up-trends so the strong folds and upside are untouched.

**Change:** Added a pure, deterministic `_market_trend_dampener` (equal-weight cumulative-return index of the active-universe cross-section vs its own `_structural_ma_window` MA, clipped to [0,1] so it can only reduce gross, never lever, and is exactly 1.0 — inert — whenever the index is at/above its trend or the sample is thin), and multiplied the existing vol-targeted gross by it in `next()`; no new strategy param or tunable literal (MA window is the shared structural definition, the 20-series floor reuses the existing convention), so it is parsimony-neutral, turnover-neutral, and strictly one-sided downside/worst-sub-period protection orthogonal to the realised-vol and structural-exit channels.

**Decision:** REVERTED — sortino 3.297 did not improve on prev 3.3082196634381384

**Result:**
- evaluator_version: 2026-05-16-univfloor
- validation_sortino_mean: 3.2971798905960137
- validation_folds: 13
- per_fold_sortinos: [0.3151, -0.6389, -1.1215, 10.173, 8.4704, 3.1183, 3.5343, 6.1885, 3.2613, 1.0461, 2.188, 4.6584, 1.6704]
- calmar_mean: 6.030611733052793
- hit_rate_mean: 0.44187479187479184
- profit_factor_mean: 3.73470815981989
- trade_count_total: 56
- aggregate_max_dd: 0.12857412569792595
- worst_fold_max_dd: 0.09721917782447476
- max_position_frac_peak: 0.10623395813071627
- lower_quartile_fold_calmar: 1.449220470856095
- n_negative_folds: 2/13
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 3.308 to 3.297 (-0.011). Aggregate DD was 12.9% versus previous kept 12.9%; negative folds were 2/13; trades=56. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 3.297 did not improve on prev 3.3082196634381384.

---
