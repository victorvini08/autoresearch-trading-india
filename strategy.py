"""Strategy B — long-only residual mean-reversion statistical arbitrage.

Branch: mean-reversion-quant-strategy. The structural inverse of the
momentum book on `main`: this strategy buys names that are oversold
*relative to their market + size factor exposures* (cumulative factor
residual most negative), expecting reversion. Sparse — 7 tunable signal
knobs, matching the momentum book's parsimony footprint so neither
autoresearch loop starts with a parsimony-gate advantage.

The signal math is extracted into pure functions (`ols_beta`,
`market_factor`, `smb_factor`, `reversion_scores`) so the bug-prone parts
are unit-testable without a backtrader scaffold — same discipline that
kept `resolve_active_universe` pure.

Rebalance: biweekly (every other Friday). On non-rebalance bars the
strategy returns early — no `order_target_percent` call.

Tunable signal hyperparameters:
  - beta_window (60) — rolling OLS window for market/size betas
  - formation_days (5) — residual accumulation / reversion horizon
  - retention_mult (2.0) — held names retained if still in top
    retention_mult × n_positions by score (turnover/cost control)
  - entry_pct (0.20) — only the most-oversold tail is entry-eligible
  - regime_pct (95) — regime-gate threshold (structurally parallel to A;
    the gate currently keys off the macro_regime label)
  - n_positions (25) — target portfolio size (diversified; <10 caused the
    structural ~80% catastrophe drawdown — see 2026-05-16)
  - sector_cap (0.25) — max single-sector weight

Trade contract: every position-change goes through
`self.order_target_percent` — never the direct buy/close order calls.
Required by `scripts.signal_today` capture logic.

Design: docs/superpowers/specs/2026-05-15-strategy-b-residual-reversal-statarb-design.md
"""

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


# ──────────────────────────────────────────────────────────────────────
# Pure signal core (no backtrader) — unit-tested in test_strategy_reversion
# ──────────────────────────────────────────────────────────────────────


def ols_beta(
    y: list[float], factors: list[list[float]]
) -> list[float] | None:
    """Least squares of `y` on an intercept + each factor column. Returns
    `[intercept, b_1, ..., b_K]`, or `None` only when the system is
    underdetermined (too few rows to fit K+1 parameters).

    Collinear / near-constant factors are NOT rejected: `np.linalg.lstsq`
    returns the minimum-norm solution, and the fitted values (hence the
    residuals — the actual reversion signal) are unique even when the
    coefficients are not. Hard-rejecting collinearity made the strategy go
    inert in low-dispersion regimes (e.g. when the cross-sectional market
    factor has near-zero variance).
    """
    yv = np.asarray(y, dtype=float)
    T = yv.shape[0]
    K = len(factors)
    if T < K + 2:  # need comfortably more rows than the K+1 parameters
        return None
    X = np.column_stack(
        [np.ones(T)] + [np.asarray(f, dtype=float) for f in factors]
    )
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    return coef.tolist()


def market_factor(returns_by_ticker: dict[str, list[float]]) -> list[float]:
    """Equal-weight cross-sectional mean return per day (the 'market mode').
    Assumes all return lists are aligned and equal length.
    """
    if not returns_by_ticker:
        return []
    M = np.asarray(list(returns_by_ticker.values()), dtype=float)
    return M.mean(axis=0).tolist()


def smb_factor(
    returns_by_ticker: dict[str, list[float]],
    adv_by_ticker: dict[str, float],
) -> list[float]:
    """Size proxy: mean return of the small-ADV tercile minus the
    large-ADV tercile, per day. We have no market cap (program.md "NOT
    available"); ADV is the size/liquidity proxy. Returns a zero series
    when there are fewer than 3 ranked tickers (tercile undefined).
    """
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
    """Per-ticker reversion score = **negative** cross-sectional z-score of
    the cumulative market+size factor residual over the last
    `formation_days`. Higher score = more oversold relative to factor
    exposure = stronger buy. Tickers with < `beta_window` history are
    omitted (cannot estimate betas).
    """
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


