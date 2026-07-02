"""The India/Dhan reference classes implement the extension-point ABCs."""

import backtrader as bt

from autoresearch.interfaces import Broker, CostModel, DataProvider, StrategyBase
from autoresearch.brokers.dhan import DhanBroker
from autoresearch.brokers.dhan_mock import DhanMock
from autoresearch.backtest.costs import IndiaCostModel, commission_inr, round_trip_cost_inr
from strategy import IndiaMomentumQualityCarry


def test_brokers_implement_broker():
    assert issubclass(DhanBroker, Broker)
    assert issubclass(DhanMock, Broker)


def test_dhan_mock_instantiates_as_broker():
    # dataclass + ABC must not collide, and all abstract methods are implemented.
    m = DhanMock()
    assert isinstance(m, Broker)


def test_strategy_implements_base_and_is_backtrader():
    assert issubclass(IndiaMomentumQualityCarry, StrategyBase)
    assert issubclass(StrategyBase, bt.Strategy)


def test_cost_model_matches_functions():
    m = IndiaCostModel()
    assert isinstance(m, CostModel)
    assert m.commission(100_000, "BUY") == commission_inr(100_000, "BUY")
    assert m.round_trip_cost(100_000) == round_trip_cost_inr(100_000)


def test_data_provider_is_abstract():
    # Contract-only ABC: cannot instantiate without implementing both methods.
    import pytest

    with pytest.raises(TypeError):
        DataProvider()
