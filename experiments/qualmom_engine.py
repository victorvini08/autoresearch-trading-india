'''IndiaQualityMomentum — momentum winners re-ranked toward high PROFITABILITY
(ROE), high deployment. Same structure as experiments/defmom_engine.py but the
tilt factor is QUALITY (roe_ttm) instead of low-vol — a controlled A/B to test
whether quality is the regime-ROBUST ingredient low-vol was not.

Hypothesis: among confirmed uptrends (momentum-qualified), tilting to high-ROE
DROPS the low-quality "junk momentum" names that crash hardest in a momentum
reversal -> tightens the worst 18-month sub-period (the thing that failed
low-vol @ −1.77 and defensive-momentum @ −1.85) -> could clear the stationarity
gate while keeping/raising return.

PIT-correct: ROE is read as-of each rebalance from fundamentals_quarterly using
`broadcast_date <= rebalance` (the day results were public). Fundamentals exist
2022-07+; names without a prior filing get momentum-rank only (not dropped), so
pre-2022 folds degrade gracefully to pure momentum.

Run via _score_window / run_backtest with the class passed directly.
'''
from __future__ import annotations

import bisect
import logging

from strategy import (
    construct_gross_targets,
    momentum_quality_scores,
    vol_targeted_gross,
)
from experiments.lowvol_engine import IndiaLowVolatilityCarry
from experiments.defmom_engine import _pct_rank

logger = logging.getLogger(__name__)

_MOM_SKIP = 21
_FUND_DB = 'storage/fundamentals.duckdb'


class IndiaQualityMomentum(IndiaLowVolatilityCarry):
    '''Quality(ROE)-tilted momentum, high deployment.'''

    def __init__(self) -> None:
        super().__init__()
        self._roe = self._load_roe()

    def _load_roe(self) -> dict:
        '''{ticker: ([broadcast_date,...] sorted, [roe_ttm,...])} for PIT lookup.'''
        out: dict = {}
        try:
            import duckdb
            con = duckdb.connect(_FUND_DB, read_only=True)
            rows = con.execute(
                "SELECT ticker, broadcast_date, roe_ttm, is_consolidated "
                "FROM fundamentals_quarterly "
                "WHERE roe_ttm IS NOT NULL AND broadcast_date IS NOT NULL "
                "ORDER BY ticker, broadcast_date"
            ).fetchall()
            con.close()
        except Exception:  # noqa: BLE001
            return out
        # prefer consolidated when duplicate (ticker, broadcast_date)
        best: dict = {}
        for tkr, bd, roe, iscons in rows:
            t = str(tkr).upper()
            key = (t, bd)
            if key not in best or (iscons and not best[key][1]):
                best[key] = (float(roe), bool(iscons))
        tmp: dict = {}
        for (t, bd), (roe, _c) in sorted(best.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            tmp.setdefault(t, ([], []))
            tmp[t][0].append(bd)
            tmp[t][1].append(roe)
        return tmp

    def _roe_asof(self, ticker: str, today) -> float | None:
        rec = self._roe.get(ticker)
        if not rec:
            return None
        dates, vals = rec
        i = bisect.bisect_right(dates, today) - 1
        return vals[i] if i >= 0 else None

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

        # quality = PIT ROE as-of today; names without a filing -> momentum-only
        roe = {t: self._roe_asof(t, today) for t in mq}
        roe = {t: v for t, v in roe.items() if v is not None}
        mqr = _pct_rank(mq)
        if len(roe) >= 10:
            qr = _pct_rank(roe)
            scores = {t: (0.5 * mqr[t] + 0.5 * qr[t]) if t in qr else mqr[t] for t in mq}
        else:
            scores = mqr  # too little quality data -> pure momentum (graceful)

        ranked = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
        selected = ranked[:n]
        band = ranked[: 2 * n]
        retained = [t for t in band if t in held]
        new_names = [t for t in band if t not in held]
        priority = retained + new_names

        book = {t: close_by_ticker[t] for t in selected if t in close_by_ticker}
        gross = vol_targeted_gross(close_by_ticker, int(self.p.vol_lookback), book)
        sector_of = {t: (self._sector_map[t].sector if self._sector_map.get(t) else 'OTHER')
                     for t in priority}
        name_cap = gross / float(n)
        targets = (
            construct_gross_targets(priority, sector_of, gross, float(self.p.sector_cap), name_cap=name_cap)
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
        logger.debug('qualmom %s: qualified=%d quality=%d deployed=%d gross=%.2f',
                     today, len(mq), len(roe), len(targets), gross)


__all__ = ['IndiaQualityMomentum']
