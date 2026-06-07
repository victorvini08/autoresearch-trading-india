"""On-demand strategy-evolution validator — Component ③ (Step 5).

This is the ONLY mechanism that can ever change strategy.py, and it is NEVER
scheduled — a human runs it against ONE PENDING hypothesis that already cleared
the Step-4 review validator. It does not brainstorm; it tries to turn that one
pre-registered claim into a strategy edit and then subjects the result to the
immutable gate machinery.

Two pieces live here:

  5.b  build_candidate  — hypothesis -> LLM prompt -> candidate strategy.py,
                          validated through the SAME AST/import sandbox the
                          nightly loop uses (scripts.loop.validate_strategy_edit).
                          The live strategy.py is never touched.

  5.c  qualify_candidate — run the candidate through the IMMUTABLE prepare.py at
                          BOTH ₹50k and ₹5L, then QUALIFY it: the 5 atomic
                          anti-overfit gates + the catastrophe gate + scale
                          robustness, at both capitals.

Qualification is NOT selection. Passing here means "this candidate is
structurally sound and scale-robust enough to deserve a live shadow trial" —
it deliberately does NOT require beating the incumbent's validation Sortino.
That bar is the overfit trap (see the robustness-over-validation-Sortino
learning); the real "is it better?" decision is made later on the shadow book's
genuinely-out-of-sample evidence, not on the in-sample validation window.

The sealed reveal (5.d) and the shadow/promote chain (5.e/5.f) are separate —
nothing here can promote a candidate into live strategy.py.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

VALIDATOR_VERSION = "v1"
PROMPT_VERSION = "v1"
REVIEW_MODEL = "claude-opus-4-7"

STRATEGY_PATH = REPO_ROOT / "strategy.py"
SNAPSHOT_DIR = REPO_ROOT / "state" / "strategy_versions"
JOURNAL_PATH = REPO_ROOT / "state" / "realworld_journal.md"

# Backtest capitals. ₹50k matches prepare.INITIAL_CASH (the evaluator default);
# ₹5L is the 10× scale check from the locked decision — ₹50k wins are routinely
# whole-share / concentration lumpiness that collapses at scale.
DEFAULT_CAPITAL = 50_000.0
SCALE_CAPITAL = 500_000.0

# A candidate's aggregate drawdown is allowed to drift up by at most this much
# from ₹50k to ₹5L. A larger swing means the ₹50k risk profile was a
# small-capital artifact, not the strategy's true behaviour.
MAX_DD_SCALE_BALLOON = 0.10


@dataclass(frozen=True)
class CandidateResult:
    ok: bool
    strategy_text: str | None
    hypothesis_text: str
    change_summary: str | None
    reject_reason: str | None


@dataclass(frozen=True)
class CandidateVerdict:
    qualified: bool
    reasons: tuple
    gates_50k: dict
    gates_5l: dict
    risk_50k: bool
    risk_5l: bool
    scale_robust: bool


# ── 5.b: candidate construction ─────────────────────────────────────────────


_PREAMBLE = """You are implementing ONE pre-registered hypothesis as an edit to
a long-only swing-trading strategy on Indian equities (NSE, CNC delivery). This
is NOT a "make the backtest look better" task: your job is to implement the
stated mechanism faithfully and MINIMALLY, then let the gates judge it.

How this candidate will be judged (so you do not waste the attempt):
- It must pass the immutable anti-overfit gates at BOTH ₹50k and ₹5L capital.
- It must be SCALE-ROBUST — an edge that only shows up at ₹50k is a lumpiness
  artifact and will be rejected.
- If it qualifies, it does NOT go live. It becomes a CHALLENGER that must earn
  promotion on a live SHADOW book against the incumbent. So do not curve-fit
  to the validation window — robustness across regimes is what survives.

Hard constraints (a deterministic validator enforces these):
1. Edit ONLY the strategy. Return the COMPLETE new strategy.py as a string.
2. Exactly ONE bt.Strategy subclass, defining __init__ and next.
3. Use order_target_percent ONLY (never self.buy()/self.close()) — the live
   signal-capture path depends on it.
4. Allowed imports only: backtrader, numpy, pandas, datetime, __future__,
   data.*, llm.features, and safe pure-computation stdlib (math, logging,
   collections, itertools, functools, statistics, bisect, heapq, random,
   operator, typing, dataclasses, enum, decimal, fractions, re, json).
   No os/sys/subprocess/pathlib/socket/requests/pickle/importlib.
