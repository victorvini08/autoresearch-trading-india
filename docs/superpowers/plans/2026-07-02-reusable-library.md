# Reusable `autoresearch` Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the working India autoresearch trading system into an installable `autoresearch` Python library with four documented extension-point ABCs, a typed `Config`, clean packaging, and a library-audience README — the India/Dhan system remaining intact as the reference implementation.

**Architecture:** All *immutable, reusable* machinery (the walk-forward evaluator + anti-overfit gates, backtest engine, brokers, data, llm, storage, the autoresearch loop driver, the four ABCs, `Config`) moves under a single importable `autoresearch/` package. The *loop-editable user artifacts* — `strategy.py` and `journal.md` — **stay at the repo root**, because a pip-installed library must never rewrite its own source in site-packages; this repo's root therefore already has the exact shape of a real downstream user's project (their `strategy.py` beside an installed `autoresearch`). `scripts/` stays at root as the operational CLI layer. Behavior is preserved at every step; `uv run pytest -q` is the guardrail.

**Tech Stack:** Python ≥3.11, uv, backtrader, duckdb, pandas/numpy/scipy, claude-agent-sdk, pytest.

---

## Design resolution (decided with the user, 2026-07-02)

The spec's literal layout nested `strategy/` inside the package. Superseded: **`strategy.py` and `journal.md` stay at repo root** as the reference user's editable project files; `prepare.py` (immutable evaluator) moves into `autoresearch/research/`. Rationale — the autoresearch loop *rewrites `strategy.py` in place*; that cannot live in an installed package. This is both the architecturally honest split (immutable harness = library, editable strategy = user code) and the lower-churn one (`import strategy`'s 18 sites and the three `strategy.py` path/name bindings stay valid).

## Behavior-preservation contract (applies to EVERY task)

- Runtime semantics of strategy, executor, backtest, and gates are identical. No changes to `prepare.py`'s evaluation math or `backtest/anti_overfit.py` gate logic (only its import lines and, in Task 3, lifting hardcoded constants into config-with-identical-defaults).
- `uv run pytest -q` must be green before every commit. Baseline must be captured first (Task 0).
- **Never `git add -A`.** The working tree has unrelated untracked `experiments/` files and modified `storage/*.duckdb`. Stage only the exact files each task touches.
- Git identity for all commits: `victorvini08 <aryan08vini@gmail.com>` (verify `git config user.email` before first commit).
- `main` and the VM are never touched. All work stays on `library-refactor`.

---

## File structure (end state)

```
autoresearch/
  __init__.py                 # version + curated top-level exports
  interfaces/
    __init__.py
    broker.py                 # Broker(ABC)
    data_provider.py          # DataProvider(ABC) + table-schema contract docstring
    strategy.py               # StrategyBase(bt.Strategy)
    cost_model.py             # CostModel(ABC)
  config.py                   # Config dataclass (env + optional config.yaml), India defaults
  research/
    __init__.py
    prepare.py                # was ./prepare.py (evaluator + gates)
  backtest/                   # was ./backtest/
  brokers/                    # was ./brokers/  (DhanBroker, DhanMock implement Broker)
  data/                       # was ./data/     (India DataProvider reference)
  llm/                        # was ./llm/
  storage/                    # was ./storage/
strategy.py                   # STAYS at root — IndiaMomentumQualityCarry(StrategyBase), loop-editable
journal.md                    # STAYS at root — user research memory
scripts/                      # STAYS at root — operational CLIs (imports rewritten)
examples/
  minimal/                    # tiny runnable StrategyBase + stub DataProvider (teaching example)
tests/                        # imports rewritten
pyproject.toml                # real build + console_scripts
LICENSE                       # NEW (MIT)
README.md                     # rewritten for library audience
```

---

### Task 0: Baseline capture + branch hygiene

**Goal:** Record a known-green test baseline and isolate the refactor diff from pre-existing working-tree noise, so any later breakage is unambiguously ours.

**Files:**
- Create: `docs/superpowers/plans/2026-07-02-reusable-library.baseline.txt` (git-ignored scratch is fine; commit is optional)

**Acceptance Criteria:**
- [ ] Full pytest result recorded (pass/fail/skip counts) as the reference baseline.
- [ ] `git config user.email` confirmed `aryan08vini@gmail.com`.
- [ ] Pre-existing untracked `experiments/**` and modified `storage/*.duckdb` confirmed as NOT part of any refactor commit (documented, left alone).

**Verify:** `uv run pytest -q` → baseline count captured.

**Steps:**

- [ ] **Step 1: Confirm branch + identity**

```bash
cd "/Users/aryanmehta/Desktop/My Work/autoresearch-trading-india"
git branch --show-current            # expect: library-refactor
git config user.email                # expect: aryan08vini@gmail.com
git config user.name                 # expect: victorvini08
```
If identity is wrong: `git config user.email aryan08vini@gmail.com && git config user.name victorvini08`.

- [ ] **Step 2: Capture the green baseline**

```bash
uv run pytest -q 2>&1 | tail -20
```
Expected: a summary like `N passed, M skipped`. Record N and M. This is the invariant every later task must preserve. If the baseline is NOT green, STOP and report — do not start restructuring on a red tree.

- [ ] **Step 3: Snapshot pre-existing noise (do not stage it later)**

```bash
git status -s | grep -vE '^\?\? docs/superpowers/plans/' | head -60
```
Note the untracked `experiments/**` and modified `storage/*.duckdb`. These are pre-existing and unrelated. Every commit in this plan uses explicit `git add <paths>` — never `git add -A` / `git add .`.

- [ ] **Step 4: Commit the plan doc only**

```bash
git add docs/superpowers/plans/2026-07-02-reusable-library.md docs/superpowers/plans/2026-07-02-reusable-library.md.tasks.json
git commit -m "plan: reusable autoresearch library implementation plan

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 1: `autoresearch` package skeleton + relocate modules + rewrite imports

**Goal:** Move `backtest/ brokers/ data/ llm/ storage/` and `prepare.py` under a new `autoresearch/` package, rewrite all ~250 import sites that reference them, and keep `strategy.py` + `scripts/` at root — in one atomic, tests-green commit.

**Files:**
- Create: `autoresearch/__init__.py`, `autoresearch/research/__init__.py`
- Move (git mv): `backtest/ → autoresearch/backtest/`, `brokers/ → autoresearch/brokers/`, `data/ → autoresearch/data/`, `llm/ → autoresearch/llm/`, `storage/ → autoresearch/storage/`, `prepare.py → autoresearch/research/prepare.py`
- Modify: every `.py` importing those modules (repo-wide, excluding `.venv`, `__pycache__`, `.claude/`)
- Test: full suite (imports only; no test logic changes beyond import lines)

**Acceptance Criteria:**
- [ ] `autoresearch` is importable: `python -c "import autoresearch, autoresearch.research.prepare, autoresearch.backtest, autoresearch.brokers, autoresearch.data, autoresearch.llm, autoresearch.storage"` exits 0.
- [ ] `strategy.py` and `scripts/` remain at repo root; `import strategy` still works unchanged.
- [ ] No remaining top-level imports of the moved modules (grep returns nothing).
- [ ] pytest count matches Task 0 baseline exactly.

**Verify:** `uv run pytest -q` → same pass/skip counts as Task 0.

**Steps:**

- [ ] **Step 1: Create the package and move modules with git (preserves history)**

```bash
cd "/Users/aryanmehta/Desktop/My Work/autoresearch-trading-india"
mkdir -p autoresearch/research
printf '"""Autoresearch trading library."""\n\n__version__ = "0.1.0"\n' > autoresearch/__init__.py
printf '"""Walk-forward evaluator + anti-overfit research harness."""\n' > autoresearch/research/__init__.py

for d in backtest brokers data llm storage; do
  git mv "$d" "autoresearch/$d"
done
git mv prepare.py autoresearch/research/prepare.py
```

- [ ] **Step 2: Rewrite all import sites with a precise regex script**

Create `scratch_rewrite_imports.py` at repo root (deleted in Step 5):

```python
import re, pathlib

ROOTS = ["autoresearch", "scripts", "tests", "experiments"]
EXTRA_FILES = ["strategy.py"]  # scanned but only `prepare` refs change; `strategy` refs untouched
MOVED_DIRS = ["backtest", "brokers", "data", "llm", "storage"]

def rewrite(text: str) -> str:
    # from <dir>...  ->  from autoresearch.<dir>...
    for d in MOVED_DIRS:
        text = re.sub(rf'(?m)^(\s*from\s+){d}(\b)', rf'\1autoresearch.{d}\2', text)
        text = re.sub(rf'(?m)^(\s*import\s+){d}(\.\w+)', rf'\1autoresearch.{d}\2', text)
        # bare `import <dir>` (rare) -> `from autoresearch import <dir>`
        text = re.sub(rf'(?m)^(\s*)import\s+{d}\s*$', rf'\1from autoresearch import {d}', text)
    # prepare -> autoresearch.research.prepare
    text = re.sub(r'(?m)^(\s*from\s+)prepare(\b)', r'\1autoresearch.research.prepare\2', text)
    text = re.sub(r'(?m)^(\s*)import\s+prepare\s*$', r'\1from autoresearch.research import prepare', text)
    # importlib.import_module("prepare") -> the full dotted path (import_module("strategy") stays!)
    text = text.replace('import_module("prepare")', 'import_module("autoresearch.research.prepare")')
    text = text.replace("import_module('prepare')", "import_module('autoresearch.research.prepare')")
    return text

files = set(EXTRA_FILES)
for root in ROOTS:
    p = pathlib.Path(root)
    if p.exists():
        files.update(str(f) for f in p.rglob("*.py") if "__pycache__" not in f.parts)

changed = 0
for f in sorted(files):
    src = pathlib.Path(f).read_text()
    out = rewrite(src)
    if out != src:
        pathlib.Path(f).write_text(out)
        changed += 1
print(f"rewrote {changed} files")
```

Run it:
```bash
uv run python scratch_rewrite_imports.py
```
Expected: `rewrote <N> files` (roughly 90–130).

- [ ] **Step 3: Verify no stale top-level imports remain**

```bash
grep -rnE "^\s*(from|import) (backtest|brokers|data|llm|storage|prepare)\b" \
  autoresearch scripts tests experiments strategy.py --include="*.py" | grep -v __pycache__
```
Expected: **no output**. (Any hit is a form the regex missed — fix by hand, e.g. multi-line `import x, y`.)

- [ ] **Step 4: Confirm imports resolve and tests pass**

```bash
uv run python -c "import autoresearch, autoresearch.research.prepare, autoresearch.backtest, autoresearch.brokers, autoresearch.data, autoresearch.llm, autoresearch.storage, strategy; print('ok')"
uv run python -c "import autoresearch.research.prepare as p; print(p.EVALUATOR_VERSION)"
uv run pytest -q 2>&1 | tail -15
```
Expected: `ok`, the evaluator version string, and pytest counts equal to the Task 0 baseline. If `import strategy` fails inside subprocess fold workers, confirm repo root is on `sys.path` (it is when run from root / via `tests/conftest.py`).

- [ ] **Step 5: Remove scratch script and commit**

```bash
rm scratch_rewrite_imports.py
git add -u
git add autoresearch
git status -s | grep -vE '^\?\? (experiments/|docs/strategy-candidates)' | head -40   # sanity: only refactor files staged
git commit -m "refactor: relocate reusable modules under autoresearch package

Move backtest/brokers/data/llm/storage + prepare.py into autoresearch/;
rewrite all import sites. strategy.py and scripts/ stay at repo root
(loop-editable user code / operational CLIs). Behavior unchanged; pytest green.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Extract the four extension-point ABCs

**Goal:** Add `autoresearch/interfaces/` with `Broker`, `DataProvider`, `StrategyBase`, `CostModel` ABCs and make the India/Dhan reference classes implement them — additively, so no runtime behavior changes.

**Files:**
- Create: `autoresearch/interfaces/__init__.py`, `broker.py`, `data_provider.py`, `strategy.py`, `cost_model.py`
- Modify: `autoresearch/brokers/dhan.py` (`class DhanBroker(Broker)`), `autoresearch/brokers/dhan_mock.py` (`class DhanMock(Broker)`), `strategy.py` (`class IndiaMomentumQualityCarry(StrategyBase)`), `autoresearch/backtest/costs.py` (add `IndiaCostModel(CostModel)` wrapping existing functions)
- Test: `tests/test_interfaces.py` (new)

**Acceptance Criteria:**
- [ ] `issubclass(DhanBroker, Broker)`, `issubclass(DhanMock, Broker)`, `issubclass(IndiaMomentumQualityCarry, StrategyBase)`, `issubclass(IndiaCostModel, CostModel)` all True.
- [ ] `StrategyBase` subclasses `bt.Strategy` (so backtrader semantics + `scripts/loop.py` AST validator still accept the reference strategy).
- [ ] ABCs document the exact contract; `DataProvider` docstring states the table schema (`daily_bars(ticker, dt, open, high, low, close, volume)`).
- [ ] pytest count = baseline + new interface tests, all green.

**Verify:** `uv run pytest -q tests/test_interfaces.py` → all pass; `uv run pytest -q` → baseline preserved.

**Steps:**

- [ ] **Step 1: Write `autoresearch/interfaces/broker.py`**

Method set is the common surface of `DhanBroker` and `DhanMock` (verified: `connect, disconnect, security_id_for, get_cash, get_positions, get_holdings, place_order, get_order, cancel_order, list_today_orders, get_fills, wait_for_done`).

```python
"""Broker extension point — implement to trade a new venue."""
from __future__ import annotations
from abc import ABC, abstractmethod

class Broker(ABC):
    """Order/position/cash gateway. Reference impls: DhanBroker, DhanMock."""

    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def security_id_for(self, ticker: str) -> str: ...
    @abstractmethod
    def get_cash(self) -> dict: ...
    @abstractmethod
    def get_positions(self) -> list: ...
    @abstractmethod
    def get_holdings(self) -> list: ...
    @abstractmethod
    def place_order(self, req, *, as_of_date=None): ...
    @abstractmethod
    def get_order(self, order_id: str): ...
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...
    @abstractmethod
    def list_today_orders(self) -> list: ...
    @abstractmethod
    def get_fills(self) -> list: ...
    @abstractmethod
    def wait_for_done(self, order_id: str, **kwargs): ...
```
Note: `DhanMock.place_order` currently has a broader signature; ABC uses `*, as_of_date=None` and `**kwargs` on `wait_for_done` to stay compatible with both. Confirm both concrete signatures satisfy it (Step 5 tests will catch mismatch via instantiation).

- [ ] **Step 2: Write `autoresearch/interfaces/cost_model.py`**

`backtest/costs.py` exposes module functions (`commission_inr`, `round_trip_cost_inr`). Define the ABC + a thin reference impl (do NOT delete the functions — other code imports them):

```python
"""Cost-model extension point — implement for a new market's fees/taxes."""
from __future__ import annotations
from abc import ABC, abstractmethod

class CostModel(ABC):
    """Per-trade cost in account currency. Reference: IndiaCostModel (DP charge, STT, STCG)."""

    @abstractmethod
    def commission(self, notional: float, side: str) -> float: ...
    @abstractmethod
    def round_trip_cost(self, notional: float) -> float: ...
```

- [ ] **Step 3: Write `autoresearch/interfaces/data_provider.py` with the table-schema contract**

```python
"""DataProvider extension point — supply prices + a point-in-time universe.

Table-schema contract (the library reads these shapes):

  daily_bars(ticker TEXT, dt DATE, open DOUBLE, high DOUBLE, low DOUBLE,
             close DOUBLE, volume DOUBLE)   -- split/bonus-adjusted closes

A point-in-time universe must be derivable from bar history alone (no
survivorship-biased "current membership" list). Reference impl: NSE bhav
archive → prices.duckdb + PIT top-N-by-ADV universe.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date

class DataProvider(ABC):
    @abstractmethod
    def read_prices(self, tickers: list[str], start: date, end: date):
        """Return adjusted daily bars for tickers in [start, end] (daily_bars schema)."""
    @abstractmethod
    def pit_universe(self, as_of: date, size: int) -> list[str]:
        """Return the point-in-time tradeable universe (top `size` by liquidity) at as_of."""
```
This ABC documents the contract; the India reference need only be *registered* as satisfying it (Step 4) — existing `autoresearch/data/*` functions stay the call path, so no behavior change.

- [ ] **Step 4: Write `autoresearch/interfaces/strategy.py` and re-base the reference classes**

```python
"""Strategy extension point.

Contract: position changes go ONLY through ``order_target_percent`` (never
buy()/close()) — scripts/signal_today.py capture depends on this. Subclass
this instead of bt.Strategy directly.
"""
import backtrader as bt

class StrategyBase(bt.Strategy):
    """Base for autoresearch strategies. Reference: IndiaMomentumQualityCarry."""
    pass
```

`autoresearch/interfaces/__init__.py`:
```python
from .broker import Broker
from .cost_model import CostModel
from .data_provider import DataProvider
from .strategy import StrategyBase

__all__ = ["Broker", "CostModel", "DataProvider", "StrategyBase"]
```

Re-base concretes (edit only the class headers + add IndiaCostModel):
- `strategy.py`: `class IndiaMomentumQualityCarry(bt.Strategy):` → `class IndiaMomentumQualityCarry(StrategyBase):` with `from autoresearch.interfaces import StrategyBase` at top (keep `import backtrader as bt`).
- `autoresearch/brokers/dhan.py`: `class DhanBroker(Broker):` + import.
- `autoresearch/brokers/dhan_mock.py`: `class DhanMock(Broker):` + import. (DhanMock is a dataclass — verify `Broker(ABC)` mixes cleanly with `@dataclass`; if metaclass conflict arises, keep DhanMock unchanged and instead `Broker.register(DhanMock)` in `autoresearch/brokers/__init__.py`.)
- `autoresearch/backtest/costs.py`: append
  ```python
  from autoresearch.interfaces import CostModel
  class IndiaCostModel(CostModel):
      def commission(self, notional: float, side: str) -> float:
          return commission_inr(notional, side)
      def round_trip_cost(self, notional: float) -> float:
          return round_trip_cost_inr(notional)
  ```

- [ ] **Step 5: Write `tests/test_interfaces.py`**

```python
from autoresearch.interfaces import Broker, CostModel, DataProvider, StrategyBase
from autoresearch.brokers.dhan import DhanBroker
from autoresearch.brokers.dhan_mock import DhanMock
from autoresearch.backtest.costs import IndiaCostModel
from strategy import IndiaMomentumQualityCarry

def test_brokers_implement_broker():
    assert issubclass(DhanBroker, Broker)
    assert issubclass(DhanMock, Broker)

def test_strategy_implements_base_and_is_backtrader():
    import backtrader as bt
    assert issubclass(IndiaMomentumQualityCarry, StrategyBase)
    assert issubclass(StrategyBase, bt.Strategy)

def test_cost_model_matches_functions():
    from autoresearch.backtest.costs import commission_inr, round_trip_cost_inr
    m = IndiaCostModel()
    assert m.commission(100_000, "BUY") == commission_inr(100_000, "BUY")
    assert m.round_trip_cost(100_000) == round_trip_cost_inr(100_000)
```

- [ ] **Step 6: Check the loop AST validator still accepts the reference strategy**

`scripts/loop.py:validate_strategy_edit` requires "a single subclass of bt.Strategy". Read lines 203–221; if it filters ClassDef by literal base name `Strategy`/`bt.Strategy`, extend the accepted-bases set to include `StrategyBase`. If it just counts ClassDef nodes, no change. Add a regression test only if you change it.

- [ ] **Step 7: Run tests and commit**

```bash
uv run pytest -q tests/test_interfaces.py -v
uv run pytest -q 2>&1 | tail -15
git add autoresearch/interfaces autoresearch/brokers/dhan.py autoresearch/brokers/dhan_mock.py autoresearch/backtest/costs.py strategy.py tests/test_interfaces.py
# include scripts/loop.py only if Step 6 changed it
git commit -m "feat: extract Broker/DataProvider/StrategyBase/CostModel ABCs

India/Dhan classes implement the new interfaces (additive; runtime unchanged).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `Config` object — lift hardcoded India settings (identical defaults)

**Goal:** Introduce `autoresearch/config.py` centralizing the settings a downstream user must change (currency, capital, universe size, rebalance cadence/parity, vol-target, mock toggle, storage paths, strategy/journal paths, evaluator window/thresholds), with India defaults exactly equal to today's hardcoded values — so behavior is byte-identical.

**Files:**
- Create: `autoresearch/config.py`, `tests/test_config.py`
- Modify (wire to Config defaults, keeping current values as defaults): `autoresearch/research/prepare.py` (constants → sourced from Config defaults), `scripts/loop.py` (`STRATEGY_PATH`/`JOURNAL_PATH` → Config), `autoresearch/data/ingest_prices.py`, `ingest_news.py`, `ingest_macro.py`, `ingest_fundamentals.py`, `data/universe.py`, `autoresearch/storage/portfolio_db.py`, `realworld_db.py` (DB paths → Config)

**Acceptance Criteria:**
- [ ] `Config()` with no args reproduces every current constant: `BACKTEST_START/END`, `INITIAL_CASH=50_000`, `WARMUP_CALENDAR_DAYS=520`, `_ANNUAL_VOL_TARGET=0.12`, `_MAX_NAME_WEIGHT=0.10`, `_REBALANCE_PARITY=0`, and the storage `*.duckdb` paths.
- [ ] No numeric/behavioral change: pytest count = baseline, all green; `uv run python -m autoresearch.research.prepare research` produces the same fold count/metrics as before (spot-check `EVALUATOR_VERSION` + first fold).
- [ ] Storage-path and strategy/journal-path functions accept a `Config` (or path) and fall back to the India defaults when not supplied.

**Verify:** `uv run pytest -q tests/test_config.py` + `uv run pytest -q` green; manual `prepare research` spot-check unchanged.

**Steps:**

- [ ] **Step 1: Write `autoresearch/config.py`** (frozen dataclass; values copied verbatim from the current constants)

```python
"""Typed configuration. India/Dhan defaults reproduce current behavior exactly."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

@dataclass(frozen=True)
class Config:
    # --- account / market ---
    currency: str = "INR"
    initial_cash: float = 50_000.0          # == prepare.INITIAL_CASH
    universe_size: int = 200
    mock: bool = True                        # DHAN_MOCK default
    # --- strategy construction ---
    annual_vol_target: float = 0.12          # == strategy._ANNUAL_VOL_TARGET
    max_name_weight: float = 0.10            # == strategy._MAX_NAME_WEIGHT
    rebalance_parity: int = 0                # == strategy._REBALANCE_PARITY
    # --- evaluator window ---
    backtest_start: date = date(2017, 7, 1)  # == prepare.BACKTEST_START
    backtest_end: date = date(2026, 5, 14)   # == prepare.BACKTEST_END
    test_boundary: date = date(2025, 1, 1)   # == prepare.TEST_BOUNDARY
    warmup_calendar_days: int = 520          # == prepare.WARMUP_CALENDAR_DAYS
    # --- editable user artifacts (loop targets) ---
    repo_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    strategy_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "strategy.py")
    journal_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "journal.md")
    # --- storage ---
    storage_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "storage")

    def db(self, name: str) -> Path:
        return self.storage_dir / name

DEFAULT_CONFIG = Config()
```

- [ ] **Step 2: Wire storage paths through Config defaults (behavior-identical)**

For each DB module, replace the literal with a Config-sourced default. Example for `autoresearch/data/ingest_prices.py:511`:
```python
from autoresearch.config import DEFAULT_CONFIG
DB_PATH = DEFAULT_CONFIG.db("prices.duckdb")   # was Path("storage/prices.duckdb")
```
Repeat: `ingest_news.py`→`news.duckdb`, `ingest_macro.py`→`macro.duckdb`, `ingest_fundamentals.py`→`fundamentals.duckdb`, `data/universe.py`→`universe.duckdb`, `storage/portfolio_db.py`→`portfolio.duckdb`, `storage/realworld_db.py`→`realworld.duckdb`. **Preserve the resolved absolute path** — `portfolio_db.py` already used `REPO_ROOT/…`; `ingest_*` used relative `Path("storage/…")` resolved against CWD. Keep each module's existing effective path (Config `storage_dir` is repo-root-anchored, matching `portfolio_db`; for the CWD-relative ingest modules, confirm they were always run from repo root — they are, via `python -m` — so the absolute path is equivalent).

- [ ] **Step 3: Wire evaluator constants in `prepare.py`**

Keep the module-level names (63 sites import them) but source values from Config defaults so there is a single source of truth:
```python
from autoresearch.config import DEFAULT_CONFIG
BACKTEST_START = DEFAULT_CONFIG.backtest_start   # unchanged value
BACKTEST_END = DEFAULT_CONFIG.backtest_end
TEST_BOUNDARY = DEFAULT_CONFIG.test_boundary
INITIAL_CASH = DEFAULT_CONFIG.initial_cash
WARMUP_CALENDAR_DAYS = DEFAULT_CONFIG.warmup_calendar_days
```
Do NOT touch fold math, gate thresholds logic, or `EVALUATOR_VERSION`.

- [ ] **Step 4: Wire loop paths**

`scripts/loop.py:32,34` → `from autoresearch.config import DEFAULT_CONFIG` then `STRATEGY_PATH = DEFAULT_CONFIG.strategy_path`, `JOURNAL_PATH = DEFAULT_CONFIG.journal_path` (same resolved locations).

- [ ] **Step 5: Write `tests/test_config.py`** asserting defaults equal the live constants

```python
from datetime import date
from autoresearch.config import Config
import autoresearch.research.prepare as prep
import strategy as strat

def test_defaults_match_live_constants():
    c = Config()
    assert c.initial_cash == prep.INITIAL_CASH == 50_000.0
    assert c.backtest_start == prep.BACKTEST_START == date(2017, 7, 1)
    assert c.backtest_end == prep.BACKTEST_END
    assert c.warmup_calendar_days == prep.WARMUP_CALENDAR_DAYS == 520
    assert c.annual_vol_target == strat._ANNUAL_VOL_TARGET == 0.12
    assert c.max_name_weight == strat._MAX_NAME_WEIGHT == 0.10
    assert c.rebalance_parity == strat._REBALANCE_PARITY == 0

def test_db_paths_resolve_under_storage():
    c = Config()
    assert c.db("prices.duckdb").name == "prices.duckdb"
    assert c.db("prices.duckdb").parent == c.storage_dir
```

- [ ] **Step 6: Verify no behavior drift + commit**

```bash
uv run pytest -q tests/test_config.py -v
uv run pytest -q 2>&1 | tail -15
uv run python -m autoresearch.research.prepare research 2>&1 | tail -20   # spot-check metrics/version unchanged
git add autoresearch/config.py tests/test_config.py autoresearch/research/prepare.py scripts/loop.py \
  autoresearch/data/ingest_prices.py autoresearch/data/ingest_news.py autoresearch/data/ingest_macro.py \
  autoresearch/data/ingest_fundamentals.py autoresearch/data/universe.py \
  autoresearch/storage/portfolio_db.py autoresearch/storage/realworld_db.py
git commit -m "feat: Config with India defaults; centralize paths + evaluator constants

Single source of truth for currency/capital/universe/cadence/vol-target,
storage paths, and strategy/journal loop targets. Defaults reproduce current
behavior exactly (asserted in tests); no numeric drift.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Data hygiene — untrack real DBs, gitignore, synthetic bootstrap

**Goal:** Ensure the built distribution and repo carry no real data, and a fresh clone can run the evaluator/backtest on synthetic bars.

**Files:**
- Modify: `.gitignore`, `.gitattributes` (drop LFS tracking of the DBs *on this branch only*)
- Create: `autoresearch/data/synthetic.py` (deterministic synthetic-bar generator), `tests/test_synthetic_bootstrap.py`

**Acceptance Criteria:**
- [ ] `storage/*.duckdb` and `**/llm_cache.sqlite` are git-ignored on `library-refactor` and no longer staged/tracked (`git ls-files storage/*.duckdb` empty).
- [ ] A documented one-liner generates a synthetic `prices.duckdb` sufficient for `prepare research` to run end-to-end without real data.
- [ ] pytest green.

**Verify:** `uv run python -m autoresearch.data.synthetic --out /tmp/prices.duckdb` then a smoke eval runs; `uv run pytest -q` green.

**Steps:**

- [ ] **Step 1: Untrack DBs on this branch (index only — files stay on disk)**

```bash
git rm --cached storage/*.duckdb 2>/dev/null || true
git rm --cached llm_cache.sqlite 2>/dev/null || true
find . -name 'llm_cache.sqlite' -not -path './.venv/*' -not -path './.claude/*'
```

- [ ] **Step 2: Add ignore rules**

Append to `.gitignore`:
```
# Real data stores — never ship; regenerate via bootstrap/backfill
storage/*.duckdb
**/llm_cache.sqlite
```
Remove the DB/sqlite lines from `.gitattributes` LFS section (leave other LFS rules intact).

- [ ] **Step 3: Write `autoresearch/data/synthetic.py`**

Deterministic GBM-ish bars matching the `daily_bars(ticker, dt, open, high, low, close, volume)` schema, seeded (no RNG-in-eval concerns — this only builds a fixture DB). Provide `--out PATH --tickers N --days D` with sensible defaults (enough tickers/history to clear `MIN_FOLD_UNIVERSE=50` and `WARMUP_CALENDAR_DAYS`). Write into a duckdb table named exactly as the reader expects (mirror `ingest_prices` schema — read that module for the table name/columns before writing).

- [ ] **Step 4: Smoke test**

```python
# tests/test_synthetic_bootstrap.py
import subprocess, sys, duckdb, tempfile, os
def test_synthetic_db_has_expected_schema():
    d = tempfile.mkdtemp(); out = os.path.join(d, "prices.duckdb")
    subprocess.run([sys.executable, "-m", "autoresearch.data.synthetic", "--out", out,
                    "--tickers", "60", "--days", "800"], check=True)
    cols = [r[1] for r in duckdb.connect(out).execute("PRAGMA table_info('daily_bars')").fetchall()]
    assert {"ticker","dt","open","high","low","close","volume"} <= set(cols)
```
(Adjust table name to match `ingest_prices`.)

- [ ] **Step 5: Commit**

```bash
git add .gitignore .gitattributes autoresearch/data/synthetic.py tests/test_synthetic_bootstrap.py
git commit -m "chore: untrack real DBs on branch + synthetic-bar bootstrap

Fresh clones regenerate data; wheel ships no real stores. Deterministic
synthetic generator lets prepare research run without live ingestion.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Packaging — real build + console scripts

**Goal:** Make `autoresearch` a real installable package with a working `uv build` and clean CLI entrypoints.

**Files:**
- Modify: `pyproject.toml`

**Acceptance Criteria:**
- [ ] `[tool.uv] package = false` removed; build backend + package discovery target `autoresearch`.
- [ ] `uv build` produces a wheel + sdist; the wheel contains `autoresearch/**` and **no** `storage/*.duckdb`, no `llm_cache.sqlite`.
- [ ] `console_scripts` expose the ops front doors, incl. `autoresearch-data` (bootstrap/backfill).
- [ ] pytest green; `uv run <console-script> --help` works for each entrypoint.

**Verify:** `uv build && python -m zipfile -l dist/*.whl | grep -c duckdb` → `0`; `uv run autoresearch-data --help` exits 0.

**Steps:**

- [ ] **Step 1: Edit `pyproject.toml`**

- Remove `[tool.uv] package = false`.
- Add build system + discovery (hatchling is simplest with uv):
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["autoresearch"]

[tool.hatch.build.targets.wheel.force-include]
# nothing from storage/ — data is regenerated, never shipped
```
- Add entrypoints (wrap existing `scripts/*` mains; create thin `autoresearch/cli.py` dispatchers only if a script isn't already `-m` runnable):
```toml
[project.scripts]
autoresearch = "scripts.run_live:main"
autoresearch-eval = "autoresearch.research.prepare:main"
autoresearch-loop = "scripts.loop:main"
autoresearch-data = "scripts.bootstrap_ingest:main"
```
(Confirm each target has a `main()`; if `prepare.py` only has `__main__`, refactor its `__main__` block into a `def main()` called from `if __name__ == "__main__"` — pure move, no logic change. Same for any script lacking `main()`.)

- [ ] **Step 2: Build and inspect the wheel**

```bash
uv build 2>&1 | tail -10
python -m zipfile -l dist/*.whl | grep -E "duckdb|sqlite" | head    # expect: empty
python -m zipfile -l dist/*.whl | grep -c "autoresearch/"           # expect: > 0
```

- [ ] **Step 3: Smoke the entrypoints**

```bash
uv run autoresearch-data --help
uv run autoresearch-eval research 2>&1 | tail -5   # or --help if added
uv run pytest -q 2>&1 | tail -8
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
# + any scripts/*.py where __main__ was refactored into main()
git commit -m "build: installable autoresearch package + console scripts

Real hatchling build (drop package=false); wheel ships autoresearch/ only,
no data stores. Entrypoints: autoresearch / -eval / -loop / -data.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: MIT LICENSE + library README + minimal example

**Goal:** Ship an MIT license, a README written for a library audience (install → get data → run reference → build your own → research harness → risk disclaimer), and a tiny runnable example demonstrating the extension points.

**Files:**
- Create: `LICENSE`, `examples/minimal/strategy.py`, `examples/minimal/provider.py`, `examples/minimal/README.md`
- Modify: `README.md` (full rewrite)

**Acceptance Criteria:**
- [ ] `LICENSE` is MIT with the correct holder/year.
- [ ] README covers: what it is; the three swappable layers; `uv`/`pip` quickstart; **"Getting the data"** (bootstrap → backfill commands, free sources, `FRED_API_KEY` note); "run the India reference"; "build your own broker/strategy/dataprovider against the ABCs" including the `DataProvider` table-schema; the research + anti-overfit harness; honest risk disclaimer (reference system, can trade real money, not financial advice).
- [ ] `examples/minimal` runs a backtest/eval on synthetic data with a ~40-line `StrategyBase` subclass + stub `DataProvider`.
- [ ] pytest green.

**Verify:** `uv run python examples/minimal/strategy.py` (or its documented command) runs on synthetic data and prints a result.

**Steps:**

- [ ] **Step 1: Add MIT `LICENSE`** (holder: the repo owner; year 2026).

- [ ] **Step 2: Write `examples/minimal/`** — a trivial momentum `StrategyBase` subclass + a stub `DataProvider` returning synthetic bars (reuse `autoresearch.data.synthetic`), with a `README.md` showing the run command. Keep it self-contained and short.

- [ ] **Step 3: Rewrite `README.md`** for the library audience per the acceptance criteria (sections above). Pull the "Getting the data" content from the spec's Data-onboarding section. State clearly: `strategy.py` + `journal.md` at root are the India reference user's editable files; the installed `autoresearch` package is the immutable machinery.

- [ ] **Step 4: Verify example + full suite, then commit**

```bash
uv run python examples/minimal/strategy.py 2>&1 | tail -10
uv run pytest -q 2>&1 | tail -8
git add LICENSE README.md examples/minimal
git commit -m "docs: MIT license + library README + minimal example

Library-audience README (install, data onboarding, run India reference,
build-your-own against the ABCs, research harness, risk disclaimer) and a
runnable minimal StrategyBase/DataProvider example on synthetic data.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-review (against the spec)

- **Spec §1 installable package** → Tasks 1, 5. ✔
- **Spec §2 four ABCs incl. DataProvider table-schema** → Task 2 (schema in `data_provider.py` docstring). ✔
- **Spec §3 light Config incl. storage paths** → Task 3. ✔
- **Spec §4 MIT LICENSE** → Task 6. ✔
- **Spec §5 no real data in dist + synthetic bootstrap** → Tasks 4, 5. ✔
- **Spec §6 clean README** → Task 6. ✔
- **Spec Data-onboarding (console front door `autoresearch-data`, DataProvider contract, config-driven paths)** → Tasks 5 (entrypoint), 2 (contract), 3 (paths); README section in Task 6. ✔
- **Behavior preservation** → baseline in Task 0; pytest gate + `prepare research` spot-check in every task. ✔
- **Divergence from spec layout (`strategy.py` stays at root)** → documented at top, user-approved 2026-07-02. ✔

Type consistency: `Config` field names (`initial_cash`, `annual_vol_target`, `max_name_weight`, `rebalance_parity`, `backtest_start/end`, `warmup_calendar_days`, `strategy_path`, `journal_path`, `db()`) are referenced identically in Tasks 3, 5, 6. ABC names (`Broker`, `DataProvider`, `StrategyBase`, `CostModel`, `IndiaCostModel`) consistent across Tasks 2, 6.

Residual risks flagged for the implementer: (a) the import-rewrite regex may miss multi-line/aliased imports — Step 1.3 grep gate catches them; (b) `DhanMock` dataclass + `Broker(ABC)` metaclass — fall back to `Broker.register(DhanMock)`; (c) `scripts/loop.py` AST validator base-name check — Task 2 Step 6; (d) CWD-relative ingest DB paths vs repo-root-anchored Config — Task 3 Step 2 note.
