"""Single-day signal generator — extract target positions from a frozen strategy.

Runs the production strategy on price history through a target date, lets
orders fill normally inside the in-memory cerebro broker (so the strategy
correctly sees its own `self.getposition(d)`), and intercepts every
`order_target_percent()` call to record the latest-target-per-ticker.

At end of run, the captured dict reflects the strategy's most recent
target for every ticker it ever addressed — which on a well-formed
rotation strategy equals exactly the current portfolio (held tickers at
their target weight, rotated-out tickers at 0).

Historical note: an earlier implementation deliberately did NOT call
super().order_target_percent — it suppressed fills entirely. That broke
any strategy whose rebalance logic reads `self.getposition(d).size`
(the production momentum-rotation strategy does this at strategy.py:343).
With fills suppressed, the strategy saw itself as holding nothing, so it
never issued explicit exit calls, and `captured` accumulated stale targets
for every ticker that was ever a buy. The fix is to let orders fill so the
strategy's "held vs new" logic runs against accurate broker state.

Output: JSON to stdout (or `--output` file), shape:
    {
      "as_of_date": "2026-05-09",
      "strategy_module": "strategy",
      "strategy_class": "IndiaMomentumQualityRegime",
      "targets": [
        {"ticker": "RELIANCE", "target_fraction": 0.165},
        {"ticker": "INFY", "target_fraction": 0.165},
        ...
      ],
      "exits": [
        {"ticker": "TCS", "target_fraction": 0.0},
        ...
      ]
    }

Usage:
    uv run python -m scripts.signal_today
    uv run python -m scripts.signal_today --date 2026-05-09
    uv run python -m scripts.signal_today --output today_signals.json

Lookback: by default loads ~500 trading days (~2 calendar years) before the
target date so all warmup indicators in the strategy are populated. Override
with --lookback-days.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import backtrader as bt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.ingest_prices import read_prices  # noqa: E402
from data.universe import get_universe_at  # noqa: E402


_MIN_BARS_PER_FEED = 60


def _load_feeds(
    start: date, end: date, tickers: list[str]
) -> dict[str, pd.DataFrame]:
    """Same shape as prepare._load_feeds — loads OHLCV in [start, end]."""
    feeds: dict[str, pd.DataFrame] = {}
    for tkr in tickers:
        df = read_prices(tkr, start.isoformat(), end.isoformat())
        if len(df) < _MIN_BARS_PER_FEED:
            continue
        df = df.set_index(pd.DatetimeIndex(df["date"])).drop(columns=["date"])
        feeds[tkr] = df
    if not feeds:
        raise RuntimeError(
            f"No price data with >= {_MIN_BARS_PER_FEED} bars in "
            f"[{start}, {end}]. Run data.ingest_prices first."
        )
    return feeds


def _find_strategy_class(module) -> type:
    """Return the single bt.Strategy subclass defined in `module`."""
    candidates = [
        cls for _, cls in inspect.getmembers(module, inspect.isclass)
        if issubclass(cls, bt.Strategy) and cls is not bt.Strategy
    ]
    if not candidates:
        raise RuntimeError(f"No bt.Strategy subclass in {module.__name__}")
    if len(candidates) > 1:
        names = [c.__name__ for c in candidates]
        raise RuntimeError(
            f"Multiple bt.Strategy subclasses in {module.__name__}: {names}"
        )
    return candidates[0]


def _make_capturing_strategy(strategy_cls: type) -> tuple[type, dict]:
    """Subclass `strategy_cls`. Lets order_target_percent fill normally
    (super() called) AND tracks each bar's order_target_percent calls so the
    LAST non-empty bar's intents can be combined with broker state in
    generate_signals to produce an accurate portfolio projection.

    Why both: broker state at end of run reflects bar D-1's orders that
    filled at bar D's open. Bar D's own order_target_percent calls are
    queued but never fill (no D+1 bar in the signal-extraction window).
    To project the portfolio AT D+1's open (which is what paper_trade
    fills against), we need:
      (a) current broker positions (today's actual holdings), AND
      (b) bar D's intents (overlay on top — exits zero out, buys add).

    Tracking last-non-empty-bar's calls (not just the last bar's) handles
    the case where target_date isn't a rebalance day. On a non-rebalance
    bar the strategy returns early (rebalance gate) and issues no calls;
    the most recent rebalance's intent is what we still want to apply.

    Returns (CapturingClass, captured_dict). The captured dict is mutated
    by the override AND by generate_signals' projection step. After the
    cerebro run, generate_signals clears `captured` and refills it with
    the broker-state + last-rebalance-overlay projection.
    """
    captured: dict[str, float] = {}

    class _SignalCapture(strategy_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._calls_this_bar: dict[str, float] = {}
            self._last_rebalance_calls: dict[str, float] = {}

        def order_target_percent(self, data=None, target=0.0, **kwargs):  # type: ignore[override]
            if data is None:
                data = self.data
            ticker = data._name
            self._calls_this_bar[ticker] = float(target)
            captured[ticker] = float(target)
            return super().order_target_percent(data=data, target=target, **kwargs)

        def next(self):
            self._calls_this_bar = {}
            super().next()
            if self._calls_this_bar:
                self._last_rebalance_calls = dict(self._calls_this_bar)

    _SignalCapture.__name__ = f"{strategy_cls.__name__}_SignalCapture"
    return _SignalCapture, captured


def _project_portfolio(strat, captured: dict[str, float]) -> dict[str, float]:
    """Compute the strategy's intended portfolio for the next session.

    projection = (current broker positions as fractions of equity)
                 OVERLAID with (the strategy's most recent rebalance intents).

    Tickers in last_rebalance_calls override broker fractions (so a held
    ticker just instructed to exit shows as 0, and a new buy shows at its
    target even though the order hasn't filled yet).

    Tickers in broker positions but NOT in last_rebalance_calls carry forward
    at their current fraction (the strategy didn't touch them this rebalance,
    so the existing position is the intent).

    The returned dict replaces `captured`'s contents in generate_signals.
    """
    projected: dict[str, float] = {}
    broker_value = float(strat.broker.get_value())

    if broker_value > 0:
        for d in strat.datas:
            pos = strat.broker.getposition(d)
            if pos.size == 0:
                continue
            close_px = float(d.close[0])
            pos_value = pos.size * close_px
            projected[d._name] = round(pos_value / broker_value, 6)

    # Overlay the strategy's most recent non-empty rebalance intents
    last_calls = getattr(strat, "_last_rebalance_calls", {}) or {}
    for ticker, target in last_calls.items():
        projected[ticker] = round(float(target), 6)

    return projected


def generate_signals(
    target_date: date,
    strategy_module_name: str = "strategy",
    lookback_days: int = 500,
) -> dict:
    """Generate target positions as of `target_date` from `strategy_module_name`.

    Returns the structured dict described in this script's docstring.
    """
    strategy_module = importlib.import_module(strategy_module_name)
    strategy_cls = _find_strategy_class(strategy_module)

    start = target_date - timedelta(days=lookback_days)
    universe = get_universe_at(target_date)
    feeds = _load_feeds(start, target_date, universe)

    # Look-ahead guard: the cerebro feed must NOT include target_date's own
    # bar — that would let the strategy size today's targets against today's
    # CLOSE while we're still in the trading session, which is future data.
    # In normal ops daily_update runs at 09:30 IST and can't ingest today's
    # bhav (not published until ~6pm IST), so feeds reliably end at T-1.
    # If a future change ever lands today's row before market close, this
    # assertion makes the look-ahead loud instead of silently profitable.
    # NOTE: replay/backfill (target_date in the past) intentionally allows
    # last_bar == target_date — there is no future to leak into.
    last_bar = max(df.index.max().date() for df in feeds.values())
    if last_bar >= target_date and target_date >= date.today():
        raise RuntimeError(
            f"signal_today look-ahead guard: feeds contain bar dated "
            f"{last_bar} but target_date={target_date} is today/future. "
            "This would let the strategy use future close as a decision input. "
            "Either run after market close, or roll target_date forward to "
            "the next trading session."
        )

    capture_cls, captured = _make_capturing_strategy(strategy_cls)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100_000.0)
    for ticker, df in feeds.items():
        data = bt.feeds.PandasData(
            dataname=df, name=ticker, fromdate=start, todate=target_date,
        )
        cerebro.adddata(data)
    cerebro.addstrategy(capture_cls)
    results = cerebro.run()
    strat = results[0]

    # Replace the raw captured dict (which accumulates stale targets when
    # backtrader rejects buys mid-run) with the projection: broker state +
    # most-recent-rebalance overlay. See _project_portfolio for rationale.
    projected = _project_portfolio(strat, captured)
    captured.clear()
    captured.update(projected)

    # I-6: Reject negative target fractions — this infrastructure is long-only.
    # A buggy strategy attempting a short must fail loudly rather than being
    # silently dropped.
    negatives = {t: v for t, v in captured.items() if v < 0.0}
    if negatives:
        raise ValueError(
            f"signal_today does not support short targets (negative fractions): {negatives}. "
            f"This strategy attempted a short position via order_target_percent."
        )

    # Split captured into entries (target > 0) and exits (target == 0).
    targets = sorted(
        ({"ticker": t, "target_fraction": round(v, 6)}
         for t, v in captured.items() if v > 0.0),
        key=lambda r: -r["target_fraction"],
    )
    exits = sorted(
        ({"ticker": t, "target_fraction": 0.0}
         for t, v in captured.items() if v == 0.0),
        key=lambda r: r["ticker"],
    )

    return {
        "as_of_date": target_date.isoformat(),
        "strategy_module": strategy_module_name,
        "strategy_class": strategy_cls.__name__,
        "targets": targets,
        "exits": exits,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--date", type=date.fromisoformat, default=date.today(),
        help="Target date (default: today).",
    )
    p.add_argument(
        "--lookback-days", type=int, default=500,
        help="Trading-history lookback for strategy warmup (default 500 days).",
    )
    p.add_argument(
        "--strategy-module", default="strategy",
        help="Module name to import (default: 'strategy').",
    )
    p.add_argument(
        "--output", type=Path, default=None,
        help="Write JSON to this path. Default: stdout.",
    )
    args = p.parse_args(argv)

    result = generate_signals(
        target_date=args.date,
        strategy_module_name=args.strategy_module,
        lookback_days=args.lookback_days,
    )
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
        print(f"wrote {len(result['targets'])} targets + "
              f"{len(result['exits'])} exits to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
