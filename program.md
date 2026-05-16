# Autoresearch program — Indian equities

**Goal:** generate a swing-trading strategy on the top-200-by-ADV liquid Nifty 500 slice, with positive risk-adjusted return after Dhan delivery costs, that survives a sealed walk-forward test on 2024-01 to 2026-05 Indian market data.

**You may edit `strategy.py`. You must NOT edit `prepare.py`** — `prepare.py` is the read-only walk-forward evaluator + anti-overfit gate runner. Do not edit it under any circumstance; changing the evaluator invalidates every prior iteration's comparison baseline.

**Constraints (do not violate):**

1. **Long-only, CNC (delivery), single segment (NSE_EQ).** No F&O, no intraday, no short selling, no margin.
2. **Position sizing via `self.order_target_percent` only.** Never call `self.buy()` or `self.close()` directly.
3. **Universe is fixed by `data/universe.py`** at each rebalance date. Strategy may rank or filter within the universe; it may not add tickers outside it.
4. **Biweekly rebalance** (alternate Fridays) is the default cadence. Loop may propose changing this; must clear anti-overfit gates.
5. **Hyperparameter parsimony budget:** starting strategy has 7 counted signal params; each new param added must improve sealed-test Sortino by ≥ 0.10 AND clear Bonferroni significance.
6. **Sector cap 25%** enforced at rebalance. Hard constraint.
7. **Anti-overfit gates** (`backtest/anti_overfit.py`) are atomic. A variant failing any gate is REJECTED.
8. **All Sortinos used for promotion are computed net of full Dhan delivery costs** (brokerage 0, STT, DP charges, exchange, GST, stamp duty).
9. **Sealed test set 2024-01 to 2026-05 is revealed ONCE per promotion.** No retries on the same variant.

**Strategy family (branch `mean-reversion-quant-strategy`):** long-only
short-horizon **residual mean-reversion statistical arbitrage** — the
structural inverse of the momentum book on `main`. Each rebalance: rolling
OLS of every name's returns on a market factor (equal-weight universe mean)
and a size factor (small-ADV minus large-ADV tercile; no market cap is
available so ADV is the size proxy), then buy the names whose cumulative
factor residual is most negative (most oversold relative to their factor
exposure), expecting reversion.

**Hyperparameters the loop may tune:**
- `beta_window` (rolling OLS window for the market/size betas)
- `formation_days` (residual accumulation / reversion horizon)
- `retention_mult` (selection retention buffer; turnover/DP-cost control)
- `entry_pct` (only the most-oversold tail is entry-eligible)
- `regime_pct` (regime-gate threshold; reversion is fragile in trending
  crashes so the defensive gate matters more, not less)
- `n_positions` (target position count; 4-10 acceptable range)
- `rebalance_freq` (biweekly default; may propose weekly/monthly with full justification)

**Data the strategy may use** — all accessors are point-in-time
(most-recent value on/before the rebalance date; signals are as-of-close,
orders fill next open — no look-ahead). Import from `llm.features`:

- Price OHLCV history (`storage/prices.duckdb`)
- `macro_regime(date)` → `'risk_on'|'neutral'|'risk_off'|'shock'|None`
  (holistic 4-class label; `None` until the macro cache is precomputed)
- `macro_signals(date)` → dict of **numeric** macro signals with real
  data coverage (absent keys simply omitted, never zero-filled). Keys:
  `india_vix`, `india_vix_pct_252d`, `nifty50_close`, `nifty50_200dma`,
  `nifty50_pct_vs_200dma`, `usd_inr`, `usd_inr_1w_change_pct`,
  `gdelt_tone_mean`, `gdelt_tone_negfrac`, `gdelt_epu_policy`,
  `gdelt_centralbank`, `gdelt_tariff_trade`, `gdelt_inflation`.
  Convenience scalars: `india_vix_percentile(date)` (0..1, high = vol
  stress), `nifty_vs_200dma_pct(date)` (trend regime). Prefer these
  numeric signals for richer/continuous regime logic than the 4-class
  label; the parsimony + anti-overfit gates police added complexity.
- `sentiment(ticker, date)`, `events(ticker, date)`, `news_volume(ticker,
  date)` (per-ticker; sentiment/events are `None`/default until their
  caches are precomputed)
- Sector classification (`data/sectors.py`)

**NOT available — do NOT write logic depending on these:**
- FII / DII flows — only ~1 recent row; 5y history deferred.
- Policy / repo rate — 16 stale rows (frozen 2022-07); excluded.
- Quality / fundamentals (ROE, D/E, op-margin) — no fundamentals ingest
  yet; the quality screen soft-degrades to pass-all (the `quality_pct`
  knob was removed for this reason).

**Output contract (STRICT — a violation wastes the whole iteration):**
- `new_strategy_py` MUST be the complete, literal Python source of
  `strategy.py` with REAL newlines — never escaped `\n`/`\t`/`\"`
  sequences, never markdown fences, never a diff.
- It MUST be syntactically valid Python (it will be `ast.parse`d) and keep
  the class name and the `order_target_percent`-only trade contract.
  Mentally compile it before returning — a syntax error = immediate reject,
  no backtest, a wasted iteration.
- Import ONLY whitelisted modules: `backtrader`, `numpy`, `pandas`, `datetime`, `data.*`, `llm.features`, `__future__`, plus safe stdlib (`math`, `logging`, `collections`, `itertools`, `functools`, `statistics`, `bisect`, `random`, `typing`, `dataclasses`, `re`, `json`) — ANY other import (`os`, `sys`, `subprocess`, `pathlib`, `requests`, …) is an instant reject, no backtest, wasted iteration.

**Decision criteria for KEEP:**
A variant is KEPT iff all gates pass:
1. Walk-forward Sortino (net of costs) > baseline AND > 0
2. `|Sortino| < 10` (sanity sortino bound — anything beyond is signal of a bug or numerical artefact)
3. Aggregate drawdown does not regress more than 10pp (10 percentage points) vs prior KEPT
4. Catastrophe-validator clear — all of:
   - gross exposure < 100% (no leverage; equal-weight long-only)
   - aggregate drawdown < 50% (account-wipe gate)
   - at least 20 trades total (below 20 trades the Sortino is too noisy to trust)
5. Anti-overfit gates clear: Bonferroni p-correction, Random-Walk Monte Carlo (5000 permutations, must beat 95th-pct null), parameter parsimony budget, sub-period stationarity (min/max sub-period Sortino ratio >= 0.30)
6. Sealed-test reveal Sortino > baseline AND > 0 (one-shot per variant; failure is final)

Otherwise: REVERT.

**Read the reject reason as a diagnosis, not history:**
- `bonferroni` p≈1.0 / `random_walk_mc` low percentile ⇒ the signal has **no
  edge** (its return ordering is no better than a random shuffle). Tuning a
  knob on it is wasted — change the *thesis*, not the parameter.
- Recurring 60–90% `catastrophe` drawdown ⇒ **structural** to a concentrated
  long-only book; fix it with construction (more names, defensive
  de-risking, vol-scaled sizing), not signal tweaks.
- Low `sub_period_stationarity` ⇒ edge isn't persistent across regimes — a
  curve fit, not a strategy.

If the last few reverts all failed for "no edge", the signal family is
exhausted: propose something **structurally different**, don't refine it.

**Out of scope for this loop iteration:**
- Changes to `prepare.py` (immutable evaluator)
- Changes to data ingest, broker, executor (separate concerns)
- Changes to anti-overfit gates (separate, deliberate design changes)
- Adding new data sources (must go through human review)
