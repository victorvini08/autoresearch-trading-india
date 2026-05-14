# Repository guide for agents

This file mirrors `CLAUDE.md` for agents that do not load `CLAUDE.md` by default (e.g. Codex CLI, Gemini CLI). See `CLAUDE.md` for the full project context.

## Quick summary

- **Project:** LLM-driven autoresearch swing-trading for Indian equities (NSE, CNC delivery)
- **Predecessor:** `autoresearch-trading-us` (archived; broker + market agnostic infra carried over)
- **Broker:** Dhan HQ Trading API (free); price data from free NSE bhav archive (Dhan's Data API is paid ₹500/mo, not used)
- **Universe:** top 200 by 20-day ADV from liquid-filtered Nifty 500
- **Strategy:** 12-1 cross-sectional momentum + quality screen + sector cap + Indian regime gate; 5 hyperparameters; theory-backed
- **Cadence:** biweekly rebalance (alternate Fridays)
- **Phase:** v1 paper-only (`dhan-paper` mode against in-memory mock); live built but halt-gated
- **Anti-overfit machinery:** sealed 2024-26 test set, Bonferroni p-correction, random-walk Monte Carlo, parsimony budget, sub-period stationarity, cost-aware Sortino

## Hard constraints

1. Never enable `dhan-live` without explicit user approval AND a successful 4-week paper validation.
2. Every order carries the SEBI algo ID (`$SEBI_ALGO_ID` env var) per the 2026-04-01 retail algo framework.
3. Strategy code uses `order_target_percent` only (not `self.buy()` / `self.close()`).
4. Anti-overfit gates are atomic — any failure rejects the variant.
5. Sealed test set is revealed ONCE per promotion; no retries on the same variant.

## Read first

- `CLAUDE.md` — full project context
- `docs/superpowers/specs/2026-05-14-india-autoresearch-trading-design.md` — design rationale
- `docs/handoff-india-pivot.md` — US→India pivot decisions (carried from US repo)
- `docs/learnings-from-us-build.md` — empirical lessons from Phase 1 (US stocks)
- `program.md` — autoresearch loop's goal/constraints
- `journal.md` — iteration memory (loop reads this every overnight run)

## Commands

```bash
uv run pytest -q                                       # tests
uv run python prepare.py research                      # walk-forward backtest
uv run python -m scripts.run_live --date YYYY-MM-DD    # paper-trade today
uv run python -m scripts.run_overnight                 # autoresearch loop
uv run python -m scripts.dashboard                     # generate dashboard HTML
```
