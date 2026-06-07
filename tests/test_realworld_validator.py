"""Tests for scripts/realworld_validator.py — the on-demand strategy-evolution
validator (Step 5.b + 5.c).

5.b (candidate builder): a PENDING hypothesis -> LLM prompt -> candidate
strategy.py text, validated through the SAME AST/import sandbox the nightly
loop uses (scripts.loop.validate_strategy_edit). The provider is injected so
these tests never shell out.

5.c (gate harness): the candidate is run through the IMMUTABLE prepare.py at
BOTH ₹50k and ₹5L, then QUALIFIED — atomic anti-overfit gates + catastrophe
gate + scale-robustness — at both capitals. This is a *qualification* gate
(does it deserve a live shadow trial?), NOT a *selection* gate: it does not
require beating the incumbent's validation Sortino (that is the overfit trap;
real selection happens later on the shadow book).

The sealed reveal (5.d) is deliberately NOT exercised here.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime

import pytest

import scripts.realworld_validator as V
from storage import realworld_db


# ── fakes / fixtures ──────────────────────────────────────────────────────


class FakeProvider:
    model_id = "fake-model"

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0

    def classify(self, prompt, timeout=600):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        raise AssertionError("FakeProvider called more times than responses given")


CURRENT_STRATEGY = '''import backtrader as bt


class MomentumStrategy(bt.Strategy):
    params = (("entry_pct", 0.30),)

    def __init__(self):
        self.x = 1

    def next(self):
        pass
'''

# Changes the AST (0.30 -> 0.25) so it is NOT a no-op edit.
CANDIDATE_STRATEGY = CURRENT_STRATEGY.replace("0.30", "0.25")

# Missing the required `next` method -> validate_strategy_edit rejects.
INVALID_STRATEGY = '''import backtrader as bt


class Broken(bt.Strategy):
    def __init__(self):
        pass
'''


def _hypothesis(**over):
    h = {
        "hypothesis_id": "rev-1-h0",
        "text": "Tightening the entry percentile to 0.25 raises selection quality.",
        "category": "hyperparameter",
        "confidence": "high",
        "causal_story": "A stricter percentile drops marginal-momentum names that "
                        "decay fastest after entry.",
        "predeclared_test": "Entries in the 0.25-0.30 band trail the kept book by "
                            ">2% over >=15 closed trades.",
        "supporting_evidence_json": '["RELIANCE", "ONGC@2026-05-26"]',
    }
    h.update(over)
    return h


def _candidate_json(strategy_text=CANDIDATE_STRATEGY):
    return json.dumps({
        "hypothesis": "Tighten entry percentile to 0.25.",
        "change_summary": "entry_pct 0.30 -> 0.25",
        "new_strategy_py": strategy_text,
    })


# ── 5.b: prompt (pure) ─────────────────────────────────────────────────────


def test_prompt_carries_hypothesis_and_current_strategy():
    h = _hypothesis()
    prompt = V.build_candidate_prompt(h, CURRENT_STRATEGY)
    assert h["text"] in prompt
    assert h["causal_story"] in prompt
    assert h["predeclared_test"] in prompt          # pre-registered acceptance bar
    assert "MomentumStrategy" in prompt             # current strategy embedded
    assert "new_strategy_py" in prompt              # JSON output contract
    assert "order_target_percent" in prompt         # CLAUDE.md hard constraint #3


def test_prompt_is_not_a_sortino_maximization_brief():
    # The candidate must IMPLEMENT one hypothesis, not "improve validation
    # Sortino" — that framing is the overfit trap we are avoiding.
    prompt = V.build_candidate_prompt(_hypothesis(), CURRENT_STRATEGY).lower()
    assert "shadow" in prompt or "robust" in prompt


# ── 5.b: build_candidate ────────────────────────────────────────────────────


def test_build_candidate_happy_path():
    prov = FakeProvider(_candidate_json())
    res = V.build_candidate(_hypothesis(), CURRENT_STRATEGY, prov)
    assert res.ok is True
    assert res.strategy_text == CANDIDATE_STRATEGY
    assert res.reject_reason is None
    assert prov.calls == 1


def test_build_candidate_rejects_invalid_edit():
    prov = FakeProvider(_candidate_json(INVALID_STRATEGY),
                        _candidate_json(INVALID_STRATEGY))
    res = V.build_candidate(_hypothesis(), CURRENT_STRATEGY, prov)
    assert res.ok is False
    assert "next" in (res.reject_reason or "")
    assert prov.calls == 2                          # initial + one retry


def test_build_candidate_rejects_noop_edit():
    prov = FakeProvider(_candidate_json(CURRENT_STRATEGY),
                        _candidate_json(CURRENT_STRATEGY))
    res = V.build_candidate(_hypothesis(), CURRENT_STRATEGY, prov)
    assert res.ok is False
    assert "no-op" in (res.reject_reason or "").lower()


def test_build_candidate_unparseable_then_fails():
    prov = FakeProvider("not json", "still not json")
    res = V.build_candidate(_hypothesis(), CURRENT_STRATEGY, prov)
    assert res.ok is False
    assert prov.calls == 2


def test_build_candidate_retry_succeeds():
    prov = FakeProvider("garbage", _candidate_json())
    res = V.build_candidate(_hypothesis(), CURRENT_STRATEGY, prov)
    assert res.ok is True
    assert prov.calls == 2


# ── 5.c: scale robustness (pure) ────────────────────────────────────────────


def _ao(sortino=1.0, p=0.001, rw=0.95, sub=(1.0, 1.1, 0.9),
        nhyper=5, ntrades=60, dd=0.10, univ=True):
    return {
        "sortino_val_mean": sortino,
        "sortino_val_pvalue": p,
        "rw_mc_null_pct": rw,
        "sub_period_sortinos": list(sub),
        "n_hyperparameters": nhyper,
        "n_trades": ntrades,
        "aggregate_dd": dd,
        "universe_respected": univ,
    }


def _metrics(risk_passed=True, **ao):
    return {"anti_overfit": _ao(**ao),
            "risk": {"passed": risk_passed, "violations": []}}


def test_scale_robust_when_dd_stable_and_positive():
    robust, reasons = V.assess_scale_robustness(
        _metrics(dd=0.10), _metrics(dd=0.12))
    assert robust is True
    assert reasons == ()


def test_scale_not_robust_when_dd_balloons():
    robust, reasons = V.assess_scale_robustness(
        _metrics(dd=0.10), _metrics(dd=0.30))
    assert robust is False
    assert any("balloon" in r.lower() or "dd" in r.lower() for r in reasons)


def test_scale_not_robust_when_5l_sortino_nonpositive():
    robust, reasons = V.assess_scale_robustness(
        _metrics(sortino=1.0), _metrics(sortino=-0.2))
    assert robust is False
    assert any("sortino" in r.lower() for r in reasons)


# ── 5.c: qualify_candidate (pure composition) ──────────────────────────────


def _qualify(m50, m5l):
    return V.qualify_candidate(
        m50, m5l, baseline_sortino=0.5, n_active_variants=1,
        baseline_hyperparams=5)


def test_qualify_passes_when_all_clean():
    v = _qualify(_metrics(), _metrics(dd=0.11))
    assert v.qualified is True
    assert v.reasons == ()
    assert v.scale_robust is True
    assert v.risk_50k is True and v.risk_5l is True


def test_qualify_fails_on_atomic_gate_at_50k():
    # rw_mc percentile below 0.90 fails the random-walk MC gate.
    v = _qualify(_metrics(rw=0.5), _metrics())
    assert v.qualified is False
    assert any("50k" in r or "₹50" in r for r in v.reasons)


def test_qualify_fails_on_catastrophe():
    v = _qualify(_metrics(risk_passed=False), _metrics())
    assert v.qualified is False
    assert any("catastrophe" in r.lower() for r in v.reasons)


def test_qualify_fails_on_5l_gate():
    v = _qualify(_metrics(), _metrics(rw=0.5))
    assert v.qualified is False
    assert any("5l" in r.lower() or "5L" in r or "₹5l" in r.lower() for r in v.reasons)


def test_qualify_fails_on_scale_dd_balloon():
    v = _qualify(_metrics(dd=0.10), _metrics(dd=0.35))
    assert v.qualified is False
    assert v.scale_robust is False


# ── 5.c: run_candidate_backtests (IO plumbing) ─────────────────────────────


def test_run_candidate_backtests_runs_both_capitals_serial(monkeypatch):
    """The ₹50k and ₹5L runs must (a) each see the right INITIAL_CASH, and
    (b) run SERIAL — prepare's parallel workers re-import by name and wouldn't
    see the in-process INITIAL_CASH override, so the harness forces serial."""
    import prepare

    seen = []

    def fake_eval(module, mode="research"):
        seen.append((prepare.INITIAL_CASH, os.environ.get("PREPARE_MAX_WORKERS")))
        return {"capital": prepare.INITIAL_CASH}

    monkeypatch.setattr(prepare, "evaluate", fake_eval)
    orig_cash = prepare.INITIAL_CASH

    out = V.run_candidate_backtests(CANDIDATE_STRATEGY, capitals=(50_000, 500_000))

    assert set(out) == {50_000, 500_000}
    assert seen[0] == (50_000.0, "1")
    assert seen[1] == (500_000.0, "1")
    # INITIAL_CASH restored after the run
    assert prepare.INITIAL_CASH == orig_cash


# ── 5.d executor: fresh sealed reveal on a forward window ──────────────────


def test_run_fresh_sealed_reveal_overrides_boundaries_and_restores(monkeypatch):
    import prepare

    seen = {}

    def fake_eval(module, mode="research"):
        seen["mode"] = mode
        seen["tb"] = prepare.TEST_BOUNDARY
        seen["be"] = prepare.BACKTEST_END
        return {"test_sortino": 0.8, "test_max_dd": 0.1,
                "test_calmar": 0.5, "test_trade_count": 12}

    monkeypatch.setattr(prepare, "evaluate", fake_eval)
    otb, obe = prepare.TEST_BOUNDARY, prepare.BACKTEST_END

    out = V.run_fresh_sealed_reveal(
        CANDIDATE_STRATEGY, date(2026, 5, 15), date(2027, 1, 1))

    assert seen["mode"] == "promotion"
    assert seen["tb"] == date(2026, 5, 15) and seen["be"] == date(2027, 1, 1)
    assert out["test_sortino"] == 0.8
    # boundaries restored — the burned window must never stay overridden
    assert prepare.TEST_BOUNDARY == otb and prepare.BACKTEST_END == obe


# ── orchestrator: run_validation ────────────────────────────────────────────


def _seed_pending(rw_path, hid="rev-1-h0"):
    conn = realworld_db.connect(rw_path)
    realworld_db.insert_hypothesis(
        conn, hypothesis_id=hid, review_id="rev-1",
        created_at=datetime(2026, 6, 1), mode="dhan-paper",
        category="hyperparameter", confidence="high",
        text="Tighten entry percentile to 0.25.",
        causal_story="Stricter percentile drops decay-prone names.",
        predeclared_test="0.25-0.30 band trails the book by >2% over >=15 trades.",
        supporting_evidence_json='["RELIANCE"]', text_lexical_hash="hh")
    conn.close()


def _run_validation(provider, tmp_path, monkeypatch, *, metrics=None, **over):
    metrics = metrics or {50_000: _metrics(), 500_000: _metrics(dd=0.11)}
    monkeypatch.setattr(V, "run_candidate_backtests", lambda text, **k: metrics)
    strat = tmp_path / "strategy.py"
    strat.write_text(CURRENT_STRATEGY)
    kw = dict(
        hypothesis_id="rev-1-h0", mode="dhan-paper", provider=provider,
        realworld_db_path=tmp_path / "rw.duckdb", strategy_path=strat,
        snapshot_dir=tmp_path / "versions", journal_path=tmp_path / "j.md",
        now=datetime(2026, 6, 7, 12, 0, 0), today=date(2026, 6, 7),
        compute_baseline=lambda *a, **k: (0.5, 5))
    kw.update(over)
    return strat, V.run_validation(**kw)


def test_run_validation_creates_challenger(tmp_path, monkeypatch):
    _seed_pending(tmp_path / "rw.duckdb")
    prov = FakeProvider(_candidate_json())
    strat, res = _run_validation(prov, tmp_path, monkeypatch)
    assert res.outcome == "CHALLENGER_CREATED"
    assert res.version_hash is not None
    assert res.sealed_status == "DEFERRED_TO_SHADOW"   # only ~3wk of fresh data
    # live strategy.py is UNTOUCHED — the validator never swaps it
    assert strat.read_text() == CURRENT_STRATEGY
    # challenger row + snapshot file exist
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    rows = realworld_db.get_strategy_versions(rw, "dhan-paper")
    assert len(rows) == 1 and rows[0]["status"] == "CHALLENGER"
    rw.close()
    assert (tmp_path / "versions" / f"{res.version_hash}.py").exists()


def test_run_validation_rejects_on_gates(tmp_path, monkeypatch):
    _seed_pending(tmp_path / "rw.duckdb")
    prov = FakeProvider(_candidate_json())
    # rw_mc below 0.90 fails the random-walk gate at ₹50k.
    bad = {50_000: _metrics(rw=0.5), 500_000: _metrics()}
    strat, res = _run_validation(prov, tmp_path, monkeypatch, metrics=bad)
    assert res.outcome == "REJECTED_GATES"
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_hypothesis(rw, "rev-1-h0")["state"] == "VALIDATOR_REJECTED"
    assert realworld_db.get_strategy_versions(rw, "dhan-paper") == []
    rw.close()


def test_run_validation_rejects_on_build(tmp_path, monkeypatch):
    _seed_pending(tmp_path / "rw.duckdb")
    prov = FakeProvider(_candidate_json(INVALID_STRATEGY),
                        _candidate_json(INVALID_STRATEGY))
    strat, res = _run_validation(prov, tmp_path, monkeypatch)
    assert res.outcome == "REJECTED_BUILD"
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert realworld_db.get_hypothesis(rw, "rev-1-h0")["state"] == "VALIDATOR_REJECTED"
    rw.close()


def test_run_validation_skips_when_not_pending(tmp_path, monkeypatch):
    # No hypothesis seeded -> nothing to validate.
    prov = FakeProvider()  # must not be called
    strat, res = _run_validation(prov, tmp_path, monkeypatch)
    assert res.outcome == "SKIPPED"
    assert prov.calls == 0


def test_run_validation_skips_if_active_challenger_exists(tmp_path, monkeypatch):
    _seed_pending(tmp_path / "rw.duckdb")
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    realworld_db.insert_strategy_version(
        rw, version_hash="v-existing", created_at=datetime(2026, 6, 5),
        mode="dhan-paper", hypothesis_id="rev-1-h0", parent_version_hash=None,
        unified_diff="x", gate_results_json="{}", scale_robustness_json="{}",
        sealed_status="DEFERRED_TO_SHADOW", sealed_metrics_json=None,
        validator_version="v1", journal_excerpt="x", snapshot_path="x.py")
    rw.close()
    prov = FakeProvider()  # must not be called
    strat, res = _run_validation(prov, tmp_path, monkeypatch)
    assert res.outcome == "SKIPPED"
    assert prov.calls == 0
