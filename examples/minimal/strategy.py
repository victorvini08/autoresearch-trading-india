"""A minimal autoresearch strategy — subclass StrategyBase, trade via
order_target_percent only.

Toy cross-sectional momentum: on a fixed cadence, hold the top-`n_hold` names
by trailing `lookback`-day return, equal-weight. This is the smallest thing
that exercises the StrategyBase contract; the real reference strategy is the
repo-root strategy.py (IndiaMomentumQualityCarry).
"""

from autoresearch.interfaces import StrategyBase


class MinimalMomentum(StrategyBase):
    # `universe_by_date` is injected by the evaluator; declared so autoresearch-eval
    # works too (this strategy trades all feeds = the universe the evaluator passes).
    params = dict(lookback=60, n_hold=5, rebalance_every=20, universe_by_date=None)

    def __init__(self):
        self._bar = 0

    def next(self):
        self._bar += 1
        if self._bar % self.p.rebalance_every != 0:
            return

        scores = {}
        for d in self.datas:
            if len(d) > self.p.lookback and d.close[-self.p.lookback] > 0:
                scores[d] = d.close[0] / d.close[-self.p.lookback] - 1.0
        if not scores:
            return

        winners = sorted(scores, key=scores.get, reverse=True)[: self.p.n_hold]
        weight = 1.0 / self.p.n_hold
        held = set(winners)
        for d in self.datas:
            # Every position change goes through order_target_percent (contract).
            self.order_target_percent(d, target=weight if d in held else 0.0)
