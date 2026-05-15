"""India autoresearch starting strategy.

12-1 cross-sectional momentum + quality screen + sector cap + Indian regime
gate. Sparse — 5 hyperparameters total, all canonical values from the
literature. The autoresearch loop may mutate this file; it must NOT mutate
`prepare.py` (immutable evaluator) or the anti-overfit gates.

Rebalance: biweekly (every other Friday). On non-rebalance bars the strategy
returns early — no `order_target_percent` call.

Hyperparameters (5):
  - lookback_days (252) + skip_days (21) — 12-1 momentum
  - retention_mult (2.0) — held names retained if still in top retention_mult × decile
  - quality_pct (50) — ROE percentile floor among candidates
  - regime_pct (95), fii_threshold_cr (-15000) — regime gate thresholds
  - n_positions (6) — target portfolio size

Trade contract: every position-change goes through `self.order_target_percent`.
Never `self.buy()` / `self.close()`. Required by `scripts.signal_today` capture
logic.
"""

from __future__ import annotations

import bisect
import logging
from datetime import date
from pathlib import Path

import backtrader as bt

from data.quality_screen import (
    apply_quality_screen,
    load_fundamentals,
)
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
    """Resolve the point-in-time eligible universe (audit-2026-05-15 Fix B).

    - None              → no PIT universe injected; all loaded feeds eligible.
    - most-recent ≤ today → that snapshot's membership.
    - today before the earliest snapshot → empty set (nothing eligible yet;
      NEVER fall forward to a future snapshot — that would reintroduce the
      look-ahead this fix exists to remove).
    """
    if not universe_by_date or not sorted_dates:
        return None
    i = bisect.bisect_right(sorted_dates, today) - 1
    if i < 0:
        return set()
    return set(universe_by_date[sorted_dates[i]])


