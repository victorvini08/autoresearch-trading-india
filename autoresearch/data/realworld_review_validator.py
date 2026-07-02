"""Deterministic policy validator for the monthly LLM review (Step 4.b).

THIS is the control surface. The review prompt ("your default is NO CHANGE,
your sample is too small...") is documentation the model can ignore; this
module is plain code it cannot argue with. A pure function: it takes the LLM's
parsed output and a `ReviewContext` of independently-rederived ground truth,
and returns which hypotheses survive.

The one principle that makes it trustworthy: the validator NEVER trusts the
LLM's self-report of a checkable fact. The trade count, the safety state, the
set of real evidence ids, and the burned-hypothesis hashes are all supplied by
the caller from the data layer — so the model cannot lie about N, claim NORMAL
state, cite a trade that never happened, or re-propose a killed idea to slip a
hypothesis through.

Six content gates, in order:
  1. schema        — required fields present, enums in range
  2. cold-start    — N < COLD_START_MIN_TRADES => no hypotheses (observations ok)
  3. drawdown      — safety_state != NORMAL => only category=risk_off
  4. causal-citation — supporting_evidence_ids non-empty AND ⊆ real evidence ids
  5. falsifiability  — a non-placeholder predeclared_test
  6. duplicate     — computed lexical hash not in the burned set

Provenance (input hash / prompt / model / timestamp) is NOT a gate here — it
is owned by the runner and enforced structurally by the audit table's NOT NULL
columns. Validating an LLM-supplied provenance block would be theatre.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

VALIDATOR_VERSION = "v1"

# Lowered from the spec's 30 to 10 (explicit user decision): at ~5-6 closed
# round-trips/month this is ~7-8 weeks. 10 is statistically weak, but the
# cold-start gate is not the real protection — a PENDING hypothesis still has
# to clear Step 5's full anti-overfit suite + a fresh sealed reveal before it
# touches strategy.py. N here counts DISTINCT CLOSED ROUND-TRIPS (the runner's
# job), not raw FIFO lot-rows.
COLD_START_MIN_TRADES = 10

_REQUIRED_FIELDS = (
    "id", "text", "category", "confidence",
    "supporting_evidence_ids", "causal_story", "predeclared_test",
)
_CATEGORIES = frozenset(
    {"risk_off", "signal", "hyperparameter", "cost", "execution", "data_bug"}
)
_CONFIDENCE = frozenset({"low", "medium", "high"})
# Weak proxy against placeholder "tests" (TODO / n/a / -). Real runnability is
# verified by Step 5, which actually executes the test against the backtest.
_MIN_PREDECLARED_TEST_LEN = 15
_PLACEHOLDER_TESTS = frozenset({"todo", "tbd", "n/a", "na", "none", "-", "."})


@dataclass(frozen=True)
class ReviewContext:
    """Ground truth the validator re-derives independently of the LLM."""
    n_realized_trades: int
    safety_state: str
    valid_evidence_ids: frozenset
    burned_hashes: frozenset


@dataclass(frozen=True)
class HypothesisVerdict:
    hypothesis: dict
    accepted: bool
    rejection_reasons: tuple
    text_lexical_hash: str


@dataclass(frozen=True)
class ValidationResult:
    result: str                       # "passed" | "failed" | "partial"
    accepted: tuple                   # hypotheses that cleared every gate
    verdicts: tuple                   # one HypothesisVerdict per hypothesis
    output_errors: tuple              # top-level/structural errors
    observations: tuple               # passthrough observations


def lexical_hash(text: str) -> str:
    """Stable hash of normalized hypothesis text (case/whitespace/punctuation
    insensitive) so near-identical re-proposals collide. Embedding-similarity
    for non-lexical paraphrases is a later phase."""
    norm = re.sub(r"[^a-z0-9 ]", " ", str(text).lower())
    norm = " ".join(norm.split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _schema_errors(h: dict) -> list:
    errs = []
    for f in _REQUIRED_FIELDS:
        if f not in h:
            errs.append(f"schema: missing field '{f}'")
    if errs:
        return errs  # can't validate types/enums on missing fields
    if not isinstance(h.get("text"), str) or not h["text"].strip():
        errs.append("schema: 'text' must be a non-empty string")
    if h.get("category") not in _CATEGORIES:
        errs.append(f"schema: 'category' not in {sorted(_CATEGORIES)}")
    if h.get("confidence") not in _CONFIDENCE:
        errs.append(f"schema: 'confidence' not in {sorted(_CONFIDENCE)}")
    if not isinstance(h.get("supporting_evidence_ids"), list):
        errs.append("schema: 'supporting_evidence_ids' must be a list")
    if not isinstance(h.get("causal_story"), str) or not h["causal_story"].strip():
        errs.append("schema: 'causal_story' must be a non-empty string")
    if not isinstance(h.get("predeclared_test"), str):
        errs.append("schema: 'predeclared_test' must be a string")
    return errs


def _content_reasons(h: dict, ctx: ReviewContext) -> list:
    """Gates 2-6, assuming schema already passed. Collects ALL reasons so a
    retry sees everything wrong at once."""
    reasons = []

    # Gate 2 — cold start.
    if ctx.n_realized_trades < COLD_START_MIN_TRADES:
        reasons.append(
            f"cold_start: only {ctx.n_realized_trades} closed round-trips "
            f"(< {COLD_START_MIN_TRADES}); hypothesis generation suppressed"
        )

    # Gate 3 — drawdown.
    if ctx.safety_state != "NORMAL" and h["category"] != "risk_off":
        reasons.append(
            f"drawdown_gate: safety_state={ctx.safety_state} permits only "
            f"category=risk_off, got '{h['category']}'"
        )

    # Gate 4 — causal citation.
    ids = h["supporting_evidence_ids"]
    if not ids:
        reasons.append("citation: supporting_evidence_ids is empty")
    else:
        unknown = [i for i in ids if i not in ctx.valid_evidence_ids]
        if unknown:
            reasons.append(f"citation: unknown evidence ids {unknown}")

    # Gate 5 — falsifiability.
    test = h["predeclared_test"].strip()
    if (not test or test.lower() in _PLACEHOLDER_TESTS
            or len(test) < _MIN_PREDECLARED_TEST_LEN):
        reasons.append("falsifiability: predeclared_test missing or placeholder")

    # Gate 6 — duplicate.
    if lexical_hash(h["text"]) in ctx.burned_hashes:
        reasons.append("duplicate: matches a previously-burned hypothesis")

    return reasons


def validate(output: dict, context: ReviewContext) -> ValidationResult:
    # Top-level schema.
    output_errors = []
    if not isinstance(output, dict):
        output_errors.append("schema: output is not a JSON object")
    else:
        if "observations" not in output:
            output_errors.append("schema: missing 'observations'")
        elif not isinstance(output["observations"], list):
            output_errors.append("schema: 'observations' must be a list")
        if "hypotheses" not in output:
            output_errors.append("schema: missing 'hypotheses'")
        elif not isinstance(output["hypotheses"], list):
            output_errors.append("schema: 'hypotheses' must be a list")
    if output_errors:
        return ValidationResult(
            result="failed", accepted=(), verdicts=(),
            output_errors=tuple(output_errors), observations=(),
        )

    observations = tuple(str(o) for o in output.get("observations", []))
    hyps = output.get("hypotheses", [])

    verdicts = []
    accepted = []
    for h in hyps:
        if not isinstance(h, dict):
            verdicts.append(HypothesisVerdict(
                hypothesis=h, accepted=False,
                rejection_reasons=("schema: hypothesis is not an object",),
                text_lexical_hash=""))
            continue
        schema_errs = _schema_errors(h)
        if schema_errs:
            verdicts.append(HypothesisVerdict(
                hypothesis=h, accepted=False,
                rejection_reasons=tuple(schema_errs),
                text_lexical_hash=lexical_hash(h.get("text", ""))))
            continue
        reasons = _content_reasons(h, context)
        h_hash = lexical_hash(h["text"])
        if reasons:
            verdicts.append(HypothesisVerdict(
                hypothesis=h, accepted=False,
                rejection_reasons=tuple(reasons), text_lexical_hash=h_hash))
        else:
            enriched = {**h, "text_lexical_hash": h_hash}
            verdicts.append(HypothesisVerdict(
                hypothesis=enriched, accepted=True,
                rejection_reasons=(), text_lexical_hash=h_hash))
            accepted.append(enriched)

    n_hyp = len(hyps)
    n_acc = len(accepted)
    if n_hyp == 0 or n_acc == n_hyp:
        result = "passed"
    elif n_acc == 0:
        result = "failed"
    else:
        result = "partial"

    return ValidationResult(
        result=result, accepted=tuple(accepted), verdicts=tuple(verdicts),
        output_errors=(), observations=observations,
    )