5. Keep it parsimonious — every new tunable hyperparameter must earn its keep;
   prefer the smallest change that implements the hypothesis.

============================================================================
HYPOTHESIS TO IMPLEMENT (pre-registered; cleared the monthly-review validator):
============================================================================
- claim: {text}
- category: {category}
- causal story: {causal_story}
- pre-registered falsification test (your edit should make this checkable):
  {predeclared_test}
- supporting evidence ids: {evidence}

============================================================================
CURRENT strategy.py:
============================================================================
{strategy}

============================================================================

Respond with STRICT JSON, no surrounding prose, no markdown fences:

{{
  "hypothesis": "one sentence restating the claim you implemented",
  "change_summary": "one sentence describing exactly what you changed",
  "new_strategy_py": "the complete new strategy.py file as a string"
}}
"""


def build_candidate_prompt(hypothesis: dict, current_strategy: str) -> str:
    """Pure: the implementation brief for ONE hypothesis + the current strategy
    + the JSON output contract. Seeded by a specific pre-registered claim, not
    an open "improve the Sortino" instruction."""
    return _PREAMBLE.format(
        text=hypothesis.get("text", ""),
        category=hypothesis.get("category", ""),
        causal_story=hypothesis.get("causal_story", ""),
        predeclared_test=hypothesis.get("predeclared_test", ""),
        evidence=hypothesis.get("supporting_evidence_json", "[]"),
        strategy=current_strategy,
    )


def _retry_suffix(reason: str) -> str:
    return ("\n\nYour previous output was rejected for this reason. Fix it and "
            f"return ONLY the corrected JSON object:\n- {reason}")


def build_candidate(
    hypothesis: dict,
    current_strategy: str,
    provider,
    *,
    max_retries: int = 1,
) -> CandidateResult:
    """Ask the provider to implement the hypothesis, then validate the edit
    through the loop's AST/import sandbox. Retries once on a fixable failure
    (unparseable output or a rejected edit) with the reason appended. Never
    writes a file."""
    from scripts.loop import (
        _coerce_valid_python,
        _extract_json_obj,
        validate_strategy_edit,
    )

    base = build_candidate_prompt(hypothesis, current_strategy)
    hyp_text = hypothesis.get("text", "")
    reason: str | None = None
    attempt = 0
    while True:
        prompt = base if reason is None else base + _retry_suffix(reason)
        raw = provider.classify(prompt, timeout=600)
        parsed = _extract_json_obj(raw)
        if parsed is None or "new_strategy_py" not in parsed:
            reason = "LLM output did not parse as the required JSON object"
            if attempt < max_retries:
                attempt += 1
                continue
            return CandidateResult(False, None, hyp_text, None, "unparseable LLM output")

        new_text = _coerce_valid_python(parsed["new_strategy_py"])
        ok, why = validate_strategy_edit(new_text, current_text=current_strategy)
        if ok:
            return CandidateResult(
                True, new_text, hyp_text, parsed.get("change_summary"), None)
        reason = f"the proposed strategy.py was rejected: {why}"
        if attempt < max_retries:
            attempt += 1
            continue
        return CandidateResult(
            False, None, hyp_text, parsed.get("change_summary"), f"invalid edit: {why}")


# ── 5.c: gate harness ───────────────────────────────────────────────────────


def _materialize_module(text: str):
    """Load candidate strategy text as an importable module WITHOUT touching the
    live strategy.py. Registered in sys.modules by a content-derived name so a
    re-run with identical text reuses it."""
    name = "_rw_candidate_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    path = Path(tempfile.gettempdir()) / f"{name}.py"
    path.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_candidate_backtests(
    candidate_text: str, *, capitals: tuple[float, ...] = (DEFAULT_CAPITAL, SCALE_CAPITAL),
) -> dict[int, dict]:
    """Run the candidate through the IMMUTABLE prepare.py at each capital,
    returning {int(capital): research_metrics}.

    Forced serial (PREPARE_MAX_WORKERS=1): prepare's parallel workers re-import
    the strategy module BY NAME in fresh processes, which would (a) not see the
    in-process INITIAL_CASH override and (b) fail to import a temp module. Serial
    uses the in-process class directly, so both the capital override and the
    dynamically-loaded module work. The validator is rare/on-demand, so the
    serial cost is irrelevant."""
    module = _materialize_module(candidate_text)
    import prepare

    prev_workers = os.environ.get("PREPARE_MAX_WORKERS")
    os.environ["PREPARE_MAX_WORKERS"] = "1"
    orig_cash = prepare.INITIAL_CASH
    out: dict[int, dict] = {}
    try:
        for cap in capitals:
            prepare.INITIAL_CASH = float(cap)
            out[int(cap)] = prepare.evaluate(module, mode="research")
    finally:
        prepare.INITIAL_CASH = orig_cash
        if prev_workers is None:
            os.environ.pop("PREPARE_MAX_WORKERS", None)
        else:
            os.environ["PREPARE_MAX_WORKERS"] = prev_workers
    return out


def assess_scale_robustness(
    metrics_50k: dict, metrics_5l: dict, *, max_dd_balloon: float = MAX_DD_SCALE_BALLOON,
) -> tuple[bool, tuple]:
    """Pure: does the candidate's behaviour SURVIVE at ₹5L? Checks the
    scale-specific failure modes the atomic gates don't (the gates measure edge
    significance; this measures capital sensitivity): the ₹5L Sortino must stay
    positive and aggregate drawdown must not balloon vs ₹50k. (Whether the ₹5L
    run also clears the atomic gates is checked separately in qualify_candidate.)"""
    ao50 = metrics_50k.get("anti_overfit", {})
    ao5l = metrics_5l.get("anti_overfit", {})
    s5l = float(ao5l.get("sortino_val_mean", 0.0))
    dd50 = float(ao50.get("aggregate_dd", 0.0))
    dd5l = float(ao5l.get("aggregate_dd", 0.0))

    reasons: list[str] = []
    if s5l <= 0.0:
        reasons.append(
            f"₹5L Sortino {s5l:.3f} not positive — edge is a small-capital artifact")
    if dd5l > dd50 + max_dd_balloon:
        reasons.append(
            f"aggregate DD balloons at scale: ₹5L {dd5l:.1%} vs ₹50k {dd50:.1%} "
            f"(+{max_dd_balloon:.0%} tolerance)")
    return (len(reasons) == 0, tuple(reasons))


def _fail_names(gate_run) -> str:
    return " · ".join(
        f"{g['name']}({g['reason']})" for g in gate_run["gates"] if not g["passed"]
    )


def qualify_candidate(
    metrics_50k: dict,
    metrics_5l: dict,
    *,
    baseline_sortino: float,
    n_active_variants: int,
    baseline_hyperparams: int,
) -> CandidateVerdict:
    """Pure composition: a candidate QUALIFIES iff it clears the atomic
    anti-overfit gates AND the catastrophe gate at BOTH ₹50k and ₹5L, AND it is
    scale-robust. Reuses the loop's gate wrapper (skip_sealed=True) so the
    gate semantics are identical to the nightly research path."""
    from scripts.loop import evaluate_anti_overfit_gates

    gr_50k, _ = evaluate_anti_overfit_gates(
        metrics_50k, iter_id="candidate-50k", baseline_sortino=baseline_sortino,
        n_active_variants=n_active_variants, baseline_hyperparams=baseline_hyperparams)
    gr_5l, _ = evaluate_anti_overfit_gates(
        metrics_5l, iter_id="candidate-5l", baseline_sortino=baseline_sortino,
        n_active_variants=n_active_variants, baseline_hyperparams=baseline_hyperparams)
    d_50k, d_5l = gr_50k.to_dict(), gr_5l.to_dict()

    risk_50k = bool(metrics_50k.get("risk", {}).get("passed", False))
    risk_5l = bool(metrics_5l.get("risk", {}).get("passed", False))
    scale_robust, scale_reasons = assess_scale_robustness(metrics_50k, metrics_5l)

    reasons: list[str] = []
    if not d_50k["passed"]:
        reasons.append(f"atomic gates failed at ₹50k: {_fail_names(d_50k)}")
    if not risk_50k:
        reasons.append("catastrophe gate failed at ₹50k: "
                       + " · ".join(metrics_50k.get("risk", {}).get("violations", []) or ["unspecified"]))
    if not d_5l["passed"]:
        reasons.append(f"atomic gates failed at ₹5L: {_fail_names(d_5l)}")
    if not risk_5l:
        reasons.append("catastrophe gate failed at ₹5L: "
                       + " · ".join(metrics_5l.get("risk", {}).get("violations", []) or ["unspecified"]))
    reasons.extend(scale_reasons)

    qualified = (d_50k["passed"] and risk_50k and d_5l["passed"]
                 and risk_5l and scale_robust)
    return CandidateVerdict(
        qualified=qualified,
        reasons=tuple(reasons),
        gates_50k=d_50k,
        gates_5l=d_5l,
        risk_50k=risk_50k,
        risk_5l=risk_5l,
        scale_robust=scale_robust,
    )


# ── 5.d executor: fresh sealed reveal on a forward window ──────────────────


def run_fresh_sealed_reveal(
    candidate_text: str, window_start: date, window_end: date,
) -> dict:
    """Reveal the candidate ONCE on a genuinely-fresh forward window by
    overriding prepare's sealed boundaries to [window_start, window_end] and
    running promotion mode. NEVER call this on the burned 2025→2026-05 window —
    backtest.sealed_budget guarantees window_start is strictly after the frozen
    boundary. Boundaries are always restored, so the burned window can't leak
    into a later run."""
    module = _materialize_module(candidate_text)
    import prepare

    prev_workers = os.environ.get("PREPARE_MAX_WORKERS")
    os.environ["PREPARE_MAX_WORKERS"] = "1"
    orig_tb, orig_be = prepare.TEST_BOUNDARY, prepare.BACKTEST_END
    try:
        prepare.TEST_BOUNDARY = window_start
        prepare.BACKTEST_END = window_end
        metrics = prepare.evaluate(module, mode="promotion")
    finally:
        prepare.TEST_BOUNDARY = orig_tb
        prepare.BACKTEST_END = orig_be
        if prev_workers is None:
            os.environ.pop("PREPARE_MAX_WORKERS", None)
        else:
            os.environ["PREPARE_MAX_WORKERS"] = prev_workers
    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "test_sortino": metrics.get("test_sortino"),
        "test_calmar": metrics.get("test_calmar"),
        "test_max_dd": metrics.get("test_max_dd"),
        "test_trade_count": metrics.get("test_trade_count"),
    }


# ── orchestrator: run_validation ────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationRunResult:
    hypothesis_id: str
    outcome: str            # SKIPPED | REJECTED_BUILD | REJECTED_GATES | CHALLENGER_CREATED
    version_hash: str | None
    sealed_status: str | None
    reasons: tuple


def _default_provider():
    from llm.provider import ClaudeCodeProvider
    return ClaudeCodeProvider(model=REVIEW_MODEL)


def compute_incumbent_baseline(strategy_path: Path | str = STRATEGY_PATH) -> tuple[float, int]:
    """Recompute the CURRENT committed strategy's research Sortino + tunable
    hyperparameter count under THIS evaluator, so the parsimony/Bonferroni
    baselines are apples-to-apples with the candidate (not a stale journal
    number from an older evaluator version)."""
    text = Path(strategy_path).read_text()
    metrics = run_candidate_backtests(text, capitals=(DEFAULT_CAPITAL,))[int(DEFAULT_CAPITAL)]
    ao = metrics.get("anti_overfit", {})
    return float(ao.get("sortino_val_mean", 0.0)), int(ao.get("n_hyperparameters", 0))


def _bonferroni_family(conn, mode: str) -> int:
    """Multiple-comparisons family for the on-demand validator: every challenger
    vetted against the CURRENT incumbent since the last promotion, +1, capped at
    10 (mirrors the loop's BONFERRONI_FAMILY_CAP). A promotion resets the
    episode (new incumbent ⇒ new family)."""
    from storage import realworld_db

    versions = realworld_db.get_strategy_versions(conn, mode)
    promoted_at = [v["created_at"] for v in versions if v["status"] == "PROMOTED"]
    cutoff = max(promoted_at) if promoted_at else None
    family = [v for v in versions if cutoff is None or v["created_at"] > cutoff]
    return max(1, min(len(family) + 1, 10))


def _sealed_state(conn, mode: str) -> tuple[date, date | None]:
    """Derive the current sealed boundary + last-reveal date from prior REVEALED
    challengers. With no fresh reveal ever spent (the live state), this is the
    initial burned boundary and no prior reveal."""
    from backtest.sealed_budget import INITIAL_FROZEN_BOUNDARY
    from storage import realworld_db

    revealed = [
        v for v in realworld_db.get_strategy_versions(conn, mode)
        if v["sealed_status"] == "REVEALED" and v.get("sealed_metrics_json")
    ]
    if not revealed:
        return INITIAL_FROZEN_BOUNDARY, None
    boundary = INITIAL_FROZEN_BOUNDARY
    last_reveal_at: date | None = None
    for v in revealed:
        try:
            sm = json.loads(v["sealed_metrics_json"])
            we = date.fromisoformat(sm["window_end"])
            boundary = max(boundary, we)
        except Exception:  # noqa: BLE001 — a malformed row must not crash the run
            pass
        created = v["created_at"]
        cd = created.date() if isinstance(created, datetime) else created
        last_reveal_at = cd if last_reveal_at is None else max(last_reveal_at, cd)
    return boundary, last_reveal_at


def _append_validator_journal(
    path: Path | str, *, now: datetime, version_hash: str, hyp: dict,
    sealed_status: str, mode: str,
) -> None:
    path = Path(path)
    lines = [
        f"\n## {now.date().isoformat()} — challenger {version_hash} ({mode})\n",
        f"- from hypothesis **{hyp.get('hypothesis_id')}**: {hyp.get('text')}\n",
        f"- qualified the atomic gates + ₹5L scale check; sealed: **{sealed_status}**\n",
        "- status: CHALLENGER (awaiting shadow trial — live strategy.py unchanged)\n",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(lines)


def run_validation(
    *,
    hypothesis_id: str,
    mode: str = "dhan-paper",
    provider=None,
    realworld_db_path: Path | str | None = None,
    strategy_path: Path | str = STRATEGY_PATH,
    snapshot_dir: Path | str = SNAPSHOT_DIR,
    journal_path: Path | str | None = None,
    now: datetime | None = None,
    today: date | None = None,
    compute_baseline=None,
) -> ValidationRunResult:
    """Validate ONE PENDING hypothesis end to end:
    build candidate → qualify (₹50k + ₹5L) → sealed budget → record a CHALLENGER.

    Never writes the live strategy.py — on success it produces a CHALLENGER
    snapshot awaiting a shadow trial; on failure it burns the hypothesis
    (VALIDATOR_REJECTED). The hypothesis stays PENDING while a challenger is in
    flight (the strategy_versions row owns the promotion lifecycle); it flips to
    VALIDATOR_KEPT only when the challenger is actually promoted (5.f)."""
    from backtest import sealed_budget as SB
    from storage import realworld_db

    provider = provider or _default_provider()
    now = now or datetime.now()
    today = today or now.date()
    compute_baseline = compute_baseline or compute_incumbent_baseline
    journal_path = journal_path if journal_path is not None else JOURNAL_PATH
    db_path = (Path(realworld_db_path) if realworld_db_path is not None
               else realworld_db.DEFAULT_DB_PATH)
    conn = realworld_db.connect(db_path)
    try:
        hyp = realworld_db.get_hypothesis(conn, hypothesis_id)
        if hyp is None or hyp["state"] != "PENDING" or hyp["mode"] != mode:
            return ValidationRunResult(
                hypothesis_id, "SKIPPED", None, None,
                ("hypothesis not found, not PENDING, or wrong mode",))

        active = [
            v for v in realworld_db.get_strategy_versions(conn, mode)
            if v["hypothesis_id"] == hypothesis_id
            and v["status"] in ("CHALLENGER", "SHADOW_ACTIVE", "PROMOTED")
        ]
        if active:
            return ValidationRunResult(
                hypothesis_id, "SKIPPED", active[0]["version_hash"], None,
                ("hypothesis already has an active challenger",))

        current = Path(strategy_path).read_text()
        cand = build_candidate(hyp, current, provider)
        if not cand.ok:
            realworld_db.update_hypothesis_state(
                conn, hypothesis_id, "VALIDATOR_REJECTED", updated_at=now)
            return ValidationRunResult(
                hypothesis_id, "REJECTED_BUILD", None, None,
                (cand.reject_reason or "candidate build failed",))

        backtests = run_candidate_backtests(cand.strategy_text)
        m50, m5l = backtests[int(DEFAULT_CAPITAL)], backtests[int(SCALE_CAPITAL)]
        baseline_sortino, baseline_hyperparams = compute_baseline(strategy_path)
        n_active = _bonferroni_family(conn, mode)
        verdict = qualify_candidate(
            m50, m5l, baseline_sortino=baseline_sortino,
            n_active_variants=n_active, baseline_hyperparams=baseline_hyperparams)
        if not verdict.qualified:
            realworld_db.update_hypothesis_state(
                conn, hypothesis_id, "VALIDATOR_REJECTED", updated_at=now)
            return ValidationRunResult(
                hypothesis_id, "REJECTED_GATES", None, None, verdict.reasons)

        # --- sealed-data budget (5.d): fresh reveal if available, else shadow ---
        frozen_boundary, last_reveal_at = _sealed_state(conn, mode)
        budget = SB.assess_sealed_budget(
            today, frozen_boundary=frozen_boundary, last_reveal_at=last_reveal_at)
        sealed_metrics_json = None
        if budget.available:
            sealed = run_fresh_sealed_reveal(
                cand.strategy_text, budget.window_start, budget.window_end)
            ts = sealed.get("test_sortino")
            if ts is not None and float(ts) <= 0.0:
                realworld_db.update_hypothesis_state(
                    conn, hypothesis_id, "VALIDATOR_REJECTED", updated_at=now)
                return ValidationRunResult(
                    hypothesis_id, "REJECTED_GATES", None, "REVEALED",
                    (f"fresh sealed reveal Sortino {ts} <= 0 on "
                     f"[{budget.window_start}..{budget.window_end}]",))
            sealed_status = "REVEALED"
            sealed_metrics_json = json.dumps(sealed)
        else:
            sealed_status = budget.status  # DEFERRED_TO_SHADOW

        # --- record the CHALLENGER (live strategy.py stays untouched) ---
        version_hash = hashlib.sha256(cand.strategy_text.encode("utf-8")).hexdigest()[:16]
        snap_dir = Path(snapshot_dir)
        snap_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snap_dir / f"{version_hash}.py"
        snapshot_path.write_text(cand.strategy_text, encoding="utf-8")

        diff = "".join(difflib.unified_diff(
            current.splitlines(keepends=True),
            cand.strategy_text.splitlines(keepends=True),
            fromfile="strategy.py (incumbent)",
            tofile=f"strategy.py ({version_hash})"))
        gate_results = {
            "baseline_sortino": baseline_sortino,
            "n_active_variants": n_active,
            "gates_50k": verdict.gates_50k,
            "gates_5l": verdict.gates_5l,
            "risk_50k": verdict.risk_50k,
            "risk_5l": verdict.risk_5l,
        }
        ao50, ao5l = m50.get("anti_overfit", {}), m5l.get("anti_overfit", {})
        scale = {
            "scale_robust": verdict.scale_robust,
            "sortino_50k": ao50.get("sortino_val_mean"),
            "sortino_5l": ao5l.get("sortino_val_mean"),
            "agg_dd_50k": ao50.get("aggregate_dd"),
            "agg_dd_5l": ao5l.get("aggregate_dd"),
        }
        realworld_db.insert_strategy_version(
            conn, version_hash=version_hash, created_at=now, mode=mode,
            hypothesis_id=hypothesis_id, parent_version_hash=None,
            unified_diff=diff, gate_results_json=json.dumps(gate_results),
            scale_robustness_json=json.dumps(scale), sealed_status=sealed_status,
            sealed_metrics_json=sealed_metrics_json,
            validator_version=VALIDATOR_VERSION,
            journal_excerpt=cand.change_summary or hyp["text"],
            snapshot_path=str(snapshot_path), status="CHALLENGER")

        _append_validator_journal(
            journal_path, now=now, version_hash=version_hash, hyp=hyp,
            sealed_status=sealed_status, mode=mode)
        return ValidationRunResult(
            hypothesis_id, "CHALLENGER_CREATED", version_hash, sealed_status, ())
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate ONE PENDING hypothesis into a CHALLENGER (Step 5).")
    ap.add_argument("hypothesis_id")
    ap.add_argument("--mode", default="dhan-paper")
    args = ap.parse_args(argv)
    res = run_validation(hypothesis_id=args.hypothesis_id, mode=args.mode)
    print(f"[realworld_validator] {res.hypothesis_id} -> {res.outcome} "
          f"version={res.version_hash} sealed={res.sealed_status}")
    if res.reasons:
        for r in res.reasons:
            print(f"  - {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
