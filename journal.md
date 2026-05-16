# Autoresearch journal — Indian equities

This is the autoresearch loop's persistent memory. Every iteration appends an entry with hypothesis, change, result, and decision (KEEP / REVERT). Entries compound across runs and inform future proposals.

**Parser hazard:** the KEEP/REVERT parser in `scripts/loop.py` matches the literal line `**Decision:** KEPT` (not substring). Preserve the exact format.

---

## Iter 0 — Baseline (2026-05-14)

**Hypothesis:** A sparse, theory-backed cross-sectional momentum strategy with quality screen, sector cap, and Indian-context regime gate will produce a positive Sortino on the train+val window (2018-01 to 2023-12) when run on the top-200-by-ADV liquid Nifty 500 slice, after Dhan delivery costs.

**Theoretical basis:**
- 12-1 cross-sectional momentum: Jegadeesh & Titman 1993; Asness, Moskowitz, Pedersen 2013
- Quality screen (ROE / D-E / Op-margin): Novy-Marx 2013; Asness, Frazzini, Pedersen 2019
- Equal-weight sizing: DeMiguel, Garlappi, Uppal 2009
- Regime-gated entries: Cooper, Gutierrez, Hameed 2004; 2024-26 Indian regime evidence (FII outflows, Quality > Momentum during corrections)

**Change:** N/A — this is the seed strategy. See `strategy.py` for the implementation.

**Hyperparameters (5):**
- `lookback_days = 252`, `skip_days = 21`
- `retention_mult = 2.0`
- `quality_pct = 50`
- `regime_pct = 95`, `fii_threshold_cr = -15000`
- `n_positions = 6`

**Result:** Pending first walk-forward run.

**Learning:** (to be filled by the first iteration after walk-forward results land) — what did this baseline teach us about Indian-market behaviour under the chosen parameter set? Was the regime gate signal active during 2024-Q4 / 2026-Q1 drawdowns? Did the quality screen materially change which names were selected?

**Decision:** PENDING

---

(future iteration entries will be appended below this line by `scripts/loop.py`)

## Iteration smoke-codex-1778866545 — REJECTED

**Hypothesis:** Ranking candidates by volatility-adjusted 12-1 momentum instead of raw 12-1 momentum should improve validation Sortino by reducing concentration in high-beta winners that later mean-revert or crash.

**Change:** Changed the momentum score to divide 12-1 return by realized daily volatility over the same lookback window, using existing lookback and skip parameters without adding a new hyperparameter.

**Decision:** REJECTED — validation failed: syntax error: unexpected character after line continuation character (line 1)

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: syntax error: unexpected character after line continuation character (line 1).

---

## Iteration 2026-05-15-50c1342 — REJECTED

**Hypothesis:** Replacing raw 12-1 momentum with volatility-adjusted 12-1 momentum will improve mean validation Sortino by favoring steadier trend leaders and reducing exposure to high-beta reversals without adding a new hyperparameter.

**Change:** Changed the ranking score to divide 12-1 return by realized daily volatility over the same lookback window, preserving the existing cadence, sector cap, retention buffer, and order_target_percent-only trade contract.

**Decision:** REJECTED — prepare.py crashed: 'str' object has no attribute 'exists'

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: prepare.py crashed: 'str' object has no attribute 'exists'.

---

## Iteration 2026-05-15-7786d97 — REVERTED

**Hypothesis:** Requiring a strictly positive 12-1 momentum score for new entries will improve mean validation Sortino by avoiding forced allocation into relative winners that are still absolute downtrends during broad selloffs.

**Change:** Filtered quality-passed new-entry candidates to names with momentum greater than zero while leaving retention, cadence, sizing, sector caps, and existing hyperparameters unchanged.

**Decision:** REVERTED — catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9846 >= alpha/N=0.0250) · random_walk_mc(only 52.50% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15)

**Result:**
- validation_sortino_mean: 1.7672545809923377
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.7074, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 5.4043, 17.5131, 6.2747, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.2921]
- calmar_mean: 6.878353634393159
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 29
- aggregate_max_dd: 0.7777282617212222
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 77.8% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.767 with no prior kept baseline. Aggregate DD was 77.8%; negative folds were 9/20; trades=29. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 77.8% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.9846 >= alpha/N=0.0250) · random_walk_mc(only 52.50% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.15).

