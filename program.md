# Autoresearch program — Indian equities

**Goal:** evolve `strategy.py` into a swing-trading strategy on the
top-200-by-ADV liquid NSE slice that earns positive risk-adjusted return
**after Dhan delivery costs** and survives a sealed walk-forward test on
2025-01 → 2026-05 data.

**You may edit `strategy.py` only.** `prepare.py` and
`backtest/anti_overfit.py` are the read-only evaluator + gate runner — never
edit them; changing the evaluator invalidates every prior comparison.

---

## Hard constraints (a violation wastes the whole iteration)

1. **Long-only, CNC delivery, NSE_EQ only.** No F&O, intraday, shorting, margin.
2. **Sizing via `self.order_target_percent` only.** Never `self.buy()`/`self.close()`.
3. **Trade only inside the injected point-in-time universe** (`universe_by_date`).
   Trading any off-universe ticker is a **hard reject** (survivorship/look-ahead).
4. **Fixed risk slots, not selected-count sizing.** Size on `n_positions`
   (`gross / n_positions`), so filtered/blocked/empty slots stay **cash**.
   `gross / len(selected)` concentrates capital and repeatedly caused >100%
   gross or account-wipe drawdown — it is banned.
5. **Sector cap 25%** at every rebalance.
6. **Output `new_strategy_py`** = complete literal `strategy.py` source: real
   newlines (no escaped `\n`/`\t`, no markdown fences, no diff), valid Python
   (`ast.parse`d), same class name, `order_target_percent`-only contract.
7. **Imports whitelisted only:** `backtrader`, `numpy`, `pandas`, `datetime`,
   `data.*`, `llm.features`, `__future__`, and safe stdlib (`math`, `logging`,
   `collections`, `itertools`, `functools`, `statistics`, `bisect`, `random`,
   `typing`, `dataclasses`, `re`, `json`). Any other import = instant reject.

---

## KEEP criteria — a variant is KEPT iff ALL hold

1. **Sortino (net of costs) > baseline AND > 0**, where *baseline* is the most
   recent KEPT iteration **under the current evaluator version**. A changed
   evaluator re-anchors: the first iteration then has no baseline and only
   needs to clear the gates below. `|Sortino| < 10` (else numerical artifact).
2. **Aggregate drawdown** doesn't regress > 10pp (10 percentage points) vs
   the prior KEPT.
3. **Catastrophe-clear:** gross < 100%, aggregate DD < 50%, ≥ 20 trades.
4. **Anti-overfit gates (atomic — fail one, rejected):**
   - **Bonferroni:** validation-Sortino p < 0.10 / N (N = variants tested
     since the last KEPT, capped at 10).
   - **Random-walk Monte-Carlo:** Sortino ≥ 90th pct of the no-edge null.
   - **Parsimony:** each hyperparameter *added beyond the current committed
     strategy* must add ≥ 0.10 validation Sortino. **Adding no parameters ⇒
     parsimony does not apply** — strict improvement is criterion 1's job, not
     parsimony's (they are no longer double-counted).
   - **Sub-period stationarity:** signed min/max Sortino ratio across disjoint
     18-month sub-periods ≥ 0.20. A non-positive sub-period while others are
     positive (a regime sign-flip) fails — the edge must persist, not merely
     average out.
5. **Sealed test** (2025-01 → 2026-05) Sortino > baseline AND > 0 — revealed
   **once per variant** at the human promotion gate; failure is final.

Else: REVERT.

---

## Read the reject reason as a diagnosis

- **Bonferroni p≈1.0 / low RW-MC percentile** ⇒ the signal has **no edge**
  (return ordering no better than noise). Change the *thesis*, not a knob.
- **Recurring 60–90% catastrophe drawdown** ⇒ **structural** to a concentrated
  long-only book. Fix with construction (more names, vol-scaled sizing,
  defensive de-risking), not signal tweaks.
- **Low sub-period stationarity / a sign-flipped sub-period** ⇒ regime-fit,
  not an edge. Seek a thesis robust across bull and bear sub-periods.
- If the last few reverts all say "no edge", the signal family is exhausted —
  propose something **structurally different**, don't refine it.

Note: walk-forward folds whose point-in-time universe is below 50 names are
**skipped** by the evaluator (the pre-2022-07 data-starved era). Every score
you see is on the real ≥200-name universe — don't reason about that early gap.

---

## Parameterization is yours to design

There is no prescribed list of knobs to tune. Invent whatever signal,
parameters, and structure you can justify from the data below — the
parsimony gate counts hyperparameters dynamically and polices added
complexity, so you are free to add, remove, or rethink parameters entirely.
Don't merely perturb the current strategy's constants; if the reject reasons
say "no edge", change the *thesis*, not a number.

Two parameter facts are **constraints, not tuning suggestions**:
- **Position count ≥ ~15** (default 25, sane range 15–35). Fewer concentrates
  the book and structurally trips the catastrophe drawdown gate —
  diversification is signal-agnostic.
- **Biweekly rebalance is the default cadence.** Weekly/monthly is allowed but
  must clear the gates and be justified (DP charge ₹14.75/scrip/sell is a real
  cost at this capital).

## Data available — this is your search space

All accessors are point-in-time (most-recent value ≤ rebalance date; signals
as-of-close, orders fill next open — no look-ahead). Import from `llm.features`:

- Price OHLCV (`storage/prices.duckdb`)
- `macro_regime(date)` → `'risk_on'|'neutral'|'risk_off'|'shock'|None`
  (4-class; `None` until macro cache precomputed)
- `macro_signals(date)` → numeric dict (absent keys omitted, never zero-filled):
  `india_vix`, `india_vix_pct_252d`, `nifty50_close`, `nifty50_200dma`,
  `nifty50_pct_vs_200dma`, `usd_inr`, `usd_inr_1w_change_pct`,
  `gdelt_tone_mean`, `gdelt_tone_negfrac`, `gdelt_epu_policy`,
  `gdelt_centralbank`, `gdelt_tariff_trade`, `gdelt_inflation`.
  Scalars: `india_vix_percentile(date)` (0..1), `nifty_vs_200dma_pct(date)`.
  Prefer these continuous signals over the 4-class label.
- `sentiment(ticker, date)`, `events(ticker, date)`, `news_volume(ticker, date)`
  (`None`/default until caches precomputed)
- Sector classification (`data/sectors.py`)

**Do NOT depend on:** FII/DII flows (~1 row), repo/policy rate (stale, frozen
2022-07), fundamentals/ROE/D-E (no ingest yet).

## Out of scope for the loop

- Editing `prepare.py` / `backtest/anti_overfit.py` (immutable evaluator)
- Data ingest, broker, executor, new data sources (separate, human-reviewed)
