"""Improvement G — gross-targeting bounded portfolio construction
(user-authorised locked-decision change, 2026-05-18).

Proven defect it replaces: old `target_each = gross/n_positions` +
sector-cap-and-leak deployed only ~24% in EVERY regime (even 2024 with
breadth_scaled_gross asking 0.99 and 142 names scored) because the 25%
sector cap divided by the tiny per-name target clamped the whole book to
~one sector and leaked the rest to cash.

`construct_gross_targets` must:
  * actually deploy the intended `gross` (continuing into other sectors
    rather than leaking the sector-capped remainder),
  * never exceed `gross` (long-only, no leverage),
  * bound per-name ≤ name_cap and per-sector ≤ sector_cap (the §4
    anti-blow-up intent — strictly safer than the banned len(selected)
    sizing).
"""
from __future__ import annotations

import pytest

from strategy import _MAX_NAME_WEIGHT, construct_gross_targets

CAP = 0.25  # sector cap


def _sectors(assign: dict[str, list[str]]) -> dict[str, str]:
    return {t: s for s, ts in assign.items() for t in ts}


def test_deploys_full_gross_across_many_sectors():
    """20 names across 10 sectors, gross 0.99 → the book actually invests
    ~0.99 (NOT the old ~0.24 pin)."""
    sect = {f"S{i}": [f"S{i}A", f"S{i}B"] for i in range(10)}
    priority = [f"S{i}{x}" for i in range(10) for x in ("A", "B")]
    w = construct_gross_targets(priority, _sectors(sect), 0.99, CAP)
    total = sum(w.values())
    assert total == pytest.approx(0.99, abs=1e-6)
    assert total > 0.90, "must deploy the intended gross, not the ~24% pin"
    assert all(v <= _MAX_NAME_WEIGHT + 1e-9 for v in w.values())


def test_never_exceeds_gross_no_leverage():
    sect = {f"S{i}": [f"S{i}A", f"S{i}B", f"S{i}C"] for i in range(15)}
    priority = [f"S{i}{x}" for i in range(15) for x in ("A", "B", "C")]
    for g in (0.35, 0.55, 0.75, 0.99):
        w = construct_gross_targets(priority, _sectors(sect), g, CAP)
        assert sum(w.values()) <= g + 1e-9
        assert sum(w.values()) == pytest.approx(g, abs=1e-6)


def test_per_sector_cap_enforced_and_walk_continues_into_other_sectors():
    """Top 8 names all in FINANCE (rank-clustered, the real-data pathology).
    The old code filled FINANCE to 25% then leaked the other 75% to cash.
    Now the walk must continue into the next sectors to reach gross."""
    assign = {
        "FIN": [f"F{i}" for i in range(8)],
        "IT": [f"I{i}" for i in range(4)],
        "PHARMA": [f"P{i}" for i in range(4)],
        "AUTO": [f"A{i}" for i in range(4)],
        "FMCG": [f"C{i}" for i in range(4)],
    }
    # priority is rank order: all FIN first (the clustering), then the rest
    priority = (
        [f"F{i}" for i in range(8)]
        + [f"I{i}" for i in range(4)]
        + [f"P{i}" for i in range(4)]
        + [f"A{i}" for i in range(4)]
        + [f"C{i}" for i in range(4)]
    )
    w = construct_gross_targets(priority, _sectors(assign), 0.99, CAP)
    fin = sum(v for k, v in w.items() if k.startswith("F"))
    assert fin <= CAP + 1e-9, "sector cap must hold"
    assert sum(w.values()) == pytest.approx(0.99, abs=1e-6), (
        "must walk past the capped FINANCE into IT/PHARMA/AUTO/FMCG to "
        "reach gross — the leak that pinned the book is gone"
    )
    # at least 4 sectors funded (diversified, not single-sector)
    funded_sectors = {
        _sectors(assign)[k] for k in w
    }
    assert len(funded_sectors) >= 4


def test_single_name_regime_is_bounded_not_a_blowup():
    """Only 1 qualifying name, gross 0.99 → it gets ≤ name_cap (10%), the
    rest stays cash. This is the §4 blow-up scenario, now SAFE (the
    predecessor put ~99% in the 1 name via len(selected) sizing)."""
    w = construct_gross_targets(["ONLY"], {"ONLY": "FIN"}, 0.99, CAP)
    assert w == {"ONLY": pytest.approx(_MAX_NAME_WEIGHT)}
    assert sum(w.values()) <= _MAX_NAME_WEIGHT + 1e-9


def test_low_gross_regime_deploys_less_downside_control_preserved():
    """Bear regime: breadth_scaled_gross → 0.35. The book must deploy only
    ~35%, NOT use name/sector caps to over-invest. Downside control (the
    strategy's genuine strength) is preserved by gross still bounding the
    total."""
    sect = {f"S{i}": [f"S{i}A", f"S{i}B"] for i in range(10)}
    priority = [f"S{i}{x}" for i in range(10) for x in ("A", "B")]
    w = construct_gross_targets(priority, _sectors(sect), 0.35, CAP)
    assert sum(w.values()) == pytest.approx(0.35, abs=1e-6)


def test_zero_or_empty_inputs_safe():
    assert construct_gross_targets([], {}, 0.99, CAP) == {}
    assert construct_gross_targets(["A"], {"A": "X"}, 0.0, CAP) == {}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
