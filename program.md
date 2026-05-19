# Autoresearch program — Indian equities (REAL-WORLD branch)

> Branch `realworld-autoresearch`. Isolated experiment loop. Its sole
> purpose: find a **robust real-world improvement** to the committed
> momentum-quality + vol-targeted book — not a higher backtest number.
> Re-aimed objective + curated learnings vs the `production-strategy`
> program. The committed strategy here = `production-strategy` @ cd5592f.

**Goal:** evolve `strategy.py` into a swing strategy on the
top-200-by-ADV liquid NSE slice that earns positive risk-adjusted return
**after real Dhan delivery costs at realistic capital**, is **robust
across bull AND bear sub-periods**, and survives the sealed walk-forward
(2025-01 → 2026-05). The committed book already beats Nifty-500 on the
sealed test (+12.07% vs −1.94%, maxDD 11.3% < 14.8%, Sortino 0.72,
scale-robust at ₹5L). You are improving a *working, validated* book — the
bar is real-world robustness, not a marginal Sortino tick.

**You may edit `strategy.py` only.** `prepare.py` and
`backtest/anti_overfit.py` are the read-only evaluator + gate runner —
never edit them; changing the evaluator invalidates every comparison.

---

## The real-world objective (how to choose what to propose)

Mean validation Sortino is **reference only**. Judge a variant — and
choose what to even attempt — by *real-world robustness*, in priority:

1. **Worst disjoint sub-period** Sortino (bear-regime survival) — a high
   mean with one weak/flipped sub-period is a curve fit, not an edge.
2. **Drawdown** — does not regress; ideally shallower.
3. **Cost-after-DP at realistic scale.** Validate the *intent* at ≥₹5L,
   not ₹50k. ₹50k whole-share/concentration lumpiness routinely makes a
   variant look good then collapse at scale (a hard, repeated finding).
   The ₹14.75/scrip/sell DP charge is the dominant cost — turnover is
   expensive; a +Sortino that doubles turnover is usually net-negative.
4. **Regime-stationarity** — the edge must persist in bull *and* bear,
   not average out.
5. Only then: net Sortino > committed baseline.

A variant that improves mean Sortino but worsens worst-sub-period OR
drawdown OR cost-at-scale is a **REVERT**. This is the
robustness-over-validation-Sortino standard and it is non-negotiable.

---

## BURNED — do NOT re-propose (sealed/research-validated dead ends)

These were rigorously tested THIS campaign and rejected. Re-attempting
any is a wasted iteration — treat as settled, not as hypotheses:

- **PEAD asymmetric suppression** (block/sever entries on negative
  earnings surprise): sealed-validated NEGATIVE — strictly worse in all
  active folds, zero drawdown benefit. Redundant with the existing
  structural-exit / vol-target.
- **PEAD positive concentration tilt** (reorder selection by SUE sign):
  sealed-validated NEGATIVE — Sortino +0.06 but Calmar 0.79→0.50, maxDD
  +0.6pp, hit-rate 41%→23% (lumpy-luck signature).
- **Asymmetric trend gating** (slow exit / fast re-entry): passed gates
  but failed the scale arbiter (₹5L −8.94%). Not the binding weakness.
- **Weekly rebalance:** research-rejected — worst-sub −0.26, drawdown
  ~63% deeper, +25% turnover, FAILS the anti-overfit gates.
