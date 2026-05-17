'''Strategy B - long-only cross-sectional momentum-quality carry.

Branch: mean-reversion-quant-strategy. This variant deliberately changes the
entry thesis away from residual falling-knife reversion: it owns liquid NSE
names with persistent 12-1 style relative strength, smooth downside behavior,
segment-level trend consistency, and limited drawdown, then keeps the book
diversified with fixed risk slots and a whole-book sector cap.

Rebalance: biweekly (every other Friday). On non-rebalance bars the strategy
returns early; every position change goes through ``order_target_percent``.

Trade contract:
  - Long-only CNC delivery behavior.
  - Trade only the injected point-in-time universe.
  - Size each selected name from fixed risk slots: gross / n_positions.
  - Never size from len(selected); unused or blocked slots remain cash.
'''

from __future__ import annotations

import bisect
import logging
from datetime import date

import backtrader as bt
import numpy as np

from data.sectors import (
    SectorAssignment,
    assign_sectors,
    enforce_sector_cap,
)

logger = logging.getLogger(__name__)


def resolve_active_universe(
    universe_by_date: dict | None,
    sorted_dates: list[date] | None,
    today: date,
) -> set[str] | None:
    '''Resolve the point-in-time eligible universe.

    - None -> no PIT universe injected; all loaded feeds eligible.
    - most-recent <= today -> that snapshot's membership.
    - today before earliest snapshot -> empty set. Never fall forward to a
      future snapshot.
    '''
    if not universe_by_date or not sorted_dates:
        return None
    i = bisect.bisect_right(sorted_dates, today) - 1
    if i < 0:
        return set()
    return set(universe_by_date[sorted_dates[i]])


# ----------------------------------------------------------------------
# Legacy pure residual helpers retained for unit-test compatibility.
# The strategy below no longer trades this signal.
# ----------------------------------------------------------------------


def ols_beta(
    y: list[float], factors: list[list[float]]
) -> list[float] | None:
    yv = np.asarray(y, dtype=float)
    T = yv.shape[0]
    K = len(factors)
    if T < K + 2:
        return None
    X = np.column_stack(
        [np.ones(T)] + [np.asarray(f, dtype=float) for f in factors]
    )
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    return coef.tolist()


def market_factor(returns_by_ticker: dict[str, list[float]]) -> list[float]:
    if not returns_by_ticker:
        return []
    M = np.asarray(list(returns_by_ticker.values()), dtype=float)
    return M.mean(axis=0).tolist()


