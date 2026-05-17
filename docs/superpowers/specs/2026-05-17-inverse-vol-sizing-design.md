# Improvement B — Inverse-vol risk-parity sizing within fixed gross

Roadmap item **B**. Designed after the A-family (gross vol-scaling) was
found structurally exhausted (learnings.md §3.5): on a long-only
right-tail momentum book, **reducing gross clips the melt-up folds**. B's
defining constraint, therefore: **never change aggregate gross** — only
re-distribute *within* the fully-invested book.

## 1. Problem (roadmap §3.2)

`next()` sizes every selected name at `target_each = gross / n_positions`
(equal weight). Equal slots ignore per-name risk ⇒ high-vol names inject
excess downside variance ⇒ depresses Sortino (= mean / downside-deviation)
even though the signal is fine.

## 2. Mechanism (aggregate-preserving, zero new counted knobs)

Tilt the equal slot by each name's inverse realized vol, **mean-1 over the
selected set** so the aggregate is identical to equal-weight:

1. `vol_i` = std of name *i*'s last `formation_days` simple returns (reuse
   the closes already loaded in `next()`; `formation_days` is an existing
   param — no new horizon knob). Floor `vol_i` at a tiny eps (no div0).
2. `raw_i = 1 / vol_i`; `tilt_i = raw_i / mean_{j∈selected}(raw_j)`.
3. `tilt_i = clip(tilt_i, 0.5, 2.0)` — the textbook risk-parity
   "0.5×–2× equal weight" concentration guardrail; one structural
   convention, pre-committed, **not** searched against any window, **not**
   a `params` entry.
4. Renormalise: `scale = len(selected) / Σ clipped_tilt`;
   `tilt_i ← clipped_i * scale` ⇒ `Σ tilt_i = len(selected)` **exactly**.
5. `target_i = target_each * tilt_i`.

Consequences, by construction:
- `Σ_{i∈selected} target_i = target_each * len(selected)` — **identical**
  to equal-weight. Unfilled slots `(n_positions − len(selected)) *
  target_each` stay cash. The §4 fixed-slot invariant holds **exactly**;
  gross is **unchanged** ⇒ B cannot clip the right tail like A did
  (verified by the mean-1 aggregate invariant, unit-tested).
- All-equal vols ⇒ all `tilt_i = 1` ⇒ B reduces to today's equal-weight
  (a strict generalisation; no behaviour change when risk is uniform).
- Lower-vol names up-weighted, higher-vol down-weighted ⇒ lower portfolio
  downside deviation with ~unchanged mean ⇒ mechanically targets higher
  Sortino, and removes the §3.2 "equal slots ignore per-name risk"
  excess downside variance.

## 3. Hard-constraint reconciliation (strategy.py only)

`enforce_sector_cap` selects *which* names using the equal-weight scalar —
**left unchanged** (selection, and the 25% cap's binding behaviour during
selection, are byte-identical to baseline ⇒ no burned-behaviour risk). But
a bounded up-tilt can push a near-cap sector's *actual* weight over 25%
(≤ 2×), violating hard constraint §5. program.md mandates strategy.py-only
edits (cannot touch `data/sectors.py`), so add an inline pure helper
`apply_sector_cap(targets, sector_of, cap)`: walk `selected` in priority
order, accumulate per-sector actual `target_i`; if a name would breach the
sector cap, reduce that name to the remaining room (≥0). **Excess stays
cash — never redistributed** (§4-safe; the banned concentration mode is
exactly "redistribute freed budget into fewer names"). Guarantees §5 on
real weights.

## 4. Surface & contract

`strategy.py` only. Two pure helpers (TDD'd in isolation):
`inverse_vol_tilt(selected, vol_by_ticker) -> {ticker: tilt}` and
`apply_sector_cap(targets, sector_of, cap) -> {ticker: target}`. `next()`:
compute per-name vol from loaded closes → tilt → per-name targets → sector
clamp → `order_target_percent(d, target=target_i)` for selected,
`target=0.0` for held-not-selected. Unchanged: class name
`IndiaMomentumQualityCarry`, `order_target_percent`-only, PIT handling,
biweekly cadence, `breadth_scaled_gross` (gross source untouched —
deliberately, per the A-learning), structural exit, the 6 counted
hyperparameters (parsimony N/A). Not a rank factor / gross gate / trailing
stop ⇒ distinct from every burned §6 trap (pure sizing, signal unchanged).

## 5. Validation (program.md KEEP + roadmap §7)

Baseline anchor (reproduced exactly): validation **2.6255**, sub-periods
**[3.029, 1.717]**, worst fold **−2.069**, agg_dd **5.18%**, all gates
pass. `prepare.py research` only (never `promotion`). KEEP iff ALL:
validation Sortino > 2.6255 & > 0 & |S|<10; **worst sub-period not
degraded vs 1.717, no sign-flip** (primary robustness bar — roadmap
§1/§7); agg_dd not regressing >10pp vs 5.18%; gross ≤100%; ≥20 trades;
all anti-overfit gates pass. Else REVERT decisively, journal, and (B being
roadmap's last high-EV "very-low-overfit" lever) report the final state.
Commit as victorvini08 on `production-strategy` only on KEEP.

## 6. Failure modes

- Selected momentum-quality names already share similar (screened-low)
  downside vol ⇒ tilts ≈ 1 ⇒ B ≈ inert ⇒ Sortino ≈ baseline ⇒ honest
  REVERT (no strict lift). Acceptable, logged.
- Sector clamp frequently binding ⇒ persistent cash drag ⇒ shows up as
  lower return/Sortino ⇒ REVERT (the clamp is correctness, not tuned).
- vol floor too low ⇒ a near-zero-vol name hoarding weight: prevented by
  the [0.5, 2.0] tilt clip (hard per-name bound regardless of vol floor).
