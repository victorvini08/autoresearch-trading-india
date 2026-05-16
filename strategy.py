"""India autoresearch strategy — 52-week-high proximity + quality + sector cap + Nifty 200-DMA gate.

The ranking signal is 52-week high proximity: current_price / max_close_over_lookback_window.
Range (0, 1]. Higher = stock is closer to its 52-week high = stronger anchoring-bias
momentum continuation (George & Hwang 2004). This is bounded, non-magnitude-biased,
and structurally distinct from the raw 12-1 return signal that repeatedly showed
Bonferroni p≈1.0 on the Indian top-200 universe.

Regime gate: Nifty 50 200-DMA trend filter (nifty50_pct_vs_200dma > 0 → allow new entries).
Replaces the LLM macro_regime_for gate, which is unreliable during backtesting: when the
cache row is absent macro_regime_for returns None → None not in (risk_on, neutral) → gate
blocks ALL new entries; when it throws → fallback True → gate allows ALL entries. The
200-DMA filter reads from macro_signals which has real price-data coverage throughout the
backtest window and is deterministic.

Rebalance: biweekly (every other Friday).

Tunable hyperparameters:
  - lookback_days (252) + skip_days (21) — proximity window
  - retention_mult (2.0) — held names retained if still in top N
  - regime_pct (95), fii_threshold_cr (-15000) — kept for API compat (not used in gate)
  - n_positions (25), sector_cap (0.25)

Trade contract: every position-change goes through `self.order_target_percent`.
Never `self.buy()` / `self.close()`. Required by `scripts.signal_today` capture logic.
"""

from __future__ import annotations

from datetime import date

import backtrader as bt

from data.quality_screen import (
    DEFAULT_ROE_PERCENTILE,
    apply_quality_screen,
    load_fundamentals,
)
from data.sectors import (
    SectorAssignment,
    assign_sectors,
    enforce_sector_cap,
)


