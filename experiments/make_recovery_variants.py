"""Generate the recovery-lag variants as patched copies of the locked
strategy.py. Each patch is a single semantic change; uniqueness of every
replaced string is ASSERTED so a silent mispatch is impossible.

  variant_fastvol    : dual-horizon vol -> FAST-only (Moreira-Muir 2017
                       canonical ~1-month realized vol). Crash-entry speed
                       retained (fast spikes first); exit-from-defense no
                       longer ratcheted by the slow 6m window.
  variant_vetorelax  : momentum selection keeps mid_mom>0 + structural-MA
                       gates but drops the long_mom<=0 hard VETO (long_mom
                       stays as a rank component). The veto only binds when
                       it excludes everything -- i.e. post-crash recoveries.
  variant_recovery   : both changes.
  variant_lowvolfilter: the parked star candidate from
                       docs/strategy-candidates.md (bottom-half-by-vol
                       pre-filter, held names grandfathered), re-adjudicable
                       now that the PIT window spans 2017-06+.

Run:  uv run python -m experiments.make_recovery_variants
"""
from __future__ import annotations

from pathlib import Path

SRC = Path("strategy.py").read_text()
OUT = Path("experiments")

VETO_OLD = (
    "        if long_mom <= 0.0 or mid_mom <= 0.0 or now < moving_average:\n"
    "            continue"
)
VETO_NEW = (
    "        if mid_mom <= 0.0 or now < moving_average:\n"
    "            continue  # VARIANT: long_mom>0 VETO removed (rank-only)"
)

MAX_OLD = "        return max(slow, fast)"
MAX_NEW = "        return fast  # VARIANT: fast-only (Moreira-Muir canonical)"

SCORES_OLD = """        scores = momentum_quality_scores(
            close_by_ticker,
            adv_by_ticker,
            int(self.p.beta_window),
            int(self.p.formation_days),
        )"""
SCORES_NEW = """        lowvol = low_vol_eligible(close_by_ticker, int(self.p.beta_window))
        scoring_pool = (
            {t: c for t, c in close_by_ticker.items()
             if t in lowvol or t in held}      # grandfather held names
            if lowvol else close_by_ticker      # thin window -> no filter
        )
        scores = momentum_quality_scores(
            scoring_pool,
            adv_by_ticker,
            int(self.p.beta_window),
            int(self.p.formation_days),
        )"""

LOWVOL_FN = '''
def low_vol_eligible(
    close_by_ticker: dict[str, list[float]],
    vol_lb: int,
) -> set[str]:
    """Bottom-half-by-trailing-realised-volatility subset (low-vol pre-filter).

    Median split = parameter-free; vol window reuses beta_window. PIT-safe.
    Returns empty set when <2 names have a computable vol (no filtering).
    """
    vols: dict[str, float] = {}
    for t, raw in close_by_ticker.items():
        if len(raw) < vol_lb + 1:
            continue
        c = np.asarray(raw[-(vol_lb + 1):], dtype=float)
        if bool(np.any(~np.isfinite(c))) or bool(np.any(c <= 0.0)):
            continue
        rets = c[1:] / c[:-1] - 1.0
        vols[t] = float(np.std(rets))
    if len(vols) < 2:
        return set()
    median_vol = float(np.median(np.asarray(list(vols.values()), dtype=float)))
    return {t for t, v in vols.items() if v <= median_vol}


'''
CLASS_ANCHOR = "class IndiaMomentumQualityCarry"

# --- V4: conditional release (fast-only vol ONLY in breadth-confirmed
# uptrends; the MAX(slow,fast) ratchet everywhere else). Reuses the
# structural-MA trend definition and the majority(>=50%) convention --
# zero new numeric constants. ---
SIG_OLD = "    fast_lb: int,\n) -> float | None:"
SIG_NEW = "    fast_lb: int,\n    release: bool = False,\n) -> float | None:"

CALL_OLD = """    rv = _dual_horizon_realised_vol(
        book_close_by_ticker, close_by_ticker, vol_lb, fast_lb
    )"""
CALL_NEW = """    rv = _dual_horizon_realised_vol(
        book_close_by_ticker, close_by_ticker, vol_lb, fast_lb,
        release=_breadth_majority_up(
            close_by_ticker, _structural_ma_window(int(lookback_days))
        ),
    )"""

MAX_COND = ("        return fast if release else max(slow, fast)"
            "  # VARIANT: conditional release")

DUAL_ANCHOR = "def _dual_horizon_realised_vol("
BREADTH_FN = '''
def _breadth_majority_up(
    close_by_ticker: dict[str, list[float]], ma_w: int
) -> bool:
    """Majority of the active cross-section above its own structural MA.

    The same per-name trend-state definition the entry filter and the
    structural exit already use (_structural_ma_window), aggregated with the
    same majority convention as the median split. >=20 usable names required
    (the module's existing thin-sample floor), else False (stay defensive).
    """
    n_up = n = 0
    for raw in close_by_ticker.values():
        if len(raw) < ma_w + 1:
            continue
        c = np.asarray(raw[-(ma_w + 1):], dtype=float)
        if bool(np.any(~np.isfinite(c))) or bool(np.any(c <= 0.0)):
            continue
        n += 1
        if float(c[-1]) >= float(np.mean(c[-ma_w:])):
            n_up += 1
    return n >= 20 and (n_up / n) >= 0.5


'''


def patch(src: str, pairs: list[tuple[str, str]]) -> str:
    out = src
    for old, new in pairs:
        n = out.count(old)
        assert n == 1, f"expected exactly 1 occurrence, got {n}: {old[:60]!r}"
        out = out.replace(old, new)
    return out


def main() -> None:
    cond_pairs = [
        (SIG_OLD, SIG_NEW),
        (CALL_OLD, CALL_NEW),
        (MAX_OLD, MAX_COND),
        (DUAL_ANCHOR, BREADTH_FN + DUAL_ANCHOR),
    ]
    variants = {
        "variant_fastvol.py": patch(SRC, [(MAX_OLD, MAX_NEW)]),
        "variant_condrelease.py": patch(SRC, cond_pairs),
        "variant_condrecovery.py": patch(
            SRC, cond_pairs + [(VETO_OLD, VETO_NEW)]
        ),
        "variant_vetorelax.py": patch(SRC, [(VETO_OLD, VETO_NEW)]),
        "variant_recovery.py": patch(
            SRC, [(MAX_OLD, MAX_NEW), (VETO_OLD, VETO_NEW)]
        ),
        "variant_lowvolfilter.py": patch(
            SRC,
            [
                (SCORES_OLD, SCORES_NEW),
                (CLASS_ANCHOR, LOWVOL_FN + CLASS_ANCHOR),
            ],
        ),
    }
    for name, text in variants.items():
        (OUT / name).write_text(text)
        print(f"wrote experiments/{name} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
