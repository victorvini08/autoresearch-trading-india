# Design: Reusable `autoresearch` Python library + clean README

**Date:** 2026-07-02
**Branch:** `library-refactor` (off `main`; `main` and the VM are never touched by this work)
**Status:** Approved design — ready for implementation plan

## Goal

Turn the working India autoresearch trading system into a **reusable, installable
Python library** that other people can build their own strategies/brokers/markets
on top of, plus a **clean README** aimed at library users. The existing India +
Dhan system remains intact as the **reference implementation** wired into clean
extension points.

## Explicitly in scope

1. Restructure the flat top-level modules into a single importable package,
   `autoresearch`, that is `pip`/`uv`-installable.
2. Define four extension-point ABCs — **`Broker`**, **`DataProvider`**,
   **`StrategyBase`**, **`CostModel`** — and make the existing India/Dhan classes
   implement them as the reference example.
3. A light typed **`Config`** object for the settings currently hardcoded to
   India/Dhan (currency, capital, universe size, rebalance cadence/parity,
   vol-target, mock toggle). India defaults ship as the example.
4. **MIT `LICENSE`** (repo has none today).
5. Ensure the **built distribution does not ship real data** (`storage/*.duckdb`,
   `llm_cache.sqlite`) and provide a **synthetic-data bootstrap** so a fresh
   install can run the backtest immediately.
6. **Clean README** rewritten for a library audience.

## Explicitly out of scope (per user decision)

- No git-history purge / force-push. History stays as-is (repo is already public;
  no credentials were ever committed — `.env` never tracked, no hardcoded tokens).
- No `CASE_STUDY.md` / journal sanitization.
- No broad personal-data scrub of the existing repo (deploy plists, docs, etc.).
- **No touching or merging `main`; no VM migration.** All work is a standalone
  deliverable on `library-refactor`. Whether/when to merge is a separate later
  decision by the user.

## Behavior-preservation contract

This is a **restructuring + packaging + documentation** change, not a logic change.
Runtime semantics of the strategy, executor, backtest, and gates must be identical.
The `tests/` suite is the guardrail: `uv run pytest -q` must stay green after every
step. No changes to `prepare.py`'s evaluation math or `backtest/anti_overfit.py`
gate logic.

## Target package layout

```
autoresearch/                     # single importable root (was flat top-level dirs)
  __init__.py                     # version + top-level exports
  interfaces/                     # NEW — extension points (ABCs)
    __init__.py
    broker.py                     #   Broker
    data_provider.py              #   DataProvider
    strategy.py                   #   StrategyBase
    cost_model.py                 #   CostModel
  config.py                       # NEW — typed Config (env + optional config.yaml)
  brokers/                        # reference: DhanBroker, DhanMock   (was brokers/)
  data/                           # reference: NSE bhav, FRED, news    (was data/)
  strategy/                       # reference: IndiaMomentumQualityCarry (was strategy.py)
  research/                       # prepare.py evaluator + loop/run_overnight
  backtest/                       # engine, metrics, risk, costs (was backtest/)
  llm/                            # optional classifiers               (was llm/)
  storage/                        # portfolio_db, realworld_db (DB files gitignored)
  execution/                      # run_live orchestration + executors
examples/india/                   # thin wiring assembling the India reference system
scripts/                          # operational CLIs (behavior unchanged)
tests/                            # imports updated, coverage unchanged
```

The immutable walk-forward evaluator + anti-overfit gates (`prepare.py` →
`autoresearch/research/`) is highlighted as the reusable research harness.

## Extension interfaces (the core value)

Four small ABCs; the India classes are the reference implementations.

- **`Broker`** — `place_order`, `get_positions`, `get_holdings`, `get_cash`,
  `get_historical_candles`. Reference: `DhanBroker`, `DhanMock`.
- **`DataProvider`** — price ingest + point-in-time universe construction.
  Reference: NSE bhav archive + FRED + news feeds.
- **`StrategyBase`** — the `order_target_percent`-only contract that
  `signal_today` capture depends on. Reference: `IndiaMomentumQualityCarry`.
- **`CostModel`** — reference: India costs (DP charge, STT, STCG).

