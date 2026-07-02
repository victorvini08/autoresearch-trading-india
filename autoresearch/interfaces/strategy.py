"""Strategy extension point.

Subclass ``StrategyBase`` instead of ``backtrader.Strategy`` directly. It is a
thin marker subclass of ``bt.Strategy`` so the backtest engine treats it
identically, while giving the library a single base to recognise autoresearch
strategies.

Contract: every position change MUST go through ``order_target_percent`` (never
``buy()`` / ``close()``). ``scripts/signal_today.py``'s capture logic and the
executor's target-fraction diffing depend on this. The reference implementation
is ``IndiaMomentumQualityCarry`` in the repo-root ``strategy.py``.
"""

from __future__ import annotations

import backtrader as bt


class StrategyBase(bt.Strategy):
    """Base class for autoresearch strategies (marker subclass of bt.Strategy)."""
