"""Monthly LLM review runner — Component ② (Step 4.d).

Read-only with respect to strategy.py and the gates: there is no code path
here that writes either. Orchestrates one review run:

    gather context -> build prompt -> call LLM -> validate -> retry-once on a
    FIXABLE failure -> persist (audit ALWAYS; PENDING hypotheses only when the
    validator passes them; one human-readable journal entry).

The validator (data/realworld_review_validator.py) is the control; this module
is the plumbing around it. The LLM provider is injected so it is fully testable
without shelling out.

Trigger is event-aligned (the month's last rebalance-execution day, wired in
daily_report at Step 4.e), or `manual`. Cold-start (N<10) means that for the
first few months a run just journals observations — the validator rejects any
hypotheses and nothing is persisted to strategy.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from data import realworld_review_validator as V
from scripts.realworld_context import (
    JOURNAL_PATH,
    ReviewInput,
    gather_review_input,
)
from storage import realworld_db

PROMPT_VERSION = "v1"
# Matches the documented autoresearch stack (Opus for the loop). Only used by
# the default provider factory; tests inject a fake.
REVIEW_MODEL = "claude-opus-4-7"

# Retry only on failures the LLM could plausibly fix on a re-call. Structural
# rejections (cold_start / drawdown_gate / duplicate) will recur identically,
# so retrying them just burns an LLM call.
_RETRYABLE_PREFIXES = ("schema", "citation", "falsifia", "json")


@dataclass(frozen=True)
class ReviewRunResult:
    review_id: str
    validator_result: str
    cold_start: bool
    n_accepted: int
    n_rejected: int
    observations: tuple


_PREAMBLE = """You are an analyst reviewing live paper-trading results for a
cross-sectional momentum-quality book on Indian equities.

YOUR DEFAULT OUTPUT IS "NO CHANGE."

Hard constraints (a deterministic validator enforces these — violations are
silently dropped, so do not waste a hypothesis on them):
1. Sample size is tiny (~5-8 closed round-trips/month). You CANNOT distinguish
   strategy decay from noise on this sample. Bias structurally toward no action.
2. Every hypothesis MUST cite specific evidence ids (from valid_evidence_ids),
   give a causal_story, and give a falsifiable predeclared_test that could be
   RUN against the realized trades / Nifty / decile scores we already store.
3. If safety_state != NORMAL, only category="risk_off" hypotheses are allowed.
4. If this run is in cold-start mode (n_realized_trades < 10), DO NOT emit any
   hypotheses at all — return observations only.
5. You cannot change anti-overfit gates, the sealed-test protocol, or the
   safety-state machine. A PENDING hypothesis is only a candidate; it still
   must clear the full backtest gates later before anything changes.

Return ONLY a single JSON object, no prose, with this exact shape:
{
  "observations": ["<diagnostic note>", ...],
  "hypotheses": [
    {
      "id": "<short id>",
      "text": "<one-sentence claim>",
      "category": "risk_off|signal|hyperparameter|cost|execution|data_bug",
      "confidence": "low|medium|high",
      "supporting_evidence_ids": ["<id from valid_evidence_ids>", ...],
      "causal_story": "<why this mechanism would produce the observation>",
      "predeclared_test": "<a concrete, runnable falsification test>"
    }
  ]
}