## Config

Typed dataclass loaded from env + optional `config.yaml`. Lifts only settings a new
user genuinely must change; India defaults preserve current behavior. No new
strategy knobs (respects the parsimony budget).

## Packaging / data hygiene

- `pyproject.toml`: switch to a real build (drop `package = false`), set package
  discovery to `autoresearch`, add `console_scripts` for the operational entrypoints.
- Untrack `storage/*.duckdb` + `llm_cache.sqlite` on the branch and gitignore them
  (only affects the branch; `main` keeps them). Exclude data dirs from the wheel.
- Synthetic-data bootstrap: a small generator (or committed synthetic fixture) so
  `prepare.py research` and the paper run work on a fresh clone with no real data.

## Data onboarding (how a new user gets prices/fundamentals/etc.)

Central to usability. Key fact: **all data is free and self-fetched** — the system
uses only free public sources (locked decision; Dhan's paid Data API is not used).
A new user does not buy or download a dataset; the library scrapes public archives
into local DuckDB stores. Only credential required is a free `FRED_API_KEY`.

Sources → stores:
- Stock prices → NSE bhav archive (public daily ZIPs) → `prices.duckdb`
- Macro → FRED (`FRED_API_KEY`) + yfinance indices (India VIX / Nifty)
- Fundamentals → yfinance snapshots + NSE XBRL filings (`ingest_fundamentals`,
  `fundamentals_xbrl`)
- News → MoneyControl / Pulse RSS / NSE filings / RBI / SEBI
- Universe → built point-in-time from the price history itself

The flow already exists (`scripts/bootstrap_ingest.py`, `scripts/backfill_5y.py`,
`scripts/backfill_universe.py`); this work makes it discoverable and reusable:

1. **README "Getting the data" section** — exact commands, what each fetches,
   rough time/size, and the FRED-key note. Two-step: fast bootstrap (~30 days) to
   start, then optional long backfill (~hours, resumable) for backtest history.
2. **Single clean `console_scripts` front door** — e.g. `autoresearch-data bootstrap`
   / `autoresearch-data backfill`, wrapping the existing scripts. No new logic.
3. **Document the `DataProvider` contract explicitly** — the exact table schemas
   the library expects (e.g. `daily_bars(ticker, dt, open, high, low, close,
   volume)` and the fundamentals schema) so a "build your own market" user knows
   precisely what to supply instead of reverse-engineering it.
4. **Config-driven storage paths** — ingest DB paths are semi-hardcoded
   (`DB_PATH = Path("storage/prices.duckdb")`) but functions already accept a path
   arg; wire them to `Config` so a user can point at their own storage location.

Distinguishes two users: the India reference user runs the flow above verbatim; the
build-your-own-market user ignores NSE ingestion entirely and implements
`DataProvider` for their own source, feeding the documented table shapes.

## README (final step)

Library-audience rewrite: what it is; the three swappable layers; `uv`/`pip`
quickstart; a **"Getting the data"** section (bootstrap → backfill commands,
free sources, FRED-key note); "run the India reference system"; "build your own
broker/strategy against the ABCs" with the `DataProvider` table-schema contract;
the research + anti-overfit harness; honest risk disclaimer (this is a reference
system that can trade real money — not financial advice). Plus MIT `LICENSE`.

## Phasing

1. Package skeleton + move modules + rewrite imports → tests green.
2. Extract the four ABCs (incl. `DataProvider` + documented table-schema contract);
   India classes implement them → tests green.
3. `Config` object; lift hardcoded India settings incl. storage paths → tests green.
4. Untrack real DBs; synthetic-data bootstrap; wheel excludes data.
5. `pyproject.toml` build/packaging + `console_scripts` (ops entrypoints +
   `autoresearch-data` bootstrap/backfill front door) → `uv build` works.
6. MIT `LICENSE` + rewritten README (incl. "Getting the data") + `examples/india`.

## Risks / notes

- ~300 import sites are rewritten (steps 1–2). The test suite is the safety net;
  each step is verified green before the next.
- Branch diverges structurally from `main`. Intentional — `main` stays the deployed
  flat layout; the library is the standalone deliverable.