def resolve_active_universe(
    universe_by_date: dict | None,
    sorted_dates: list[date] | None,
    today: date,
) -> set[str] | None:
    """Resolve the point-in-time eligible universe (audit-2026-05-15 Fix B).

    - None              -> no PIT universe injected; all loaded feeds eligible.
    - most-recent <= today -> that snapshot's membership.
    - today before the earliest snapshot -> empty set (no look-ahead).
    """
    if not universe_by_date or not sorted_dates:
        return None
    lo, hi = 0, len(sorted_dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_dates[mid] <= today:
            lo = mid + 1
        else:
            hi = mid
    i = lo - 1
    if i < 0:
        return set()
    return set(universe_by_date[sorted_dates[i]])


class IndiaMomentumQualityRegime(bt.Strategy):
    """Cross-sectional 52-week-high proximity + quality + sector cap + Nifty 200-DMA gate."""

    params = (
        ("lookback_days", 252),
        ("skip_days", 21),
        ("retention_mult", 2.0),
        ("regime_pct", 95),
        ("fii_threshold_cr", -15000.0),
        ("n_positions", 25),
        ("sector_cap", 0.25),
        ("rebalance_weekday", 4),
        ("rebalance_period_weeks", 2),
        ("rebalance_week_parity", 0),
        ("universe_db_path", "storage/universe.duckdb"),
        ("fundamentals_db_path", "storage/fundamentals.duckdb"),
        ("macro_db_path", "storage/macro.duckdb"),
        ("enforce_sector_cap", True),
        ("universe_by_date", None),
    )

    def __init__(self) -> None:
        self._tickers = [self._ticker_of(d) for d in self.datas]
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        self._fund_cache: dict[date, dict] = {}
        self._regime_cache: dict[date, bool] = {}
        self._week_parity_initialized = False
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = (
            sorted(ubd) if ubd else None
        )

    def _active_universe(self, today: date) -> set[str] | None:
        return resolve_active_universe(
            self.p.universe_by_date, self._univ_dates, today
        )

    @staticmethod
    def _ticker_of(d) -> str:
        name = getattr(d, "_name", "") or getattr(d, "name", "") or ""
        return name.upper()

    def _load_sector_map(self) -> dict[str, SectorAssignment]:
        rows = []
        for d in self.datas:
            ind = getattr(d, "_industry", None) or getattr(d, "industry", None)
            t = self._ticker_of(d)

            class _Row:
                ticker = t
                industry = ind or ""

            rows.append(_Row())
        return assign_sectors(rows)

    def _is_rebalance_today(self) -> bool:
        today = self.datas[0].datetime.date(0)
        if today.weekday() != self.p.rebalance_weekday:
            return False
        iso_week = today.isocalendar().week
        if not self._week_parity_initialized:
            self._week_parity_initialized = True
            object.__setattr__(self.params, "rebalance_week_parity", iso_week % 2)
            return True
        return iso_week % 2 == self.p.rebalance_week_parity

    def _high52_proximity_for(self, d) -> float | None:
        """Score = current_close / max_close_over_lookback_window, range (0, 1].

        Higher means the stock is closer to its 52-week high. Captures the
        anchoring-bias momentum of George & Hwang (2004): analysts anchor price
        targets to the 52-week high and underreact to good news near that level,
        producing continued upward drift. Window ends skip_days ago to match
        execution lag (signal as-of-close, orders fill next open).
        """
        n = len(d)
        need = self.p.lookback_days + self.p.skip_days + 1
        if n < need:
            return None
        c_recent = d.close[-self.p.skip_days]
        if c_recent is None or c_recent <= 0:
            return None
        window_high = None
        for k in range(self.p.skip_days, self.p.lookback_days + self.p.skip_days + 1):
            val = d.close[-k]
            if val is not None and val > 0:
                if window_high is None or val > window_high:
                    window_high = val
        if window_high is None or window_high <= 0:
            return None
        return c_recent / window_high

    def _rank_universe(
        self, active: set[str] | None = None
    ) -> list[tuple[str, float]]:
        scores: list[tuple[str, float]] = []
        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            score = self._high52_proximity_for(d)
            if score is None:
                continue
            scores.append((t, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def _regime_gate(self, today: date) -> bool:
        """Allow new entries only when Nifty 50 trades above its 200-day moving average.

        Uses nifty50_pct_vs_200dma from macro_signals, which has real price-data coverage
        throughout the backtest window (computed from NSE price data, not an LLM job).
        Positive value means Nifty is trending up → allow new buys.
        Fallback is True (allow) when macro DB is unavailable.
        """
        if today in self._regime_cache:
            return self._regime_cache[today]
        result = True
        try:
            from llm.features import macro_signals  # type: ignore

            signals = macro_signals(today)
            if signals and "nifty50_pct_vs_200dma" in signals:
                result = signals["nifty50_pct_vs_200dma"] > 0.0
        except Exception:
            pass
        self._regime_cache[today] = result
        return result

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)

        active = self._active_universe(today)
        ranked = self._rank_universe(active)
        if not ranked:
            return

        decile_count = max(self.p.n_positions * 3, int(0.2 * len(ranked)))
        candidate_tickers = [t for t, _ in ranked[:decile_count]]
        fundamentals = load_fundamentals(
            self.p.fundamentals_db_path, candidate_tickers, today
        )
        passed_quality, _screen_results = apply_quality_screen(
            candidate_tickers,
            fundamentals,
            sector_map=self._sector_map,
            roe_percentile=DEFAULT_ROE_PERCENTILE,
        )
        if not passed_quality:
            passed_quality = candidate_tickers

        allow_new = self._regime_gate(today)

        held = {self._ticker_of(d): self.getposition(d).size for d in self.datas}
        held = {t: q for t, q in held.items() if q > 0}
        retention_cap = int(self.p.retention_mult * self.p.n_positions)
        top_retain = {t for t, _ in ranked[: max(retention_cap, self.p.n_positions)]}
        retained = [t for t in held if t in top_retain]
        slots_remaining = self.p.n_positions - len(retained)

        new_entries: list[str] = []
        if allow_new and slots_remaining > 0:
            new_candidates = [
                t for t in passed_quality if t not in retained and t not in held
            ]
            if self.p.enforce_sector_cap and self._sector_map:
                target_each = 1.0 / max(self.p.n_positions, 1)
                new_entries = enforce_sector_cap(
                    ranked_candidates=new_candidates,
                    target_fraction_each=target_each,
                    sector_map=self._sector_map,
                    max_sector_fraction=self.p.sector_cap,
                    n_target=slots_remaining,
                )
            else:
                new_entries = new_candidates[:slots_remaining]

        selected = retained + new_entries
        target_each = 0.99 / max(len(selected), 1) if selected else 0.0

        for d in self.datas:
            t = self._ticker_of(d)
            if t in selected:
                self.order_target_percent(d, target=target_each)
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today


__all__ = ["IndiaMomentumQualityRegime"]