REVIEW CONTEXT (JSON):
"""


def build_prompt(review_input: ReviewInput) -> str:
    """Pure: hard-constraint preamble + the JSON output contract + the context
    payload. The payload carries valid_evidence_ids so the model cites real ids."""
    payload_json = json.dumps(review_input.payload, indent=2, default=str)
    return _PREAMBLE + payload_json


def _parse_json(raw: str) -> dict | None:
    s = (raw or "").strip()
    if s.startswith("```"):
        parts = s.split("```")
        if len(parts) >= 2:
            s = parts[1]
            if s.lstrip().lower().startswith("json"):
                s = s.lstrip()[4:]
            s = s.strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        i, j = s.find("{"), s.rfind("}")
        if 0 <= i < j:
            try:
                obj = json.loads(s[i:j + 1])
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
        return None


def _collect_failures(result: V.ValidationResult) -> list:
    failures = list(result.output_errors)
    for v in result.verdicts:
        if not v.accepted:
            hid = v.hypothesis.get("id", "?") if isinstance(v.hypothesis, dict) else "?"
            for r in v.rejection_reasons:
                failures.append(f"[{hid}] {r}")
    return failures


def _is_retryable(failures: list) -> bool:
    return any(
        any(f.split("]")[-1].strip().startswith(p) or f.startswith(p)
            for p in _RETRYABLE_PREFIXES)
        for f in failures
    )


def _retry_suffix(failures: list) -> str:
    return ("\n\nYour previous output was rejected for these reasons. Fix them "
            "and return ONLY the corrected JSON object:\n- " + "\n- ".join(failures))


def _gen_review_id(ri: ReviewInput, now: datetime) -> str:
    return f"rev-{ri.input_snapshot_hash[:10]}-{now:%Y%m%d%H%M%S}"


def _default_provider():
    from llm.provider import ClaudeCodeProvider
    return ClaudeCodeProvider(model=REVIEW_MODEL)


def _append_journal(
    path: Path, *, d: date, review_id: str, mode: str, ri: ReviewInput,
    validator_result: str, accepted: tuple, failures: list, observations: tuple,
) -> None:
    lines = [f"\n## {d.isoformat()} — review {review_id} ({mode})\n"]
    if ri.cold_start:
        lines.append(f"> {ri.payload['cold_start_banner']}\n")
    lines.append(f"- validator_result: **{validator_result}**, safety_state: "
                 f"{ri.safety_state}, N={ri.n_realized_trades}\n")
    if observations:
        lines.append("- Observations:\n")
        lines.extend(f"  - {o}\n" for o in observations)
    if accepted:
        lines.append("- Accepted hypotheses (PENDING — not yet promoted):\n")
        for h in accepted:
            lines.append(f"  - [{h.get('category')}/{h.get('confidence')}] "
                         f"{h.get('text')}\n")
    if failures:
        lines.append(f"- Rejected/failures ({len(failures)}): "
                     f"{'; '.join(failures[:6])}"
                     f"{' …' if len(failures) > 6 else ''}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(lines)


def run_review(
    *,
    d: date,
    mode: str = "dhan-paper",
    provider=None,
    trigger: str = "monthly",
    review_input: ReviewInput | None = None,
    realworld_db_path: Path | str | None = None,
    journal_path: Path | str | None = None,
    now: datetime | None = None,
    review_id: str | None = None,
    max_retries: int = 1,
) -> ReviewRunResult:
    provider = provider or _default_provider()
    ri = review_input if review_input is not None else gather_review_input(d, mode)
    now = now or datetime.now()
    review_id = review_id or _gen_review_id(ri, now)
    journal_path = Path(journal_path) if journal_path is not None else JOURNAL_PATH
    base_prompt = build_prompt(ri)

    failures: list = []
    result: V.ValidationResult | None = None
    raw = ""
    attempt = 0
    while True:
        prompt = base_prompt if attempt == 0 else base_prompt + _retry_suffix(failures)
        raw = provider.classify(prompt)
        parsed = _parse_json(raw)
        if parsed is None:
            failures = ["json: output was not a valid JSON object"]
            result = None
            if attempt < max_retries:
                attempt += 1
                continue
            break
        result = V.validate(parsed, ri.context)
        if result.result in ("passed", "partial"):
            break
        failures = _collect_failures(result)
        if attempt < max_retries and _is_retryable(failures):
            attempt += 1
            continue
        break

    if result is None:
        validator_result = "failed"
        accepted: tuple = ()
        observations: tuple = ()
        n_rejected = 0
    else:
        validator_result = result.result
        accepted = result.accepted
        observations = result.observations
        failures = _collect_failures(result)
        n_rejected = sum(1 for v in result.verdicts if not v.accepted)

    # --- persist: audit ALWAYS, hypotheses only when accepted ---
    db_path = (Path(realworld_db_path) if realworld_db_path is not None
               else realworld_db.DEFAULT_DB_PATH)
    conn = realworld_db.connect(db_path)
    try:
        realworld_db.insert_audit(
            conn,
            review_id=review_id,
            run_at=now,
            mode=mode,
            trigger=trigger,
            input_snapshot_hash=ri.input_snapshot_hash,
            prompt_version=PROMPT_VERSION,
            model_id=getattr(provider, "model_id", "unknown"),
            output_json=raw,
            validator_version=V.VALIDATOR_VERSION,
            validator_result=validator_result,
            validator_failures_json=json.dumps(failures),
            n_realized_trades=ri.n_realized_trades,
            safety_state=ri.safety_state,
            cold_start=ri.cold_start,
        )
        for i, h in enumerate(accepted):
            realworld_db.insert_hypothesis(
                conn,
                hypothesis_id=f"{review_id}-h{i}",
                review_id=review_id,
                created_at=now,
                mode=mode,
                category=h["category"],
                confidence=h["confidence"],
                text=h["text"],
                causal_story=h["causal_story"],
                predeclared_test=h["predeclared_test"],
                supporting_evidence_json=json.dumps(h["supporting_evidence_ids"]),
                text_lexical_hash=h["text_lexical_hash"],
            )
    finally:
        conn.close()

    _append_journal(
        journal_path, d=d, review_id=review_id, mode=mode, ri=ri,
        validator_result=validator_result, accepted=accepted,
        failures=failures, observations=observations,
    )

    return ReviewRunResult(
        review_id=review_id,
        validator_result=validator_result,
        cold_start=ri.cold_start,
        n_accepted=len(accepted),
        n_rejected=n_rejected,
        observations=observations,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the monthly LLM review (read-only).")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--mode", default="dhan-paper")
    ap.add_argument("--trigger", default="manual",
                    choices=["monthly", "event_triggered", "manual"])
    args = ap.parse_args()
    d = date.fromisoformat(args.date)
    res = run_review(d=d, mode=args.mode, trigger=args.trigger)
    print(f"[realworld_review] {res.review_id} result={res.validator_result} "
          f"cold_start={res.cold_start} accepted={res.n_accepted} "
          f"rejected={res.n_rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
