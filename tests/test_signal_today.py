"""Signal generator tests — use a synthetic in-memory strategy + feeds so the
test doesn't depend on the real strategy.py at HEAD or on stored prices."""
from datetime import date
import backtrader as bt
import pandas as pd
import pytest

from scripts.signal_today import (
    _find_strategy_class,
    _make_capturing_strategy,
    generate_signals,
)


class _ToyEqualWeight(bt.Strategy):
    """Trivial strategy: on every bar, set every feed to 1/N of equity."""

    def next(self):
        n = len(self.datas)
        for d in self.datas:
            self.order_target_percent(data=d, target=1.0 / n)


class _ToyDropOne(bt.Strategy):
    """Targets the FIRST data at 0.1 and EXPLICITLY exits the second."""

    def next(self):
        if len(self.datas) >= 1:
            self.order_target_percent(data=self.datas[0], target=0.1)
        if len(self.datas) >= 2:
            self.order_target_percent(data=self.datas[1], target=0.0)


def _toy_feed(name: str, start: str, end: str, base_price: float = 100.0) -> bt.feeds.PandasData:
    """Build a synthetic daily-OHLCV feed (flat prices) for backtrader."""
    idx = pd.bdate_range(start=start, end=end)
    df = pd.DataFrame(
        {
            "open": base_price,
            "high": base_price * 1.01,
            "low": base_price * 0.99,
            "close": base_price,
            "volume": 1_000_000,
        },
        index=idx,
    )
    return bt.feeds.PandasData(dataname=df, name=name)


def test_capturing_strategy_lets_orders_fill():
    """The capturing strategy MUST let order_target_percent fill normally —
    otherwise any strategy that branches on self.getposition(d).size sees
    itself as flat and produces wrong captured state.
    """
    cls, captured = _make_capturing_strategy(_ToyEqualWeight)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100_000.0)
    cerebro.adddata(_toy_feed("AAA", "2025-01-01", "2025-01-15"))
    cerebro.adddata(_toy_feed("BBB", "2025-01-01", "2025-01-15"))
    cerebro.addstrategy(cls)
    results = cerebro.run()
    strat = results[0]

    # Captured records the raw order_target_percent calls (latest-wins per ticker)
    assert captured == {"AAA": 0.5, "BBB": 0.5}
    # Orders DO fill — broker cash drops and both positions are non-zero.
    assert cerebro.broker.getcash() < 100_000.0
    assert strat.broker.getposition(strat.datas[0]).size > 0
    assert strat.broker.getposition(strat.datas[1]).size > 0
    # The per-bar tracker captured this bar's calls as the last rebalance
    assert strat._last_rebalance_calls == {"AAA": 0.5, "BBB": 0.5}


def test_rotation_projection_matches_final_holdings(monkeypatch):
    """End-to-end via generate_signals: a rotation strategy that issues
    order_target_percent only for held+exiting and in-target tickers must
    produce a final signal that matches the FINAL holdings, not the union of
    every ticker that was ever a buy.

    Without the broker-state-based projection in signal_today, captured
    accumulates targets for tickers whose buys failed in backtrader's cash
    queue, summing far above the strategy's intended gross. With projection,
    the result reflects actual portfolio state.
    """
    import sys

    class _ThreeWayRotation(bt.Strategy):
        """Holds AAA for bars 0-3, rotates to BBB for bars 4-7, then CCC."""

        def __init__(self):
            self._bar = 0

        def next(self):
            self._bar += 1
            phase = (self._bar - 1) // 4
            target_name = {0: "AAA", 1: "BBB", 2: "CCC"}.get(phase, "CCC")
            for d in self.datas:
                held = self.getposition(d).size != 0
                in_target = d._name == target_name
                if held and not in_target:
                    self.order_target_percent(data=d, target=0.0)
                elif in_target:
                    self.order_target_percent(data=d, target=0.10)

    fake_module = type(sys)("fake_rotation_strategy")
    fake_module.RotationStrategy = _ThreeWayRotation
    sys.modules["fake_rotation_strategy"] = fake_module

    fake_feeds = {
        t: pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1_000_000},
            index=pd.bdate_range("2025-01-01", "2025-01-20"),
        )
        for t in ["AAA", "BBB", "CCC"]
    }
    monkeypatch.setattr(
        "scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds,
    )
    monkeypatch.setattr(
        "scripts.signal_today.get_universe_at", lambda d: ["AAA", "BBB", "CCC"],
    )

    result = generate_signals(
        target_date=date(2025, 1, 20),
        strategy_module_name="fake_rotation_strategy",
        lookback_days=90,
    )

    # Final phase is CCC. Projection should show CCC held at ~10% gross.
    # AAA and BBB rotated out earlier (multiple bars ago) — they're not in
    # the last rebalance's calls AND not in broker state, so they don't
    # appear in the signal at all. Paper_trade handles "held in ledger but
    # not in signals" as implicit exits via its own ledger comparison.
    target_tickers = {t["ticker"] for t in result["targets"]}
    assert target_tickers == {"CCC"}
    ccc = next(t for t in result["targets"] if t["ticker"] == "CCC")
    assert ccc["target_fraction"] == pytest.approx(0.10, abs=0.005)
    # Gross sum is exactly the rotation's intended exposure, not 3× from
    # accumulated stale targets.
    gross = sum(t["target_fraction"] for t in result["targets"])
    assert gross == pytest.approx(0.10, abs=0.005)


