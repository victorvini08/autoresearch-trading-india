'''Strategy B - long-only cross-sectional momentum-quality carry.

Branch: mean-reversion-quant-strategy. This variant deliberately changes the
entry thesis away from residual falling-knife reversion: it owns liquid NSE
names with persistent 12-1 style relative strength, smooth downside behavior,
segment-level trend consistency, volume-confirmed accumulation, and limited
drawdown, then keeps the book diversified with fixed risk slots and a whole-book
sector cap.

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


def _volume_accumulation(
    signal_returns: np.ndarray,
    signal_dollar_volume: np.ndarray,
) -> float:
    if signal_returns.size == 0:
        return 0.0
    if signal_dollar_volume.size != signal_returns.size:
        return 0.0
    if bool(np.any(~np.isfinite(signal_dollar_volume))):
        return 0.0

    up_mask = signal_returns > 0.0
    down_mask = signal_returns < 0.0
    if int(np.sum(up_mask)) == 0 or int(np.sum(down_mask)) == 0:
        return 0.0

    up_turnover = float(np.mean(signal_dollar_volume[up_mask]))
    down_turnover = float(np.mean(signal_dollar_volume[down_mask]))
    if up_turnover <= 0.0 or down_turnover <= 0.0:
        return 0.0
    return float(np.log(up_turnover / down_turnover))


def momentum_quality_scores(
    close_by_ticker: dict[str, list[float]],
    adv_by_ticker: dict[str, float],
    lookback_days: int,
    skip_days: int,
    dollar_volume_by_ticker: dict[str, list[float]] | None = None,
) -> dict[str, float]:
    '''Rank positive 12-1 style momentum by quality of the path.

    Higher score favors names with positive long and medium relative strength,
    positive stock-specific momentum after removing the active-universe market
    return, current price still near its trailing high, smaller drawdown, lower
    downside volatility, momentum accumulated across many skip-length segments,
    and stronger up-day than down-day turnover during the pre-skip trend. All
    components are cross-sectional percentile ranks, so no scale fitting is
    needed.
    '''
    rows: dict[str, dict[str, float]] = {}
    returns_by_ticker: dict[str, np.ndarray] = {}
    skip = max(1, int(skip_days))
    lookback = max(skip + 21, int(lookback_days))
    use_volume = dollar_volume_by_ticker is not None

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
        ma_window = min(200, max(50, lookback * 3 // 4))
        moving_average = float(np.mean(closes[-ma_window:]))

        long_mom = pre_skip / start - 1.0
        mid_mom = pre_skip / mid_start - 1.0
        if long_mom <= 0.0 or mid_mom <= 0.0 or now < moving_average:
            continue

        returns = closes[1:] / closes[:-1] - 1.0
        trailing_high = float(np.max(closes))
        high_proximity = now / trailing_high if trailing_high > 0.0 else 0.0
        returns_by_ticker[t] = returns
        rows[t] = {
            'long_mom': long_mom,
            'mid_mom': mid_mom,
            'high_proximity': high_proximity,
            'max_drawdown': _max_drawdown(closes),
            'downside_vol': _downside_volatility(returns),
            'trend_consistency': _trend_consistency(closes, skip),
            'adv': float(adv_by_ticker.get(t, 0.0)),
        }

        if use_volume:
            raw_dollar_volume = dollar_volume_by_ticker.get(t, [])
            rows[t]['volume_accumulation'] = 0.0
            if len(raw_dollar_volume) >= lookback + 1:
                dollar_volume = np.asarray(
                    raw_dollar_volume[-(lookback + 1):], dtype=float
                )
                if dollar_volume.size == closes.size and not bool(
                    np.any(dollar_volume < 0.0)
                ):
                    return_dollar_volume = dollar_volume[1:]
                    signal_returns = (
                        returns[:-skip] if skip < returns.size else returns
                    )
                    signal_dollar_volume = (
                        return_dollar_volume[:-skip]
                        if skip < return_dollar_volume.size
                        else return_dollar_volume
                    )
                    rows[t]['volume_accumulation'] = _volume_accumulation(
                        signal_returns, signal_dollar_volume
                    )

    if len(rows) < 2:
        return {}

    market_returns = np.vstack([returns_by_ticker[t] for t in rows]).mean(axis=0)
    market_signal = market_returns[:-skip] if skip < market_returns.size else market_returns
    market_var = float(np.var(market_signal))
    for t in rows:
        stock_returns = returns_by_ticker[t]
        stock_signal = stock_returns[:-skip] if skip < stock_returns.size else stock_returns
        if stock_signal.size != market_signal.size or stock_signal.size == 0:
            rows[t]['residual_mom'] = 0.0
            continue
        if market_var > 0.0:
            beta = float(np.cov(stock_signal, market_signal, ddof=0)[0, 1] / market_var)
        else:
            beta = 1.0
        residual = stock_signal - beta * market_signal
        rows[t]['residual_mom'] = float(np.sum(residual))

    long_rank = _rank_metric(rows, 'long_mom', True)
    mid_rank = _rank_metric(rows, 'mid_mom', True)
    residual_rank = _rank_metric(rows, 'residual_mom', True)
    high_rank = _rank_metric(rows, 'high_proximity', True)
    dd_rank = _rank_metric(rows, 'max_drawdown', False)
    downvol_rank = _rank_metric(rows, 'downside_vol', False)
    consistency_rank = _rank_metric(rows, 'trend_consistency', True)
    adv_rank = _rank_metric(rows, 'adv', True)

    use_volume_rank = False
    volume_rank: dict[str, float] = {}
    if use_volume:
        volume_values = [rows[t]['volume_accumulation'] for t in rows]
        use_volume_rank = max(volume_values) > min(volume_values)
        if use_volume_rank:
            volume_rank = _rank_metric(rows, 'volume_accumulation', True)

    scores: dict[str, float] = {}
    for t in rows:
        score = (
            long_rank[t]
            + mid_rank[t]
            + residual_rank[t]
            + high_rank[t]
            + dd_rank[t]
            + downvol_rank[t]
            + consistency_rank[t]
            + 0.25 * adv_rank[t]
        )
        if use_volume_rank:
            score += volume_rank[t]
        scores[t] = score
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


# Biweekly rebalance parity — FIXED, not derived. The prior derivation
# ("first Friday in the rolling backtest window") was fragile: as the
# window slid forward by 1 day each calendar day, its first Friday
# occasionally crossed into the next week, flipping parity → the
# strategy silently re-decided which Fridays were rebalance days
# between runs (see 2026-05-26 Tuesday-rebalance incident). Anchoring
# to a constant makes "biweekly" reproducibly mean the same calendar
# set forever. NOT a tunable hyperparameter — it's a calendar choice,
# the same status as `rebalance_weekday = 4` (Friday).
_REBALANCE_PARITY = 0


class IndiaResidualReversalStatArb(bt.Strategy):
    '''Long-only PIT-universe momentum-quality carry with fixed slots.'''

    _ADV_WINDOW = 20

    params = (
        ('beta_window', 252),
        ('formation_days', 21),
        ('retention_mult', 2.0),
        ('entry_pct', 0.30),
        ('regime_pct', 95),
        ('n_positions', 25),
        ('sector_cap', 0.25),
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
        # Biweekly cadence anchored to a FIXED parity constant
        # (_REBALANCE_PARITY), not derived from "the first Friday in the
        # rolling backtest window" — that derivation let the chosen
        # rebalance-Friday set silently flip whenever the rolling window's
        # start crossed a Friday (see 2026-05-26 Tuesday-rebalance bug).
        period = max(1, int(self.p.rebalance_period_weeks))
        return today.isocalendar().week % period == _REBALANCE_PARITY

    def _held_positions(self) -> dict[str, float]:
        held = {
            self._ticker_of(d): self.getposition(d).size for d in self.datas
        }
        return {t: q for t, q in held.items() if q > 0}

    def _split_held_positions(
        self, held: dict[str, float], active: set[str] | None
    ) -> tuple[dict[str, float], dict[str, float]]:
        if active is None:
            return held, {}
        active_held: dict[str, float] = {}
        inactive_held: dict[str, float] = {}
        for t, q in held.items():
            if t in active:
                active_held[t] = q
            else:
                inactive_held[t] = q
        return active_held, inactive_held

    def _exit_ineligible_held(
        self, held: dict[str, float], active: set[str] | None
    ) -> dict[str, float]:
        active_held, _ = self._split_held_positions(held, active)
        return active_held

    def _sector_bucket(self, ticker: str) -> str:
        sa = self._sector_map.get(ticker)
        return sa.sector if sa else 'OTHER'

    def _held_sector_fractions(self, held_tickers: set[str]) -> dict[str, float]:
        if not held_tickers:
            return {}
        account_value = float(self.broker.getvalue())
        if account_value <= 0.0:
            return {}

        totals: dict[str, float] = {}
        for d in self.datas:
            t = self._ticker_of(d)
            if t not in held_tickers:
                continue
            pos = self.getposition(d)
            if pos.size <= 0:
                continue
            price = float(d.close[0])
            if price <= 0.0:
                continue
            frac = max(0.0, float(pos.size) * price / account_value)
            bucket = self._sector_bucket(t)
            totals[bucket] = totals.get(bucket, 0.0) + frac
        return totals

    def _select_with_sector_cap(
        self,
        ranked_candidates: list[str],
        target_fraction_each: float,
        n_target: int,
        existing_sector_totals: dict[str, float] | None = None,
    ) -> list[str]:
        chosen: list[str] = []
        sector_totals = dict(existing_sector_totals or {})
        max_sector_fraction = float(self.p.sector_cap)

        for ticker in ranked_candidates:
            if len(chosen) >= n_target:
                break
            bucket = self._sector_bucket(ticker)
            prospective = sector_totals.get(bucket, 0.0) + target_fraction_each
            if prospective > max_sector_fraction + 1e-9:
                continue
            sector_totals[bucket] = prospective
            chosen.append(ticker)
        return chosen

    def _close_adv_volume(
        self, active: set[str] | None
    ) -> tuple[
        dict[str, list[float]],
        dict[str, float],
        dict[str, list[float]],
    ]:
        lookback = int(self.p.beta_window)
        need = max(lookback + 1, self._ADV_WINDOW)
        close_by_ticker: dict[str, list[float]] = {}
        adv_by_ticker: dict[str, float] = {}
        dollar_volume_by_ticker: dict[str, list[float]] = {}

        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            if len(d) < need:
                continue
            closes = [
                float(d.close[-i]) for i in range(lookback, -1, -1)
            ]
            dollar_volumes = [
                float(d.close[-i]) * float(d.volume[-i])
                for i in range(lookback, -1, -1)
            ]
            if any(c <= 0.0 for c in closes):
                continue
            if any(not bool(np.isfinite(c)) for c in closes):
                continue
            if any(not bool(np.isfinite(v)) or v < 0.0 for v in dollar_volumes):
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
            dollar_volume_by_ticker[t] = dollar_volumes
        return close_by_ticker, adv_by_ticker, dollar_volume_by_ticker

    def _close_and_adv(
        self, active: set[str] | None
    ) -> tuple[dict[str, list[float]], dict[str, float]]:
        close_by_ticker, adv_by_ticker, _ = self._close_adv_volume(active)
        return close_by_ticker, adv_by_ticker

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)
        active = self._active_universe(today)
        held_all = self._held_positions()
        held, inactive_held = self._split_held_positions(held_all, active)
        n_positions = max(int(self.p.n_positions), 1)
        open_slots = max(n_positions - len(inactive_held), 0)
        close_by_ticker, adv_by_ticker, dollar_volume_by_ticker = (
            self._close_adv_volume(active)
        )
        if len(close_by_ticker) < 3:
            self._last_rebalance_date = today
            return

        scores = momentum_quality_scores(
            close_by_ticker,
            adv_by_ticker,
            int(self.p.beta_window),
            int(self.p.formation_days),
            dollar_volume_by_ticker,
        )
        if not scores or open_slots <= 0:
            for d in self.datas:
                t = self._ticker_of(d)
                if active is not None and t not in active:
                    continue
                if t in held:
                    self.order_target_percent(d, target=0.0)
            self._last_rebalance_date = today
            return

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        eligible_n = max(
            n_positions, int(float(self.p.entry_pct) * len(ranked))
        )
        retain_n = max(
            n_positions,
            int(float(self.p.retention_mult) * n_positions),
        )

        retained_priority = [t for t, _ in ranked[:retain_n] if t in held]
        entry_priority = [t for t, _ in ranked[:eligible_n] if t not in held]
        priority = retained_priority + entry_priority

        gross = breadth_scaled_gross(close_by_ticker, int(self.p.beta_window))
        target_each = gross / n_positions

        if self.p.enforce_sector_cap and self._sector_map:
            inactive_sector_fractions = self._held_sector_fractions(
                set(inactive_held)
            )
            selected = self._select_with_sector_cap(
                ranked_candidates=priority,
                target_fraction_each=target_each,
                n_target=open_slots,
                existing_sector_totals=inactive_sector_fractions,
            )
        else:
            selected = priority[:open_slots]

        selected_set = set(selected)
        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            if t in selected_set:
                self.order_target_percent(d, target=target_each)
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            'rebalance %s: scored=%d, selected=%d, active_held=%d, inactive_held=%d, gross=%.2f, slot=%.4f',
            today,
            len(scores),
            len(selected),
            len(held),
            len(inactive_held),
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
    'IndiaResidualReversalStatArb',
]
