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
