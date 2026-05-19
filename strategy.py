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
  - Deploy the regime-scaled `gross` down the ranked list via
    ``construct_gross_targets`` (Improvement G, 2026-05-18, user-authorised
    locked-decision change): walk the ranking allocating capital until the
    intended `gross` is actually invested, bounded by a per-name cap
    (``_MAX_NAME_WEIGHT``) AND the per-sector cap, continuing into other
    sectors rather than leaking the sector-capped remainder to cash.
  - This is NOT the §4-banned naive ``gross / len(selected)`` sizing: the
    hard per-name and per-sector caps bound single-name/single-sector
    concentration (the blow-up risk §4 exists to prevent), while removing
    the unintended deployment pin (old fixed-slot `gross/n_positions` +
    cap-and-leak deployed only ~24% in ALL regimes -- even when
    breadth_scaled_gross asked for 0.99 -- because the sector cap divided by
    a tiny per-name target clamped the whole book to ~one sector).
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


def _structural_ma_window(lookback: int) -> int:
    '''Length of the structural trend MA, derived from the signal lookback.

    Single source of truth so the entry filter (price must be ABOVE this MA
    to qualify) and the between-rebalance structural exit (sell once price
    falls BELOW it) provably use the SAME definition and cannot drift apart.
    Not a new tunable knob -- this is the strategy's pre-existing inline
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


# Annualised portfolio volatility TARGET (a risk POLICY, not a fitted
# knob): the vol-managed-momentum overlay scales gross so the book runs at
# ~this realised volatility. 12% is a standard institutional moderate
# target. This is the single most-replicated robust improvement to a
# momentum book (Barroso & Santa-Clara 2015; Moreira & Muir 2017): it
# deploys MORE in calm up-trends (captures upside -- the user's core ask)
# and LESS in turbulent / momentum-crash regimes (principled downside,
# not the old 25%-cap bug artefact). Now meaningful only because the
# sector-wiring bug is fixed and gross actually deploys.
_ANNUAL_VOL_TARGET = 0.12
_TRADING_DAYS = 252


def _annualised_realised_vol(
    close_by_ticker: dict[str, list[float]], vol_lb: int
) -> float | None:
    '''Annualised std of the equal-weight cross-sectional daily return.

    Pure/deterministic. Returns None when fewer than 20 usable series are
    available (caller decides the fallback), so the same robust 20-name
    floor is enforced whether the input is the held book or the broad
    active-universe proxy -- no new tunable knob is introduced.
    '''
    rets = []
    for raw in close_by_ticker.values():
        if len(raw) < vol_lb + 1:
            continue
        c = np.asarray(raw[-(vol_lb + 1):], dtype=float)
        if bool(np.any(~np.isfinite(c))) or bool(np.any(c <= 0.0)):
            continue
        rets.append(c[1:] / c[:-1] - 1.0)
    if len(rets) < 20:
        return None
    mkt = np.mean(np.asarray(rets, dtype=float), axis=0)
    return float(np.std(mkt)) * float(np.sqrt(_TRADING_DAYS))


def _dual_horizon_realised_vol(
    book_close_by_ticker: dict[str, list[float]] | None,
    close_by_ticker: dict[str, list[float]],
    slow_lb: int,
    fast_lb: int,
) -> float | None:
    '''MAX of a slow (~6m) and a fast (~1m) annualised realised-vol estimate.

    Both estimates are drawn from the SAME source resolved by the existing
    robust preference -- the held qualified momentum book if it yields a
    slow estimate with >= 20 usable series, else the broad active-universe
    cross-section -- so the proven held-book referencing (Daniel-Moskowitz:
    a momentum crash is foreshadowed by the rising vol of the momentum
    book ITSELF, not the market) is preserved unchanged.

    Taking the MAX makes the overlay weakly MORE defensive ONLY when the
    book's short-horizon vol spikes above its slow estimate -- precisely
    the momentum-crash precursor a 6-month estimate lags -- and leaves it
    ~unchanged in calm regimes (fast ~ slow). It can NEVER be less
    defensive than the committed slow-only estimator, so the resulting
    gross can only fall, never rise, relative to the kept behaviour:
    one-sided toward drawdown / worst-sub-period protection and
    turnover-neutral (the overlay still changes only the gross LEVEL, not
    which names are held). No new tunable hyperparameter: fast_lb is
    DERIVED from the existing slow window exactly as slow_lb is derived
    from the signal lookback. Pure and deterministic.
    '''
    for src in (book_close_by_ticker, close_by_ticker):
        if not src:
            continue
        slow = _annualised_realised_vol(src, slow_lb)
        if slow is None:
            continue
        fast = _annualised_realised_vol(src, fast_lb)
        if fast is None:
            return slow
        return max(slow, fast)
    return None


def vol_targeted_gross(
    close_by_ticker: dict[str, list[float]],
    lookback_days: int,
    book_close_by_ticker: dict[str, list[float]] | None = None,
) -> float:
    '''Volatility-targeted gross exposure, referenced to the HELD book.

    gross = clip(_ANNUAL_VOL_TARGET / realised_vol_annualised, 0.0, 0.99)

    Refinement (this iteration): the realised-vol risk input is now the
    MAX of a slow ~6-month estimate (the committed window) and a fast
    ~1-month estimate of the *same* qualified momentum-quality book we
    actually deploy (``book_close_by_ticker``), with the robust fall-back
    chain unchanged (held-book proxy if >= 20 usable series -> else the
    broad active-universe cross-section -> else 0.75). Daniel-Moskowitz
    (2016) show momentum crashes are foreshadowed by a RAPID rise in the
    momentum portfolio's OWN volatility; a single 6-month estimate lags
    that rise by months, so the de-risk arrives after the worst of the
    drawdown. Adding the fast estimate via MAX makes the overlay cut gross
    promptly when short-horizon book vol spikes (earlier crash de-risk in
    exactly the turbulent/bear sub-periods that set the worst disjoint
    Sortino) while staying byte-~equivalent in calm trends (fast ~ slow,
    still clipped at 0.99 -- upside capture preserved). The MAX guarantees
    the estimate is never below the committed slow-only value, so gross is
    weakly LOWER only -- never higher -- than the kept behaviour: strictly
    one-sided downside protection, never levered (cap 0.99), turnover-
    neutral (only the gross LEVEL moves, not which names are held). Same
    _ANNUAL_VOL_TARGET, same 20-name floor; the fast window is DERIVED
    from the existing slow window (no new hyperparameter). Pure and
    deterministic.
    '''
    vol_lb = min(126, max(63, int(lookback_days) // 2))  # ~6 months (slow)
    # ~1-month fast horizon, DERIVED from the slow window the same way the
    # slow window is derived from lookback -- NOT a new tunable knob.
    fast_lb = max(21, int(vol_lb) // 6)

    rv = _dual_horizon_realised_vol(
        book_close_by_ticker, close_by_ticker, vol_lb, fast_lb
    )
    if rv is None:
        return 0.75
    if not np.isfinite(rv) or rv <= 1e-9:
        return 0.99
    return float(np.clip(_ANNUAL_VOL_TARGET / rv, 0.0, 0.99))


# Pre-committed single-name concentration limit (NOT a searched/tunable
# knob -- a hard risk control, same status as the 0.5-2.0 risk-parity clip
# the codebase already pre-commits). 10% => a fully-invested book is spread
# over at least ~10 names. This is precisely what bounds the blow-up risk
# CLAUDE.md §4 exists to prevent (the predecessor blew up sizing from
# len(selected) with NO per-name bound and 1 name qualifying). With this
# cap, even a 1-name regime puts <=10% in that name and the rest stays cash
# -- strictly safer than the old fixed-slot scheme, never concentrated.
_MAX_NAME_WEIGHT = 0.10


def construct_gross_targets(
    priority: list[str],
    sector_of: dict[str, str],
    gross: float,
    sector_cap: float,
    name_cap: float = _MAX_NAME_WEIGHT,
) -> dict[str, float]:
    '''Deploy `gross` down the ranked `priority` list, bounded by per-name
    `name_cap` and per-sector `sector_cap`, CONTINUING into lower-ranked
    names in other sectors until the gross budget is met (instead of
    leaking the sector-capped remainder to cash -- the bug that pinned the
    old book to ~24% deployed in every regime).

    Greedy by rank: each name in turn gets
    ``min(name_cap, remaining gross budget, remaining sector room)``; once
    a sector is full the walk simply moves on to the next ranked name in a
    sector with room. Pure and deterministic.

    Invariants (long-only, no leverage, bounded concentration):
      * Σ targets <= gross  (<= 0.99 -- the budget is never exceeded; it can
        only fall short when the priority list / sector rooms are exhausted,
        which is the correct defensive behaviour in a genuinely narrow
        market, not a leak).
      * targets[t] <= name_cap for every name.
      * Σ_{t∈sector} targets[t] <= sector_cap for every sector.
    '''
    budget = float(gross)
    if budget <= 0.0 or not priority:
        return {}
    name_cap = float(name_cap)
    sector_cap = float(sector_cap)
    targets: dict[str, float] = {}
    sec_used: dict[str, float] = {}
    for t in priority:
        if budget <= 1e-9:
            break
        if t in targets:
            continue
        sec = sector_of.get(t, 'OTHER')
        room = sector_cap - sec_used.get(sec, 0.0)
        if room <= 1e-9:
            continue
        w = min(name_cap, budget, room)
        if w <= 1e-9:
            continue
        targets[t] = w
        sec_used[sec] = sec_used.get(sec, 0.0) + w
        budget -= w
    return targets


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
        '''Per-ticker sector from the PIT universe enrichment.

        ROOT-CAUSE FIX (Improvement G, 2026-05-18): the backtest/live feeds
        (`bt.feeds.PandasData`) never carry an `_industry` attribute, so the
        old `getattr(d,'_industry',...)` made EVERY name 'OTHER' -- the 25%
        per-sector cap silently became a hard 25% whole-book net-exposure
        ceiling in every backtest ever run (and live). Industry is static
        enrichment metadata (CLAUDE.md locked decision: the Nifty-500 list
        is sector/ISIN enrichment, never a membership/return signal), so
        sourcing it from the universe DB is point-in-time-safe -- it is not
        a tradable look-ahead. Feed attribute is kept as a fallback; if the
        DB is unavailable the old (degenerate) behaviour is preserved so
        nothing hard-fails.
        '''
        industry_by_ticker: dict[str, str] = {}
        try:
            import duckdb

            conn = duckdb.connect(
                str(self.p.universe_db_path), read_only=True
            )
            try:
                for tkr, ind in conn.execute(
                    "SELECT ticker, industry FROM universe_snapshot "
                    "WHERE industry IS NOT NULL AND industry <> '' "
                    "AND UPPER(industry) <> 'OTHER'"
                ).fetchall():
                    # last non-OTHER wins; sector classification is stable
                    industry_by_ticker[str(tkr).upper()] = str(ind)
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 -- DB absent in some unit tests
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
        iso_week = today.isocalendar().week
        # Honour rebalance_period_weeks (previously a dead param --
        # biweekly was hardcoded as iso_week % 2). period=2 is
        # behaviour-identical to the prior code (committed default
        # unchanged); period=1 => every rebalance_weekday (weekly).
        period = max(1, int(self.p.rebalance_period_weeks))
        if not self._week_parity_initialized:
            self._week_parity_initialized = True
            object.__setattr__(
                self.params, 'rebalance_week_parity', iso_week % period
            )
            return True
        return iso_week % period == self.p.rebalance_week_parity

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
        the moment it is re-entered -- no stale flag can silently disable a
        future structural exit on a re-bought position.
        '''
        if getattr(trade, 'isclosed', False):
            self._stop_pending.discard(self._ticker_of(trade.data))

    def _apply_structural_exit(self) -> None:
        '''Slope-confirmed trend-state exit, symmetric with the entry filter.

        The entry (momentum_quality_scores) only buys a name whose close is
        ABOVE its own beta_window-derived structural MA. The committed exit
        sold a held name the instant its close fell BELOW that SAME MA. The
        refinement here: the exit now ALSO requires the structural MA to be
        falling (its same-length value as of ``skip`` bars ago exceeds
        today's). Rationale (real-world objective: turnover/DP cost is the
        dominant trade-level cost, and choppy/whipsaw sub-periods set the
        worst disjoint Sortino): a close dipping below a still-RISING long
        MA is a routine 5-10% Indian mid-cap pullback within an intact
        uptrend -- momentum's right tail. The bare close<MA rule churned
        those winners out (a sell = a ~190d-MA-crossing whipsaw and a
        ₹14.75/scrip DP charge) only to re-buy them at the next rebalance
        when the trend never actually broke. Gating the exit on the MA's
        OWN slope keeps the name through the pullback and exits only on a
        genuine breakdown, where the long MA has itself rolled over.

        This is strictly weakly FEWER exits than the committed behaviour
        (new exits are a subset: it still requires close < MA, plus the
        extra MA-falling condition), so it is byte-equivalent once the MA
        has rolled over in a real bear and only ever defers/suppresses the
        false-exit case. Directional downside is still protected by two
        orthogonal channels untouched here: the vol-targeted gross overlay
        de-risks on the book's own rising volatility, and the biweekly
        re-selection drops any name that falls below retain_n. Adds NO new
        tunable hyperparameter -- both the MA window and the ``skip`` slope
        horizon are the strategy's existing structural/formation
        quantities, reused (the same no-new-knob convention the codebase
        already uses for the dual-horizon vol estimator). Pure and
        deterministic.

        Runs only on non-rebalance bars so the rebalance owns every order
        decision on its own bar (no same-bar double-ordering); a structurally
        exited name may be re-entered at any later rebalance if it requalifies.
        '''
        skip = max(1, int(self.p.formation_days))
        lookback = max(skip + 21, int(self.p.beta_window))
        ma_window = _structural_ma_window(lookback)
        # Need ma_window points for today's MA plus `skip` more to also
        # compute the SAME-length MA as of `skip` bars ago (its slope sign).
        need = ma_window + skip

        for d in self.datas:
            t = self._ticker_of(d)
            if self.getposition(d).size <= 0:
                self._stop_pending.discard(t)
                continue
            if t in self._stop_pending:
                continue  # exit submitted; await next-open fill
            if len(d) < need + 1:
                continue
            closes = np.asarray(
                [float(d.close[-i]) for i in range(need, -1, -1)],
                dtype=float,
            )
            if bool(np.any(~np.isfinite(closes))) or bool(
                np.any(closes <= 0.0)
            ):
                continue
            close_now = float(closes[-1])
            structural_ma = float(np.mean(closes[-ma_window:]))
            # Same-length structural MA evaluated `skip` bars earlier; its
            # comparison to today's MA is a parameter-free slope sign that
            # reuses the strategy's existing formation/skip horizon (no new
            # tunable knob).
            structural_ma_prev = float(
                np.mean(closes[-(ma_window + skip):-skip])
            )
            ma_falling = structural_ma < structural_ma_prev
            if close_now < structural_ma and ma_falling:
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
        retain_n = max(
            int(self.p.n_positions),
            int(float(self.p.retention_mult) * int(self.p.n_positions)),
        )

        # Held winners still ranked within retain_n keep priority (low
        # turnover => low DP drag); then ALL remaining ranked, quality-gated
        # names by score as new-entry candidates. The pool is intentionally
        # the full ranked list (not capped at an eligible_n) so the
        # construction can walk DEEP across sectors to actually reach the
        # intended gross -- the old eligible_n/n_positions caps were part of
        # the ~24% deployment pin. A held name ranked BELOW retain_n is not
        # in priority => it is exited (momentum discipline preserved).
        retained_priority = [t for t, _ in ranked[:retain_n] if t in held]
        new_candidates = [t for t, _ in ranked if t not in held]
        priority = retained_priority + new_candidates

        # Volatility-target referenced to the HELD momentum book: the
        # priority names ARE the qualified momentum-quality pool the
        # construction deploys (all ⊂ close_by_ticker ⊂ active universe --
        # strictly PIT, no off-universe leak). Daniel-Moskowitz: momentum
        # crashes are foreshadowed by the momentum book's OWN rising vol,
        # not market vol -- and a 6-month estimate lags that rise, so the
        # overlay now also reads a derived ~1-month fast vol of the same
        # book and uses the MAX (de-risk earlier in the bear/turbulent
        # sub-periods, ~unchanged in calm). Falls back to the broad
        # cross-section then 0.75 when the qualified pool is thin, so a
        # deep-bear thin sample never regresses behaviour.
        book_close_by_ticker = {
            t: close_by_ticker[t]
            for t in priority
            if t in close_by_ticker
        }
        gross = vol_targeted_gross(
            close_by_ticker,
            int(self.p.beta_window),
            book_close_by_ticker,
        )
        sector_of = {
            t: (self._sector_map[t].sector
                if self._sector_map.get(t) else 'OTHER')
            for t in priority
        }
        targets = (
            construct_gross_targets(
                priority, sector_of, gross, float(self.p.sector_cap)
            )
            if self.p.enforce_sector_cap and self._sector_map
            else construct_gross_targets(
                priority, {}, gross, 1.0  # no sector cap → name_cap only
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
            'rebalance %s: scored=%d, deployed_names=%d, held=%d, '
            'gross=%.2f, sum_w=%.3f',
            today,
            len(scores),
            len(targets),
            len(held),
            gross,
            sum(targets.values()),
        )


__all__ = [
    'resolve_active_universe',
    'ols_beta',
    'market_factor',
    'smb_factor',
    'reversion_scores',
    'momentum_quality_scores',
    'breadth_scaled_gross',
    'vol_targeted_gross',
    'construct_gross_targets',
    'IndiaMomentumQualityCarry',
]