---

## Iteration 2026-05-16-f921e9d — REJECTED

**Hypothesis:** Adding a parameter-free time-series trend overlay that exits to cash whenever Nifty 50 is below its 200-day moving average will raise mean validation Sortino by truncating the structural ~78% concentrated-long-only catastrophe drawdown that pure cross-sectional momentum cannot fix.

**Change:** Added a canonical Faber-style index-trend de-risking overlay (using llm.features.nifty_vs_200dma_pct with a fixed 0.0 crossing, no new tunable hyperparameter) that forces all positions flat when the broad index is below its 200DMA, leaving the cross-sectional momentum selection untouched.

**Decision:** REJECTED — validation failed: disallowed import: bisect

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: disallowed import: bisect.

---

## Iteration 2026-05-16-d60ac22 — REJECTED

**Hypothesis:** A Faber-style Nifty 200DMA trend overlay — exiting all positions to cash when Nifty 50 closes below its 200DMA — will truncate the structural ~78% concentrated-long-only drawdown; this re-attempts the sound f921e9d idea but fixes the implementation failure by replacing the disallowed `bisect` import with an inline binary search.

**Change:** Added `_nifty_above_200dma(today)` method using `llm.features.nifty_vs_200dma_pct` (no new hyperparameter; 0.0 crossing is canonical Faber threshold) and an early-exit in `next()` that liquidates all held positions when the index is in a downtrend; replaced the `bisect` import in `resolve_active_universe` with a manual bisect-right loop to clear the disallowed-import gate.

**Decision:** REJECTED — validation failed: disallowed import: logging

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: disallowed import: logging.

---

## Iteration 2026-05-16-3fa1857 — REJECTED

**Hypothesis:** A parameter-free Faber-style Nifty 200DMA trend overlay that liquidates all positions to cash when Nifty 50 is below its 200DMA will truncate the structural concentrated-long-only drawdown; this is the correct implementation of the prior two rejected attempts, fixing both disallowed imports by replacing `import bisect` with an inline bisect function and removing `import logging` entirely.

**Change:** Removed `import bisect` (replaced with inline `_bisect_right`) and `import logging` (removed entirely), then added `_nifty_above_200dma(today)` using `llm.features.nifty_vs_200dma_pct` with an early-exit in `next()` that liquidates all held positions at each biweekly rebalance when Nifty 50 is in a downtrend.

**Decision:** REJECTED — validation failed: disallowed import: pathlib

**Learning:** No scored strategy inference: the iteration failed before prepare.py produced validation metrics. Treat this as an implementation failure, not evidence about the hypothesis. Failure reason: validation failed: disallowed import: pathlib.

---

## Iteration 2026-05-16-28121b1 — REVERTED

**Hypothesis:** A parameter-free Faber-style Nifty 200DMA trend overlay that liquidates all positions when Nifty 50 closes below its 200DMA will truncate the structural ~78% concentrated-long-only catastrophe drawdown, reduce negative-fold count, and improve mean validation Sortino without consuming any parsimony budget.

**Change:** Added _nifty_above_200dma(today) using llm.features.nifty_vs_200dma_pct with a fixed 0.0 crossing (canonical Faber 2007 threshold, no new hyperparameter), moved held-position computation before the 200DMA check to enable clean early-exit liquidation, and removed the disallowed pathlib import by passing fundamentals_db_path as a string directly to load_fundamentals.

**Decision:** REVERTED — catastrophe: max drawdown: 86.4% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.02)

