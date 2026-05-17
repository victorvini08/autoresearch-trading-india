# Improvement C — Residual momentum as the PRIMARY signal

Roadmap item **C**, on the kept **B** baseline. Targets the structural
weakness the (now-burned) sealed test *diagnosed*: every total-return
momentum variant collapsed 2.6→0.3-1.0 OOS because 2025-26 contains a
momentum-hostile factor reversal (Jan-26→Mar-26). Developed in research
mode only — the sealed window is a diagnosis, NOT a tuning target.

## 1. Thesis

Total-return 12-1 momentum carries time-varying market/size beta; in a
sharp factor reversal those betas make it crash (the OOS failure).
**Residual (idiosyncratic) momentum** (Blitz–Huij–Martens 2011): rank by
the stock-specific return after stripping market + size factors. Evidence:
~2× the risk-adjusted performance of total-return momentum AND materially
crash-robust OOS, precisely because the factor-beta crash channel is
removed. This is a *thesis replacement*, not a tuning knob, and directly
attacks the diagnosed failure. `learnings.md §3.3` ("quality beats
momentum in corrections") is the same signal.

## 2. Mechanism (replace the total-return core; 0 new hyperparameters)

In `momentum_quality_scores`, replace the total-return `long_mom`/`mid_mom`
core with one residual-momentum signal, reusing the EXISTING, unit-tested
factor helpers (`market_factor`, `smb_factor`, `ols_beta` — the same OLS
machinery `reversion_scores` already uses, without its reversion sign
flip):

1. `returns_by_ticker` from the PIT-filtered `close_by_ticker` (already
   restricted to the active universe upstream by `_close_and_adv` ⇒ factors
   are PIT-safe; this is what prior reverted residual attempts got wrong —
   they reintroduced survivorship/look-ahead and failed `universe_respect`).
2. `mkt = market_factor(returns_by_ticker)`, `smb = smb_factor(...)` over
   the lookback window (equal-length per name).
3. Per name: `a,b_m,b_s = ols_beta(r, [mkt, smb])`;
   `resid = r − (a + b_m·mkt + b_s·smb)`.
4. **Residual momentum** = Σ `resid` over the formation window EXCLUDING
   the last `skip` days (the 12-1 convention: skip the recent month to
   avoid short-term reversal) = `sum(resid[: lookback − skip])`.
5. Entry filter: `resid_mom > 0 AND now ≥ structural_MA` (replaces
   `long_mom>0 AND mid_mom>0`; the structural-MA filter — twin of the
   structural exit — is kept, it is robust and regime-defensive).
6. Score = `resid_mom_rank + high_proximity_rank + (−)max_dd_rank +
   (−)downside_vol_rank + trend_consistency_rank + 0.25·adv_rank`
   (the quality ranks are unchanged; only the momentum core swaps total
   → residual; one primary momentum rank replaces the two total-return
   ranks).

Unchanged: B inverse-vol sizing + sector clamp, structural exit, biweekly
cadence, PIT handling, `order_target_percent`-only, class name, the 6
counted hyperparameters (residual momentum reuses `beta_window` /
`formation_days`; the 2-factor set is structural, not tunable) ⇒ parsimony
N/A.

## 3. Distinctness from burned traps (§6 / journal)

Roadmap §6 explicitly sanctions "residual momentum as PRIMARY signal
(replace total-return; *not an added rank — burned*)". The journal's
reverted residual attempts were all **added ranks** on top of total-return
(162f9a8, 67a3f8f, 09f1a54, 9e7ef59…) or had `universe_respect` bugs.
C **replaces** the primary signal and builds factors only from the
PIT-active set ⇒ structurally different and PIT-safe. Not a gross gate
(A-family), not a trailing stop.

## 4. Validation (research mode only)

`prepare.py research`. Judge on the corrected **robustness** criterion
(memory feedback_robustness_over_validation_sortino): all anti-overfit
gates pass (atomic) → then fewest negative folds, lowest aggregate
drawdown, worst sub-period positive with no sign-flip, regime balance —
PLUS the structural crash-robustness rationale. Mean Sortino reference
only. The sealed window is NOT consulted during development. Compare
{B, C} on research robustness + theory; pick the single best; KEEP/REVERT
decisively; journal + commit as victorvini08. One final sealed reveal on
the single best final variant only (one-shot integrity check, not a
selection criterion).

## 5. Failure modes

- Residual momentum on ~200 names with a 2-factor model may be noisy ⇒
  weak/no research edge ⇒ honest REVERT to B, logged.
- If `ols_beta` returns None for many names (short history) they are
  skipped (as today) ⇒ ensure ≥ a few names remain or the fold scores
  inert (the existing `len(rows) < 2 ⇒ {}` guard handles this).
- Must keep `universe_respect` green (factors from PIT closes only).
