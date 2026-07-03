# autoresearch-trading

A framework for building **LLM-driven autoresearch trading systems**: an
immutable walk-forward evaluator with anti-overfit gates, and four swappable
extension points — **Broker**, **DataProvider**, **StrategyBase**, **CostModel** —
so you can target your own market, broker, and signal.

It ships with a complete **reference implementation**: a long-only,
delivery-only swing-trading system for Indian equities (NSE) executing through
the Dhan HQ Trading API, using only free public data. That reference is the
repo itself — `strategy.py` at the root, `scripts/` for operations — built on
top of the same `autoresearch` package you install.

> ⚠️ **Not financial advice.** This is research/engineering infrastructure. The
> reference system can place real orders with real money. Backtests overfit,
> live markets differ from simulations, and you are solely responsible for any
> capital you deploy. Start in paper mode and read the code before trading.

---

## The idea

Three layers, decoupled by small interfaces:

1. **Research harness** (`autoresearch.research`, `autoresearch.backtest`) — a
   walk-forward evaluator with anti-overfit gates (Bonferroni correction,
   random-walk Monte-Carlo null, sub-period stationarity, parsimony budget,
   cost-aware Sortino). This is the immutable part you don't edit.
2. **Strategy** (`StrategyBase`) — your signal, as a `backtrader` strategy that
   changes positions only via `order_target_percent`.
3. **Execution + data** (`Broker`, `DataProvider`, `CostModel`) — how orders
   reach a venue, how prices/universe are sourced, and what trading costs apply.

The **autoresearch loop** (`scripts/loop.py`) closes the circle: an LLM reads a
journal of past hypotheses, proposes one edit to your `strategy.py`, runs the
evaluator, and KEEP/REVERTs against the gates — so your editable `strategy.py`
and `journal.md` are *your project's files*, while the immutable machinery is
the installed library.

---

## Install

Requires Python ≥ 3.11. With [uv](https://docs.astral.sh/uv/):

```bash
uv add autoresearch-trading   # or: pip install autoresearch-trading
```

The distribution is `autoresearch-trading`; the importable package is
`autoresearch` (e.g. `from autoresearch.interfaces import StrategyBase`).

To work on the reference system, clone the repo and sync:

```bash
git clone <this-repo>
cd autoresearch-trading-india
uv sync --extra dev
```

---

## Start your own project

Not sure where to begin after installing? Just run **`autoresearch`** (or
**`autoresearch-trading`** — same command, matching the install name) with no
arguments and it prints exactly what to do next. The fastest way in is to
scaffold a project that **runs immediately**, then edit three files:

```bash
autoresearch-trading              # prints "what to do next" (or: autoresearch)
autoresearch init my-quant        # scaffold a project (alias: autoresearch-init)
cd my-quant
python run.py                     # backtests on synthetic data — no setup
```

You now own `strategy.py`, `provider.py`, `config.py`, and `journal.md`. Edit
them in that order — your signal, your data, your knobs. The library stays
installed and untouched. (`autoresearch-init` is one command in this package,
not a separate install.)

## Quickstart (no data, no credentials)

Or run the bundled example — a toy backtest on deterministic **synthetic** data
that shows the extension points wired together:

```bash
uv run python examples/minimal/run.py
```

This uses `SyntheticDataProvider(DataProvider)` + `MinimalMomentum(StrategyBase)`
through the backtest engine. See [`examples/minimal/`](examples/minimal/).

You can also generate a synthetic prices + universe pair directly:

```bash
uv run autoresearch-data            # writes storage/prices.duckdb + universe.duckdb
```

---

## Getting the data (real market data)

**All data is free and self-fetched** — there is no dataset to buy. The reference
system scrapes free public archives into local DuckDB stores. The only
credential is a free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html)
for macro series.

| Data | Source (free) | Store |
|---|---|---|
| Stock prices | NSE bhav archive (daily ZIPs) | `storage/prices.duckdb` |
| Universe | derived point-in-time from price history | `storage/universe.duckdb` |
| Macro | FRED (`FRED_API_KEY`) + yfinance indices (India VIX / Nifty) | `storage/macro.duckdb` |
| Fundamentals | yfinance + NSE XBRL filings | `storage/fundamentals.duckdb` |
| News | MoneyControl / Pulse RSS / NSE filings / RBI / SEBI | `storage/news.duckdb` |

The data stores are **git-ignored and never shipped in the wheel** — you
regenerate them locally. Two steps:

