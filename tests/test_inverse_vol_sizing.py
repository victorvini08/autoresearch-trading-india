"""Unit tests for Improvement B pure helpers in strategy.py:

- `inverse_vol_tilt(selected, vol_by_ticker)` -> mean~1 inverse-vol tilt,
  clipped to the [0.5, 2.0] risk-parity guardrail, renormalised so
  Σ tilt = len(selected) (aggregate-preserving — the §4 fixed-slot
  invariant), with a post-scale hard cap of 2.0 (freed weight -> cash, so
  Σ tilt is NEVER above len; gross can never be increased).
- `apply_sector_cap(selected, targets, sector_of, cap)` -> walks priority
  order, clamps each name to its sector's remaining room; excess stays
  cash (never redistributed); guarantees the 25% §5 cap on actual weights.

Pins docs/superpowers/specs/2026-05-17-inverse-vol-sizing-design.md.
Pure functions, real inputs, no mocks.
"""
from __future__ import annotations

import pytest

from strategy import apply_sector_cap, inverse_vol_tilt


# ── inverse_vol_tilt ────────────────────────────────────────────────────


def test_tilt_is_identity_when_all_vols_equal():
    # Uniform risk => B must reduce to today's equal-weight (no behaviour
    # change). Every tilt == 1.0, Σ == len.
    sel = [f"T{i}" for i in range(10)]
    vols = {t: 0.02 for t in sel}
    tilt = inverse_vol_tilt(sel, vols)
    assert all(v == pytest.approx(1.0) for v in tilt.values())
    assert sum(tilt.values()) == pytest.approx(len(sel))


def test_lower_vol_gets_more_weight_monotone():
    sel = ["LO", "MID", "HI"]
    vols = {"LO": 0.01, "MID": 0.02, "HI": 0.04}
    tilt = inverse_vol_tilt(sel, vols)
    assert tilt["LO"] > tilt["MID"] > tilt["HI"]


def test_aggregate_preserved_sum_equals_len_when_no_cap_binds():
    # Mild vol spread: post-scale cap does NOT bind => Σ tilt == len
    # EXACTLY (gross identical to equal-weight; cannot clip the right tail).
    sel = ["A", "B", "C", "D", "E"]
    vols = {"A": 0.015, "B": 0.02, "C": 0.025, "D": 0.018, "E": 0.022}
    tilt = inverse_vol_tilt(sel, vols)
    assert sum(tilt.values()) == pytest.approx(len(sel))


def test_sum_never_exceeds_len_even_with_extreme_vol_spread():
    # An ultra-low-vol name must not let Σ tilt exceed len (that would
    # raise gross above equal-weight and risk the >100% catastrophe gate).
    sel = ["TINY", "B", "C", "D", "E"]
    vols = {"TINY": 1e-6, "B": 0.05, "C": 0.05, "D": 0.05, "E": 0.05}
    tilt = inverse_vol_tilt(sel, vols)
    assert sum(tilt.values()) <= len(sel) + 1e-9
    assert max(tilt.values()) <= 2.0 + 1e-9          # hard concentration cap
    assert min(tilt.values()) > 0.0
    assert all(t == t for t in tilt.values())        # no NaN
    assert all(t not in (float("inf"),) for t in tilt.values())


def test_single_name_tilt_is_one():
    assert inverse_vol_tilt(["ONLY"], {"ONLY": 0.03}) == {"ONLY": pytest.approx(1.0)}


def test_missing_vol_is_treated_neutrally_not_extreme():
    # A name absent from vol_by_ticker must not blow up or grab max weight;
    # it gets a neutral (~mean) tilt.
    sel = ["A", "B", "MISSING"]
    vols = {"A": 0.02, "B": 0.02}
    tilt = inverse_vol_tilt(sel, vols)
    assert tilt["MISSING"] == pytest.approx(1.0, abs=0.25)
    assert sum(tilt.values()) <= len(sel) + 1e-9


def test_tilt_is_deterministic():
    sel = ["A", "B", "C"]
    vols = {"A": 0.01, "B": 0.03, "C": 0.02}
    assert inverse_vol_tilt(sel, vols) == inverse_vol_tilt(sel, vols)


def test_empty_selected_returns_empty():
    assert inverse_vol_tilt([], {}) == {}


# ── apply_sector_cap ────────────────────────────────────────────────────


def test_sector_cap_no_op_when_all_under_cap():
    sel = ["A", "B"]
    targets = {"A": 0.04, "B": 0.04}
    secs = {"A": "TECH", "B": "BANK"}
    out = apply_sector_cap(sel, targets, secs, 0.25)
    assert out == pytest.approx({"A": 0.04, "B": 0.04})


def test_sector_cap_clamps_overweight_sector_excess_to_cash():
    # Three TECH names at 0.10 each (=0.30) must be clamped so the sector
    # totals exactly the 0.25 cap; the third (lowest priority) absorbs the
    # cut; excess (0.05) is NOT redistributed to the BANK name.
    sel = ["T1", "T2", "T3", "B1"]
    targets = {"T1": 0.10, "T2": 0.10, "T3": 0.10, "B1": 0.08}
    secs = {"T1": "TECH", "T2": "TECH", "T3": "TECH", "B1": "BANK"}
    out = apply_sector_cap(sel, targets, secs, 0.25)
    assert out["T1"] == pytest.approx(0.10)
    assert out["T2"] == pytest.approx(0.10)
    assert out["T3"] == pytest.approx(0.05)          # trimmed to remaining room
    assert out["B1"] == pytest.approx(0.08)          # untouched (no redistribution)
    assert sum(v for k, v in out.items() if secs[k] == "TECH") == pytest.approx(0.25)


def test_sector_cap_name_into_full_sector_gets_cash():
    sel = ["T1", "T2", "T3"]
    targets = {"T1": 0.13, "T2": 0.13, "T3": 0.13}   # all TECH, cap 0.25
    secs = {t: "TECH" for t in sel}
    out = apply_sector_cap(sel, targets, secs, 0.25)
    assert out["T1"] == pytest.approx(0.13)
    assert out["T2"] == pytest.approx(0.12)          # remaining room
    assert out["T3"] == pytest.approx(0.0)           # sector full -> cash
    assert sum(out.values()) == pytest.approx(0.25)


def test_sector_cap_priority_order_respected_and_deterministic():
    sel = ["HI", "MID", "LO"]                         # priority order
    targets = {"HI": 0.20, "MID": 0.20, "LO": 0.20}
    secs = {t: "TECH" for t in sel}
    out = apply_sector_cap(sel, targets, secs, 0.25)
    assert out["HI"] == pytest.approx(0.20)           # top priority keeps full
    assert out["MID"] == pytest.approx(0.05)
    assert out["LO"] == pytest.approx(0.0)
    assert out == apply_sector_cap(sel, targets, secs, 0.25)
