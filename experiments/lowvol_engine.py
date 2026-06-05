'''IndiaLowVolatilityCarry — long-only downside-vol-targeted LOW-VOLATILITY engine.

Production candidate (2026-06-04). This is the SAME chassis as the locked
``strategy.IndiaMomentumQualityCarry`` — point-in-time universe, biweekly
rebalance, the locked downside-vol-targeted gross overlay
(``strategy.vol_targeted_gross``), and the bounded gross-targeting construction
(``strategy.construct_gross_targets``) — with exactly ONE change:

    the SELECTION signal is LOWEST TRAILING REALISED VOLATILITY,
    instead of 12-1 cross-sectional momentum-quality.

Why this is the genuine, robust improvement (validated in
``experiments.low_vol_deploy``; see memory ``project_lowvol_engine_found``):
because low-vol names have low realised vol BY CONSTRUCTION, the SAME 0.12
downside-vol target deploys ~full gross (~95%) for this book, versus the
momentum book's ~46%. The deployment lever that *blew the drawdown budget* on
the high-beta momentum book is *safe* on a low-vol book. That high deployment
is the validated source of the bull-participation / recovery-catch the momentum
book structurally misses, while low-vol SELECTION supplies the crash defence —
two independent, well-documented mechanisms (the low-volatility anomaly +
downside-vol-managed deployment), not regime luck.

Construction is EQUAL-WEIGHT within the gross budget (``gross / n_names`` per
name, bounded by the same per-name and per-sector caps as the locked book) so
the book stays diversified — the low-vol premium is a diversification effect,
not a concentration bet. The single-name weight (~3.3% at full gross) is far
under the locked 10% hard cap, so concentration is bounded MORE conservatively
than the momentum book (CLAUDE.md hard-constraint §10 satisfied a fortiori).

No structural-MA exit (that is a momentum/trend device; low-vol names mean-revert
on routine dips, so an MA exit would churn the book — it was not part of the
validated low-vol overlay and is deliberately omitted here).

Helper methods (_load_sector_map, _close_and_adv, _exit_ineligible_held,
_is_rebalance_today, ...) are duplicated from ``strategy`` rather than inherited:
``prepare._find_strategy_class`` requires EXACTLY ONE ``bt.Strategy`` subclass in
the module's namespace, so importing/subclassing the momentum class (which would
put a second Strategy subclass in scope) is not possible. Module-level helper
FUNCTIONS are imported (they are not Strategy subclasses), so the risk overlay
and construction are byte-identical to the locked book — only the signal differs.
'''

from __future__ import annotations

import logging
from datetime import date

import backtrader as bt
import numpy as np

from data.sectors import SectorAssignment, assign_sectors
from strategy import (
    _REBALANCE_PARITY,
    construct_gross_targets,
    resolve_active_universe,
    vol_targeted_gross,
)

logger = logging.getLogger(__name__)


def low_volatility_scores(
    close_by_ticker: dict[str, list[float]],
    lookback_days: int,
) -> dict[str, float]:
    '''Cross-sectional score = NEGATIVE trailing realised volatility.

    For each ticker, take the std of trailing ``lookback_days`` daily returns;
    score = -std so that the LOWEST-vol names rank HIGHEST (sorted descending),
    mirroring the momentum-quality scorer's "higher = better" interface. Rank
    is scale-invariant, so no annualisation is needed. Pure / deterministic.

    Names with insufficient history, non-finite / non-positive closes, or
    degenerate (zero) volatility are skipped — exactly the same robustness
    filters the momentum scorer applies.
    '''
    scores: dict[str, float] = {}
    lb = max(21, int(lookback_days))
    for t, raw in close_by_ticker.items():
        if len(raw) < lb + 1:
            continue
        c = np.asarray(raw[-(lb + 1):], dtype=float)
        if bool(np.any(~np.isfinite(c))) or bool(np.any(c <= 0.0)):
            continue
        rets = c[1:] / c[:-1] - 1.0
        sd = float(np.std(rets))
        if not np.isfinite(sd) or sd <= 0.0:
            continue
        scores[t] = -sd
    return scores


