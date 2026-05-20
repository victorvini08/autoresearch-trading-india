# Strategy B — Long-only residual mean-reversion statistical arbitrage

**Date:** 2026-05-15
**Branch:** `mean-reversion-quant-strategy`
**Status:** Approved design → implementation

## 1. Intent & non-convergence guarantee

Strategy B is a **long-only short-horizon statistical-arbitrage book**:
cross-sectional residual mean-reversion on factor-neutralized returns — the
canonical systematic-quant swing strategy (Avellaneda–Lee lineage; Lo &
MacKinlay 1990; Lehmann 1990).

It is the **structural inverse** of branch A's momentum book
(`IndiaMomentumQualityRegime` on `main`): A buys winners (trend
continuation), B buys names oversold *relative to their factor exposures*
(reversion). The two autoresearch loops cannot converge because:

1. They rank on **opposite-signed signals** (cumulative residual return:
   A favours large positive past return, B favours large negative residual).
2. They run on **separate git branches** — independent `strategy.py`,
   `journal.md`, `iterations/log.csv`, and independent once-per-promotion
   sealed-test budgets. No shared-memory guardrail is required (user
   decision 2026-05-15).

`prepare.py:_find_strategy_class` requires **exactly one** `bt.Strategy`
subclass in `strategy.py`. Branch B therefore *replaces*
`IndiaMomentumQualityRegime` with `IndiaResidualReversalStatArb`; the two
are never co-resident, and **no backward-compat alias** is added (a second
module name bound to the same class breaks the single-subclass check).
Reusable module-level helpers (`resolve_active_universe`, the
`data.sectors` helpers) are kept — they are not `bt.Strategy` subclasses.

## 2. Signal construction (rolling market + size regression)

Computed **on rebalance bars only** (biweekly; mirrors A's early-return
gate), over the point-in-time active universe resolved by
`resolve_active_universe`:

- **Per-stock daily returns** `r_i,t` from feed closes:
  `close[-t]/close[-t-1] - 1`.
- **Market factor** `r_M,t` = equal-weight mean of `r_i,t` across the
  active-universe feeds (the "market mode"; PIT, self-contained, no Nifty
  feed dependency).
- **Size factor** `r_S,t` = SMB proxy. We have **no market cap**
  (`program.md` "NOT available"). Size is proxied by an **in-feed ADV**:
  `adv_i = mean(close*volume)` over the last 20 bars, computed inside the
  strategy from past bars only (PIT, no sidecar DB dependency). The active
  universe is split into ADV terciles **as of the rebalance bar**;
  `r_S,t = mean(r in small-ADV tercile) - mean(r in large-ADV tercile)`,
  with tercile membership frozen at the rebalance date.
- **Betas:** per stock, rolling OLS of `r_i` on `[r_M, r_S]` over
  `beta_window` bars → `β_M, β_S` (closed-form 2-regressor + intercept
  least squares; degenerate/insufficient-history stocks are skipped).
- **Reversion score:** cumulative residual over `formation_days`:
  `e_i = Σ_{last formation_days} (r_i,t − β_M·r_M,t − β_S·r_S,t)`.
  Score = **negative cross-sectional z-score** of `e_i`. The most-negative
  residual (most oversold vs its factor exposures) gets the highest score.
- **Entry gate:** only names in the **bottom `entry_pct`** of the residual
  distribution (most-oversold tail) are entry-eligible — suppresses
  weak-signal churn (analogous to A's top-decile gate).

## 3. Portfolio construction & constraints

Counted tunable signal params (int/float, per
`prepare.py:count_hyperparameters`, excluding `_PLUMBING_PARAMS`):

| Param            | Seed | Role |
|------------------|------|------|
| `beta_window`    | 60   | rolling OLS lookback for β estimation |
| `formation_days` | 5    | residual accumulation / reversion horizon |
| `retention_mult` | 2.0  | held name kept if still in top `retention_mult×n` by score — turnover/cost control |
| `entry_pct`      | 0.20 | residual-tail entry gate |
| `regime_pct`     | 95   | regime-gate threshold (structurally parallel to A) |
| `n_positions`    | 6    | target book size (range 4–10) |
| `sector_cap`     | 0.25 | hard SEBI/spec constraint |

**7 counted params — exactly A's parsimony footprint** (verified:
`test_gate_wiring.py` asserts A counts 7), so neither loop starts with a
parsimony-gate advantage. A's dead `fii_threshold_cr` knob (FII
unavailable) is **not** replicated; its slot is the genuinely-live
`entry_pct`.

