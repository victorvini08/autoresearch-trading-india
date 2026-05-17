# Robust Indian-equity strategy — roadmap & next-session brief

Brainstorm output, 2026-05-17. A vetted *menu* + mission to bootstrap a
fresh session. Read `PRODUCTION_STRATEGY.md` and
`STRATEGY_DEVELOPMENT_PLAN.md` first.

## 1. Mission

Build an optimal, robust **long-only NSE CNC** strategy on the top-200-ADV
PIT universe, **₹50k net of Dhan costs**, that is good in **bull, bear, AND
neutral** regimes:

- Robust judged on the **worst** regime sub-period, never the average; no
  sign-flip across regimes.
- Ride bull upside (don't truncate momentum's right tail); limit bear
  drawdown (graceful de-risk); keep aggregate drawdown controlled.
- Beat buy-and-hold Nifty 500 risk-adjusted over a full cycle.
- Cash-only: gross ≤ 100%, no leverage, long-only.
- **Forward `dhan-paper` is the only arbiter** — all historical windows are
  burned. Non-goal: maximising backtest Sortino (that caused a 3.8→−8%
  blow-up).

## 2. Current baseline

`production-strategy`, strategy code = `e745434`, class
`IndiaMomentumQualityCarry`: long-only, biweekly, equal fixed-slot
(`gross/n_positions`), 7 equal-weight percentile ranks behind mom>0 &
price≥~190-DMA filters, 25% sector cap, step-function gross, **+ symmetric
structural exit** (sell below the entry's own structural MA). 6 honest
hyperparameters.

- `research`: validation 2.626, `sub_period_sortinos` [3.029, **1.717**],
  worst fold −2.069, agg_dd 5.18%, all gates pass.
- Sealed 2025-01→2026-05 (revealed once, human-authorized): **Sortino 1.00,
  maxDD 4.38%, 24 trades** vs #2 foundation 0.75 / 4.66% / 22.
- The loop never trained on the sealed window (research-mode only), so the
  structural exit's 0.75→1.00 OOS gain is a *clean* result — but it's now
  seen (one window, n=24): legitimate, not "proven". Forward decides.

## 3. Structural gaps

1. **No volatility scaling of exposure** — crash risk is predictable from
   momentum's own variance; our gross proxy is a crude step function.
2. **Equal slots ignore per-name risk** → excess downside variance.
3. **Liquid momentum is India's weak leg** (~8.5% vs ~19% illiquid, below
   Nifty); low-vol/quality are the robust Indian factors but blended at
   arbitrary equal weight with total-return momentum.
4. **DP cost ~2–4%/yr at ₹50k** suppresses NET return (signal-independent).

## 4. Evidence

- Vol-scaled momentum (Barroso–Santa-Clara; Daniel–Moskowitz): scaling to
  momentum's variance "virtually eliminated crashes, ~2× Sharpe" — but only
  **conditional** vol-targeting works on long-only equity (naive backfires).
- Residual/idiosyncratic momentum (Blitz–Huij–Martens): ~2× risk-adjusted
  vs total-return, crash-avoiding, robust OOS.
- India: low-vol = most robust anomaly; quality+low-vol lead; multi-factor
  beats cap-weight long-horizon.

Sources: [Barroso–Santa-Clara](https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002566)
· [Daniel–Moskowitz](https://alphaarchitect.com/risk-of-momentum-crashes/)
· [Blitz–Huij–Martens](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2319883)
· [NSE multi-factor](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
· [India low-vol](https://backtestindia.com/blog/low-volatility-anomaly-india-nse-backtest)
· [Conditional vol-targeting (Man)](https://www.man.com/insights/the-impact-of-volatility-targeting)

## 5. Improvement menu (do now; news/data-eng deferred)

| # | Improvement | Evidence | EV / overfit | Effort |
|---|---|---|---|---|
| **A** ⭐ | **Conditional volatility scaling of gross** (replace step-function with realized-vol scaling, de-risk only in elevated-vol states) | Barroso–Santa-Clara; Daniel–Moskowitz | Highest EV; **low** overfit (replaces hidden knobs) | Med |
| **B** | **Inverse-vol / risk-parity sizing** within fixed gross (Σw=gross) | Vol-parity | High; **very low** overfit (no signal change) | Low–Med |
| **C** | **Residual momentum as PRIMARY signal** (replace total-return; not an added rank — burned). Factor machinery already in `strategy.py` | Blitz–Huij–Martens | High ceiling; invasive | Med–High |
| **D** | **Tilt fixed blend → Indian low-vol/quality** (theory-pinned, not tunable) | NSE/India low-vol | Medium | Low |
| **E** | **Cost/turnover/hold-period efficiency** (count, cadence, STCG→LTCG) | Mechanical | Bounded; **~zero** overfit | Low–Med |

**Sequence (one at a time, forward-validate each): A → B → (C) → D/E.**
A first: most-validated crash defense, targets the bear/worst-regime goal,
parsimony-neutral, distinct from everything burned.

## 6. Burned — do NOT retry

More cross-sectional rank factors (over-fit path #3→#4); binary macro/regime
gross gates (degraded worst bucket); price-distance trailing stops
(anti-momentum whipsaw); unbounded let-winners-run retention (over-sticky);
tuning any parameter to a historical window (all burned).

## 7. Guardrails

`prepare.py research` only — judge on worst sub-period (no degrade/
sign-flip) + all anti-overfit gates + controlled drawdown + gross ≤100%;
mean Sortino is reference only. **Never run `prepare.py promotion` again.**
No hidden complexity. Long-only; `order_target_percent` only; PIT universe;
size from `n_positions`; never edit `prepare.py`/`backtest/anti_overfit.py`;
commit as victorvini08; stay on `production-strategy`; one change at a time;
revert decisively; git log is the manual-dev ledger.

## 8. New-session prompt

> Branch `production-strategy` (verify; never other branches). Read
> `PRODUCTION_STRATEGY.md`, `STRATEGY_DEVELOPMENT_PLAN.md`, and this roadmap
> in full. Goal: optimal robust long-only Indian-equity strategy good in
> bull/bear/neutral, judged on the worst regime sub-period + forward
> robustness, never backtest Sortino (windows burned). From committed
> `e745434`, take **A (conditional vol scaling)** into a full design (then
> B, then optionally C), one at a time; validate each via `prepare.py
> research` (worst sub-period + gates + drawdown); never `promotion`;
> respect §6 burned traps and §7 guardrails. News deferred. Own judgment —
> leads, not a recipe.
