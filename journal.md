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

## Iteration 2026-05-16-be234cb — REVERTED

**Hypothesis:** Replacing single-horizon 52-week-high proximity with the geometric mean of 12-month and 6-month proximity scores will select stocks with persistent multi-horizon uptrends rather than those merely near an old annual high, improving sub_period_stationarity without adding any new hyperparameter — addressing the 0.27 ratio failure of the return-consistency variant whose absolute monthly-count measure was regime-dependent (easy to pass in bull periods, hard in bear periods).

**Change:** In `_high52_proximity_for`, added a second proximity loop over the medium-term window (lookback_days // 2 = 126 bars, a derived constant not a free parameter) and returned math.sqrt(prox_long * prox_mid); a stock must be near its highs at BOTH the 6-month and 12-month horizons to score well, stocks that have broken their 6-month high (prox_mid > 1.0) get a natural boost as emerging leaders, and the fully-relative score removes the regime-dependency that caused the consistency-factor variant's stationarity failure.

**Decision:** REVERTED — sortino 1.731 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0158 >= alpha/N=0.0063) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.44)

**Result:**
- validation_sortino_mean: 1.731086856661324
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.5528, 0.2391, -0.7706, 0.7962, -2.5258, 4.815, 8.2059, 2.3572, 1.5235, 5.4293, 1.6074, 0.4337, 2.0078, -1.8947, -2.5701]
- calmar_mean: 3.1560284839798105
- hit_rate_mean: 0.3873686313686314
- profit_factor_mean: 1.7514046377703807
- trade_count_total: 350
- aggregate_max_dd: 0.2650978102417821
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.20086740505134904
- lower_quartile_fold_calmar: -0.8570652623118019
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.731 (-0.441). Aggregate DD was 26.5% versus previous kept 22.2%; negative folds were 6/20; trades=350. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.731 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0158 >= alpha/N=0.0063) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.44).

---

## Iteration 2026-05-16-3df953d — REVERTED

**Hypothesis:** Blending 52-week-high proximity with a cross-sectionally normalized skip_days return rank (score = proximity × (0.5 + 0.5 × normalized_short_term_rank)) will improve mean validation Sortino by selecting stocks with both sustained anchoring-bias momentum and recent relative strength, where cross-sectional normalization makes the secondary signal regime-independent — directly addressing the stationarity failure of the absolute consistency-factor variant (which used an absolute monthly-count that was regime-dependent).

**Change:** Replace the single-signal proximity sort in _rank_universe with a two-pass rank blend: compute skip_days returns for all candidates, normalize them cross-sectionally to [0,1], then multiply each stock's proximity by (0.5 + 0.5 × normalized_rank) so proximity remains the primary signal while recent relative strength provides a continuous, regime-invariant tiebreaker — no new hyperparameters added.

**Decision:** REVERTED — anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.0090 >= alpha/N=0.0056) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16)

**Result:**
- validation_sortino_mean: 2.2462927404418083
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -1.1951, 0.2348, 1.8849, -0.2903, -1.3, 3.5893, 13.3181, 6.2305, 4.8196, 2.3504, -0.2846, 0.267, 0.8389, -0.279, -0.7793]
- calmar_mean: 5.339451570330285
- hit_rate_mean: 0.3944182575932069
- profit_factor_mean: 2.267341351345501
- trade_count_total: 406
- aggregate_max_dd: 0.27120429335615726
- worst_fold_max_dd: 0.19559955313427288
- max_position_frac_peak: 0.20926766798047633
- lower_quartile_fold_calmar: -0.604024072725275
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.246 (+0.074). Aggregate DD was 27.1% versus previous kept 22.2%; negative folds were 7/20; trades=406. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: universe_respect(variant traded tickers outside the point-in-time universe — survivorship/look-ahead reintroduced (hard reject)) · bonferroni(p=0.0090 >= alpha/N=0.0056) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.16).

---

## Iteration 2026-05-16-45960f7 — REVERTED

**Hypothesis:** Scaling gross portfolio exposure to 50% when the Nifty 200-DMA gate signals bear regime — combined with fixed n_positions-slot sizing (gross/n_positions rather than gross/len(selected)) — will reduce bear-market drawdown and smooth sub-period Sortino variance without adding any new hyperparameter, improving both stationarity and aggregate Sortino.