```bash
cp .env.example .env            # add FRED_API_KEY (optional but recommended)

# 1. Fast bootstrap: last ~30 days, enough to start
uv run python -m scripts.bootstrap_ingest

# 2. Optional deep history for backtests (~hours, resumable)
uv run python -m scripts.backfill_5y --all
uv run python -m scripts.backfill_universe
```

**Bringing your own market?** Ignore NSE ingestion entirely and implement
`DataProvider` for your source, returning the documented table shape (below).

---

## Run the reference system

The India reference lives at the repo root (`strategy.py`) and in `scripts/`. It
defaults to paper mode (`DHAN_MOCK=1`), so no broker account is needed to try it.

```bash
# Walk-forward backtest of the current strategy.py (+ anti-overfit gates)
uv run autoresearch-eval research
# equivalently: uv run python -m autoresearch.research.prepare research

# One end-to-end paper run for today
uv run python -m scripts.run_live --date $(date +%Y-%m-%d)

# One autoresearch loop iteration (LLM proposes a strategy.py edit, gated)
uv run python -m scripts.loop --iterations 1
```

> **The autoresearch loop needs an LLM CLI, not a Python SDK.** It drives the
> model by shelling out to a local command, so there's no LLM package to
> install. Install and sign in to **either** [Claude Code](https://claude.com/product/claude-code)
> (the `claude` CLI) **or** the [OpenAI Codex CLI](https://github.com/openai/codex)
> (the `codex` CLI) and put it on your PATH — the loop (and the optional LLM
> classifiers) use whichever is available. Everything else — backtests, the
> evaluator, paper trading — needs no LLM at all.

The operational commands (`run_live`, `daily_update`, `premarket_scan`,
`daily_report`, `loop`) live in `scripts/` and run from a clone with
`python -m scripts.<name>`. Enabling real live trading requires explicit,
deliberate steps (a halt-flag gate + a paper-validation window) — see the code
and `CLAUDE.md`.

---

## Build your own

Implement the interfaces in `autoresearch.interfaces` and point the evaluator at
your strategy. The India/Dhan classes are the reference implementations.

```python
from autoresearch.interfaces import Broker, DataProvider, StrategyBase, CostModel
```

- **`StrategyBase`** — subclass it; change positions only via
  `order_target_percent`. Put your strategy in a `strategy.py` at your project
  root (this is the file the autoresearch loop edits).
- **`Broker`** — `place_order / get_positions / get_holdings / get_cash /
  get_fills / …`. Reference: `DhanBroker`, `DhanMock`.
- **`DataProvider`** — `read_prices` + `pit_universe`. Reference: NSE bhav ingest.
- **`CostModel`** — `commission` + `round_trip_cost`. Reference: `IndiaCostModel`.

### DataProvider table-schema contract

The library reads adjusted daily bars in this shape (DuckDB `daily_bars` in the
reference impl):

```
daily_bars(ticker TEXT, dt DATE, open DOUBLE, high DOUBLE, low DOUBLE,
           close DOUBLE, volume DOUBLE)   -- split/bonus-adjusted close
```

A point-in-time universe must be derivable from bar history alone (never a
"current membership" list — that injects survivorship bias). See
[`examples/minimal/provider.py`](examples/minimal/provider.py) for a working
implementation and `autoresearch/interfaces/data_provider.py` for the full
contract.

---

## The research + anti-overfit harness

`autoresearch.research.prepare` is the immutable evaluator. It walk-forwards over
train/validation folds, holds out a sealed test window, and scores each variant
against **atomic** gates — a variant that fails any gate is rejected, not
partially accepted. This is the point of the framework: the loop *will* try to
overfit, and the gates are what catch it. Settings that a downstream user
changes (capital, currency, universe size, cadence, vol target, dates, storage
paths) live in `autoresearch.config.Config` with the India values as defaults.

---

## Repository layout

```
autoresearch/            # the installable library
  interfaces/            #   Broker, DataProvider, StrategyBase, CostModel (ABCs)
  config.py              #   typed Config (India defaults)
  research/prepare.py    #   immutable walk-forward evaluator + gates
  backtest/              #   engine, metrics, risk, costs
  brokers/ data/ llm/ storage/   # India/Dhan reference implementations
strategy.py              # reference strategy (loop-editable, at repo root)
journal.md               # reference autoresearch memory (at repo root)
scripts/                 # reference operational CLIs
examples/minimal/        # runnable synthetic-data example
tests/                   # test suite
```

## License

[MIT](LICENSE).