**Result:**
- validation_sortino_mean: 1.2226461221135445
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, -0.4525, -3.5735, -2.0113, -3.4524, -4.2897, -2.4906, -2.185, 1.7866, 14.9913, 7.6339, 3.128, 2.8153, 3.1902, 0.7265, -0.4423, -3.2094, -3.2096]
- calmar_mean: 5.63899541603786
- hit_rate_mean: 0.24500000000000002
- profit_factor_mean: 0.46706373444576477
- trade_count_total: 32
- aggregate_max_dd: 0.8635885353748112
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -2.0368618152186424
- n_negative_folds: 10/20
- risk.passed: False
- risk.violations: ['max drawdown: 86.4% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.223 with no prior kept baseline. Aggregate DD was 86.4%; negative folds were 10/20; trades=32. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 86.4% > 50% (account-wipe territory) | anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.02).

---

## Iteration 2026-05-16-2782a0d — REVERTED

**Hypothesis:** When the average 12-1 momentum of the top-n_positions ranked stocks is non-positive, the market is in a systemic bear phase and exiting all held positions to cash will break the fold-over-fold equity decay responsible for the 80%+ aggregate drawdown.

**Change:** Removed the disallowed pathlib import (passing fundamentals_db_path as a string directly), moved held-position snapshot before the quality screen to enable early exit, and added a market-breadth bear-market gate that liquidates all positions when the average momentum of the top-n_positions names is <= 0.

**Decision:** REVERTED — catastrophe: max drawdown: 80.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8484 >= alpha/N=0.0167) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16)

**Result:**
- validation_sortino_mean: 1.6879103804644635
- validation_folds: 20
- per_fold_sortinos: [10.2078, 4.2456, 1.044, 1.6464, -0.6936, -2.0323, -2.954, -3.3106, -2.7456, -2.1572, 4.0833, 17.5131, 5.9853, 3.3435, 2.8153, 3.1902, 0.7265, -0.6481, -3.2094, -3.2921]
- calmar_mean: 6.891923644733654
- hit_rate_mean: 0.175
- profit_factor_mean: 0.409919297689169
- trade_count_total: 32
- aggregate_max_dd: 0.8022901704841484
- worst_fold_max_dd: 0.4021710423452941
- max_position_frac_peak: 1.2186307069176447
- lower_quartile_fold_calmar: -1.8914079368162482
- n_negative_folds: 9/20
- risk.passed: False
- risk.violations: ['max drawdown: 80.2% > 50% (account-wipe territory)']

**Learning:** Sortino scored 1.688 with no prior kept baseline. Aggregate DD was 80.2%; negative folds were 9/20; trades=32. Do not reuse this exact setup: it failed the catastrophe gate, so the result is not a usable edge even if the hypothesis was economically plausible. Decision reason: catastrophe: max drawdown: 80.2% > 50% (account-wipe territory) | anti-overfit FAILED: bonferroni(p=0.8484 >= alpha/N=0.0167) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16).

---

## Iteration 2026-05-16-ffb5ca4 — REVERTED

**Hypothesis:** Scaling total portfolio gross exposure inversely with realized 21-day portfolio volatility (targeting a 12% annual portfolio vol) will break the structural 80-86% aggregate drawdown by dynamically cutting position sizes to ~30-50% during high-volatility bear market periods while restoring full 99% exposure in calm bull markets — addressing the 'vol-scaled sizing' construction fix called out explicitly in the program spec.

**Change:** Added _realized_vol() and _vol_scale_exposure() methods that estimate equal-weight portfolio daily vol from individual stock 21-day realized returns (with a correlation-adjustment divisor of 2.5 for Indian equity co-movement), then multiply the 0.99 gross exposure cap by min(target_daily_vol / port_vol_est, 1.0) before dividing by position count; also removed the disallowed `pathlib` import and pass fundamentals_db_path as a plain string.

**Decision:** REVERTED — anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 90.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.21)

**Result:**
- validation_sortino_mean: 1.538269424338637
- validation_folds: 20
- per_fold_sortinos: [10.9017, 4.9413, 0.598, 0.6802, -1.0115, -1.8831, -3.2434, -1.4152, -2.0368, -2.9316, 7.135, 11.9529, 4.3797, 3.6344, 3.7262, 2.9956, 0.8411, -0.6268, -3.463, -4.4093]
- calmar_mean: 3.0497317764654293
- hit_rate_mean: 0.38345238095238093
- profit_factor_mean: 2.0557522608445726
- trade_count_total: 74
- aggregate_max_dd: 0.3587002504697492
- worst_fold_max_dd: 0.16250342876837526
- max_position_frac_peak: 0.5126483937131874
- lower_quartile_fold_calmar: -1.9486268207024624
- n_negative_folds: 9/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.538 with no prior kept baseline. Aggregate DD was 35.9%; negative folds were 9/20; trades=74. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: bonferroni(p=1.0000 >= alpha/N=0.0125) · random_walk_mc(only 90.42% percentile vs RW null) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.21).

