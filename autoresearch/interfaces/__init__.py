"""Extension points for building your own autoresearch trading system.

Implement these four ABCs to target a new broker, market, strategy, or cost
structure. The India/Dhan classes in this package are the reference
implementations:

- ``Broker``        → ``autoresearch.brokers.dhan.DhanBroker`` / ``DhanMock``
- ``DataProvider``  → NSE bhav archive ingest in ``autoresearch.data``
- ``StrategyBase``  → ``IndiaMomentumQualityCarry`` (repo-root ``strategy.py``)
- ``CostModel``     → ``autoresearch.backtest.costs.IndiaCostModel``
"""

from .broker import Broker
from .cost_model import CostModel
from .data_provider import DataProvider
from .strategy import StrategyBase

__all__ = ["Broker", "CostModel", "DataProvider", "StrategyBase"]
