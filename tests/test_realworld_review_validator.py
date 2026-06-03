"""Tests for data/realworld_review_validator.py (Step 4.b).

The validator is the ACTUAL control surface of the monthly LLM review — the
prompt is documentation, this is enforcement. It is a pure function: given the
LLM's parsed output and a context of independently-rederived ground truth
(trade count, safety state, valid evidence ids, burned hashes), it decides
which hypotheses survive. It NEVER trusts the LLM's self-report of those facts.

Six content gates: schema, cold-start, drawdown, causal-citation,
falsifiability, duplicate. (Provenance is enforced structurally by the audit
table + runner, not here.)
"""
from __future__ import annotations

import pytest

from data import realworld_review_validator as V


def _ctx(**overrides):
    base = dict(
        n_realized_trades=20,
        safety_state="NORMAL",
        valid_evidence_ids=frozenset({"t-1", "t-2", "RELIANCE"}),
        burned_hashes=frozenset(),
    )
    base.update(overrides)
    return V.ReviewContext(**base)


def _hyp(**overrides):
    base = dict(
        id="h1",
        text="Names entering below decile 7 underperform the held book.",
        category="signal",
        confidence="high",
        supporting_evidence_ids=["t-1"],
        causal_story="Late-decile entries lack momentum persistence.",
        predeclared_test=(
            "Entries below decile 7 trail Nifty by >2% over the hold "
            "across >=15 trades."
        ),
    )
    base.update(overrides)
    return base


def _output(hyps=None, observations=None):
    return {
        "observations": (observations if observations is not None
                         else ["Reconciliation balanced to <1bp."]),
        "hypotheses": hyps if hyps is not None else [],
    }


# ---- lexical hash --------------------------------------------------------

def test_lexical_hash_normalizes_case_whitespace_punctuation():
    a = V.lexical_hash("Late-decile entries underperform.")
    b = V.lexical_hash("  late   DECILE entries underperform !!! ")
    assert a == b


def test_lexical_hash_differs_for_different_claims():
    assert V.lexical_hash("Cost drag is high") != V.lexical_hash("Vol target too low")


# ---- happy path ----------------------------------------------------------

def test_empty_hypotheses_passes():
    res = V.validate(_output(hyps=[]), _ctx())
    assert res.result == "passed"
    assert res.accepted == ()
    assert res.observations  # observations preserved


def test_valid_hypothesis_accepted():
    res = V.validate(_output(hyps=[_hyp()]), _ctx())
    assert res.result == "passed"
    assert len(res.accepted) == 1
    # validator attaches the hash it computed (runner persists it)
    assert res.accepted[0]["text_lexical_hash"] == V.lexical_hash(_hyp()["text"])


# ---- gate 1: schema ------------------------------------------------------

def test_malformed_top_level_fails():
    res = V.validate({"nonsense": True}, _ctx())
    assert res.result == "failed"
    assert res.output_errors


def test_hypothesis_missing_field_rejected():
    h = _hyp()
    del h["causal_story"]
    res = V.validate(_output(hyps=[h]), _ctx())
    assert res.result == "failed"
    assert any("schema" in r for r in res.verdicts[0].rejection_reasons)


def test_bad_category_enum_rejected():
    res = V.validate(_output(hyps=[_hyp(category="wizardry")]), _ctx())
    assert res.result == "failed"
    assert any("category" in r for r in res.verdicts[0].rejection_reasons)


def test_bad_confidence_enum_rejected():
    res = V.validate(_output(hyps=[_hyp(confidence="certain")]), _ctx())
    assert res.result == "failed"


# ---- gate 2: cold-start --------------------------------------------------

def test_cold_start_suppresses_hypotheses_below_10():
    res = V.validate(_output(hyps=[_hyp()]), _ctx(n_realized_trades=9))
    assert res.result == "failed"
    assert any("cold_start" in r for r in res.verdicts[0].rejection_reasons)
    assert res.observations  # observations still survive cold start


def test_cold_start_observations_only_passes():
    res = V.validate(_output(hyps=[]), _ctx(n_realized_trades=0))
    assert res.result == "passed"


def test_exactly_10_trades_allows_hypotheses():
    res = V.validate(_output(hyps=[_hyp()]), _ctx(n_realized_trades=10))
    assert res.result == "passed"


# ---- gate 3: drawdown ----------------------------------------------------

def test_drawdown_blocks_non_risk_off():
    res = V.validate(_output(hyps=[_hyp(category="signal")]),
                     _ctx(safety_state="WATCH"))
    assert res.result == "failed"
    assert any("drawdown" in r for r in res.verdicts[0].rejection_reasons)


def test_drawdown_allows_risk_off():
    h = _hyp(category="risk_off",
             text="Cut gross when realised vol spikes intra-month.",
             predeclared_test="Halving gross above 18% ann vol reduces maxDD by >X.")
    res = V.validate(_output(hyps=[h]), _ctx(safety_state="RISK_REDUCED"))
    assert res.result == "passed"


# ---- gate 4: causal-citation ---------------------------------------------

def test_empty_citation_rejected():
    res = V.validate(_output(hyps=[_hyp(supporting_evidence_ids=[])]), _ctx())
    assert res.result == "failed"
    assert any("citation" in r for r in res.verdicts[0].rejection_reasons)


def test_hallucinated_citation_rejected():
    res = V.validate(_output(hyps=[_hyp(supporting_evidence_ids=["t-999"])]), _ctx())
    assert res.result == "failed"
    assert any("citation" in r for r in res.verdicts[0].rejection_reasons)


def test_held_position_drift_citation_accepted():
    # RELIANCE is a currently-held ticker in valid_evidence_ids — early on,
    # the real evidence is held-name drift, not closed round-trips.
    res = V.validate(_output(hyps=[_hyp(supporting_evidence_ids=["RELIANCE"])]),
                     _ctx())
    assert res.result == "passed"


# ---- gate 5: falsifiability ----------------------------------------------

def test_missing_predeclared_test_rejected():
    res = V.validate(_output(hyps=[_hyp(predeclared_test="")]), _ctx())
    assert res.result == "failed"
    assert any("falsifia" in r or "predeclared" in r
               for r in res.verdicts[0].rejection_reasons)


def test_placeholder_predeclared_test_rejected():
    res = V.validate(_output(hyps=[_hyp(predeclared_test="TODO")]), _ctx())
    assert res.result == "failed"


# ---- gate 6: duplicate ---------------------------------------------------

def test_duplicate_burned_hash_rejected():
    h = _hyp()
    burned = frozenset({V.lexical_hash(h["text"])})
    res = V.validate(_output(hyps=[h]), _ctx(burned_hashes=burned))
    assert res.result == "failed"
    assert any("duplicate" in r for r in res.verdicts[0].rejection_reasons)


# ---- mixed ---------------------------------------------------------------

def test_partial_when_one_of_two_rejected():
    good = _hyp(id="g")
    bad = _hyp(id="b", supporting_evidence_ids=[])
    res = V.validate(_output(hyps=[good, bad]), _ctx())
    assert res.result == "partial"
    assert len(res.accepted) == 1
    assert res.accepted[0]["id"] == "g"


def test_all_reasons_collected_not_just_first():
    # A hypothesis that violates citation AND falsifiability should report both.
    h = _hyp(supporting_evidence_ids=[], predeclared_test="")
    res = V.validate(_output(hyps=[h]), _ctx())
    reasons = res.verdicts[0].rejection_reasons
    assert any("citation" in r for r in reasons)
    assert any("falsifia" in r or "predeclared" in r for r in reasons)
