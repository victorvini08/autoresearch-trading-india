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
