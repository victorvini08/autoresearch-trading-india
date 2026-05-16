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
