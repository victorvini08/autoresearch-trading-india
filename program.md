# Autoresearch program — Indian equities

**Goal:** generate a swing-trading strategy on the top-200-by-ADV liquid Nifty 500 slice, with positive risk-adjusted return after Dhan delivery costs, that survives a sealed walk-forward test on 2024-01 to 2026-05 Indian market data.

**You may edit `strategy.py`. You must NOT edit `prepare.py`** — `prepare.py` is the read-only walk-forward evaluator + anti-overfit gate runner. Do not edit it under any circumstance; changing the evaluator invalidates every prior iteration's comparison baseline.

**Constraints (do not violate):**

1. **Long-only, CNC (delivery), single segment (NSE_EQ).** No F&O, no intraday, no short selling, no margin.
2. **Position sizing via `self.order_target_percent` only.** Never call `self.buy()` or `self.close()` directly.
3. **Universe is fixed by `data/universe.py`** at each rebalance date. Strategy may rank or filter within the universe; it may not add tickers outside it.
4. **Biweekly rebalance** (alternate Fridays) is the default cadence. Loop may propose changing this; must clear anti-overfit gates.
5. **Hyperparameter parsimony budget:** starting strategy has 5 params; each new param added must improve sealed-test Sortino by ≥ 0.10 AND clear Bonferroni significance.
6. **Sector cap 25%** enforced at rebalance. Hard constraint.
7. **Anti-overfit gates** (`backtest/anti_overfit.py`) are atomic. A variant failing any gate is REJECTED.
8. **All Sortinos used for promotion are computed net of full Dhan delivery costs** (brokerage 0, STT, DP charges, exchange, GST, stamp duty).
9. **Sealed test set 2024-01 to 2026-05 is revealed ONCE per promotion.** No retries on the same variant.

**Hyperparameters the loop may tune:**
- `lookback_days`, `skip_days` (momentum signal)
- `retention_mult` (selection retention buffer)
- `quality_pct` (quality screen percentile threshold)
- `regime_pct`, `fii_threshold_cr` (regime gate thresholds)
- `n_positions` (target position count; 4-10 acceptable range)
- `rebalance_freq` (biweekly default; may propose weekly/monthly with full justification)

**Data the strategy may use:**
- Price OHLCV history (from `storage/prices.duckdb`)
- Macro regime classification (from `llm/features.py` → `macro_regime` for date)
- Per-ticker sentiment classification (from `llm/features.py` → `sentiment` for (ticker, date))
- Per-ticker events classification (from `llm/features.py` → `events` for (ticker, date))
- FII / DII flows (from `storage/macro.duckdb`)
- India VIX (from `storage/macro.duckdb`)
- Quality metrics (from `data/quality_screen.py` outputs)
- Sector classification (from `data/sectors.py`)

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

**Out of scope for this loop iteration:**
- Changes to `prepare.py` (immutable evaluator)
- Changes to data ingest, broker, executor (separate concerns)
- Changes to anti-overfit gates (separate, deliberate design changes)
- Adding new data sources (must go through human review)