- **Equity shorting / any F&O:** structurally locked out (CNC-only,
  retail can't hold equity shorts overnight); not low-risk;
  momentum+short is the classic momentum-crash failure. Permanently out.
- **Per-ticker news as a return signal:** horizon mismatch — news is
  priced in hours, we rebalance biweekly; weaker/noisier than earnings,
  which already failed. Do not build a news alpha.
- **Constant-tweak revert streaks:** after 2–3 "no edge" reverts a
  family is exhausted — change the *thesis*, don't perturb knobs.

---

## Hard constraints (a violation wastes the whole iteration)

1. **Long-only, CNC delivery, NSE_EQ only.** No F&O, intraday, shorting, margin.
2. **Sizing via `self.order_target_percent` only.** Never `self.buy()`/`self.close()`.
3. **Trade only inside the injected point-in-time universe** (`universe_by_date`).
   Off-universe ticker = **hard reject** (survivorship/look-ahead).
4. **Bounded gross-targeting, never `gross / len(selected)`.** The
   committed `construct_gross_targets` deploys intended gross down the
   ranked list bounded by per-name ≤10% AND per-sector ≤25%. Naive
   `gross/len(selected)` (account-wipe risk) is banned.
5. **Sector cap 25%** at every rebalance.
6. **Output `new_strategy_py`** = complete literal `strategy.py` source: real
   newlines (no escaped `\n`/`\t`, no fences, no diff), valid Python
   (`ast.parse`d), same class name, `order_target_percent`-only contract.
7. **Imports whitelisted only:** `backtrader`, `numpy`, `pandas`, `datetime`,
   `data.*`, `llm.features`, `__future__`, safe stdlib (`math`, `logging`,
   `collections`, `itertools`, `functools`, `statistics`, `bisect`, `random`,
   `typing`, `dataclasses`, `re`, `json`). Any other import = instant reject.

---

## KEEP criteria — a variant is KEPT iff ALL hold

1. **Sortino (net of costs) > baseline AND > 0** (baseline = most recent
   KEPT under the current evaluator version). `|Sortino| < 10`.
2. **Aggregate drawdown** doesn't regress > 10pp vs prior KEPT.
3. **Catastrophe-clear:** gross < 100%, aggregate DD < 50%, ≥ 20 trades.
4. **Anti-overfit gates (atomic — fail one, rejected):** Bonferroni
   p < 0.10/N; random-walk MC Sortino ≥ 90th pct null; parsimony (each
   added hyperparameter ≥ +0.10 val Sortino; adding none ⇒ N/A);
   sub-period stationarity ratio ≥ 0.20 (a non-positive sub-period while
   others are positive FAILS).
5. **Sealed test** (2025-01 → 2026-05) Sortino > baseline AND > 0 —
   revealed **once per variant** at the human promotion gate; final.

Plus the real-world objective above governs *whether the keep is worth
keeping* — a gate-passing variant that worsens worst-sub/drawdown/
cost-at-scale is still a REVERT.

---

## Read the reject reason as a diagnosis (priors, not hypotheses)

- **Bonferroni p≈1.0 / low RW-MC pct** ⇒ the signal has **no edge**.
  Tuning a knob never recovers it — change the *thesis*.
- **Recurring 60–90% catastrophe DD** ⇒ structural to a concentrated
  long-only book; fix with construction (more names / vol-scaled sizing /
  defensive de-risking), never `len(selected)` sizing.
- **Low sub-period stationarity / sign-flipped sub-period** ⇒ regime-fit.
- **Revert streak of small tweaks** ⇒ propose something structurally
  different.

Walk-forward folds with a PIT universe < 50 names (pre-2022-07
data-starved era) are **skipped** by the evaluator — every score is on
the real ≥200-name universe.

---

## Parameters

You choose the signal/params; the parsimony gate counts hyperparameters
automatically. Two hard constraints:
- **Position count ≥ 15** (default 25, range 15–35).
- **Rebalance: biweekly (committed).** Weekly is BURNED (above); monthly
  allowed only if it clears the gates and the real-world objective.

## Data available — this is your search space

PIT accessors (most-recent value ≤ rebalance date; signals as-of-close,
orders fill next open — no look-ahead). Import from `llm.features` /
`data.*`:

- Price OHLCV (`storage/prices.duckdb`) — current to 2026-05-18.
- **Fundamentals / earnings surprise — NOW AVAILABLE** (pipeline fixed
  this campaign; NSE Integrated-Filing fetch repaired; current to
  2026-03; look-ahead tripwire passes). `data.pead.pead_signal(ticker,
  today, earnings_db=..., fundamentals_db=...)` → robust PIT SUE
  (Hampel/MAD-cleaned, ±8 clip) + quality-conditioned cut. **Caveat:**
  computable SUE only spans ~2024-04 → 2026-05 (2022+ NSE horizon +
  8-quarter seasonal burn-in) — ~2 years, growing each quarter. BOTH
  naive uses (suppression, concentration) are BURNED above. Only worth
  touching with a *genuinely novel, theory-grounded* formulation that
  respects the thin/growing sample — and expect the sub-period gate to
  punish a 2-year-only signal. Default stance: deprioritize until more
  history accrues.
- `macro_regime(date)` / `macro_signals(date)` (continuous: `india_vix`,
  `india_vix_pct_252d`, `nifty50_pct_vs_200dma`, `usd_inr_1w_change_pct`,
  `gdelt_*`). Prefer continuous over the 4-class label. `None` until
  macro cache precomputed.
- `sentiment/events/news_volume(ticker, date)` — available but per-ticker
  news as a *return* signal is BURNED (horizon mismatch). Only a rare
  adverse-event *veto* is even arguable, and it overlaps the
  already-failed suppression family — low priority.
- Sector classification (`data/sectors.py`).

**Do NOT depend on:** FII/DII flows (~1 row), repo/policy rate (frozen
2022-07).

## Out of scope for the loop

- Editing `prepare.py` / `backtest/anti_overfit.py` (immutable evaluator).
- Data ingest, broker, executor, new data sources (separate, human-reviewed).
- Shorting / F&O / weekly rebalance / the burned earnings overlays.
