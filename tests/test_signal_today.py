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


# ---------------------------------------------------------------------------
# Live-position seeding: the signal must reflect the LIVE account's holdings,
# not a from-scratch re-simulation (the sim-vs-live divergence fix).
# ---------------------------------------------------------------------------

def test_current_positions_seed_held_state(monkeypatch):
    """When `current_positions` is provided, the strategy must see those
    holdings as its own broker positions on the decision bar — so retention
    logic runs against the LIVE account, not a re-derived imaginary book.

    The toy strategy only ever RETAINS a name it already holds and never
    initiates a new one: with no seed it holds nothing (→ no targets); seeded
    with AAA held it retains AAA. This isolates exactly the held-state input.
    """
    import sys

    class _RetainHeldOnly(bt.Strategy):
        def next(self):
            for d in self.datas:
                if self.getposition(d).size > 0:
                    self.order_target_percent(data=d, target=0.2)

    fake_module = type(sys)("fake_retain_strategy")
    fake_module.RetainHeld = _RetainHeldOnly
    sys.modules["fake_retain_strategy"] = fake_module

    fake_feeds = {
        t: pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1_000_000},
            index=pd.bdate_range("2025-01-01", "2025-03-31"),
        )
        for t in ["AAA", "BBB"]
    }
    monkeypatch.setattr("scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds)
    monkeypatch.setattr("scripts.signal_today.get_universe_at", lambda d: ["AAA", "BBB"])

    # No seed (legacy path) → strategy holds nothing → no targets.
    res_none = generate_signals(
        target_date=date(2025, 3, 31),
        strategy_module_name="fake_retain_strategy",
        lookback_days=90,
    )
    assert res_none["targets"] == []

    # Seed AAA as held → strategy retains AAA at 0.2; BBB (not seeded) untouched.
    res_seed = generate_signals(
        target_date=date(2025, 3, 31),
        strategy_module_name="fake_retain_strategy",
        lookback_days=90,
        current_positions={"AAA": 10},
        current_cash=100_000.0,
    )
    assert {r["ticker"] for r in res_seed["targets"]} == {"AAA"}
    assert res_seed["targets"][0]["target_fraction"] == pytest.approx(0.2)


def test_seeding_does_not_trade_on_warmup_bars(monkeypatch):
    """Seeded mode must let the strategy act ONLY on the final decision bar —
    a strategy that buys every bar must, when seeded, still produce exactly
    its single decision-bar target (no accumulation from replayed bars)."""
    import sys

    class _BuyAAAEveryBar(bt.Strategy):
        def next(self):
            self.order_target_percent(data=self.datas[0], target=0.3)

    fake_module = type(sys)("fake_buyaaa_strategy")
    fake_module.BuyAAA = _BuyAAAEveryBar
    sys.modules["fake_buyaaa_strategy"] = fake_module

    fake_feeds = {
        "AAA": pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 1_000_000},
            index=pd.bdate_range("2025-01-01", "2025-03-31"),
        ),
    }
    monkeypatch.setattr("scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds)
    monkeypatch.setattr("scripts.signal_today.get_universe_at", lambda d: ["AAA"])

    res = generate_signals(
        target_date=date(2025, 3, 31),
        strategy_module_name="fake_buyaaa_strategy",
        lookback_days=90,
        current_positions={},  # empty live book → seeded mode, picks fresh
        current_cash=100_000.0,
    )
    assert {r["ticker"] for r in res["targets"]} == {"AAA"}
    assert res["targets"][0]["target_fraction"] == pytest.approx(0.3)


def test_live_seeding_retains_held_qualifying_names_real_strategy(monkeypatch):
    """Regression for the sim-vs-live divergence (issue #3) on the REAL
    production strategy: any QUALIFYING name the live account already holds
    must be RETAINED when the signal is seeded from live positions — never
    rotated out for a from-scratch re-pick. This is the order-level property
    behind the 2026-06-01 phantom churn (sold FEDERALBNK/BHARATFORG to buy
    TITAN/SHRIRAMFIN despite the live book already holding qualifying names).
    """
    import numpy as np

    # 20 monotonically-rising synthetic names (decreasing slope) → all pass the
    # momentum-quality gate; the feed ends on a real rebalance Friday.
    idx = pd.bdate_range("2025-04-01", "2026-05-29")  # >253 bars; ends Fri 2026-05-29
    names = [f"N{i + 1:02d}" for i in range(20)]
    fake_feeds = {}
    for i, t in enumerate(names):
        close = 100.0 + (len(names) - i) * np.arange(len(idx), dtype=float)
        fake_feeds[t] = pd.DataFrame(
            {"open": close, "high": close * 1.001, "low": close * 0.999,
             "close": close, "volume": 1_000_000},
            index=idx,
        )
    monkeypatch.setattr("scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds)
    monkeypatch.setattr("scripts.signal_today.get_universe_at", lambda d: list(names))

    tdate = date(2026, 6, 1)  # decision bar = last feed bar = Fri 2026-05-29 (rebalance)

    # From-scratch: the strategy re-picks its own book and (being budget/cap
    # bounded) does NOT hold every name.
    scratch = {r["ticker"] for r in generate_signals(target_date=tdate)["targets"]}
    assert scratch, "from-scratch produced no targets (rebalance did not fire?)"
    not_held = sorted(set(names) - scratch)
    assert len(not_held) >= 2, "from-scratch held everything; can't observe rotation"

    # Seed the live book with TWO qualifying names the from-scratch path dropped.
    seed_names = not_held[:2]
    seeded = {
        r["ticker"]
        for r in generate_signals(
            target_date=tdate,
            current_positions={n: 10 for n in seed_names},
            current_cash=100_000.0,
        )["targets"]
    }

    # The fix: those held qualifying names are RETAINED, not phantom-rotated.
    for n in seed_names:
        assert n not in scratch, f"{n} should be absent from the from-scratch pick"
        assert n in seeded, f"{n} (held + qualifying) must be retained when seeded"
    assert seeded != scratch  # the live seed genuinely changes the outcome


def test_carry_forward_fractions_match_live_book_non_rebalance(monkeypatch):
    """Regression for the 2026-06-02 over-leverage bug: on a NON-rebalance day
    the live-seeded carry-forward must report each held name at its TRUE equity
    fraction, not a value inflated by a stale broker total. The bug divided each
    position by cash-only (seeded positions never filled, so the broker's cached
    value excluded them), ~doubling every fraction and levering the paper book
    to ~80% gross. Equity must be cash + marked positions.
    """
    idx = pd.bdate_range("2025-05-01", "2026-06-01")  # ends Mon 2026-06-01 (non-rebalance)
    prices = {"AAA": 100.0, "BBB": 200.0, "CCC": 50.0}
    fake_feeds = {
        t: pd.DataFrame(
            {"open": p, "high": p * 1.001, "low": p * 0.999, "close": p,
             "volume": 1_000_000},
            index=idx,
        )
        for t, p in prices.items()
    }
    monkeypatch.setattr("scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds)
    monkeypatch.setattr("scripts.signal_today.get_universe_at", lambda d: list(prices))

    # Held book: AAA 100×100=10k, BBB 50×200=10k, CCC 100×50=5k → positions 25k;
    # cash 75k → equity 100k. True fractions: 0.10 / 0.10 / 0.05 (gross 0.25).
    live = {"AAA": 100, "BBB": 50, "CCC": 100}
    res = generate_signals(
        target_date=date(2026, 6, 2),
        current_positions=live, current_cash=75_000.0,
    )
    frac = {r["ticker"]: r["target_fraction"] for r in res["targets"]}
    assert frac["AAA"] == pytest.approx(0.10, abs=0.005)   # 10k/100k — NOT 0.133 (the bug)
    assert frac["BBB"] == pytest.approx(0.10, abs=0.005)
    assert frac["CCC"] == pytest.approx(0.05, abs=0.005)
    assert sum(frac.values()) == pytest.approx(0.25, abs=0.01)  # true gross, not ~0.33


def _gated_strategy_module(name: str = "fake_gated_strategy"):
    """A strategy that rebalances ONLY when `_is_rebalance_today()` is True
    (default: never) — mirroring IndiaMomentumQualityCarry's calendar gate.
    Registered as an importable module so generate_signals can load it."""
    import sys

    class _GatedRebalance(bt.Strategy):
        def _is_rebalance_today(self):
            return False  # calendar gate closed on every bar by default

        def next(self):
            if not self._is_rebalance_today():
                return
            self.order_target_percent(data=self.datas[0], target=0.1)

    mod = type(sys)(name)
    mod.GatedRebalance = _GatedRebalance
    sys.modules[name] = mod
    return name


def _gated_feeds(monkeypatch):
    """Flat feeds ending on a NON-rebalance Monday so the calendar gate would
    naturally keep the book flat without the force flag."""
    idx = pd.bdate_range("2025-05-01", "2026-06-01")
    fake_feeds = {
        t: pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
             "volume": 1_000_000},
            index=idx,
        )
        for t in ["AAA", "BBB"]
    }
    monkeypatch.setattr("scripts.signal_today._load_feeds", lambda s, e, t: fake_feeds)
    monkeypatch.setattr("scripts.signal_today.get_universe_at", lambda d: ["AAA", "BBB"])


def test_force_rebalance_deploys_empty_book(monkeypatch):
    """First-day live bootstrap: force_rebalance makes a gated strategy
    rebalance on the seeded decision bar even though its calendar gate is
    closed — so a freshly-funded empty book deploys immediately instead of
    idling until the next rebalance Friday."""
    name = _gated_strategy_module()
    _gated_feeds(monkeypatch)
    res = generate_signals(
        target_date=date(2026, 6, 2),
        strategy_module_name=name,
        current_positions={},          # freshly-funded empty live book
        current_cash=50_000.0,
        force_rebalance=True,
    )
    frac = {r["ticker"]: r["target_fraction"] for r in res["targets"]}
    assert frac.get("AAA") == pytest.approx(0.1)


def test_no_force_leaves_empty_book_flat(monkeypatch):
    """Without the flag, the same gated strategy stays flat on a non-rebalance
    day — exactly the idling the bootstrap exists to prevent."""
    name = _gated_strategy_module()
    _gated_feeds(monkeypatch)
    res = generate_signals(
        target_date=date(2026, 6, 2),
        strategy_module_name=name,
        current_positions={},
        current_cash=50_000.0,
        force_rebalance=False,
    )
    assert res["targets"] == []


def test_force_rebalance_ignored_on_legacy_path(monkeypatch):
    """force_rebalance is honoured ONLY on the seeded path. The legacy
    from-scratch replay (current_positions=None) must ignore it so backtests
    and the gated rebalance calendar stay untouched."""
    name = _gated_strategy_module()
    _gated_feeds(monkeypatch)
    res = generate_signals(
        target_date=date(2026, 6, 2),
        strategy_module_name=name,
        current_positions=None,        # legacy path
        force_rebalance=True,
    )
    assert res["targets"] == []