---

## Iteration 2026-05-16-21916f3 — KEPT

**Hypothesis:** Replacing the raw 12-1 return cross-sectional ranking with 52-week high proximity (current_price / max_close_over_252_days) will produce a statistically significant cross-sectional edge — where raw momentum repeatedly yielded Bonferroni p≈1.0 — by exploiting the anchoring bias documented by George & Hwang (2004): stocks near their 52-week high experience analyst underreaction and continued positive drift, a behavioral effect that is distinct from, and more robust than, raw return magnitude sorting.

**Change:** Replaced `_momentum_for` (raw 12-1 return) with `_high52_proximity_for` (current_close / 252-day max close, range (0,1]) as the sole ranking signal; also removed three disallowed imports (bisect → inline binary search, logging → removed entirely, pathlib.Path → string passed directly to load_fundamentals) that caused the prior three iterations to be rejected before any backtest ran.

**Decision:** KEPT — sortino 1.933 > prev None, agg_dd 21.3%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- validation_sortino_mean: 1.933431293775231
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2037, 0.3582, 0.7687, -0.8172, -0.4734, 0.9904, 1.2429, 1.185, -2.1273, 3.6006, 9.0061, 2.7433, 3.8208, 5.4293, 1.6074, -0.5268, 1.8146, -1.5021, -3.628]
- calmar_mean: 3.292489013604263
- hit_rate_mean: 0.37513322934375565
- profit_factor_mean: 1.8568861944920798
- trade_count_total: 333
- aggregate_max_dd: 0.2130510720750258
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.20481992543689143
- lower_quartile_fold_calmar: -0.7432964652523935
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino scored 1.933 with no prior kept baseline. Aggregate DD was 21.3%; negative folds were 6/20; trades=333. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 1.933 > prev None, agg_dd 21.3%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-224b0c4 — KEPT

**Hypothesis:** Replacing the LLM macro_regime gate — which either blocks all new entries when the cache row is absent (returns None) or allows all entries when it throws — with the deterministic Nifty 50 200-DMA trend filter (nifty50_pct_vs_200dma > 0 from macro_signals, which has real price-data coverage throughout the backtest window) will make the bear-market guard actually work, reducing new-entry losses in the 6 negative folds and improving mean validation Sortino without changing the cross-sectional 52-week proximity ranking signal.

**Change:** Replaced _regime_gate to read nifty50_pct_vs_200dma from macro_signals instead of macro_regime_for: positive value (Nifty above 200DMA) allows new entries, zero-or-negative blocks them, with graceful fallback to True when the macro DB is unavailable; also updated _regime_cache type from dict[date,str] to dict[date,bool] and added per-call memoization to avoid redundant DB reads on the same rebalance date.

**Decision:** KEPT — sortino 2.172 > prev 1.933431293775231, agg_dd 22.2%, catastrophe gate clear, anti-overfit gates passed

**Result:**
- validation_sortino_mean: 2.172090958313302
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.5528, 0.4111, -0.4923, 1.5587, -2.3272, 4.9112, 11.2162, 3.1341, 3.8208, 5.4293, 1.6074, 0.4337, 1.6485, -0.3075, -2.5701]
- calmar_mean: 3.4307496059067644
- hit_rate_mean: 0.4030257631446087
- profit_factor_mean: 1.894437452959771
- trade_count_total: 348
- aggregate_max_dd: 0.22169253664442026
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.20137086447217914
- lower_quartile_fold_calmar: -0.47584757926680854
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 1.933 to 2.172 (+0.239). Aggregate DD was 22.2% versus previous kept 21.3%; negative folds were 6/20; trades=348. Keep compounding on this change, but future iterations should still explain whether the gain came from better return, lower downside, or fewer fragile folds. Decision reason: sortino 2.172 > prev 1.933431293775231, agg_dd 22.2%, catastrophe gate clear, anti-overfit gates passed.

---

## Iteration 2026-05-16-563b585 — REVERTED

