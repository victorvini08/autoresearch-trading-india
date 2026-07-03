"""``autoresearch-init`` — scaffold a new autoresearch trading project.

Creates a small project of the files YOU own (the library stays installed and
untouched). The generated project RUNS immediately on synthetic data:

    autoresearch-init my-project
    cd my-project
    python run.py

Then you edit three things, in order: your strategy (`strategy.py`), your data
(`provider.py`), and the knobs (`config.py`). Everything is a plain file — the
autoresearch loop rewrites `strategy.py` in place, which is exactly why these
live in your project and not inside the installed package.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_STRATEGY = '''\
"""Your strategy — EDIT THIS FILE. The autoresearch loop rewrites it in place.

Contract: change positions ONLY through order_target_percent (never buy() /
close()). The signal-capture and executor layers depend on it.
"""

from autoresearch.interfaces import StrategyBase


class MyStrategy(StrategyBase):
    # Tune these, or let the autoresearch loop evolve the whole class.
    # `universe_by_date` is injected by the evaluator (autoresearch-eval); declare
    # it so evaluation works. This strategy trades all its feeds, which ARE the
    # point-in-time universe the evaluator passes, so it respects it by construction.
    params = dict(lookback=60, n_hold=5, rebalance_every=20, universe_by_date=None)

    def __init__(self):
        self._bar = 0

    def next(self):
        self._bar += 1
        if self._bar % self.p.rebalance_every != 0:
            return

        # Toy cross-sectional momentum: hold the top-n by trailing return.
        scores = {}
        for d in self.datas:
            if len(d) > self.p.lookback and d.close[-self.p.lookback] > 0:
                scores[d] = d.close[0] / d.close[-self.p.lookback] - 1.0
        if not scores:
            return

        winners = set(sorted(scores, key=scores.get, reverse=True)[: self.p.n_hold])
        weight = 1.0 / self.p.n_hold
        for d in self.datas:
            self.order_target_percent(d, target=weight if d in winners else 0.0)
'''

_PROVIDER = '''\
"""Your market data — EDIT THIS FILE to trade a real market.

It ships wired to the library's synthetic generator so `python run.py` works
immediately. When you're ready for real data, implement your own DataProvider
(read_prices + pit_universe) and return it from make_provider().
"""

from autoresearch.data.synthetic import SyntheticDataProvider


def make_provider():
    # Works out of the box on deterministic synthetic data:
    return SyntheticDataProvider()

    # --- To bring your own market, implement this and return it above: ---
    #
    # from datetime import date
    # from autoresearch.interfaces import DataProvider
    #
    # class MyProvider(DataProvider):
    #     def read_prices(self, tickers, start, end):
    #         """Return {ticker: OHLCV DataFrame indexed by date}.
    #            Columns: open, high, low, close, volume  (split/bonus-adjusted close)."""
    #         ...
    #     def pit_universe(self, as_of, size):
    #         """Return the top-`size` liquid tickers as of `as_of` (point-in-time,
    #            derived from price history — never a 'current members' list)."""
    #         ...
    # return MyProvider()
'''

_RUN = '''\
"""Run a backtest of your strategy on your data. Start here:  python run.py"""

from datetime import date

from autoresearch.backtest.engine import run_backtest

from config import CONFIG
from provider import make_provider
from strategy import MyStrategy


def main():
    provider = make_provider()
    universe = provider.pit_universe(date(2019, 1, 1), size=30)
    feeds = provider.read_prices(universe, date(2019, 1, 1), date(2022, 12, 31))

    result = run_backtest(MyStrategy, feeds, initial_cash=CONFIG.initial_cash)

    print(f"universe    : {len(feeds)} tickers")
    print(f"final value : {result['final_value']:,.2f}")
    print(f"return      : {result['final_value'] / CONFIG.initial_cash - 1:+.2%}")
    print(f"trades      : {result['trade_count']}")


if __name__ == "__main__":
    main()
'''

_CONFIG = '''\
"""Your knobs — EDIT THIS FILE. Defaults are the India reference values."""

from autoresearch.config import Config

CONFIG = Config(
    currency="INR",
    initial_cash=50_000.0,
    universe_size=200,
    annual_vol_target=0.12,
    # backtest_start / backtest_end / storage_dir / strategy_path ... also live here.
)
'''

_JOURNAL = '''\
# Research journal

Append-only memory for the autoresearch loop. Each iteration the loop reads the
recent entries here, proposes ONE edit to `strategy.py`, runs the evaluator, and
records the hypothesis + result + KEEP/REVERT decision below.

Start writing your own hypotheses here, or run:

    python -m scripts.loop --iterations 1   # (from a clone of the reference repo)

---
'''

_README = '''\
# {name}

A trading project built on [`autoresearch-trading`](https://pypi.org/project/autoresearch-trading/).

## Run it now (synthetic data, no setup)

```bash
python run.py
```

## Then edit, in order

1. **`strategy.py`** — your signal (`MyStrategy(StrategyBase)`), positions via
   `order_target_percent` only.
2. **`provider.py`** — your market data. Ships on synthetic data; implement your
   own `DataProvider` when ready.
3. **`config.py`** — capital, universe size, cadence, vol target, dates.

## Files

| File | Yours to edit? | What it is |
|---|---|---|
| `strategy.py` | ✎ (the loop edits it too) | Your strategy |
| `provider.py` | ✎ | Where prices + universe come from |
| `config.py`   | ✎ | The knobs |
| `journal.md`  | ✎ (loop appends) | Research memory |
| `run.py`      | rarely | Wires the above through the backtest engine |
'''

_GITIGNORE = '''\
__pycache__/
*.py[cod]
.venv/
.env
storage/*.duckdb
storage/*.sqlite
'''

_ENV = '''\
# Optional — only needed if your DataProvider fetches macro/broker data.
FRED_API_KEY=
# DHAN_ACCESS_TOKEN=
# DHAN_CLIENT_ID=
'''


def scaffold(target: Path) -> None:
    """Write the starter project into `target` (which must be empty or new)."""
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"error: {target} already exists and is not empty")

    (target / "storage").mkdir(parents=True, exist_ok=True)
    files = {
        "strategy.py": _STRATEGY,
        "provider.py": _PROVIDER,
        "run.py": _RUN,
        "config.py": _CONFIG,
        "journal.md": _JOURNAL,
        "README.md": _README.format(name=target.name),
        ".gitignore": _GITIGNORE,
        ".env.example": _ENV,
    }
    for name, content in files.items():
        (target / name).write_text(content)
    (target / "storage" / ".gitkeep").write_text("")

    print(f"Created autoresearch project in {target}/\n")
    print("Next steps:")
    print(f"  cd {target}")
    print("  python run.py            # runs immediately on synthetic data")
    print("  # then edit strategy.py -> provider.py -> config.py")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="autoresearch-init",
        description="Scaffold a new autoresearch trading project.",
    )
    ap.add_argument("name", help="project directory to create (e.g. my-quant)")
    args = ap.parse_args()
    scaffold(Path(args.name))


if __name__ == "__main__":
    sys.exit(main())