class IndiaMomentumQualityRegime(bt.Strategy):
    """Cross-sectional 12-1 momentum + quality + sector cap + regime gate."""

    params = (
        ("lookback_days", 252),
        ("skip_days", 21),
        ("retention_mult", 2.0),
        ("quality_pct", 50),
        ("regime_pct", 95),
        ("fii_threshold_cr", -15000.0),
        ("n_positions", 6),
        ("sector_cap", 0.25),
        # Rebalance cadence (biweekly = every other Friday)
        ("rebalance_weekday", 4),       # Friday
        ("rebalance_period_weeks", 2),
        ("rebalance_week_parity", 0),   # 0 or 1 — pinned at start of backtest
        # Optional sidecar DB paths (defaults match runtime layout). Backtest
        # / live can override.
        ("universe_db_path", "storage/universe.duckdb"),
        ("fundamentals_db_path", "storage/fundamentals.duckdb"),
        ("macro_db_path", "storage/macro.duckdb"),
        # Sector cap: when True, sector_map is loaded from `data.sectors` using
        # the per-ticker industry tag carried on the data feeds.
        ("enforce_sector_cap", True),
        # Point-in-time universe injected by the evaluator / live runner:
        # {snapshot_date: frozenset(tickers)}. When set, only names in the
        # most-recent snapshot ON OR BEFORE the rebalance date are eligible
        # for ranking/entry (exits of dropped names still fire). When None,
        # every loaded feed is eligible (standalone / unit-test behaviour).
        # This is the audit-2026-05-15 Fix B guard against survivorship /
        # frozen-universe look-ahead and must not be removed by the loop.
        ("universe_by_date", None),
    )

    # ──────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._tickers = [self._ticker_of(d) for d in self.datas]
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        self._fund_cache: dict[date, dict] = {}
        self._regime_cache: dict[date, str] = {}
        # Pin rebalance week parity to the first Friday on or after start
        # so we don't drift across data-feed start variations.
        self._week_parity_initialized = False
        # Sorted snapshot dates for the point-in-time universe (Fix B).
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = (
            sorted(ubd) if ubd else None
        )

    def _active_universe(self, today: date) -> set[str] | None:
        """Tickers eligible for ranking/entry as of `today`. Thin wrapper over
        the pure resolver so the (bug-prone) point-in-time lookup is unit-
        testable without a backtrader scaffold."""
        return resolve_active_universe(
            self.p.universe_by_date, self._univ_dates, today
        )

    @staticmethod
    def _ticker_of(d) -> str:
        name = getattr(d, "_name", "") or getattr(d, "name", "") or ""
        return name.upper()

    def _load_sector_map(self) -> dict[str, SectorAssignment]:
        # The feeds may carry an `industry` attribute (set by ingest helpers);
        # if not, return empty (sector cap becomes a no-op).
        rows = []
        for d in self.datas:
            ind = getattr(d, "_industry", None) or getattr(d, "industry", None)
            t = self._ticker_of(d)

            class _Row:
                ticker = t
                industry = ind or ""

            rows.append(_Row())
        return assign_sectors(rows)

    # ──────────────────────────────────────────────────────────
    # Rebalance gate
    # ──────────────────────────────────────────────────────────

    def _is_rebalance_today(self) -> bool:
        today = self.datas[0].datetime.date(0)
        if today.weekday() != self.p.rebalance_weekday:
            return False
        iso_week = today.isocalendar().week
        if not self._week_parity_initialized:
            # Pin parity to today's parity ⇒ rebalance on this Friday and every
            # other one. Stable across data-start variations.
            self._week_parity_initialized = True
            object.__setattr__(self.params, "rebalance_week_parity", iso_week % 2)
            return True
        return iso_week % 2 == self.p.rebalance_week_parity

    # ──────────────────────────────────────────────────────────
    # Signals
    # ──────────────────────────────────────────────────────────

    def _momentum_for(self, d) -> float | None:
        n = len(d)
        need = self.p.lookback_days + self.p.skip_days + 1
        if n < need:
            return None
        c_recent = d.close[-self.p.skip_days]
        c_start = d.close[-(self.p.lookback_days + self.p.skip_days)]
        if c_start is None or c_start <= 0:
            return None
        return (c_recent / c_start) - 1.0

    def _rank_universe(
        self, active: set[str] | None = None
    ) -> list[tuple[str, float]]:
        scores: list[tuple[str, float]] = []
        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue  # not in the point-in-time universe as of today
            mom = self._momentum_for(d)
            if mom is None:
                continue
            scores.append((t, mom))
        scores.sort(key=lambda t: t[1], reverse=True)
        return scores

    def _regime_gate(self, today: date) -> bool:
        """Returns True if new entries are ALLOWED today.

        Reads `llm.features.macro_regime_for(today)` if available; falls back
        to permissive (allow) so v1 paper can run before macro classifiers
        are wired up. The autoresearch loop's job is to discover the
        precise composition of the gate; we keep the structure here.
        """
        try:
            from llm.features import macro_regime_for  # type: ignore

            regime = macro_regime_for(today)
            self._regime_cache[today] = regime
            return regime in ("risk_on", "neutral")
        except Exception:
            return True

    # ──────────────────────────────────────────────────────────
    # Backtrader hook
    # ──────────────────────────────────────────────────────────

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)

        # 1. Rank by 12-1 momentum, restricted to the point-in-time universe
        #    as of today (Fix B: no survivorship / frozen-universe look-ahead)
        active = self._active_universe(today)
        ranked = self._rank_universe(active)
        if not ranked:
            return

        # 2. Quality screen on the top-decile candidates (≈20% of universe)
        decile_count = max(self.p.n_positions * 3, int(0.2 * len(ranked)))
        candidate_tickers = [t for t, _ in ranked[:decile_count]]
        fundamentals_path = Path(self.p.fundamentals_db_path)
        fundamentals = load_fundamentals(
            fundamentals_path, candidate_tickers, today
        )
        passed_quality, _screen_results = apply_quality_screen(
            candidate_tickers,
            fundamentals,
            sector_map=self._sector_map,
            roe_percentile=self.p.quality_pct,
        )
        if not passed_quality:
            passed_quality = candidate_tickers  # soft-degrade

        # 3. Regime gate (block new entries on risk_off / shock)
        allow_new = self._regime_gate(today)

        # 4. Retention buffer: held names that are still in top retention_mult × decile pass
        held = {self._ticker_of(d): self.getposition(d).size for d in self.datas}
        held = {t: q for t, q in held.items() if q > 0}
        retention_cap = int(self.p.retention_mult * self.p.n_positions)
        top_retain = {t for t, _ in ranked[: max(retention_cap, self.p.n_positions)]}
        retained = [t for t in held if t in top_retain]
        slots_remaining = self.p.n_positions - len(retained)

        # 5. Select new entries (if allow_new), respecting sector cap
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
        # 1% cash buffer for commission + slippage; without this backtrader can
        # silently reject the final order when the cumulative target hits 100%.
        target_each = 0.99 / max(len(selected), 1) if selected else 0.0

        # 6. Issue orders: order_target_percent for every name (selected or
        # held-but-being-exited gets 0.0)
        for d in self.datas:
            t = self._ticker_of(d)
            if t in selected:
                self.order_target_percent(d, target=target_each)
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            "rebalance %s: ranked=%d, quality_passed=%d, retained=%d, new=%d, target=%d",
            today,
            len(ranked),
            len(passed_quality),
            len(retained),
            len(new_entries),
            len(selected),
        )


__all__ = ["IndiaMomentumQualityRegime"]