**Hypothesis:** Replacing equal-weight position allocation with inverse-volatility weighting (each stock sized proportional to 1/realized_21d_annualized_vol, normalized to 99% gross exposure) will reduce capital at risk in high-volatility names during bear folds, lower per-fold drawdown contribution from volatile laggards, and improve mean validation Sortino without adding any new hyperparameters — using the existing skip_days window as the volatility lookback.

**Change:** Added `_realized_vol_for` method computing 21-day annualized log-return realized volatility per ticker, then replaced the flat `target_each = 0.99 / len(selected)` in `next()` with per-ticker inverse-vol weights normalized to 99% gross exposure; no new hyperparameters introduced (vol window reuses `skip_days`).

**Decision:** REVERTED — sortino 2.160 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.01)

**Result:**
- validation_sortino_mean: 2.16033672389409
- validation_folds: 20
- per_fold_sortinos: [12.9201, 4.2031, 0.3472, 0.8075, -0.9307, -0.9878, 0.2459, -0.0376, 0.0, -0.0018, 6.6058, 7.9296, 1.9422, 1.5039, 5.8157, 2.9089, 0.5131, 2.0535, 0.1987, -2.8304]
- calmar_mean: 3.432341935234838
- hit_rate_mean: 0.34547617161047295
- profit_factor_mean: 3.1879399851432697
- trade_count_total: 248
- aggregate_max_dd: 0.21806432934922693
- worst_fold_max_dd: 0.15673607189996763
- max_position_frac_peak: 0.2598348659751656
- lower_quartile_fold_calmar: 0.25200407382646617
- n_negative_folds: 5/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.160 (-0.012). Aggregate DD was 21.8% versus previous kept 22.2%; negative folds were 5/20; trades=248. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.160 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.01).

---

## Iteration 2026-05-16-78994ab — REVERTED

**Hypothesis:** Adding a short-term momentum confirmation filter to the 52-week-high proximity signal — only scoring stocks where close[0] > close[-skip_days] (positive return over the past skip_days bars) — will improve mean validation Sortino by excluding near-high stocks already in short-term downtrend (early distribution phase) and naturally exiting held positions that develop negative recent return at the next rebalance, without adding any new hyperparameter.

**Change:** In `_high52_proximity_for`, added a guard that returns None when `d.close[0] <= d.close[-skip_days]` (flat or negative skip_days return), so only stocks in active upward continuation near their 52-week high are scored and retained, reusing the existing skip_days parameter as the confirmation window with no parsimony cost.

**Decision:** REVERTED — sortino 1.190 did not improve on prev 2.172090958313302 | aggregate DD regressed: 44.1% > prev 22.2% + 10pp tolerance | anti-overfit FAILED: bonferroni(p=0.0544 >= alpha/N=0.0250) · random_walk_mc(only 94.58% percentile vs RW null) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.98)

**Result:**
- validation_sortino_mean: 1.1904168640741644
- validation_folds: 20
- per_fold_sortinos: [8.5213, 2.5383, -0.0957, 3.429, -1.8966, -1.5663, -0.9898, -0.7871, -1.0439, -3.4643, 0.046, 7.0844, 0.8044, 4.013, 5.3176, 1.3346, 0.6816, 1.9448, 0.2249, -2.2879]
- calmar_mean: 2.9311977323270364
- hit_rate_mean: 0.45508738682125377
- profit_factor_mean: 1.6754850660127039
- trade_count_total: 435
- aggregate_max_dd: 0.44100255543440897
- worst_fold_max_dd: 0.16013537861385396
- max_position_frac_peak: 0.9308459729642642
- lower_quartile_fold_calmar: -1.3314325366635944
- n_negative_folds: 9/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.190 (-0.982). Aggregate DD was 44.1% versus previous kept 22.2%; negative folds were 9/20; trades=435. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.190 did not improve on prev 2.172090958313302 | aggregate DD regressed: 44.1% > prev 22.2% + 10pp tolerance | anti-overfit FAILED: bonferroni(p=0.0544 >= alpha/N=0.0250) · random_walk_mc(only 94.58% percentile vs RW null) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.98).

---

## Iteration 2026-05-16-23f9205 — REVERTED

