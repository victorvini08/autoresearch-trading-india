"""bonferroni_family_size: principled, bounded multiple-comparisons family.

Replaces the old `len(recent_attempts(20)) + 1`, which never reset on KEEP,
counted crashes that never touched the data, and grew unbounded.
"""
from scripts.loop import BONFERRONI_FAMILY_CAP, bonferroni_family_size


def _row(decision):
    return {"decision": decision}


def test_empty_is_one():
    assert bonferroni_family_size([]) == 1


def test_only_reverted_counts_plus_current():
    # 3 data-tested variants + the current one == 4
    assert bonferroni_family_size([_row("REVERTED")] * 3) == 4


def test_rejected_crashes_excluded():
    # REJECTED (crash / invalid edit / hard reject) never produced a p-value
    rows = [_row("REJECTED"), _row("REVERTED"), _row("REJECTED")]
    assert bonferroni_family_size(rows) == 2  # 1 REVERTED + current


def test_kept_resets_episode():
    # Family is only the variants AFTER the most recent KEPT baseline.
    rows = [
        _row("REVERTED"), _row("REVERTED"),  # old episode — ignored
        _row("KEPT"),                         # boundary
        _row("REVERTED"), _row("REVERTED"),  # current episode
    ]
    assert bonferroni_family_size(rows) == 3  # 2 REVERTED + current


def test_capped():
    rows = [_row("REVERTED")] * 50
    assert bonferroni_family_size(rows) == BONFERRONI_FAMILY_CAP


def test_case_and_whitespace_insensitive():
    assert bonferroni_family_size([{"decision": " reverted "}]) == 2
    assert bonferroni_family_size([{"decision": None}]) == 1