def smb_factor(
    returns_by_ticker: dict[str, list[float]],
    adv_by_ticker: dict[str, float],
) -> list[float]:
    tickers = [t for t in returns_by_ticker if t in adv_by_ticker]
    T = len(next(iter(returns_by_ticker.values()))) if returns_by_ticker else 0
    if len(tickers) < 3:
        return [0.0] * T
    order = sorted(tickers, key=lambda t: adv_by_ticker[t])
    k = max(1, len(order) // 3)
    small = order[:k]
    large = order[-k:]
    S = np.asarray([returns_by_ticker[t] for t in small], dtype=float).mean(0)
    L = np.asarray([returns_by_ticker[t] for t in large], dtype=float).mean(0)
    return (S - L).tolist()


def reversion_scores(
    returns_by_ticker: dict[str, list[float]],
    adv_by_ticker: dict[str, float],
    beta_window: int,
    formation_days: int,
) -> dict[str, float]:
    rbt = {
        t: list(r)[-beta_window:]
        for t, r in returns_by_ticker.items()
        if len(r) >= beta_window
    }
    if len(rbt) < 3:
        return {}
    mkt = market_factor(rbt)
    smb = smb_factor(rbt, adv_by_ticker)

    cum_resid: dict[str, float] = {}
    for t, r in rbt.items():
        coef = ols_beta(r, [mkt, smb])
        if coef is None:
            continue
        a, b_m, b_s = coef
        resid = [
            r[i] - (a + b_m * mkt[i] + b_s * smb[i]) for i in range(len(r))
        ]
        cum_resid[t] = float(np.sum(resid[-formation_days:]))

    if len(cum_resid) < 2:
        return {}
    vals = np.asarray(list(cum_resid.values()), dtype=float)
    mu = float(vals.mean())
    sd = float(vals.std())
    if sd == 0.0:
        return {t: 0.0 for t in cum_resid}
    return {t: -((v - mu) / sd) for t, v in cum_resid.items()}


# ----------------------------------------------------------------------
# Momentum-quality signal core.
# ----------------------------------------------------------------------


def _rank_metric(
    rows: dict[str, dict[str, float]],
    key: str,
    higher_is_better: bool = True,
) -> dict[str, float]:
    if not rows:
        return {}
    ordered = sorted((vals[key], t) for t, vals in rows.items())
    n = len(ordered)
    if n == 1:
        return {ordered[0][1]: 0.5}
    ranks: dict[str, float] = {}
    denom = float(n - 1)
    for i, (_, t) in enumerate(ordered):
        pct = i / denom
        ranks[t] = pct if higher_is_better else 1.0 - pct
    return ranks


def _max_drawdown(closes: np.ndarray) -> float:
    peaks = np.maximum.accumulate(closes)
    drawdowns = closes / peaks - 1.0
    return abs(float(np.min(drawdowns)))


def _downside_volatility(returns: np.ndarray) -> float:
    downside = returns[returns < 0.0]
    if downside.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(downside * downside)))


def _trend_consistency(closes: np.ndarray, skip: int) -> float:
    trend_closes = closes[:-skip] if skip > 0 else closes
    chunk = max(1, skip)
    if trend_closes.size <= chunk:
        return 0.0

    segment_returns: list[float] = []
    start = 0
    while start + chunk < trend_closes.size:
        end = start + chunk
        base = float(trend_closes[start])
        if base > 0.0:
            segment_returns.append(float(trend_closes[end]) / base - 1.0)
        start = end

    if not segment_returns:
        return 0.0
    positive = np.asarray(segment_returns, dtype=float) > 0.0
    return float(np.mean(positive))


