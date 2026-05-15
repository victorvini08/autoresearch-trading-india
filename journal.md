# Autoresearch journal — Indian equities (branch: mean-reversion-quant-strategy)

This is the autoresearch loop's persistent memory for the **residual
mean-reversion stat-arb** parallel experiment. Every iteration appends an
entry with hypothesis, change, result, and decision (KEEP / REVERT).
Entries compound across runs and inform future proposals.

This branch is intentionally isolated from `main`'s momentum lineage: its
journal starts fresh so the reversion loop is not biased by burned
momentum ideas (and vice-versa). The two experiments are compared as
separate lineages.

**Parser hazard:** the KEEP/REVERT parser in `scripts/loop.py` matches the literal line `**Decision:** KEPT` (not substring). Preserve the exact format.

---

## Iter 0 — Baseline (2026-05-15)

**Hypothesis:** A sparse, theory-backed long-only cross-sectional residual mean-reversion strategy — buying names oversold relative to their market + size factor exposures, with a retention buffer, sector cap, and Indian-context regime gate — will produce a positive Sortino on the train+val window (2018-01 to 2023-12) on the top-200-by-ADV liquid slice, after Dhan delivery costs. It is the structural inverse of the momentum book on `main`, so the two autoresearch loops cannot converge.

**Theoretical basis:**
- Short-horizon cross-sectional reversal / statistical arbitrage: Lehmann 1990; Lo & MacKinlay 1990; Avellaneda & Lee 2010 (factor-residual reversion)
- Factor neutralization (market + size) before scoring residuals: standard stat-arb desk construction (residual = idiosyncratic, mean-reverting component)
- Size proxied by ADV (no market cap available; Amihud 2002 illiquidity/size linkage)
- Equal-weight sizing: DeMiguel, Garlappi, Uppal 2009
- Regime-gated entries: reversion suffers "falling-knife" failure in trending crashes — defensive gating is more important here than for momentum

**Change:** N/A — this is the seed strategy. See `strategy.py` (`IndiaResidualReversalStatArb`) for the implementation.

**Hyperparameters (7 counted signal knobs):**
- `beta_window = 60`, `formation_days = 5`
- `retention_mult = 2.0`
- `entry_pct = 0.20`
- `regime_pct = 95`
- `n_positions = 6`
- `sector_cap = 0.25`

**Result:** Pending first walk-forward run.

**Learning:** (to be filled by the first iteration after walk-forward results land) — does the long-only residual-reversion edge survive Dhan DP costs at biweekly cadence? Is the cross-sectional market factor informative on real data (vs the near-degenerate synthetic case), and how often does the regime gate block entries during the 2024-Q4 / 2026-Q1 drawdowns?

**Decision:** PENDING

---

(future iteration entries will be appended below this line by `scripts/loop.py`)