**Change:** In `next()`, replaced `target_each = 0.99 / max(len(selected), 1)` with `gross_target / max(self.p.n_positions, 1)` where `gross_target = 0.99` in bull regime and `0.50` in bear regime (using the existing `allow_new` boolean), so held positions are sized at half weight during Nifty downtrends and unused slots always remain cash rather than concentrating capital into a smaller selected count.

**Decision:** REVERTED — sortino 1.431 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0268 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.74) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.26)

**Result:**
- validation_sortino_mean: 1.430954191376197
- validation_folds: 20
- per_fold_sortinos: [3.9756, 3.2696, 0.765, 0.0578, -1.4921, -1.0072, -0.5388, 0.3874, 1.4954, -0.6391, 1.9004, 9.0244, 3.5838, 3.7081, 5.4362, 2.3497, -0.1964, 1.2757, -0.9479, -3.7886]
- calmar_mean: 1.1249288706088312
- hit_rate_mean: 0.35381078587725384
- profit_factor_mean: 1.7912299359257489
- trade_count_total: 382
- aggregate_max_dd: 0.09687727778597065
- worst_fold_max_dd: 0.060847373270009594
- max_position_frac_peak: 0.04139157131695759
- lower_quartile_fold_calmar: -0.4570980492323684
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.431 (-0.741). Aggregate DD was 9.7% versus previous kept 22.2%; negative folds were 7/20; trades=382. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.431 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0268 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.74) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.26).

---

## Iteration 2026-05-16-0a547d5 — REVERTED

**Hypothesis:** Blending 52-week-high proximity with daily up-bar fraction (fraction of days that closed higher than the previous day within the lookback window) will produce a more stationary cross-sectional signal than proximity alone, because daily persistence is computed from 252 granular samples versus the 12 monthly intervals used in prior failed variants — making it far less sensitive to whether a given sub-period is a bull or bear regime and better at distinguishing genuine trend leaders from one-time spikers that happen to be near an old high.

**Change:** In `_high52_proximity_for`, after computing window_high, simultaneously count up-bars (consecutive closes where the more-recent bar > the older bar) across the 252-bar lookback window, then return `proximity × (0.5 + trend_persistence)` — a multiplier mapping [0, 1] persistence to [0.5, 1.5] that keeps proximity as the dominant signal while rewarding stocks with consistently rising daily closes and penalizing choppy/declining ones; no new hyperparameters are added.

**Decision:** REVERTED — sortino 1.792 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0076 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.38)

**Result:**
- validation_sortino_mean: 1.7915726035460016
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.5406, 1.3708, 2.6127, -0.772, -2.2944, 3.3388, 4.0055, 1.5926, 3.3672, 5.0225, 2.1137, 1.3228, 1.8388, 0.3797, -3.0474]
- calmar_mean: 3.4544721096342483
- hit_rate_mean: 0.3667823491165597
- profit_factor_mean: 1.4321371699240668
- trade_count_total: 323
- aggregate_max_dd: 0.2857990155110232
- worst_fold_max_dd: 0.16881332054897596
- max_position_frac_peak: 0.2148136699272667
- lower_quartile_fold_calmar: -0.09609427425485945
- n_negative_folds: 5/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.792 (-0.381). Aggregate DD was 28.6% versus previous kept 22.2%; negative folds were 5/20; trades=323. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.792 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0076 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.38).

---

## Iteration 2026-05-16-c6abf7a — REVERTED

**Hypothesis:** Replacing raw 52-week-high proximity with volatility-adjusted proximity (score = proximity / (1 + annualized_21d_realized_vol)) will improve mean validation Sortino by selecting stocks whose price path to the 52-week high was orderly (low vol, steady trend) over those that arrived there via a volatile spike — which is more likely to revert — consistent with George & Hwang (2004) anchoring-bias being strongest when the signal is unambiguous.

**Change:** Modified `_high52_proximity_for` to compute a trailing 21-bar annualized realized volatility (anchored at skip_days ago to avoid look-ahead) and divide the proximity score by (1 + realized_vol), penalizing spike-driven near-highs while rewarding smooth uptrends; added `import math` (whitelisted); zero new hyperparameters, graceful fallback to plain proximity when insufficient bars for vol computation.

**Decision:** REVERTED — sortino 1.865 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0234 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.31)

