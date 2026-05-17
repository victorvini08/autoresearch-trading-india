'''India autoresearch strategy.

PIT-strict long-only swing strategy for NSE equities. The strategy ranks only
tickers in the injected point-in-time universe, selects positive-trend names
with lower realized volatility, mild recent strength, defensive relative
strength on weak market days, persistent multi-leg trend quality, fresh
intermediate trend confirmation, modest short-term pullback quality, avoids
one-week and one-day upside exhaustion, rewards efficient intermediate trends,
favors constructive recent range location, requires basic accumulation support,
adds intermediate and recent close-location accumulation confirmation, avoids
recent downside shocks, applies a 25% sector cap, and sizes by fixed risk slots
so blocked slots remain cash.

Trade contract: every position change goes through order_target_percent only.
'''

from __future__ import annotations

import bisect
import logging
import math
from datetime import date

import backtrader as bt

from data.sectors import SectorAssignment, assign_sectors

logger = logging.getLogger(__name__)


def resolve_active_universe(
    universe_by_date: dict | None,
    sorted_dates: list[date] | None,
    today: date,
) -> set[str] | None:
    if not universe_by_date or not sorted_dates:
        return None
    i = bisect.bisect_right(sorted_dates, today) - 1
    if i < 0:
        return set()
    return set(universe_by_date[sorted_dates[i]])