**Hypothesis:** Tightening the retention buffer from `retention_mult × n_positions` to `n_positions` when the Nifty 200-DMA gate signals bear regime (allow_new=False) will shed the weakest held positions at each bear-regime rebalance, reducing drawdown in the negative folds without introducing any new hyperparameter.

**Change:** In `next()`, split the retention_cap into bull (retention_mult × n_positions = 50) versus bear (n_positions = 25) based on the existing allow_new flag, so positions ranked below n_positions are exited at each bear-regime rebalance instead of held until they fall out of the wider buffer.

**Decision:** REVERTED — sortino 2.090 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.08)

**Result:**
- validation_sortino_mean: 2.0902495230419262
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.5352, 0.7694, -0.4923, 1.5587, -2.7978, 5.7274, 8.9373, 3.1341, 3.8208, 5.4293, 1.6074, 0.4337, 1.6485, -0.3075, -2.6494]
- calmar_mean: 3.752320594937557
- hit_rate_mean: 0.3936704887893343
- profit_factor_mean: 1.8743486638591444
- trade_count_total: 353
- aggregate_max_dd: 0.22259295238242968
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.2129509286403574
- lower_quartile_fold_calmar: -0.4791699654296854
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.090 (-0.082). Aggregate DD was 22.3% versus previous kept 22.2%; negative folds were 6/20; trades=353. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.090 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.08).

---

## Iteration 2026-05-16-5f210ed — REVERTED

**Hypothesis:** Repurposing the currently-unused regime_pct parameter as a VIX stress threshold — halving gross exposure to 50% when India VIX's 252-day percentile exceeds regime_pct/100 (default 95th percentile) while keeping the 200-DMA new-entry gate unchanged — will reduce downside deviation in the 6 negative folds by cutting leverage during genuine market stress episodes, improving mean validation Sortino without consuming any new parsimony budget.

**Change:** Merged _regime_gate into a new _macro_state method that returns both (allow_new, gross_mult): allow_new is the existing 200-DMA check; gross_mult is 0.50 when macro_signals['india_vix_pct_252d'] > regime_pct/100 else 1.0; next() multiplies the 0.99 gross-exposure target by gross_mult so all selected positions are sized at half weight during VIX stress, with graceful fallback to full exposure when the macro DB is unavailable.

**Decision:** REVERTED — sortino 2.162 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.01)

**Result:**
- validation_sortino_mean: 2.16191284563873
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.5735, -1.6107, -0.3482, 0.6975, -0.4923, 1.5587, -2.3272, 4.9112, 11.2162, 3.1341, 3.8208, 5.4293, 1.6074, 0.0559, 2.285, -0.1016, -2.7408]
- calmar_mean: 3.4228816863907072
- hit_rate_mean: 0.3975346917160373
- profit_factor_mean: 1.8538356350044882
- trade_count_total: 353
- aggregate_max_dd: 0.23010774753495603
- worst_fold_max_dd: 0.14640939339255754
- max_position_frac_peak: 0.20510836721620584
- lower_quartile_fold_calmar: -0.27939930435403665
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.162 (-0.010). Aggregate DD was 23.0% versus previous kept 22.2%; negative folds were 7/20; trades=353. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.162 did not improve on prev 2.172090958313302 | anti-overfit FAILED: parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.01).

---

## Iteration 2026-05-16-3121bee — REVERTED

**Hypothesis:** Replacing the point-in-time 52-week-high proximity score (close at skip_days ago divided by the max of the prior non-overlapping window) with a smoothed proximity score (SMA of the last skip_days closes divided by the max of the full lookback_days window) will produce a more stable cross-sectional ranking that rewards sustained proximity to the annual high rather than a one-day price coincidence, improving mean validation Sortino without adding new hyperparameters.

**Change:** In `_high52_proximity_for`, replaced the single-bar numerator `close[-skip_days]` with the simple average of the last `skip_days` closes (reusing the existing skip_days parameter as a smoothing window), and shifted the denominator from the non-overlapping prior window `[skip_days, lookback_days+skip_days]` to the full `[0, lookback_days]` window so the signal measures sustained recent strength relative to the true annual high rather than a lagged snapshot of both.

**Decision:** REVERTED — sortino 1.597 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0298 >= alpha/N=0.0100) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.58)

