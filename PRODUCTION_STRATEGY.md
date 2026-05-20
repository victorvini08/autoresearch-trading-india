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

---

## 6. Manual development log — 2026-05-17 (session 1)

Worst-regime-first manual phase. Anchor = the measured committed #2 base
(`prepare.py research`, evaluator `2026-05-16-univfloor`): `sub_period_
sortinos` **[2.819, 1.717]** (worst bucket **1.717**), worst fold **−2.069**,
agg_dd **5.17%**, mean 2.480, all anti-overfit gates pass. Acceptance test
applied throughout (per STRATEGY_DEVELOPMENT_PLAN §HOW TO VALIDATE, **not**
the loop's mean-first rule): a change is kept **only if** the worst
sub-period does not degrade/sign-flip **and** every statistical gate passes
**and** drawdown stays controlled **and** gross ≤ 100% — mean Sortino is a
reference, never the objective. `promotion` never run; sealed set untouched.

| # | Commit | Change | Verdict |
|---|---|---|---|
| 1 | `9bc8b2c` | Remove dead `regime_pct` param (declared + parsimony-counted but never read; verified repo-wide) | **KEPT** — provably behaviour-neutral (per-fold/sub-period byte-identical); honest parsimony 7→6 |
| — | _(reverted)_ | Vol-distance trailing stop (`stop_vol_mult`·σ_dn band) | **REVERTED** — anti-momentum whipsaw: turnover 0.11→0.44, worst bucket 1.72→0.75, universe hard-reject. Learning: a price-distance band amputates momentum's right tail; the exit must be a **trend-state** break, not a distance band |
| 2 | `e745434` | **Symmetric structural trend exit**: sell a held name on any non-rebalance bar once close falls below the SAME `beta_window`-derived structural MA the entry requires it to be above (shared `_structural_ma_window`; **0 new params**) | **KEPT** — worst bucket **byte-identical** [3.029, **1.717**], worst fold −2.069 unchanged, agg_dd 5.18% & turnover 0.111 flat, only 3/13 folds changed (fires rarely), all gates pass. Installs the forward bear/transition defence the base structurally lacked (was calendar luck) |
| — | _(reverted)_ | Unbounded "let winners run" retention (retain all still-qualifying incumbents; retire `retention_mult`) | **REVERTED** — degrades worst bucket 1.7172→1.7107 **and** bucket-0 3.03→2.54 / mean 2.63→2.28 (a ~15-20 % haircut to the strong-regime right-tail edge) to buy −31 % turnover. Sound principle, over-corrected implementation; the binding rule forbids trading worst-regime/right-tail for cost |

**State after session:** HEAD `e745434`. Honest 6-param base + a genuine,
gate-clean, zero-cost, theory-grounded (Asness/Novy-Marx trend filter on
momentum) forward bear/transition defence; worst sub-period preserved exactly.

**Why the session stopped here (not a premature halt):** the
structurally-sound, evidence-supported lever was captured (#2). The remaining
plan leads are exhausted or contraindicated: adding cross-sectional ranks is
the proven over-fit path (journal #3→#4); binary **and** continuous macro
gross gates degrade the in-sample worst bucket (both in-sample sub-periods
are bull — any de-risk depresses them) and #2 already gives *emergent*
de-risking without a gate; refining the just-reverted retention idea is the
"wasted compute" program.md warns against. Pushing further would chase the
backtest number — the exact failure this whole effort exists to avoid.

**Honest limitation & recommendation:** both in-session sub-periods are
bull/neutral, so `research` **cannot certify** real-bear behaviour — only
that #2's defence is non-destructive, gate-clean and theory-sound. The real
arbiter remains forward `dhan-paper` validation (roadmap #4). Recommend:
promote `e745434` to forward paper; do **not** chase further `research`
gains.

### 6.1 Sealed reveal — 2026-05-17 (explicit human authorization)

The user (the designated promotion authority), after being shown the full
irreversibility/contamination warning and the safe alternative, **explicitly
authorized one `prepare.py promotion` run on `e745434`**. Recorded here for
provenance; `iterations/sealed_reveals.csv` was NOT written (prepare.py's
promotion path does not call `record_sealed_reveal` — only the loop's
`sealed_test_gate` does).

Sealed 2025-01→2026-05 result (`e745434`): **Sortino 1.000**, Calmar 0.913,
**maxDD 4.38%**, hit-rate 0.458, **24 trades**. Documented #2 foundation on
the same window (§3): Sortino 0.746, maxDD 4.66%, 22 trades. So the symmetric
structural exit improved the (already-burned) OOS Sortino 0.75→1.00 and cut
OOS maxDD 4.66%→4.38% while validation moved only 2.48→2.63 — the **opposite
of the #4 over-fit signature**, mild positive triangulation that the change
is directionally real.

**This does not certify anything.** The number is upward-biased (window
peeked 24+×, foundation selected on it), n=24 is thin, and it changes no
recommendation. **The 2025-01→2026-05 window's contamination is now total
and final** — it must NEVER again be run or used as a signal for any
derivative of this strategy. Forward `dhan-paper` remains the only arbiter;
no future change will be tuned against this number.