**Result:**
- validation_sortino_mean: 1.8652598274737415
- validation_folds: 20
- per_fold_sortinos: [10.9726, 4.2385, 0.3582, 0.7687, -0.8172, -0.6607, 0.8289, 1.57, 0.6899, -2.1696, 3.0738, 4.425, 2.1058, 5.3617, 5.5514, 1.7842, 0.7118, 1.4321, -0.3446, -2.5752]
- calmar_mean: 2.3128621919230428
- hit_rate_mean: 0.3229892559131689
- profit_factor_mean: 1.6748521392682842
- trade_count_total: 230
- aggregate_max_dd: 0.19939200870934268
- worst_fold_max_dd: 0.14184105194783447
- max_position_frac_peak: 0.19296424776512208
- lower_quartile_fold_calmar: 0.24632865368435009
- n_negative_folds: 5/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.865 (-0.307). Aggregate DD was 19.9% versus previous kept 22.2%; negative folds were 5/20; trades=230. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.865 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0234 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.31).

---

## Iteration 2026-05-16-2883cd7 — REVERTED

**Hypothesis:** Monthly rebalancing (rebalance_period_weeks=4 instead of 2) will improve mean validation Sortino by cutting DP charges (~₹14.75/scrip/sell) by approximately half, reducing unnecessary signal noise in a 252-day-lookback signal that has no informational need for biweekly execution, and producing more stationary sub-period returns — consistent with George & Hwang (2004) documenting the 52-week-high effect using monthly rebalancing.

**Change:** Changed rebalance_period_weeks default from 2 to 4 and generalized _is_rebalance_today to use iso_week % self.p.rebalance_period_weeks (replacing the hardcoded % 2), halving transaction frequency and DP costs with no signal or construction changes and no new hyperparameters.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.30)

**Result:**
- validation_sortino_mean: 2.2947392511558444
- validation_folds: 20
- per_fold_sortinos: [10.9588, 4.1955, 0.3584, 0.7836, -0.7963, -0.8801, 0.9018, 1.6278, -0.0407, -1.8163, 5.7465, 13.145, 0.9453, 4.7497, 4.0216, 2.2624, 0.8767, 0.8961, 0.4196, -2.4605]
- calmar_mean: 3.9407475401125516
- hit_rate_mean: 0.42029193029193035
- profit_factor_mean: 3.967527493205747
- trade_count_total: 160
- aggregate_max_dd: 0.19576189817874487
- worst_fold_max_dd: 0.14052107150389867
- max_position_frac_peak: 0.1996428791722996
- lower_quartile_fold_calmar: 0.282945594495983
- n_negative_folds: 5/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.295 (+0.123). Aggregate DD was 19.6% versus previous kept 22.2%; negative folds were 5/20; trades=160. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.30).

---

## Iteration 2026-05-16-a450cc1 — REVERTED

**Hypothesis:** Monthly rebalancing (rebalance_period_weeks=4) combined with a tighter retention buffer (retention_mult=1.5, capping retained names at 37 instead of 50) will improve mean validation Sortino above 2.172 and push sub-period stationarity above 0.30 by preserving the DP-cost savings of monthly execution while forcing faster exit of fading proximity-rank names that caused the previous monthly-only attempt to accumulate losers during bear sub-periods.

**Change:** Changed rebalance_period_weeks default from 2 to 4 (monthly, halving DP charges) and retention_mult from 2.0 to 1.5 (retention cap 37 vs 50) so that at each monthly rebalance, names ranking outside the top 37 by 52-week-high proximity are sold rather than held for another month — targeting specifically the bear-period fold losses that caused the previous monthly-only attempt to fail sub_period_stationarity at exactly 0.30; also ported the iso_week % rebalance_period_weeks generalization from that attempt.

**Decision:** REVERTED — anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.21)

**Result:**
- validation_sortino_mean: 2.617589646013365
- validation_folds: 20
- per_fold_sortinos: [10.9588, 4.1955, 0.3584, 0.7836, -0.7963, -1.2888, 0.2825, 1.8849, 0.0088, -1.7711, 5.4033, 16.8647, 4.3504, 3.6294, 4.5813, 1.8959, 1.4096, 1.3341, 0.0155, -1.7487]
- calmar_mean: 4.567814956565874
- hit_rate_mean: 0.4507547277284119
- profit_factor_mean: 5.132911489464811
- trade_count_total: 174
- aggregate_max_dd: 0.2046259030358155
- worst_fold_max_dd: 0.14052107150389867
- max_position_frac_peak: 0.2011879250338348
- lower_quartile_fold_calmar: -0.1706465322211021
- n_negative_folds: 6/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 2.618 (+0.445). Aggregate DD was 20.5% versus previous kept 22.2%; negative folds were 6/20; trades=174. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: anti-overfit FAILED: sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.21).