class IndiaMomentumQualityRegime(bt.Strategy):
    '''PIT-safe fixed-slot low-volatility trend strategy.'''

    params = (
        ('trend_days', 126),
        ('recent_days', 21),
        ('vol_days', 63),
        ('max_drawdown_days', 63),
        ('defensive_days', 42),
        ('n_positions', 16),
        ('gross_exposure', 0.97),
        ('sector_cap', 0.25),
        ('rebalance_weekday', 4),
        ('rebalance_period_weeks', 2),
        ('rebalance_week_parity', 1),
        ('enforce_sector_cap', True),
        ('universe_by_date', None),
    )

    def __init__(self) -> None:
        self._tickers = [self._ticker_of(d) for d in self.datas]
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = sorted(ubd) if ubd else None

    @staticmethod
    def _ticker_of(d) -> str:
        name = getattr(d, '_name', '') or getattr(d, 'name', '') or ''
        return name.upper()

    def _active_universe(self, today: date) -> set[str] | None:
        return resolve_active_universe(self.p.universe_by_date, self._univ_dates, today)

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
        period = max(int(self.p.rebalance_period_weeks), 1)
        return iso_week % period == self.p.rebalance_week_parity % period

    def _price_at(self, d, ago: int) -> float | None:
        try:
            px = float(d.close[-ago])
        except Exception:
            return None
        if not math.isfinite(px) or px <= 0:
            return None
        return px

    def _open_at(self, d, ago: int) -> float | None:
        try:
            px = float(d.open[-ago])
        except Exception:
            return None
        if not math.isfinite(px) or px <= 0:
            return None
        return px

    def _high_at(self, d, ago: int) -> float | None:
        try:
            px = float(d.high[-ago])
        except Exception:
            return None
        if not math.isfinite(px) or px <= 0:
            return None
        return px

    def _low_at(self, d, ago: int) -> float | None:
        try:
            px = float(d.low[-ago])
        except Exception:
            return None
        if not math.isfinite(px) or px <= 0:
            return None
        return px

    def _volume_at(self, d, ago: int) -> float | None:
        try:
            vol = float(d.volume[-ago])
        except Exception:
            return None
        if not math.isfinite(vol) or vol < 0:
            return None
        return vol

    def _returns(self, d, days: int) -> list[float] | None:
        if len(d) < days + 2:
            return None
        out: list[float] = []
        for i in range(days, 0, -1):
            p0 = self._price_at(d, i)
            p1 = self._price_at(d, i - 1)
            if p0 is None or p1 is None:
                return None
            out.append((p1 / p0) - 1.0)
        return out

    def _worst_return(self, d, days: int) -> float | None:
        rets = self._returns(d, days)
        if not rets:
            return None
        vals = [r for r in rets if math.isfinite(r)]
        if len(vals) < max(10, days // 2):
            return None
        return min(vals)

    def _simple_ma_distance(self, d, days: int) -> float | None:
        if len(d) < days + 1:
            return None
        current = self._price_at(d, 0)
        if current is None:
            return None
        total = 0.0
        used = 0
        for i in range(days, -1, -1):
            px = self._price_at(d, i)
            if px is None:
                return None
            total += px
            used += 1
        ma = total / max(used, 1)
        if ma <= 0 or not math.isfinite(ma):
            return None
        return (current / ma) - 1.0

    def _realized_vol(self, d, days: int) -> float | None:
        rets = self._returns(d, days)
        if not rets or len(rets) < 20:
            return None
        mean = sum(rets) / len(rets)
        var = sum((r - mean) * (r - mean) for r in rets) / max(len(rets) - 1, 1)
        vol = math.sqrt(max(var, 0.0)) * math.sqrt(252.0)
        if not math.isfinite(vol) or vol <= 0:
            return None
        return vol

    def _trend_efficiency(self, d, days: int) -> float | None:
        rets = self._returns(d, days)
        if not rets or len(rets) < 20:
            return None
        total = sum(rets)
        path = sum(abs(r) for r in rets)
        if path <= 0.0 or not math.isfinite(path):
            return None
        efficiency = total / path
        if not math.isfinite(efficiency):
            return None
        return max(min(efficiency, 1.0), -1.0)

    def _range_location(self, d, days: int) -> float | None:
        if len(d) < days + 1:
            return None
        current = self._price_at(d, 0)
        if current is None:
            return None
        low = None
        high = None
        for i in range(days, -1, -1):
            px = self._price_at(d, i)
            if px is None:
                return None
            if low is None or px < low:
                low = px
            if high is None or px > high:
                high = px
        if low is None or high is None or high <= low:
            return None
        location = (current - low) / (high - low)
        if not math.isfinite(location):
            return None
        return max(min(location, 1.0), 0.0)

    def _volume_accumulation(self, d, days: int) -> float | None:
        if len(d) < days + 2:
            return None
        up_value = 0.0
        down_value = 0.0
        used = 0
        for i in range(days, 0, -1):
            p0 = self._price_at(d, i)
            p1 = self._price_at(d, i - 1)
            vol = self._volume_at(d, i - 1)
            if p0 is None or p1 is None or vol is None:
                return None
            value = vol * p1
            if not math.isfinite(value) or value < 0.0:
                return None
            ret = (p1 / p0) - 1.0
            if ret > 0.0:
                up_value += value
                used += 1
            elif ret < 0.0:
                down_value += value
                used += 1
        total = up_value + down_value
        if used < 20 or total <= 0.0:
            return None
        score = (up_value - down_value) / total
        if not math.isfinite(score):
            return None
        return max(min(score, 1.0), -1.0)

    def _close_location_accumulation(self, d, days: int) -> float | None:
        if len(d) < days + 2:
            return None
        weighted = 0.0
        total_value = 0.0
        used = 0
        for i in range(days, 0, -1):
            close_px = self._price_at(d, i - 1)
            high_px = self._high_at(d, i - 1)
            low_px = self._low_at(d, i - 1)
            vol = self._volume_at(d, i - 1)
            if close_px is None or high_px is None or low_px is None or vol is None:
                return None
            daily_range = high_px - low_px
            if daily_range <= 0.0 or not math.isfinite(daily_range):
                continue
            value = close_px * vol
            if not math.isfinite(value) or value < 0.0:
                return None
            close_location = ((close_px - low_px) / daily_range) - 0.5
            weighted += value * close_location
            total_value += value
            used += 1
        if used < 20 or total_value <= 0.0:
            return None
        score = 2.0 * weighted / total_value
        if not math.isfinite(score):
            return None
        return max(min(score, 1.0), -1.0)

    def _max_drawdown(self, d, days: int) -> float | None:
        if len(d) < days + 1:
            return None
        peak = None
        worst = 0.0
        for i in range(days, -1, -1):
            px = self._price_at(d, i)
            if px is None:
                return None
            if peak is None or px > peak:
                peak = px
            dd = (px / peak) - 1.0
            if dd < worst:
                worst = dd
        return abs(worst)

    def _trend_persistence(self, d) -> float | None:
        segments = 6
        step = max(1, self.p.trend_days // segments)
        if len(d) < (segments * step) + 2:
            return None

        positive = 0
        used = 0
        total = 0.0
        for idx in range(segments, 0, -1):
            p0 = self._price_at(d, idx * step)
            p1 = self._price_at(d, (idx - 1) * step)
            if p0 is None or p1 is None:
                return None
            interval_ret = (p1 / p0) - 1.0
            if not math.isfinite(interval_ret):
                return None
            if interval_ret > 0.0:
                positive += 1
            total += interval_ret
            used += 1

        if used < segments:
            return None
        hit_rate = positive / used
        avg_step = total / used
        clipped_avg = max(min(avg_step * 3.0, 0.15), -0.15)
        return (hit_rate - 0.5) + clipped_avg

    def _recent_market_returns(self, active: set[str] | None, days: int) -> list[float] | None:
        daily_returns: list[list[float]] = []
        for d in self.datas:
            ticker = self._ticker_of(d)
            if active is not None and ticker not in active:
                continue
            rets = self._returns(d, days)
            if rets is not None:
                daily_returns.append(rets)
        if len(daily_returns) < 50:
            return None

        market: list[float] = []
        for i in range(days):
            vals = [row[i] for row in daily_returns if math.isfinite(row[i])]
            if len(vals) < 50:
                return None
            vals.sort()
            mid = len(vals) // 2
            if len(vals) % 2:
                market.append(vals[mid])
            else:
                market.append((vals[mid - 1] + vals[mid]) / 2.0)
        return market

    def _defensive_relative_strength(self, d, market_returns: list[float] | None) -> float:
        if not market_returns:
            return 0.0
        rets = self._returns(d, len(market_returns))
        if not rets:
            return 0.0

        rel_sum = 0.0
        used = 0
        weak_sum = 0.0
        weak_used = 0
        for stock_ret, market_ret in zip(rets, market_returns):
            if not math.isfinite(stock_ret) or not math.isfinite(market_ret):
                continue
            if market_ret < 0.0:
                rel_sum += stock_ret - market_ret
                used += 1
            if market_ret < -0.004:
                weak_sum += stock_ret - market_ret
                weak_used += 1

        if used < 8:
            return 0.0
        score = rel_sum / used
        if weak_used >= 4:
            score = (0.65 * score) + (0.35 * (weak_sum / weak_used))
        return max(min(score, 0.04), -0.04)

    def _score_for(self, d, market_returns: list[float] | None = None) -> float | None:
        need = max(
            self.p.trend_days,
            self.p.vol_days,
            self.p.max_drawdown_days,
            self.p.defensive_days,
        ) + 2
        if len(d) < need:
            return None

        current = self._price_at(d, 0)
        prior = self._price_at(d, 1)
        trend_start = self._price_at(d, self.p.trend_days)
        intermediate_start = self._price_at(d, self.p.vol_days)
        recent_start = self._price_at(d, self.p.recent_days)
        fast_days = max(3, self.p.recent_days // 4)
        fast_start = self._price_at(d, fast_days)
        if (
            current is None
            or prior is None
            or trend_start is None
            or intermediate_start is None
            or recent_start is None
            or fast_start is None
        ):
            return None

        trend = (current / trend_start) - 1.0
        intermediate = (current / intermediate_start) - 1.0
        recent = (current / recent_start) - 1.0
        fast = (current / fast_start) - 1.0
        one_day = (current / prior) - 1.0
        if trend <= 0.03 or intermediate <= 0.0 or recent < -0.04 or one_day > 0.075:
            return None

        vol = self._realized_vol(d, self.p.vol_days)
        drawdown = self._max_drawdown(d, self.p.max_drawdown_days)
        persistence = self._trend_persistence(d)
        ma_distance = self._simple_ma_distance(d, self.p.recent_days)
        efficiency = self._trend_efficiency(d, self.p.vol_days)
        range_location = self._range_location(d, self.p.vol_days)
        accumulation = self._volume_accumulation(d, self.p.vol_days)
        close_accumulation = self._close_location_accumulation(d, self.p.vol_days)
        recent_close_accumulation = self._close_location_accumulation(d, self.p.recent_days)
        worst_recent = self._worst_return(d, self.p.recent_days)
        if (
            vol is None
            or drawdown is None
            or persistence is None
            or ma_distance is None
            or efficiency is None
            or range_location is None
            or accumulation is None
            or close_accumulation is None
            or recent_close_accumulation is None
            or worst_recent is None
        ):
            return None
        if (
            vol > 0.75
            or drawdown > 0.35
            or persistence < -0.05
            or ma_distance > 0.16
            or efficiency < -0.05
            or range_location < 0.32
            or accumulation < -0.12
            or close_accumulation < -0.18
            or recent_close_accumulation < -0.24
            or worst_recent < -0.085
        ):
            return None

        pullback_quality = -abs(ma_distance - 0.015)
        range_quality = -abs(range_location - 0.75)
        fast_exhaustion = max(fast - 0.055, 0.0)
        one_day_exhaustion = max(one_day - 0.035, 0.0)
        defensive = self._defensive_relative_strength(d, market_returns)
        return (
            (0.64 * trend)
            + (0.13 * recent)
            + (0.22 * persistence)
            + (0.10 * efficiency)
            + (0.08 * range_quality)
            + (0.18 * pullback_quality)
            + (0.06 * accumulation)
            + (0.045 * close_accumulation)
            + (0.025 * recent_close_accumulation)
            + (2.25 * defensive)
            - (0.45 * vol)
            - (0.35 * drawdown)
            - (0.70 * fast_exhaustion)
            - (0.45 * one_day_exhaustion)
        )

    def _rank_universe(self, active: set[str] | None) -> list[tuple[str, float]]:
        scores: list[tuple[str, float]] = []
        market_returns = self._recent_market_returns(active, self.p.defensive_days)
        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            score = self._score_for(d, market_returns)
            if score is None:
                continue
            scores.append((t, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores

    def _sector_of(self, ticker: str) -> str:
        assignment = self._sector_map.get(ticker)
        if assignment is None:
            return ''
        sector = getattr(assignment, 'sector', '') or getattr(assignment, 'bucket', '') or ''
        return str(sector)

    def _select_with_sector_cap(self, ranked: list[tuple[str, float]]) -> list[str]:
        selected: list[str] = []
        sector_counts: dict[str, int] = {}
        max_per_sector = max(1, int(math.floor(self.p.n_positions * self.p.sector_cap)))
        breadth_floor = max(self.p.n_positions + 2, int(math.ceil(self.p.n_positions * 1.20)))
        if len(ranked) < breadth_floor:
            return selected
        for ticker, _score in ranked:
            if len(selected) >= self.p.n_positions:
                break
            sector = self._sector_of(ticker)
            if self.p.enforce_sector_cap and sector:
                count = sector_counts.get(sector, 0)
                if count >= max_per_sector:
                    continue
                sector_counts[sector] = count + 1
            selected.append(ticker)
        return selected

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)
        active = self._active_universe(today)
        if active is not None and not active:
            return

        ranked = self._rank_universe(active)
        selected = self._select_with_sector_cap(ranked)
        selected_set = set(selected)
        target_each = self.p.gross_exposure / max(self.p.n_positions, 1)

        held = {self._ticker_of(d): self.getposition(d).size for d in self.datas}
        held = {t: q for t, q in held.items() if q > 0}

        for d in self.datas:
            ticker = self._ticker_of(d)
            if active is not None and ticker not in active:
                continue
            if ticker in selected_set:
                self.order_target_percent(d, target=target_each)
            elif ticker in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            'rebalance %s: active=%s ranked=%d selected=%d target_each=%.4f',
            today,
            len(active) if active is not None else None,
            len(ranked),
            len(selected),
            target_each,
        )


__all__ = ['IndiaMomentumQualityRegime']
