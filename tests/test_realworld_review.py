"""Tests for scripts/realworld_review.py (Step 4.d) — the runner.

Orchestrates: gather context -> build prompt -> call LLM -> validate ->
retry-once on fixable failure -> persist (audit ALWAYS, PENDING hypotheses
only on pass, journal entry). The LLM provider is injected, so these tests use
a FakeProvider with canned JSON and never shell out. The runner is read-only
wrt strategy.py — there is no code path here that writes it.
"""
from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from data import realworld_review_validator as V
from storage import realworld_db
import scripts.realworld_context as ctx
import scripts.realworld_review as review


class FakeProvider:
    model_id = "fake-model"

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0

    def classify(self, prompt, timeout=120):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        raise AssertionError("FakeProvider called more times than responses given")


def _ri(n_realized_trades=20, safety_state="NORMAL"):
    return ctx.assemble_review_input(
        d=date(2026, 5, 29),
        mode="dhan-paper",
        reconciliation={"date": "2026-05-29", "drawdown_threshold": {"status": "ok"}},
        trade_context={
            "held": [{"ticker": "RELIANCE", "flag": "warn"}],
            "closed": [{"ticker": "ONGC", "sell_date": "2026-05-26"}],
        },
        safety_state=safety_state,
        n_realized_trades=n_realized_trades,
        burned_hashes=frozenset(),
        past_hypotheses=[],
        journal_tail="",
    )


def _valid_hyp_json(**over):
    h = {
        "id": "h1",
        "text": "Names entering below decile 7 underperform the held book.",
        "category": "signal",
        "confidence": "high",
        "supporting_evidence_ids": ["ONGC@2026-05-26"],
        "causal_story": "Late-decile entries lack momentum persistence.",
        "predeclared_test": "Entries below decile 7 trail Nifty by >2% across >=15 trades.",
    }
    h.update(over)
    return h


def _run(provider, ri, tmp_path, **over):
    kw = dict(
        d=date(2026, 5, 29),
        mode="dhan-paper",
        provider=provider,
        review_input=ri,
        realworld_db_path=tmp_path / "rw.duckdb",
        journal_path=tmp_path / "journal.md",
        now=datetime(2026, 5, 29, 16, 0, 0),
        review_id="rev-1",
    )
    kw.update(over)
    return review.run_review(**kw)


# ---- prompt (pure) -------------------------------------------------------

def test_build_prompt_has_constraints_and_payload():
    prompt = review.build_prompt(_ri())
    assert "NO CHANGE" in prompt
    assert "cold" in prompt.lower()
    # the JSON output contract is spelled out
    assert "hypotheses" in prompt and "predeclared_test" in prompt
    # the actual evidence ids are present so the model can cite them
    assert "ONGC@2026-05-26" in prompt


# ---- cold start ----------------------------------------------------------

def test_cold_start_observations_only_passes(tmp_path):
    prov = FakeProvider(json.dumps({"observations": ["Reconciliation balanced."],
                                    "hypotheses": []}))
    res = _run(prov, _ri(n_realized_trades=0), tmp_path)
    assert res.validator_result == "passed"
    assert res.cold_start is True
    assert res.n_accepted == 0
    # audit row always written
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_audit(rw, "rev-1") is not None
    rw.close()


def test_cold_start_hypothesis_rejected_but_audited(tmp_path):
    prov = FakeProvider(json.dumps({"observations": [], "hypotheses": [_valid_hyp_json()]}))
    res = _run(prov, _ri(n_realized_trades=3), tmp_path)
    assert res.validator_result == "failed"
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_audit(rw, "rev-1") is not None        # audited
    assert realworld_db.get_hypotheses(rw, "dhan-paper") == []    # nothing persisted
    rw.close()


# ---- happy path ----------------------------------------------------------

def test_valid_hypothesis_persisted_pending(tmp_path):
    prov = FakeProvider(json.dumps({"observations": [], "hypotheses": [_valid_hyp_json()]}))
    res = _run(prov, _ri(), tmp_path)
    assert res.validator_result == "passed"
    assert res.n_accepted == 1
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    rows = realworld_db.get_hypotheses(rw, "dhan-paper")
    assert len(rows) == 1
    assert rows[0]["state"] == "PENDING"
    assert rows[0]["category"] == "signal"
    assert rows[0]["text_lexical_hash"] == V.lexical_hash(_valid_hyp_json()["text"])
    rw.close()


# ---- retry ---------------------------------------------------------------

def test_malformed_json_retries_once_then_audits(tmp_path):
    prov = FakeProvider("not json at all", "still not json")
    res = _run(prov, _ri(), tmp_path)
    assert prov.calls == 2  # initial + one retry
    assert res.validator_result == "failed"
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_audit(rw, "rev-1") is not None
    rw.close()


def test_retry_succeeds_on_second_attempt(tmp_path):
    good = json.dumps({"observations": [], "hypotheses": [_valid_hyp_json()]})
    prov = FakeProvider("garbage", good)
    res = _run(prov, _ri(), tmp_path)
    assert prov.calls == 2
    assert res.validator_result == "passed"
    assert res.n_accepted == 1


def test_structural_rejection_does_not_retry(tmp_path):
    # cold-start rejection is structural — retrying wastes an LLM call.
    prov = FakeProvider(json.dumps({"observations": [], "hypotheses": [_valid_hyp_json()]}))
    _run(prov, _ri(n_realized_trades=2), tmp_path)
    assert prov.calls == 1


# ---- drawdown ------------------------------------------------------------

def test_drawdown_blocks_signal_hypothesis(tmp_path):
    prov = FakeProvider(json.dumps({"observations": [], "hypotheses": [_valid_hyp_json()]}))
    res = _run(prov, _ri(safety_state="WATCH"), tmp_path)
    assert res.validator_result == "failed"
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_audit(rw, "rev-1")["safety_state"] == "WATCH"
    assert realworld_db.get_hypotheses(rw, "dhan-paper") == []
    rw.close()


# ---- journal -------------------------------------------------------------

def test_journal_appended(tmp_path):
    prov = FakeProvider(json.dumps({"observations": ["Recon balanced."], "hypotheses": []}))
    _run(prov, _ri(n_realized_trades=0), tmp_path)
    text = (tmp_path / "journal.md").read_text()
    assert "2026-05-29" in text
    assert "rev-1" in text


def test_output_json_stored_in_audit(tmp_path):
    raw = json.dumps({"observations": ["x"], "hypotheses": []})
    prov = FakeProvider(raw)
    _run(prov, _ri(n_realized_trades=0), tmp_path)
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    audit = realworld_db.get_audit(rw, "rev-1")
    assert "observations" in audit["output_json"]
    rw.close()