**Result:**
- validation_sortino_mean: 1.596539344583681
- validation_folds: 20
- per_fold_sortinos: [11.1907, 4.2259, 0.4588, 0.7686, -0.7728, -0.5513, 1.0339, 1.7527, -0.4823, -1.774, 0.6978, 4.3593, 2.8739, 3.931, 4.1689, 2.1645, 0.2613, 0.4067, -0.6216, -2.161]
- calmar_mean: 2.18365877599336
- hit_rate_mean: 0.31306679168532614
- profit_factor_mean: 1.1141064770610263
- trade_count_total: 364
- aggregate_max_dd: 0.19556945378768198
- worst_fold_max_dd: 0.1430762843825889
- max_position_frac_peak: 0.20945083760090574
- lower_quartile_fold_calmar: -0.6092709968386791
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.597 (-0.576). Aggregate DD was 19.6% versus previous kept 22.2%; negative folds were 6/20; trades=364. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.597 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0298 >= alpha/N=0.0100) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.58).

---

## Iteration 2026-05-16-d997519 — REVERTED

**Hypothesis:** Requiring new entrants to also trade above their individual 200-day moving average — in addition to the existing Nifty 50 200-DMA regime gate — will filter out false-momentum candidates (stocks near their 52-week high via a v-shaped bounce in a broader individual downtrend rather than a sustained uptrend) and improve mean validation Sortino by ensuring only stocks with persistent multi-month strength are added to the portfolio.

**Change:** Added `_above_200dma()` method that checks `close[-skip_days] > 200-day SMA` (same execution lag as the proximity signal, no new hyperparameter) and applied it as an additional filter on `new_candidates` in `next()`, leaving retained positions entirely unaffected.

**Decision:** REVERTED — sortino 2.039 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0086 >= alpha/N=0.0083) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.13)

**Result:**
- validation_sortino_mean: 2.039320165525777
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.4164, 0.7687, -0.8172, -0.5528, 1.2034, -0.4713, 1.1348, -2.3996, 3.5525, 11.2162, 2.2063, 3.4215, 5.6777, 1.3493, 0.3043, 1.6485, -0.599, -2.4841]
- calmar_mean: 3.28820289161959
- hit_rate_mean: 0.4185328843291491
- profit_factor_mean: 1.948112706085709
- trade_count_total: 352
- aggregate_max_dd: 0.20357034284904976
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.3270445622256013
- lower_quartile_fold_calmar: -0.6065448654235599
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.039 (-0.133). Aggregate DD was 20.4% versus previous kept 22.2%; negative folds were 6/20; trades=352. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 2.039 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0086 >= alpha/N=0.0083) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.13).

---

## Iteration 2026-05-16-8ef3d8e — REVERTED

**Hypothesis:** Multiplying the 52-week-high proximity score by a return-consistency factor (fraction of monthly skip_days-length intervals within the lookback window that had positive returns) will improve mean validation Sortino by penalizing stocks that achieved high proximity via a single spike rather than a sustained uptrend, selecting for durable momentum candidates without adding any new hyperparameter.

**Change:** In `_high52_proximity_for`, after computing proximity, compute consistency as pos_months/total_months over the lookback window using skip_days-length buckets, then return proximity × consistency to blend George & Hwang anchoring-bias momentum with Grinblatt & Moskowitz return persistence — no new parameter added.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27)

**Result:**
- validation_sortino_mean: 2.245680254311999
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.5191, 1.8713, 1.6666, -0.517, -1.8275, 5.6828, 6.5354, 2.358, 3.0298, 5.2962, 3.2091, 1.2798, 3.0187, 1.4035, -3.0945]
- calmar_mean: 4.774396914140037
- hit_rate_mean: 0.4093494827436953
- profit_factor_mean: 2.036861309435179
- trade_count_total: 380
- aggregate_max_dd: 0.21459077250102954
- worst_fold_max_dd: 0.14746650530063382
- max_position_frac_peak: 0.19413266438044952
- lower_quartile_fold_calmar: 0.6480195476183077
- n_negative_folds: 5/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.246 (+0.074). Aggregate DD was 21.5% versus previous kept 22.2%; negative folds were 5/20; trades=380. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.27).

---
