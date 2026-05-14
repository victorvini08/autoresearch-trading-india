from scripts.loop import (
    _last_accepted_value,
    journal_entry,
    last_accepted_sortino,
    learning_summary,
    validate_strategy_edit,
)


def _metrics(sortino=0.72):
    return {
        "validation_sortino_mean": sortino,
        "validation_folds": 25,
        "side_panel": {
            "calmar_mean": 0.1,
            "hit_rate_mean": 0.42,
            "profit_factor_mean": 1.8,
            "trade_count_total": 120,
        },
        "risk": {
            "passed": True,
            "violations": [],
        },
        "risk_signals": {
            "aggregate_max_dd": 0.14,
            "worst_fold_max_dd": 0.05,
            "max_position_frac_peak": 0.06,
            "lower_quartile_fold_calmar": -0.2,
            "n_negative_folds": 7,
            "n_folds": 25,
        },
    }


def test_journal_entry_fills_learning_for_scored_iteration():
    learning = learning_summary(
        "KEPT",
        "sortino improved",
        _metrics(),
        previous_sortino=0.62,
        previous_aggregate_dd=0.13,
    )

    entry = journal_entry(
        "iter-test",
        hypothesis="test hypothesis",
        change_summary="test change",
        decision="KEPT",
        reason="sortino improved",
        metrics=_metrics(),
        learning=learning,
    )

    assert "**Learning:** Sortino changed from 0.620 to 0.720 (+0.100)." in entry
    assert "Aggregate DD was 14.0% versus previous kept 13.0%" in entry
    assert "filled by next iteration" not in entry


def test_journal_entry_fills_learning_for_pre_eval_failure():
    entry = journal_entry(
        "iter-test",
        hypothesis="bad edit",
        change_summary="syntax-breaking change",
        decision="REJECTED",
        reason="validation failed: syntax error",
        metrics=None,
    )

    assert "**Learning:** No scored strategy inference" in entry
    assert "implementation failure" in entry
    assert "filled by next iteration" not in entry


# ---------------------------------------------------------------------------
# Regression test for the journal-parser bug that silently lost progress on
# mean-reversion-aryan: a REVERTED entry whose hypothesis text mentioned
# "KEPT iteration" was treated as a KEPT block, causing the loop to compare
# new iters against a worse Sortino baseline and accept regressions as wins.
# ---------------------------------------------------------------------------


_JOURNAL_WITH_REVERTED_MENTIONING_KEPT = """\
# Journal

## Iteration alpha — KEPT

**Decision:** KEPT — sortino 1.018 > prev 1.006

**Result:**
- validation_sortino_mean: 1.018
- aggregate_max_dd: 0.118

---

## Iteration beta — REVERTED

**Hypothesis:** Building on the only KEPT iteration so far (1.018), I want to
extend the volatility-awareness principle that drove its KEPT decision.

**Decision:** REVERTED — sortino 0.886 did not improve on prev 1.018

**Result:**
- validation_sortino_mean: 0.886
- aggregate_max_dd: 0.080

---
"""


def test_last_accepted_sortino_ignores_reverted_blocks_mentioning_kept():
    """Regression test: a REVERTED block whose hypothesis text mentions
    'KEPT' (e.g. 'the only KEPT iteration so far') must NOT be treated as a
    KEPT block. Without this, the loop reads validation_sortino_mean from
    the wrong block and compares new iters against a worse baseline."""
    s = last_accepted_sortino(_JOURNAL_WITH_REVERTED_MENTIONING_KEPT)
    assert s == 1.018, (
        f"expected 1.018 from KEPT block, got {s} — "
        "parser is matching the REVERTED block via substring 'KEPT'"
    )


def test_last_accepted_value_returns_none_on_no_kept_history():
    """No KEPT entries → None, so the loop's `improved` check trivially
    passes (first iter). Mentions of KEPT in REVERTED hypothesis text don't
    count."""
    journal_with_only_reverts = """\
# Journal

## Iteration foo — REVERTED

**Hypothesis:** Some idea referencing KEPT in the abstract.

**Decision:** REVERTED — sortino -0.1

**Result:**
- validation_sortino_mean: -0.1

---
"""
    assert _last_accepted_value(journal_with_only_reverts, "validation_sortino_mean") is None


# ---------------------------------------------------------------------------
# No-op edit detection: agent proposals whose AST is identical to HEAD
# (e.g. only added comments/docstrings/whitespace) get rejected pre-backtest.
# Saves ~25s per wasted iteration; observed 4 such "iters" with identical
# Sortinos to the prior KEPT on mean-reversion-aryan.
# ---------------------------------------------------------------------------


_VALID_STRATEGY_PY = '''\
import backtrader as bt


class MyStrategy(bt.Strategy):
    def next(self):
        pass
'''


def test_validate_strategy_edit_rejects_noop_via_comment_only_change():
    """Adding only a comment is a no-op at runtime — should be rejected."""
    new_text = '''\
import backtrader as bt


class MyStrategy(bt.Strategy):
    def next(self):
        # added a comment but no actual change
        pass
'''
    ok, why = validate_strategy_edit(new_text, current_text=_VALID_STRATEGY_PY)
    assert ok is False
    assert "no-op" in why.lower()


def test_validate_strategy_edit_accepts_real_change():
    """A genuine code change passes validation."""
    new_text = '''\
import backtrader as bt


class MyStrategy(bt.Strategy):
    def next(self):
        if self.position.size == 0:
            self.buy()
'''
    ok, why = validate_strategy_edit(new_text, current_text=_VALID_STRATEGY_PY)
    assert ok is True, f"expected ok, got: {why}"


def test_validate_strategy_edit_no_op_check_is_optional():
    """Backward compat: callers that don't pass current_text still work
    (the no-op check is skipped). Important so existing tests / callers on
    other branches don't break when this loop.py merges."""
    ok, why = validate_strategy_edit(_VALID_STRATEGY_PY)
    assert ok is True, f"expected ok, got: {why}"
