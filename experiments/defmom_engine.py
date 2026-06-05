'''IndiaDefensiveMomentum — "the calmest of the winners", high-deployment.

Synthesis of the two engines' strengths, motivated by the gate diagnosis:
  - Plain LOW-VOL fails sub_period_stationarity because it holds the calmest
    names REGARDLESS of trend, so in a drifting-down regime it sits in calm
    LOSERS -> a negative 18-month sub-period (-1.77 @5L).
  - MOMENTUM passes stationarity because it only ever holds confirmed
    uptrends (positive every regime), but it under-returns and deploys ~46%.

This engine takes the MOMENTUM-QUALIFIED set (positive 12-1, above its trend MA
-- the property that makes momentum regime-robust), then RE-RANKS it 50/50
toward LOW realised volatility ("buy the calmest winners"), and deploys it with
the LOW-VOL engine's book-referenced downside-vol target (so a calm book of
winners deploys high -> the return engine). Equal-weight, same bounded
construction + caps.

Inherits IndiaLowVolatilityCarry (high-deployment + equal-weight construction);
overrides ONLY the selection scoring. Run via _score_window with the class
passed directly (never prepare.evaluate's _find_strategy_class), so importing
the parent for inheritance is fine.

No new tunable hyperparameter vs the low-vol engine: the momentum skip
(formation) is hardcoded to the locked book's 21, and the 50/50 factor weight
is the neutral/principled split (not searched). Counts 3 hyperparameters
(vol_lookback, n_names, sector_cap) like the low-vol engine.
'''
from __future__ import annotations

import logging

import numpy as np

from strategy import (
    construct_gross_targets,
    momentum_quality_scores,
    vol_targeted_gross,
)
from experiments.lowvol_engine import IndiaLowVolatilityCarry, low_volatility_scores

logger = logging.getLogger(__name__)

_MOM_SKIP = 21  # locked momentum formation_days; not a new tunable knob


def _pct_rank(d: dict[str, float]) -> dict[str, float]:
    '''Cross-sectional percentile rank in [0,1]; higher value -> higher rank.'''
    if not d:
        return {}
    items = sorted(d.items(), key=lambda kv: kv[1])
    n = len(items)
    if n == 1:
        return {items[0][0]: 0.5}
    return {t: i / (n - 1) for i, (t, _) in enumerate(items)}


class IndiaDefensiveMomentum(IndiaLowVolatilityCarry):
    '''Calmest-of-the-winners, downside-vol-targeted (high-deployment).'''

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)
        active = self._active_universe(today)
        held = self._exit_ineligible_held(self._held_positions(), active)
        close_by_ticker, adv_by_ticker = self._close_and_adv(active)

        n = max(1, int(self.p.n_names))
        if len(close_by_ticker) < 3:
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        # 1) momentum-QUALIFIED set (positive 12-1 + above trend MA): the
        #    property that keeps the book in confirmed uptrends every regime.
        mq = momentum_quality_scores(
            close_by_ticker, adv_by_ticker, int(self.p.vol_lookback), _MOM_SKIP
        )
        if not mq:
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        # 2) re-rank the winners 50/50 toward LOW realised vol (calmest winners)
        lv = low_volatility_scores(
            {t: close_by_ticker[t] for t in mq}, int(self.p.vol_lookback)
        )
        mqr = _pct_rank(mq)
        lvr = _pct_rank(lv)
        scores = {t: 0.5 * mqr[t] + 0.5 * lvr.get(t, 0.0) for t in mq}

        ranked = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
        selected = ranked[:n]
        band = ranked[: 2 * n]
        retained = [t for t in band if t in held]
        new_names = [t for t in band if t not in held]
        priority = retained + new_names

        # 3) deploy with the book-referenced downside-vol target (calm book of
        #    winners -> high gross; if few winners qualify -> book thin ->
        #    fallback to broad-universe vol -> lower gross -> bear defense).
        book_close_by_ticker = {
            t: close_by_ticker[t] for t in selected if t in close_by_ticker
        }
        gross = vol_targeted_gross(
            close_by_ticker, int(self.p.vol_lookback), book_close_by_ticker
        )
        sector_of = {
            t: (self._sector_map[t].sector if self._sector_map.get(t) else 'OTHER')
            for t in priority
        }
        name_cap = gross / float(n)
        targets = (
            construct_gross_targets(priority, sector_of, gross,
                                    float(self.p.sector_cap), name_cap=name_cap)
            if self.p.enforce_sector_cap and self._sector_map
            else construct_gross_targets(priority, {}, gross, 1.0, name_cap=name_cap)
        )
        for d in self.datas:
            t = self._ticker_of(d)
            if t in targets:
                self.order_target_percent(d, target=targets[t])
            elif t in held:
                self.order_target_percent(d, target=0.0)
        self._last_rebalance_date = today
        logger.debug('defmom %s: qualified=%d, deployed=%d, gross=%.2f',
                     today, len(mq), len(targets), gross)


__all__ = ['IndiaDefensiveMomentum']