def test_overrides_keep_latest_target_per_ticker():
    """Strategy fires order_target_percent on every bar — the captured value
    should be the last bar's value, not an accumulation."""
    class _ChangingTarget(bt.Strategy):
        def next(self):
            # Targets shrink over time: 0.5 → 0.4 → 0.3 → ...
            bar_idx = len(self) - 1
            t = max(0.5 - bar_idx * 0.05, 0.05)
            self.order_target_percent(data=self.data, target=t)

    cls, captured = _make_capturing_strategy(_ChangingTarget)
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100_000.0)
    cerebro.adddata(_toy_feed("AAA", "2025-01-01", "2025-01-10"))
    cerebro.addstrategy(cls)
    cerebro.run()

    # Bar-by-bar target shrinks. Last bar wins regardless of how many bars
    # ran — the captured value should be at-or-near the strategy's floor.
    # (The exact value depends on the bdate range; floor is 0.05.)
    assert pytest.approx(captured["AAA"], abs=0.01) == 0.15


def test_find_strategy_class_picks_single_subclass():
    class _M:
        Strategy = bt.Strategy

        class S(bt.Strategy):
            pass

    cls = _find_strategy_class(_M)
    assert cls is _M.S


def test_find_strategy_class_raises_on_multiple():
    class _M:
        class S1(bt.Strategy):
            pass

        class S2(bt.Strategy):
            pass

    with pytest.raises(RuntimeError, match="Multiple"):
        _find_strategy_class(_M)


def test_find_strategy_class_raises_on_none():
    class _M:
        pass  # noqa: PIE790

    with pytest.raises(RuntimeError, match="No bt.Strategy subclass"):
        _find_strategy_class(_M)


def test_generate_signals_splits_targets_and_exits(monkeypatch):
    """Integration test: end-to-end signal generation with a toy strategy."""
    # 1. Stub the strategy module to use our _ToyDropOne
    import sys
    fake_module = type(sys)("fake_strategy")
    fake_module.MyStrategy = _ToyDropOne
    sys.modules["fake_strategy"] = fake_module

    # 2. Stub _load_feeds + get_universe_at so the real DBs aren't read
    fake_feeds = {
        "AAA": pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1_000_000},
            index=pd.bdate_range("2025-01-01", "2025-03-31"),
        ),
        "BBB": pd.DataFrame(
            {"open": 50.0, "high": 50.5, "low": 49.5,
             "close": 50.0, "volume": 500_000},
            index=pd.bdate_range("2025-01-01", "2025-03-31"),
        ),
    }
    monkeypatch.setattr(
        "scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds,
    )
    monkeypatch.setattr(
        "scripts.signal_today.get_universe_at", lambda d: ["AAA", "BBB"],
    )

    result = generate_signals(
        target_date=date(2025, 3, 31),
        strategy_module_name="fake_strategy",
        lookback_days=90,
    )

    assert result["as_of_date"] == "2025-03-31"
    assert result["strategy_class"] == "_ToyDropOne"
    # _ToyDropOne sets AAA to 0.1 and BBB to 0.0
    assert {r["ticker"] for r in result["targets"]} == {"AAA"}
    assert result["targets"][0]["target_fraction"] == 0.1
    assert {r["ticker"] for r in result["exits"]} == {"BBB"}


# ---------------------------------------------------------------------------
# I-6: negative target fractions raise ValueError
# ---------------------------------------------------------------------------

def test_negative_target_raises(monkeypatch):
    """A strategy that calls order_target_percent with target < 0 (attempting
    a short) must trigger a ValueError from generate_signals with 'short' in
    the message.
    """
    import sys

    class _ShortingStrategy(bt.Strategy):
        def next(self):
            self.order_target_percent(data=self.datas[0], target=-0.1)

    fake_module = type(sys)("fake_short_strategy")
    fake_module.ShortingStrategy = _ShortingStrategy
    sys.modules["fake_short_strategy"] = fake_module

    fake_feeds = {
        "AAA": pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1_000_000},
            index=pd.bdate_range("2025-01-01", "2025-03-31"),
        ),
    }
    monkeypatch.setattr(
        "scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds,
    )
    monkeypatch.setattr(
        "scripts.signal_today.get_universe_at", lambda d: ["AAA"],
    )

    with pytest.raises(ValueError, match="short"):
        generate_signals(
            target_date=date(2025, 3, 31),
            strategy_module_name="fake_short_strategy",
            lookback_days=90,
        )