def _structural_ma_window(lookback: int) -> int:
    '''Length of the structural trend MA, derived from the signal lookback.

    Single source of truth so the entry filter (price must be ABOVE this MA
    to qualify) and the between-rebalance structural exit (sell once price
    falls BELOW it) provably use the SAME definition and cannot drift apart.
    Not a new tunable knob — this is the strategy's pre-existing inline
    convention (was `min(200, max(50, lookback*3//4))` in
    momentum_quality_scores), now named and shared.
    '''
    return min(200, max(50, int(lookback) * 3 // 4))


def momentum_quality_scores(
    close_by_ticker: dict[str, list[float]],
    adv_by_ticker: dict[str, float],
    lookback_days: int,
    skip_days: int,
) -> dict[str, float]:
    '''Rank positive 12-1 style momentum by quality of the path.

    Higher score favors names with positive long and medium relative strength,
    current price still near its trailing high, smaller drawdown, lower
    downside volatility, and momentum accumulated across many skip-length
    segments rather than one isolated jump. All components are cross-sectional
    percentile ranks, so no scale fitting is needed.
    '''
    rows: dict[str, dict[str, float]] = {}
    skip = max(1, int(skip_days))
    lookback = max(skip + 21, int(lookback_days))

    for t, raw_closes in close_by_ticker.items():
        if len(raw_closes) < lookback + 1:
            continue
        closes = np.asarray(raw_closes[-(lookback + 1):], dtype=float)
        if closes.size < lookback + 1:
            continue
        if bool(np.any(~np.isfinite(closes))) or bool(np.any(closes <= 0.0)):
            continue

        now = float(closes[-1])
        pre_skip = float(closes[-(skip + 1)])
        start = float(closes[0])
        half = max(skip + 21, lookback // 2)
        mid_start = float(closes[-(half + 1)])
        ma_window = _structural_ma_window(lookback)
        moving_average = float(np.mean(closes[-ma_window:]))

        long_mom = pre_skip / start - 1.0
        mid_mom = pre_skip / mid_start - 1.0
        if long_mom <= 0.0 or mid_mom <= 0.0 or now < moving_average:
            continue

        returns = closes[1:] / closes[:-1] - 1.0
        trailing_high = float(np.max(closes))
        high_proximity = now / trailing_high if trailing_high > 0.0 else 0.0
        rows[t] = {
            'long_mom': long_mom,
            'mid_mom': mid_mom,
            'high_proximity': high_proximity,
            'max_drawdown': _max_drawdown(closes),
            'downside_vol': _downside_volatility(returns),
            'trend_consistency': _trend_consistency(closes, skip),
            'adv': float(adv_by_ticker.get(t, 0.0)),
        }

    if len(rows) < 2:
        return {}

    long_rank = _rank_metric(rows, 'long_mom', True)
    mid_rank = _rank_metric(rows, 'mid_mom', True)
    high_rank = _rank_metric(rows, 'high_proximity', True)
    dd_rank = _rank_metric(rows, 'max_drawdown', False)
    downvol_rank = _rank_metric(rows, 'downside_vol', False)
    consistency_rank = _rank_metric(rows, 'trend_consistency', True)
    adv_rank = _rank_metric(rows, 'adv', True)

    scores: dict[str, float] = {}
    for t in rows:
        scores[t] = (
            long_rank[t]
            + mid_rank[t]
            + high_rank[t]
            + dd_rank[t]
            + downvol_rank[t]
            + consistency_rank[t]
            + 0.25 * adv_rank[t]
        )
    return scores


def breadth_scaled_gross(
    close_by_ticker: dict[str, list[float]], lookback_days: int
) -> float:
    '''Conservative gross exposure from cross-sectional market health.

    The book remains long-only, but when fewer names are above their own
    intermediate moving average and the median three-month return is weak,
    the fixed slots are funded with less gross instead of concentrating risk.
    '''
    above = 0
    usable = 0
    short_rets: list[float] = []
    ma_window = min(200, max(50, int(lookback_days) * 3 // 4))
    ret_window = min(63, max(21, int(lookback_days) // 4))

    for raw_closes in close_by_ticker.values():
        if len(raw_closes) < max(ma_window, ret_window) + 1:
            continue
        closes = np.asarray(raw_closes, dtype=float)
        if bool(np.any(~np.isfinite(closes))) or bool(np.any(closes <= 0.0)):
            continue
        usable += 1
        now = float(closes[-1])
        if now >= float(np.mean(closes[-ma_window:])):
            above += 1
        short_rets.append(now / float(closes[-(ret_window + 1)]) - 1.0)

    if usable < 20:
        return 0.75
    breadth = above / float(usable)
    median_short_ret = float(np.median(np.asarray(short_rets, dtype=float)))

    if breadth < 0.35 and median_short_ret < 0.0:
        return 0.35
    if breadth < 0.45:
        return 0.55
    if breadth < 0.55 or median_short_ret < 0.0:
        return 0.75
    return 0.99


def inverse_vol_tilt(
    selected: list[str],
    vol_by_ticker: dict[str, float],
) -> dict[str, float]:
    '''Mean~1 inverse-vol risk-parity tilt within fixed slots.

    raw_i = 1/vol_i (vol floored; missing/invalid -> neutral = mean raw).
    tilt0_i = raw_i / mean(raw); clip to [0.5, 2.0] (the standard
    risk-parity 0.5x-2x-equal concentration guardrail — pre-committed, not
    searched, not a tunable param); renormalise so the clipped tilts sum
    to len(selected); then a post-scale hard cap of 2.0 whose freed weight
    becomes CASH (NOT redistributed) so the sum is NEVER above
    len(selected). Gross can therefore only stay equal to or drop a hair
    below equal-weight, never increase — it cannot trip the >100% gross
    catastrophe gate and (unlike scaling GROSS, learnings.md 3.5) cannot
    clip the long book's right tail. Identity (all tilt == 1.0) when vols
    are uniform, so this is a strict generalisation of equal-weight.
    '''
    n = len(selected)
    if n == 0:
        return {}
    if n == 1:
        return {selected[0]: 1.0}
    eps = 1e-9
    raw: dict[str, float | None] = {}
    present: list[float] = []
    for t in selected:
        v = vol_by_ticker.get(t)
        if v is None or not np.isfinite(v) or v <= 0.0:
            raw[t] = None
        else:
            rv = 1.0 / max(float(v), eps)
            raw[t] = rv
            present.append(rv)
    if not present:
        return {t: 1.0 for t in selected}     # no risk info -> equal-weight
    neutral = float(np.mean(present))
    raws = np.array(
        [neutral if raw[t] is None else raw[t] for t in selected],
        dtype=float,
    )
    t0 = raws / float(np.mean(raws))
    clipped = np.clip(t0, 0.5, 2.0)
    scale = n / float(np.sum(clipped))
    tilt = np.minimum(clipped * scale, 2.0)   # post-scale cap; excess -> cash
    return {t: float(tilt[i]) for i, t in enumerate(selected)}


def apply_sector_cap(
    selected: list[str],
    targets: dict[str, float],
    sector_of: dict[str, str],
    cap: float,
) -> dict[str, float]:
    '''Clamp per-name targets so no sector exceeds `cap` on ACTUAL
    (tilted) weights — the §5 25% hard cap, enforced in strategy.py since
    only this file is editable and `enforce_sector_cap` assumes equal
    weight. Walk `selected` in priority order; each name gets
    min(target, sector remaining room); a name into a full sector gets
    0.0 (cash). Excess is NEVER redistributed (that is precisely the §4
    banned concentration mode) — it stays cash. Pure, deterministic.
    '''
    out: dict[str, float] = {}
    sec_sum: dict[str, float] = {}
    for t in selected:
        tgt = float(targets.get(t, 0.0))
        sec = sector_of.get(t, 'OTHER')
        used = sec_sum.get(sec, 0.0)
        room = cap - used
        give = tgt if tgt <= room else max(0.0, room)
        out[t] = give
        sec_sum[sec] = used + give
    return out


class IndiaMomentumQualityCarry(bt.Strategy):
    '''Long-only PIT-universe momentum-quality carry with fixed slots.'''

    _ADV_WINDOW = 20

    params = (
        ('beta_window', 252),
        ('formation_days', 21),
        ('retention_mult', 2.0),
        ('entry_pct', 0.30),
        ('n_positions', 25),
        ('sector_cap', 0.25),
        ('rebalance_weekday', 4),
        ('rebalance_period_weeks', 2),
        ('rebalance_week_parity', 0),
        ('universe_db_path', 'storage/universe.duckdb'),
        ('macro_db_path', 'storage/macro.duckdb'),
        ('enforce_sector_cap', True),
        ('universe_by_date', None),
    )

    def __init__(self) -> None:
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        self._week_parity_initialized = False
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = sorted(ubd) if ubd else None
        # Names whose structural-exit order is submitted but not yet filled;
        # suppresses duplicate exits across the bars until the fill. Cleared
        # deterministically in notify_trade when the round-trip closes.
        self._stop_pending: set[str] = set()

    def _active_universe(self, today: date) -> set[str] | None:
        return resolve_active_universe(
            self.p.universe_by_date, self._univ_dates, today
        )

    @staticmethod
    def _ticker_of(d) -> str:
        name = getattr(d, '_name', '') or getattr(d, 'name', '') or ''
        return name.upper()

    def _load_sector_map(self) -> dict[str, SectorAssignment]:
        rows = []
        for d in self.datas:
            ind = getattr(d, '_industry', None) or getattr(d, 'industry', None)
            t = self._ticker_of(d)

            class _Row:
                ticker = t
                industry = ind or ''

            rows.append(_Row())
        return assign_sectors(rows)

    def _is_rebalance_today(self) -> bool:
        today = self.datas[0].datetime.date(0)
        if today.weekday() != self.p.rebalance_weekday:
            return False
        iso_week = today.isocalendar().week
        if not self._week_parity_initialized:
            self._week_parity_initialized = True
            object.__setattr__(
                self.params, 'rebalance_week_parity', iso_week % 2
            )
            return True
        return iso_week % 2 == self.p.rebalance_week_parity

    def _held_positions(self) -> dict[str, float]:
        held = {
            self._ticker_of(d): self.getposition(d).size for d in self.datas
        }
        return {t: q for t, q in held.items() if q > 0}

    def _close_and_adv(
        self, active: set[str] | None
    ) -> tuple[dict[str, list[float]], dict[str, float]]:
        lookback = int(self.p.beta_window)
        need = max(lookback + 1, self._ADV_WINDOW)
        close_by_ticker: dict[str, list[float]] = {}
        adv_by_ticker: dict[str, float] = {}

        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            if len(d) < need:
                continue
            closes = [
                float(d.close[-i]) for i in range(lookback, -1, -1)
            ]
            if any(c <= 0.0 for c in closes):
                continue
            adv = float(
                np.mean(
                    [
                        float(d.close[-i]) * float(d.volume[-i])
                        for i in range(self._ADV_WINDOW)
                    ]
                )
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

    def notify_trade(self, trade) -> None:
        '''Clear pending-exit state the bar a round-trip closes.

        backtrader delivers this before ``next()`` on the fill bar, so a
        name exited (structurally or by rebalance) is stop-eligible again
        the moment it is re-entered — no stale flag can silently disable a
        future structural exit on a re-bought position.
        '''
        if getattr(trade, 'isclosed', False):
            self._stop_pending.discard(self._ticker_of(trade.data))

    def _apply_structural_exit(self) -> None:
        '''Trend-state exit, symmetric with the entry's structural filter.

        The entry (momentum_quality_scores) only buys a name whose close is
        ABOVE its own beta_window-derived structural MA. This sells a held
        name once its close falls BELOW that SAME MA — i.e. its long
        uptrend has objectively broken. A ~190-day MA does not move on the
        routine 5-10% Indian mid-cap pullbacks (so intact winners are never
        churned — momentum's right tail is preserved), only on a sustained
        breakdown (regime transition / bear), where many names breaking
        together cascade the book toward cash: emergent graceful de-risking
        with no binary macro gate and gross only ever falling (long-only,
        <=100%, no leverage). Adds no tunable hyperparameter — the MA is the
        strategy's existing structural definition applied symmetrically.

        Runs only on non-rebalance bars so the rebalance owns every order
        decision on its own bar (no same-bar double-ordering); a structurally
        exited name may be re-entered at any later rebalance if it requalifies.
        '''
        skip = max(1, int(self.p.formation_days))
        lookback = max(skip + 21, int(self.p.beta_window))
        ma_window = _structural_ma_window(lookback)

        for d in self.datas:
            t = self._ticker_of(d)
            if self.getposition(d).size <= 0:
                self._stop_pending.discard(t)
                continue
            if t in self._stop_pending:
                continue  # exit submitted; await next-open fill
            if len(d) < ma_window + 1:
                continue
            closes = np.asarray(
                [float(d.close[-i]) for i in range(ma_window, -1, -1)],
                dtype=float,
            )
            if bool(np.any(~np.isfinite(closes))) or bool(
                np.any(closes <= 0.0)
            ):
                continue
            close_now = float(closes[-1])
            structural_ma = float(np.mean(closes[-ma_window:]))
            if close_now < structural_ma:
                self.order_target_percent(d, target=0.0)
                self._stop_pending.add(t)

    def next(self) -> None:
        if not self._is_rebalance_today():
            self._apply_structural_exit()
            return

        today = self.datas[0].datetime.date(0)
        active = self._active_universe(today)
        held = self._exit_ineligible_held(self._held_positions(), active)
        close_by_ticker, adv_by_ticker = self._close_and_adv(active)
        if len(close_by_ticker) < 3:
            self._last_rebalance_date = today
            return

        scores = momentum_quality_scores(
            close_by_ticker,
            adv_by_ticker,
            int(self.p.beta_window),
            int(self.p.formation_days),
        )
        if not scores:
            for d in self.datas:
                t = self._ticker_of(d)
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        eligible_n = max(
            int(self.p.n_positions), int(float(self.p.entry_pct) * len(ranked))
        )
        retain_n = max(
            int(self.p.n_positions),
            int(float(self.p.retention_mult) * int(self.p.n_positions)),
        )

        retained_priority = [t for t, _ in ranked[:retain_n] if t in held]
        entry_priority = [t for t, _ in ranked[:eligible_n] if t not in held]
        priority = retained_priority + entry_priority

        gross = breadth_scaled_gross(close_by_ticker, int(self.p.beta_window))
        target_each = gross / max(int(self.p.n_positions), 1)

        if self.p.enforce_sector_cap and self._sector_map:
            selected = enforce_sector_cap(
                ranked_candidates=priority,
                target_fraction_each=target_each,
                sector_map=self._sector_map,
                max_sector_fraction=float(self.p.sector_cap),
                n_target=int(self.p.n_positions),
            )
        else:
            selected = priority[: int(self.p.n_positions)]

        # Improvement B: inverse-vol risk-parity tilt WITHIN the fixed
        # slots. Gross (breadth_scaled_gross) is deliberately untouched —
        # A's learning (learnings.md 3.5): scaling gross down clips this
        # long book's right tail. Σ targets is never above the
        # equal-weight total, so the §4 fixed-slot/unfilled-stays-cash
        # invariant and the gross<=100% gate still hold; only the
        # intra-book distribution tilts toward lower-realized-vol names
        # (lowers downside deviation without truncating melt-ups).
        fd = max(2, int(self.p.formation_days))
        vol_by_ticker: dict[str, float] = {}
        for t in selected:
            c = close_by_ticker.get(t)
            if not c or len(c) < fd + 1:
                continue
            arr = np.asarray(c[-(fd + 1):], dtype=float)
            rr = arr[1:] / arr[:-1] - 1.0
            vol_by_ticker[t] = float(rr.std())
        tilt = inverse_vol_tilt(selected, vol_by_ticker)
        sector_of = {
            t: (self._sector_map[t].sector
                if self._sector_map.get(t) else 'OTHER')
            for t in selected
        }
        targets = apply_sector_cap(
            selected,
            {t: target_each * tilt.get(t, 1.0) for t in selected},
            sector_of,
            float(self.p.sector_cap),
        )

        selected_set = set(selected)
        for d in self.datas:
            t = self._ticker_of(d)
            if t in selected_set:
                self.order_target_percent(d, target=targets.get(t, 0.0))
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            'rebalance %s: scored=%d, selected=%d, held=%d, gross=%.2f, slot=%.4f',
            today,
            len(scores),
            len(selected),
            len(held),
            gross,
            target_each,
        )


__all__ = [
    'resolve_active_universe',
    'ols_beta',
    'market_factor',
    'smb_factor',
    'reversion_scores',
    'momentum_quality_scores',
    'breadth_scaled_gross',
    'inverse_vol_tilt',
    'apply_sector_cap',
    'IndiaMomentumQualityCarry',
]