---

## Iteration 2026-05-16-d50fdd7 — REVERTED

**Hypothesis:** 3-week rebalancing (rebalance_period_weeks=3) will improve mean validation Sortino above the 2.172 baseline by reducing DP charges ~35% versus biweekly, while preserving sub-period stationarity better than 4-week monthly rebalancing — which achieved Sortino 2.295 but failed stationarity at 0.30 because the longer 4-week cycle creates lumpier per-period P&L with fewer decision points per sub-period.

**Change:** Changed rebalance_period_weeks default from 2 to 3 and generalized _is_rebalance_today to use iso_week % self.p.rebalance_period_weeks instead of the hardcoded % 2, giving every-third-Friday rebalancing with ~17 cycles/year versus 26 biweekly or 13 monthly — a middle ground that banks meaningful cost savings while keeping enough rebalances per sub-period to avoid the extreme fold-variance that caused monthly to fail stationarity.

**Decision:** REVERTED — sortino 1.501 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0192 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.67)

**Result:**
- validation_sortino_mean: 1.501254090666921
- validation_folds: 20
- per_fold_sortinos: [10.9398, 4.2182, 0.3474, 0.7644, -0.777, -0.768, -1.7176, 2.4727, -1.6953, -3.1815, 1.7818, 5.4108, 3.2867, 2.5442, 6.6387, 1.6824, 0.5327, 1.2806, 0.1019, -3.8379]
- calmar_mean: 3.2768706243469707
- hit_rate_mean: 0.3904428495481127
- profit_factor_mean: 14.479588635951298
- trade_count_total: 243
- aggregate_max_dd: 0.30237822382435103
- worst_fold_max_dd: 0.1453311772367363
- max_position_frac_peak: 0.21346291066580517
- lower_quartile_fold_calmar: -1.1813680830944882
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.501 (-0.671). Aggregate DD was 30.2% versus previous kept 22.2%; negative folds were 7/20; trades=243. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.501 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0192 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.67).

---

## Iteration 2026-05-16-67876d2 — REVERTED

**Hypothesis:** Enforcing strict n_positions slot sizing — retained stocks collected in proximity-ranked order and capped at n_positions, with target_each fixed at 0.99/n_positions so filtered/blocked slots remain cash rather than being redistributed — will improve mean validation Sortino by eliminating the silent over-retention bug (retained>n_positions → diluted sizing) and holding appropriate cash when the universe is sparse or sector-constrained.

**Change:** Changed retention collection to iterate the ranked list and cap at n_positions (instead of taking all held stocks in unranked order up to retention_cap), and changed target_each from 0.99/len(selected) to 0.99/n_positions so that absent/filtered/sector-blocked slots stay as cash, matching the spec's 'fixed risk slots based on n_positions' intent.

**Decision:** REVERTED — sortino 1.506 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0216 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.67) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25)

**Result:**
- validation_sortino_mean: 1.5058331191655143
- validation_folds: 20
- per_fold_sortinos: [3.9756, 3.2696, 0.765, 0.0578, -1.4921, -1.0072, -0.5388, 0.3874, 1.4954, -0.4692, 2.6292, 9.544, 3.6443, 3.7081, 5.4362, 2.3497, -0.1964, 1.2757, -0.9479, -3.7699]
- calmar_mean: 1.1834877947023954
- hit_rate_mean: 0.35381078587725384
- profit_factor_mean: 1.879545247589378
- trade_count_total: 382
- aggregate_max_dd: 0.09687727778597051
- worst_fold_max_dd: 0.060847373270009594
- max_position_frac_peak: 0.04139157131695759
- lower_quartile_fold_calmar: -0.4570980492323684
- n_negative_folds: 7/20
- risk.passed: True
- risk.violations: []

**Learning:** Sortino changed from 2.172 to 1.506 (-0.666). Aggregate DD was 9.7% versus previous kept 22.2%; negative folds were 7/20; trades=382. Do not repeat this exact idea without a materially different mechanism; the keep gate rejected it for the stated reason. Decision reason: sortino 1.506 did not improve on prev 2.172090958313302 | anti-overfit FAILED: bonferroni(p=0.0216 >= alpha/N=0.0050) · parsimony(baseline params=7, strategy=7; needs Sortino +0.00, has +-0.67) · sub_period_stationarity(min/max ratio of |Sortino| across 3 sub-periods = 0.25).

---
