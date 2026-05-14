# autoresearch-trading-india

LLM-driven autoresearch swing-trading system for Indian equities (NSE, CNC delivery) via the Dhan HQ Trading API.

**Status:** v1 paper-only. Live mode built but gated by `halt.json` until 4 weeks of clean paper validation.

This repo is the India-market rebuild of the abandoned `autoresearch-trading-us` (US stocks via IBKR), which discovered empirically that US-fractional commission economics make the strategy mathematically unprofitable at small capital. Indian equities + Dhan delivery (free brokerage) restore the economics.

---

## Quickstart

```bash
# 1. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is not installed
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID, SEBI_ALGO_ID, FRED_API_KEY.
# Set DHAN_MOCK=1 if you don't have a Dhan token yet (v1 paper-only mode).

# 3. Run tests
uv run pytest -q

# 4. Run a walk-forward backtest on the current strategy
uv run python prepare.py research

# 5. Paper-trade today
uv run python -m scripts.run_live --date $(date +%Y-%m-%d)

# 6. Generate the dashboard
uv run python -m scripts.dashboard
open state/reports/dashboard.html
```

---

## Architecture in one paragraph

An **autoresearch loop** (Claude Opus 4.7, run overnight via `scripts/run_overnight.py`) reads `journal.md`, proposes an edit to `strategy.py`, runs walk-forward backtest (`prepare.py`) with anti-overfit gates (`backtest/anti_overfit.py`), and decides KEEP or REVERT. The current `strategy.py` is a `backtrader.Strategy` that ranks the **top 200 liquid Nifty 500 names** by **12-month momentum (skip last month)**, applies a **quality screen** (ROE, debt/equity, operating margin), enforces a **25% sector cap**, and **blocks new entries** when the macro regime is risk-off (Nifty < 200-DMA OR India VIX > 95th-pct OR FII 20-day net flow < -₹15kCr). A **Dhan executor** (`scripts/executors/dhan.py`) translates intended positions into orders, places them through the Dhan Trading API, reconciles fills, and writes an **8-table ledger** (`storage/portfolio.duckdb`).

For v1 the executor runs against an **in-memory mock Dhan client** (`brokers/dhan_mock.py`); live trading requires a real access token and is currently disabled by `halt.json`.

---

## What's different from a typical algo trading repo

1. **Karpathy 3-file pattern** — `prepare.py` (immutable evaluator), `strategy.py` (loop-editable), `journal.md` (memory). Most algo repos mix all three; we keep them surgical.
2. **Anti-overfit gates are first-class** — sealed test set, Bonferroni p-correction, random-walk Monte Carlo, parameter parsimony budget. The loop *will* try to overfit; the gates exist because of that.
3. **News + macro classifiers feed the strategy** — LLM-classified `macro_regime`, per-ticker `sentiment`, and `events` features are pre-computed daily (cached, model-id stamped) and read by the strategy via `llm/features.py`. Strategy code stays small; the cognition is in the cache.
4. **Cost model matches the broker we'll execute on** — `backtest/costs.py` mirrors Dhan delivery (brokerage ₹0, STT 0.1% sell, DP charge ₹14.75 per scrip per sell, etc.). Promotion-gate Sortino is computed net of these.
5. **SEBI retail-algo compliance** — every order carries our algo ID; OPS counter logged daily; static IP whitelist enforced.

---

## Documentation

- `CLAUDE.md` — project context, daily operation, user setup steps
- `docs/superpowers/specs/2026-05-14-india-autoresearch-trading-design.md` — design spec
- `docs/handoff-india-pivot.md` — US→India pivot decisions (from predecessor repo)
- `docs/learnings-from-us-build.md` — empirical lessons from Phase 1

---

## License

Private — no license granted.
