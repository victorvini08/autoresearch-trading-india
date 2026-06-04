# autoresearch-trading-india

LLM-driven autoresearch swing-trading system for Indian equities (NSE, CNC delivery) via the Dhan HQ Trading API.

**Status:** v1 **paper-only** (`dhan-paper`; runs against an in-memory mock Dhan client with `DHAN_MOCK=1`). Live mode (`dhan-live`) is built but disabled by `state/halt.json` until 4 weeks of clean paper validation. The paper account is **₹1,00,000**. The nightly autoresearch loop is **not** scheduled — `strategy.py` is locked and strategy evolution is on-demand only.

This repo is the India-market rebuild of the abandoned `autoresearch-trading-us` (US stocks via IBKR), which found that US fractional-commission economics make the strategy unprofitable at small capital. Indian equities + Dhan delivery (free brokerage) restore the economics.

---

## Quickstart

```bash
# 1. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is not installed
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env: DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID, FRED_API_KEY (SEBI_ALGO_ID is optional).
# Keep DHAN_MOCK=1 to run paper-only against the mock client (default for v1).

# 3. Run tests
uv run pytest -q

# 4. Walk-forward backtest of the current strategy (research mode — sealed test stays hidden)
uv run python prepare.py research

# 5. Paper-trade today
uv run python -m scripts.run_live --date $(date +%Y-%m-%d)

# 6. Generate the dashboard
uv run python -m scripts.dashboard
open state/reports/dashboard.html
```

---

## Architecture

**Three layers — broker/market-agnostic at the top, India-specific at the bottom:**

1. **Autoresearch loop** (`scripts/loop.py`, `scripts/run_overnight.py`) — reads `journal.md`, proposes a `strategy.py` edit, runs the walk-forward backtest (`prepare.py`) under anti-overfit gates (`backtest/anti_overfit.py`), and KEEPs/REVERTs. *Currently unscheduled — the strategy is locked.*
2. **Strategy** (`strategy.py`) — `IndiaMomentumQualityCarry`, a `backtrader.Strategy`: cross-sectional **12-1 momentum-quality selection** over the point-in-time top-200-by-ADV universe → **bounded gross-targeting** (deploy down the ranked list, ≤10% per name, ≤25% per sector) → **downside-vol-targeted gross** (`clip(0.12 / downside_vol_ann, 0, 0.99)`, risk input = MAX of a slow ~6m and fast ~1m downside semi-deviation) → a between-rebalance **structural MA exit**. Rebalances biweekly (fixed-parity alternate Fridays). The locked signal is **purely price-derived** — it does not read the LLM classifiers.
3. **Executor + data** (`scripts/run_live.py`, `scripts/executors/`, `brokers/`, `data/`) — translates target weights into `order_target_percent` orders, places them via Dhan (or the mock), reconciles fills, and writes the ledger (`storage/portfolio_db.py` → `storage/portfolio.duckdb`).

On top sits a **real-world paper-trading + self-improving review layer**: daily reconciliation (`scripts/reconciliation.py`), a deterministic equity-driven **safety state machine** (`data/safety_state.py`, `scripts/safety_evaluator.py`), a **month-end LLM review** gated by deterministic policy checks (`scripts/realworld_review.py`, `data/realworld_review_validator.py`, `storage/realworld_db.py`), and a faithful **paper-trading replay harness** (`scripts/replay_paper.py`).

---

## What's different from a typical algo repo

1. **Karpathy 3-file pattern** — `prepare.py` (immutable evaluator), `strategy.py` (editable signal), `journal.md` (append-only memory). Kept surgical.
2. **Anti-overfit gates are first-class** — sealed test set (2025-01→2026-05), Bonferroni p-correction, random-walk Monte Carlo, parsimony budget, sub-period stationarity. The loop *will* try to overfit; the gates exist because of that. Variants are also validated at ≥10× capital (₹5L).
3. **Cost model matches the broker** — `backtest/costs.py` mirrors Dhan delivery (₹0 brokerage, STT, ₹14.75 DP charge per scrip per sell). Sortino is net of these.
4. **Robustness over raw Sortino** — strategies are picked by real-world robustness (gates + worst-case + drawdown), not by beating a baseline validation Sortino.
5. **Honest about its edge** — see below.

---

## Honest performance note

The locked book's edge is **drawdown protection, not return alpha.** An early sealed-test reveal of +12.07% (vs Nifty −1.94%) was later traced to a GOLD/SILVER **ETF leak**; the de-leaked, equity-only sealed return is ≈ **−2.8% vs Nifty −1.94%**, with max drawdown **9.2% < 14.8%**. The book runs ~46% deployed with roughly symmetric up/down capture (~0.28 over the clean validation era) — it **lags sustained bull markets by design** and protects in down/flat regimes. Five separate alpha-lever experiments (low-vol prefilter, inverse-vol sizing, higher vol-target, illiquidity tilt, breadth-confirmed convexity) were tested and rejected as non-robust; the conclusion on file is that this is a defensive sleeve at its risk-adjusted optimum, and the robust way to add bull capture is a **portfolio-level index blend** (`scripts/blend_frontier.py`), not strategy tuning.

---

## Documentation

- `CLAUDE.md` / `AGENTS.md` — project context, locked decisions, hard constraints, daily operation, setup (kept in sync)
- `PRODUCTION_STRATEGY.md` — canonical locked-strategy definition + caveats
- `STRATEGY_DEVELOPMENT_PLAN.md` — goal + guardrails for on-demand development
- `docs/superpowers/specs/2026-05-14-india-autoresearch-trading-design.md` — original design spec
- `docs/superpowers/specs/2026-05-28-realworld-autoresearch-design.md` — real-world paper + review layer design
- `docs/strategy-candidates.md` — rigorously-tested-but-not-promoted ideas
- `docs/handoff-india-pivot.md`, `docs/learnings-from-us-build.md` — predecessor (US) lessons

---

## License

Private — no license granted.