class IndiaLowVolatilityCarry(bt.Strategy):
    '''Long-only PIT-universe LOW-VOLATILITY carry, downside-vol-targeted.'''

    _ADV_WINDOW = 20

    params = (
        # ── Tunable signal hyperparameters (counted by the parsimony gate) ──
        ('vol_lookback', 252),     # trailing window for the realised-vol rank
        ('n_names', 30),           # low-vol basket size; >=20 guarantees the
                                   # book-level downside-vol estimate in
                                   # vol_targeted_gross is valid (its >=20-usable
                                   # floor), so deployment references the book's
                                   # OWN low vol rather than falling back to the
                                   # broad universe. Rounded up from the
                                   # validated 20 for estimate-validity margin
                                   # and diversification — NOT tuned for return.
        ('sector_cap', 0.25),      # per-sector weight ceiling (locked-book value)
        # ── Plumbing / structure (excluded from the parsimony count) ──
        ('rebalance_weekday', 4),
        ('rebalance_period_weeks', 2),
        ('universe_db_path', 'storage/universe.duckdb'),
        ('macro_db_path', 'storage/macro.duckdb'),
        ('enforce_sector_cap', True),
        ('universe_by_date', None),
    )

    def __init__(self) -> None:
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = sorted(ubd) if ubd else None

    # ── helpers duplicated from strategy.IndiaMomentumQualityCarry ──────────

    def _active_universe(self, today: date) -> set[str] | None:
        return resolve_active_universe(
            self.p.universe_by_date, self._univ_dates, today
        )

    @staticmethod
    def _ticker_of(d) -> str:
        name = getattr(d, '_name', '') or getattr(d, 'name', '') or ''
        return name.upper()

    def _load_sector_map(self) -> dict[str, SectorAssignment]:
        '''Per-ticker sector from the PIT universe enrichment (Improvement G
        root-cause fix — see strategy._load_sector_map). Point-in-time-safe
        static enrichment, never a return signal.'''
        industry_by_ticker: dict[str, str] = {}
        try:
            import duckdb

            conn = duckdb.connect(str(self.p.universe_db_path), read_only=True)
            try:
                for tkr, ind in conn.execute(
                    "SELECT ticker, industry FROM universe_snapshot "
                    "WHERE industry IS NOT NULL AND industry <> '' "
                    "AND UPPER(industry) <> 'OTHER'"
                ).fetchall():
                    industry_by_ticker[str(tkr).upper()] = str(ind)
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 — DB absent in some unit tests
            industry_by_ticker = {}

        rows = []
        for d in self.datas:
            t = self._ticker_of(d)
            ind = (
                industry_by_ticker.get(t)
                or getattr(d, '_industry', None)
                or getattr(d, 'industry', None)
                or ''
            )
            rows.append(type('_Row', (), {'ticker': t, 'industry': ind})())
        return assign_sectors(rows)

    def _is_rebalance_today(self) -> bool:
        today = self.datas[0].datetime.date(0)
        if today.weekday() != self.p.rebalance_weekday:
            return False
        period = max(1, int(self.p.rebalance_period_weeks))
        return today.isocalendar().week % period == _REBALANCE_PARITY

    def _held_positions(self) -> dict[str, float]:
        held = {
            self._ticker_of(d): self.getposition(d).size for d in self.datas
        }
        return {t: q for t, q in held.items() if q > 0}

    def _close_and_adv(
        self, active: set[str] | None
    ) -> tuple[dict[str, list[float]], dict[str, float]]:
        lookback = int(self.p.vol_lookback)
        need = max(lookback + 1, self._ADV_WINDOW)
        close_by_ticker: dict[str, list[float]] = {}
        adv_by_ticker: dict[str, float] = {}

        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            if len(d) < need:
                continue
            closes = [float(d.close[-i]) for i in range(lookback, -1, -1)]
            if any(c <= 0.0 for c in closes):
                continue
            adv = float(
                np.mean([
                    float(d.close[-i]) * float(d.volume[-i])
                    for i in range(self._ADV_WINDOW)
                ])
            )
            if adv <= 0.0:
                continue
            close_by_ticker[t] = closes
            adv_by_ticker[t] = adv
        return close_by_ticker, adv_by_ticker

    def _exit_ineligible_held(
        self, held: dict[str, float], active: set[str] | None
    ) -> dict[str, float]:
        if active is None:
            return held
        still_held: dict[str, float] = {}
        for d in self.datas:
            t = self._ticker_of(d)
            if t not in held:
                continue
            if t in active:
                still_held[t] = held[t]
            else:
                self.order_target_percent(d, target=0.0)
        return still_held

    # ── signal: low-vol selection + locked risk overlay + construction ─────

    def next(self) -> None:
        # Low-vol book holds between rebalances; no structural-MA exit (a
        # momentum/trend device that would churn mean-reverting low-vol names).
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)
        active = self._active_universe(today)
        held = self._exit_ineligible_held(self._held_positions(), active)
        close_by_ticker, adv_by_ticker = self._close_and_adv(active)

        n = max(1, int(self.p.n_names))
        # Need a real cross-section to form a diversified low-vol book; if the
        # PIT universe is too thin (data-starved early era) exit to cash.
        if len(close_by_ticker) < n:
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        scores = low_volatility_scores(close_by_ticker, int(self.p.vol_lookback))
        if not scores:
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        # score = -vol, so descending sort == ascending volatility.
        ranked = [
            t for t, _ in sorted(
                scores.items(), key=lambda kv: kv[1], reverse=True
            )
        ]
        selected = ranked[:n]                 # the low-vol book (drives gross)
        # Priority extends to the lowest-2N band so the sector-cap walk fills
        # the gross budget with STILL-LOW-vol names rather than leaking to
        # cash; held names still inside that band keep front priority (low
        # turnover -> low DP drag). Names that drift past 2N are dropped.
        band = ranked[: 2 * n]
        retained = [t for t in band if t in held]
        new_names = [t for t in band if t not in held]
        priority = retained + new_names

        # Deployment references the SELECTED low-vol book's OWN downside vol
        # (>=20 names -> valid estimate). Low book vol -> gross clips to ~0.99
        # in calm regimes; in a crash the book's downside vol rises and gross
        # falls (the same one-sided, never-levered overlay as the locked book).
        book_close_by_ticker = {
            t: close_by_ticker[t] for t in selected if t in close_by_ticker
        }
        gross = vol_targeted_gross(
            close_by_ticker, int(self.p.vol_lookback), book_close_by_ticker
        )

        sector_of = {
            t: (self._sector_map[t].sector
                if self._sector_map.get(t) else 'OTHER')
            for t in priority
        }
        # Equal-weight within the gross budget: name_cap = gross / n_names means
        # construct_gross_targets deploys ~gross/n to each of the first ~n names
        # (sector permitting, continuing across sectors), i.e. an equal-weight
        # diversified low-vol book. Still hard-bounded by the per-sector cap.
        name_cap = gross / float(n)
        targets = (
            construct_gross_targets(
                priority, sector_of, gross, float(self.p.sector_cap),
                name_cap=name_cap,
            )
            if self.p.enforce_sector_cap and self._sector_map
            else construct_gross_targets(
                priority, {}, gross, 1.0, name_cap=name_cap
            )
        )

        for d in self.datas:
            t = self._ticker_of(d)
            if t in targets:
                self.order_target_percent(d, target=targets[t])
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            'lowvol rebalance %s: scored=%d, deployed=%d, held=%d, '
            'gross=%.2f, sum_w=%.3f',
            today, len(scores), len(targets), len(held), gross,
            sum(targets.values()),
        )


__all__ = [
    'low_volatility_scores',
    'IndiaLowVolatilityCarry',
]
