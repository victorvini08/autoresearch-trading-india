# Production strategy — foundation for manual development

**Selected: momentum-quality carry, checkpoint `2026-05-17-a05b891`**
(source commit `a03660124f`, from the branch *misnamed* `mean-reversion-quant-strategy`).

This document is the authoritative record of WHY this is the chosen
foundation, the evidence, and the honest caveats. Read it before touching
`strategy.py`.

---

## 1. What this strategy actually is (read carefully)

Despite the source branch name and the class name `IndiaResidualReversalStatArb`,
**this is NOT a mean-reversion strategy.** Its own docstring:

> *"Strategy B — long-only cross-sectional momentum-quality carry … deliberately
> changes the entry thesis away from residual falling-knife reversion: owns
> liquid NSE names with persistent 12-1 relative strength, smooth downside
> behaviour, segment-level trend consistency, and limited drawdown, diversified
> with fixed risk slots and a whole-book sector cap."*

The autoresearch loop on that branch abandoned mean-reversion by its **first**
KEPT and ran momentum-quality for the entire campaign. All 4 KEPTs are this
same thesis. **There is no working mean-reversion strategy in any of the three
campaigns.** (Cleanup task #1 below: rename the class to stop the lie.)

Thesis in one line: **long-only top-200-by-ADV NSE names with persistent
12-1 / mid-horizon relative strength AND quality/defensive overlays (low
downside vol, limited drawdown, proximity to trailing high, beta-adjusted
"residual" strength), diversified, sector-capped, biweekly.**

## 2. Why this one — reasoning grounded in Indian equities

- **Empirics:** of three structurally-distinct campaigns it is the *only*
  OOS-positive, regime-robust lineage. Pure/aggressive momentum
  (`momentum-rotation`, 289 iters) overfit catastrophically — all 20 KEPTs
  lose OOS (−3% to −15%). 12-1 momentum+quality+regime (`momentum-aryan`)
  generalised to ≈cash (no edge). Momentum-quality carry: **OOS-positive at
  every checkpoint and it sidestepped the −14% 2026-Q1 crash** (lost 0.0–0.6%
  that quarter vs Nifty 500 −14%).
- **Theory:** India has a strong long-run momentum premium but severe momentum
  *crash* risk; quality / low-volatility are independently robust Indian
  anomalies. Momentum **conditioned on quality/low-downside** is the textbook
  way to keep the premium while cutting the crash — and the OOS crash-resilience
  here is exactly that effect, not a fluke.
- **Practical fit (₹50k, Dhan costs):** momentum-quality is comparatively
  *low-turnover* (persistent signal, longer holds) → tolerable ₹14.75/scrip DP
  drag — a real advantage over any high-churn (reversal) book at this capital.
- **Right complexity for a foundation:** checkpoint #2 is near-minimal — it
  adds only "segment-level trend consistency" over #1. It avoids the
  overfitting tail: #3 (+6.5% OOS) is selection-biased and adds a residual-mom
  factor; #4 (+3.1% OOS) adds volume-confirmation and *degraded* OOS while
  validation kept rising — the classic over-optimisation signature. #2 has the
  best OOS risk/return of the low-complexity versions and the lowest OOS
  drawdown (4.66%). A clean, simple, coherent base is what you can reason about.

## 3. Evidence (validation vs sealed out-of-sample 2025-01 → 2026-05)

| | Validation Sortino | OOS Sortino | OOS return | OOS maxDD | OOS trades |
|---|--:|--:|--:|--:|--:|
| **#2 (this)** | 2.480 | **+0.746** | **+5.36%** | 4.66% | 22 |
| #1 simplest | 2.055 | +0.581 | +4.02% | 5.95% | 20 |
| #3 (biased) | 2.925 | +0.966 | +6.50% | 5.73% | 20 |
| #4 final | 3.117 | +0.712 | +3.11% | 4.12% | 19 |
| Nifty 500 (benchmark) | — | — | +0.01% | ≈−18% | — |

OOS per-quarter (#2): 2025 Q1 −0.56% · Q2 +2.22% · Q3 −1.54% · Q4 +4.13% ·
2026 Q1 −0.02% (vs index −14%) · Q2 +1.11%.

## 4. Honest caveats — do NOT treat this as a proven edge

1. **Modest magnitude.** ≈+5%/16mo, OOS Sortino ≈0.75, ~22 trades — a
   *plausible* edge, statistically thin (n≈22). Not proven.
2. **Selection bias / burned holdout.** This was chosen after testing 24+
   checkpoints against the 2025-01→2026-05 set. That window is now CONSUMED —
   it can never again be an honest OOS measure for any derivative of these
   strategies. The +5.36% is an upward-biased estimate.
3. **The only honest test left is FORWARD paper validation** (CLAUDE.md's
   4-week `dhan-paper` gate). No more historical backtesting as "proof".
4. **Hidden complexity:** reports 7 tunable params but embeds many hard-coded
   windows/thresholds (factor lookbacks, the `long_mom>0 & mid_mom>0 & price>MA`
   filter). True complexity > 7; the parsimony gate never saw it.
5. **Provenance:** source branch history has commits from `aryan-socratic`
   (company account — forbidden per repo rule), `inosritika`, `Nishantgoyal918`.
   This branch's NEW commits are clean (`victorvini08`).

## 5. Optimisation roadmap (the manual phase)

1. **Rename `IndiaResidualReversalStatArb` → an honest name** (e.g.
   `IndiaMomentumQualityCarry`) and document every hard-coded window as an
   explicit, named parameter so complexity is visible.
2. **Turnover / cost audit at ₹50k** — quantify DP+STT drag per rebalance;
   test 3–4 week cadence vs biweekly for net-of-cost improvement.
3. **Regime gate review** — make the crash-resilience explicit and robust
   (India VIX percentile + Nifty 200-DMA), not incidental.
4. **Forward paper validation** before any live capital.
5. Only THEN parameter work — on a clean, renamed, fully-parameterised base.

`strategy.py` here is byte-identical to checkpoint #2 so the OOS numbers above
remain reproducible. Make changes deliberately, one at a time, from this base.