Reused unchanged from A's contract:

- Biweekly cadence + week-parity plumbing (`rebalance_*` params, in
  `_PLUMBING_PARAMS`).
- `resolve_active_universe` (audit-2026-05-15 Fix B PIT guard).
- `enforce_sector_cap` (25% hard cap) from `data.sectors`.
- `macro_regime_for` label gate: block new entries on `risk_off`/`shock`,
  permissive fallback when the macro cache is `None`. Defensive gating
  matters **more** for reversion ("falling-knife" risk in trending
  crashes), so the gate is retained, not weakened.
- Trade contract: `self.order_target_percent` **only**, equal-weight,
  0.99 cash buffer, exits via `target=0.0`.

## 4. Coupled changes required for an end-to-end green branch

Replacing the strategy class ripples into strategy-coupled tests and the
loop's memory docs. All are in-scope for this branch:

- `tests/test_prepare.py` — `_find_strategy_class` name assertion →
  `"IndiaResidualReversalStatArb"`.
- `tests/test_gate_wiring.py` — import + `count_hyperparameters == 7`
  comment updated to the new param set (count stays 7).
- `tests/test_warmup_scoring.py` — import → new class; the multi-ticker
  oscillating synthetic feed still exercises entries/exits for reversion.
- `tests/test_engine.py` — import → new class; engine tests that need
  trades to occur get multi-ticker feeds (single-ticker feeds cannot
  produce a cross-sectional signal — an honest behavioural difference,
  not a regression).
- `tests/test_strategy_reversion.py` — **new**: unit tests for OLS beta
  recovery, market/SMB factor construction, residual-z ranking direction,
  rebalance gate, sector cap, regime block, and the
  `order_target_percent`-only trade contract.
- `program.md` — "Hyperparameters the loop may tune" + strategy-shape
  line + size-proxy data note rewritten for reversion. Invariants checked
  by `test_program_md.py` (Sortino, `strategy.py`, `prepare.py`, >1KB,
  immutability phrasing, `100%`/`50%`/`20 trades`/`10pp`/`Sortino`+`10`)
  are preserved.
- `journal.md` — Iter 0 seed entry rewritten for the reversion
  hypothesis/theory/params; parser hazard note and the
  hypothesis/change/result/learning keywords (asserted by
  `test_program_md.py`) preserved.
- `CLAUDE.md` — short branch banner noting this is the stat-arb parallel
  experiment; the locked-decisions table (which documents the *main*
  line's rationale) is left intact.

## 5. Honest risks (a seed that fails the gates is still informative)

1. **Long-only forfeits the short leg** → ~half the classic stat-arb
   alpha; the surviving long-reversion edge in Indian large-caps is
   thinner. May not clear the gates — an acceptable, informative seed
   outcome per CLAUDE.md ("a bad strategy that passes the gates is a
   learning data point").
2. **Cost fragility** — short-horizon reversion churns; DP ₹14.75/scrip/
   sell dominates at ₹50k. Mitigated structurally (biweekly cadence,
   `retention_mult` band, `entry_pct` gate); the cost-aware Sortino +
   anti-overfit gates exist to expose residual cost drag.
3. **Regime fragility** — reversion breaks in trending crashes; the
   defensive gate helps but the macro cache may be `None` early
   (permissive fallback), so the backtest can flatter live until the
   classifiers are precomputed.
4. **Size proxy is in-feed ADV, not market cap** (none available) —
   documented approximation; the loop may later refine (e.g. PCA factors)
   if it earns the param under the parsimony budget.

## 6. Verification bar

- `uv run pytest -q` green on the branch.
- `uv run python prepare.py research` runs end-to-end (walk-forward on
  synthetic prices for the first run) and returns a structured result
  with the new class.
- `prepare.py` is **byte-identical** to `main` (immutable evaluator —
  `git diff main -- prepare.py` empty).
