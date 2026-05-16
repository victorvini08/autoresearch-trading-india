"""Equivalence guarantees for the parallelized walk-forward evaluator.

prepare.py is the IMMUTABLE evaluator. The 2026-05-16 change (load feeds
once + slice, fan folds across processes) is allowed ONLY because it is
numerically identical to the old serial per-fold-load path. These tests pin
that invariant so a future edit can't silently change the evaluator's
numbers under the cover of "just parallelism".

Kept fast by restricting to a small ticker subset + 2 folds: fold scoring is
independent of universe size, so equivalence on 12 names proves equivalence
on 200.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

import prepare
import strategy as strategy_mod

_SUBSET = 12


def _two_real_folds():
    folds = prepare._walk_forward_folds(
        prepare.BACKTEST_START, prepare.TEST_BOUNDARY
    )
    out = []
    for (_ts, _te, val_s, val_e) in folds:
        members, ubd = prepare._pit_universe(val_e)
        if members:
            out.append((val_s, val_e, members[:_SUBSET], ubd))
        if len(out) == 2:
            break
    if len(out) < 2:
        pytest.skip("need >=2 universe-backed folds (run universe backfill)")
    return out


def test_slice_equals_load():
    """_slice_feeds(global, s, e, m) == old per-fold _load_feeds(s, e, m)."""
    folds = _two_real_folds()
    g_start = min(
        vs - timedelta(days=prepare.WARMUP_CALENDAR_DAYS) for vs, _, _, _ in folds
    )
    g_end = max(ve for _, ve, _, _ in folds)
    union = sorted({t for _, _, m, _ in folds for t in m})
    global_feeds = prepare._load_feeds(g_start, g_end, union)

    for val_s, val_e, members, _ in folds:
        s = val_s - timedelta(days=prepare.WARMUP_CALENDAR_DAYS)
        direct = prepare._load_feeds(s, val_e, members)
        sliced = prepare._slice_feeds(global_feeds, s, val_e, members)
        assert set(direct) == set(sliced)
        for tkr in direct:
            pd.testing.assert_frame_equal(
                direct[tkr], sliced[tkr], check_freq=False
            )


def test_serial_equals_parallel():
    """_score_window (serial, in-proc) == _run_one_fold (process pool)."""
    from concurrent.futures import ProcessPoolExecutor

    folds = _two_real_folds()
    g_start = min(
        vs - timedelta(days=prepare.WARMUP_CALENDAR_DAYS) for vs, _, _, _ in folds
    )
    g_end = max(ve for _, ve, _, _ in folds)
    union = sorted({t for _, _, m, _ in folds for t in m})
    global_feeds = prepare._load_feeds(g_start, g_end, union)

    cls = prepare._find_strategy_class(strategy_mod)
    payloads, serial = [], []
    for i, (val_s, val_e, members, ubd) in enumerate(folds):
        feeds = prepare._slice_feeds(
            global_feeds,
            val_s - timedelta(days=prepare.WARMUP_CALENDAR_DAYS),
            val_e, members,
        )
        serial.append(
            prepare._score_window(cls, feeds, ubd, score_start=val_s)
        )
        payloads.append(
            {"idx": i, "mod": strategy_mod.__name__,
             "feeds": feeds, "ubd": ubd, "val_s": val_s}
        )

    with ProcessPoolExecutor(max_workers=2) as ex:
        parallel = {i: s for i, s in ex.map(prepare._run_one_fold, payloads)}

    for i, exp in enumerate(serial):
        got = parallel[i]
        for k in ("sortino", "calmar", "max_dd", "hit_rate",
                  "profit_factor", "turnover", "trade_count"):
            assert exp[k] == pytest.approx(got[k], nan_ok=True), (
                f"fold {i} metric {k}: serial={exp[k]} parallel={got[k]}"
            )
        pd.testing.assert_series_equal(
            exp["equity_curve"], got["equity_curve"], check_freq=False
        )