# ──────────────────────────────────────────────────────────────────────
# backtrader adapter
# ──────────────────────────────────────────────────────────────────────


class IndiaResidualReversalStatArb(bt.Strategy):
    """Long-only cross-sectional residual mean-reversion + sector cap +
    regime gate. Buys the most-oversold tail of the factor-residual
    distribution, retains names still scoring well, exits the rest."""

    _ADV_WINDOW = 20  # in-feed ADV proxy lookback (structural, not tuned)

    params = (
        ("beta_window", 60),
        ("formation_days", 5),
        ("retention_mult", 2.0),
        ("entry_pct", 0.20),
        ("regime_pct", 95),
        ("n_positions", 25),
        ("sector_cap", 0.25),
        # Rebalance cadence (biweekly = every other Friday) — plumbing.
        ("rebalance_weekday", 4),       # Friday
        ("rebalance_period_weeks", 2),
        ("rebalance_week_parity", 0),   # 0 or 1 — pinned at start of backtest
        # Optional sidecar DB paths (defaults match runtime layout) —
        # plumbing; the signal itself is self-contained (in-feed ADV).
        ("universe_db_path", "storage/universe.duckdb"),
        ("macro_db_path", "storage/macro.duckdb"),
        # Sector cap: when True, sector_map is loaded from `data.sectors`
        # using the per-ticker industry tag carried on the data feeds.
        ("enforce_sector_cap", True),
        # Point-in-time universe injected by the evaluator / live runner:
        # {snapshot_date: frozenset(tickers)}. When set, only names in the
        # most-recent snapshot ON OR BEFORE the rebalance date are eligible
        # for ranking/entry (exits of dropped names still fire). When None,
        # every loaded feed is eligible (standalone / unit-test behaviour).
        # audit-2026-05-15 Fix B guard — must not be removed by the loop.
        ("universe_by_date", None),
    )

    # ──────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._data_by_ticker = {self._ticker_of(d): d for d in self.datas}
        self._sector_map = self._load_sector_map()
        self._last_rebalance_date: date | None = None
        self._regime_cache: dict[date, str] = {}
        self._week_parity_initialized = False
        ubd = self.p.universe_by_date
        self._univ_dates: list[date] | None = sorted(ubd) if ubd else None

    def _active_universe(self, today: date) -> set[str] | None:
        """Tickers eligible for ranking/entry as of `today`. Thin wrapper
        over the pure resolver so the point-in-time lookup is unit-testable
        without a backtrader scaffold."""
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

    # ──────────────────────────────────────────────────────────
    # Rebalance gate
    # ──────────────────────────────────────────────────────────

    def _is_rebalance_today(self) -> bool:
        today = self.datas[0].datetime.date(0)
        if today.weekday() != self.p.rebalance_weekday:
            return False
        iso_week = today.isocalendar().week
        if not self._week_parity_initialized:
            self._week_parity_initialized = True
            object.__setattr__(
                self.params, "rebalance_week_parity", iso_week % 2
            )
            return True
        return iso_week % 2 == self.p.rebalance_week_parity

    # ──────────────────────────────────────────────────────────
    # Feed → pure-signal extraction
    # ──────────────────────────────────────────────────────────

    def _returns_and_adv(
        self, active: set[str] | None
    ) -> tuple[dict[str, list[float]], dict[str, float]]:
        """Build aligned trailing return series + an in-feed ADV proxy for
        every eligible feed with enough history. Returns oldest→newest."""
        w = self.p.beta_window
        need = w + 1
        returns_by_ticker: dict[str, list[float]] = {}
        adv_by_ticker: dict[str, float] = {}
        for d in self.datas:
            t = self._ticker_of(d)
            if active is not None and t not in active:
                continue
            if len(d) < max(need, self._ADV_WINDOW):
                continue
            closes = [d.close[-i] for i in range(w, -1, -1)]  # oldest→newest
            if any(c is None or c <= 0 for c in closes):
                continue
            rets = [
                closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))
            ]
            adv = float(
                np.mean(
                    [
                        d.close[-i] * d.volume[-i]
                        for i in range(self._ADV_WINDOW)
                    ]
                )
            )
            returns_by_ticker[t] = rets
            adv_by_ticker[t] = adv
        return returns_by_ticker, adv_by_ticker

    # ──────────────────────────────────────────────────────────
    # Regime gate
    # ──────────────────────────────────────────────────────────

    def _regime_gate(self, today: date) -> bool:
        """True if new entries are ALLOWED today. Reversion is fragile in
        trending crashes ('falling knife'), so a defensive gate matters
        MORE here, not less. Falls back to permissive when the macro cache
        is not yet precomputed."""
        try:
            from llm.features import macro_regime_for  # type: ignore

            regime = macro_regime_for(today)
            self._regime_cache[today] = regime
            return regime in ("risk_on", "neutral")
        except Exception:
            return True

    # ──────────────────────────────────────────────────────────
    # backtrader hook
    # ──────────────────────────────────────────────────────────

    def next(self) -> None:
        if not self._is_rebalance_today():
            return

        today = self.datas[0].datetime.date(0)

        # 1. Eligible feeds (point-in-time universe; Fix B guard)
        active = self._active_universe(today)
        returns_by_ticker, adv_by_ticker = self._returns_and_adv(active)
        if len(returns_by_ticker) < 3:
            return

        # 2. Residual reversion score; rank most-oversold first
        scores = reversion_scores(
            returns_by_ticker,
            adv_by_ticker,
            self.p.beta_window,
            self.p.formation_days,
        )
        if not scores:
            return
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

        # 3. Only the most-oversold tail is entry-eligible
        eligible_n = max(
            self.p.n_positions, int(self.p.entry_pct * len(ranked))
        )
        candidates = [t for t, _ in ranked[:eligible_n]]

        # 4. Regime gate (block new entries on risk_off / shock)
        allow_new = self._regime_gate(today)

        # 5. Retention buffer: held names still scoring in the top
        #    retention_mult × n band are kept (suppresses turnover/DP drag)
        held = {
            self._ticker_of(d): self.getposition(d).size for d in self.datas
        }
        held = {t: q for t, q in held.items() if q > 0}
        retention_cap = int(self.p.retention_mult * self.p.n_positions)
        top_retain = {
            t for t, _ in ranked[: max(retention_cap, self.p.n_positions)]
        }
        retained = [t for t in held if t in top_retain]
        slots_remaining = self.p.n_positions - len(retained)

        # 6. New entries (if allowed), respecting the sector cap
        new_entries: list[str] = []
        if allow_new and slots_remaining > 0:
            new_candidates = [
                t
                for t in candidates
                if t not in retained and t not in held
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
        # 1% cash buffer for commission + slippage; without it backtrader can
        # silently reject the final order when the cumulative target hits 100%.
        target_each = 0.99 / max(len(selected), 1) if selected else 0.0

        # 7. order_target_percent for every name (exits get 0.0)
        for d in self.datas:
            t = self._ticker_of(d)
            if t in selected:
                self.order_target_percent(d, target=target_each)
            elif t in held:
                self.order_target_percent(d, target=0.0)

        self._last_rebalance_date = today
        logger.debug(
            "rebalance %s: scored=%d, eligible=%d, retained=%d, new=%d, "
            "target=%d",
            today,
            len(scores),
            len(candidates),
            len(retained),
            len(new_entries),
            len(selected),
        )


__all__ = [
    "resolve_active_universe",
    "ols_beta",
    "market_factor",
    "smb_factor",
    "reversion_scores",
    "IndiaResidualReversalStatArb",
]
