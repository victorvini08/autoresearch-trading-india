"""Autoresearch loop — single iteration.

One run does:
  1. Read program.md, journal.md (last 20 hypotheses), strategy.py.
  2. Build a prompt asking the LLM for ONE strategy edit + a hypothesis.
  3. Validate the proposed strategy.py (AST, structure, allowlisted imports).
  4. Apply the edit, run prepare.py research, parse metrics.
  5. Compare to the last accepted iteration's validation Sortino.
  6. Keep (commit strategy.py + journal.md) or revert (commit journal only).

Run as:
    uv run python scripts/loop.py                       # one iteration
    uv run python scripts/loop.py --provider claude     # explicit provider
    uv run python scripts/loop.py --provider codex      # alternative provider

Designed to be invoked repeatedly by run_overnight.py.
"""
from __future__ import annotations

import argparse
import ast
import csv
import importlib
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_PATH = REPO_ROOT / "strategy.py"
PROGRAM_PATH = REPO_ROOT / "program.md"
JOURNAL_PATH = REPO_ROOT / "journal.md"
ITER_DIR = REPO_ROOT / "iterations"
ITER_LOG_PATH = ITER_DIR / "log.csv"
ITER_LOG_FIELDS = [
    "iteration_id", "timestamp", "decision",
    "sortino", "calmar", "trade_count", "risk_passed",
    "hypothesis", "reason",
]

# Bound disk usage: keep trade-level CSVs only for the most recent N
# iterations. log.csv is kept forever (one row per iteration ≈ 200 bytes,
# negligible) so the Sortino-over-iterations signal survives across the
# whole project's life. Old iterations still appear in the dashboard
# slider; their drill-down panel just shows "trade detail pruned".
MAX_TRADE_HISTORY = 50

# Make root-level modules (strategy.py, prepare.py) importable when this
# script is run as `uv run python scripts/loop.py`.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm.provider import ClaudeCodeProvider, CodexProvider, Provider  # noqa: E402
from scripts._dashboard import render_dashboard  # noqa: E402

# Modules a generated strategy.py is allowed to import. Any module not on this
# list is rejected — we don't want the agent reaching for the network or the
# filesystem.
ALLOWED_IMPORT_PREFIXES = (
    "backtrader",
    "math",
    "numpy",
    "pandas",
    "datetime",
    "data.",
    "llm.features",
    "__future__",
)

RECENT_ATTEMPTS_N = 20


# ---------------------------------------------------------------------------
# Task 4: novelty signal — recent attempts WITH outcomes (not just hypothesis
# text). Reads from iterations/log.csv instead of regex-parsing journal.md
# because the CSV is already structured.
# ---------------------------------------------------------------------------


def recent_attempts(n: int = RECENT_ATTEMPTS_N) -> list[dict]:
    """Return the last `n` rows of iterations/log.csv as dicts. Each dict
    has at least: iteration_id, decision, sortino, hypothesis. Empty list
    if the log file doesn't exist yet (first run)."""
    if not ITER_LOG_PATH.exists():
        return []
    with ITER_LOG_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[-n:]


def _format_attempt(a: dict) -> str:
    """Render one attempt as: `- [DECISION, sortino=X.XXX]: "hypothesis"`.

    Sortino omitted for REJECTED iterations (prepare.py never ran).
    """
    decision = a.get("decision", "?") or "?"
    sortino_raw = a.get("sortino", "") or ""
    bracket = decision
    if sortino_raw:
        try:
            bracket = f"{decision}, sortino={float(sortino_raw):.3f}"
        except (TypeError, ValueError):
            pass
    hyp = (a.get("hypothesis", "") or "")[:220]
    return f'- [{bracket}]: "{hyp}"'


# ---------------------------------------------------------------------------
# Task 3: edit-quality validator — reject malformed strategy.py before running
# ---------------------------------------------------------------------------


def validate_strategy_edit(
    text: str, current_text: str | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason). On True, reason == 'ok'.

    If `current_text` is provided, also rejects no-op edits — proposals whose
    AST is semantically identical to the current strategy.py (modulo comments,
    docstrings, and whitespace). Observed on mean-reversion-aryan: 4 reverted
    iters had `validation_sortino_mean` exactly equal to the prior KEPT,
    meaning the agent added unused params or dead code that didn't change
    runtime behavior. Each wasted ~25s of evaluation; pre-rejecting saves
    that time and gives the agent immediate feedback to try something else.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return False, f"syntax error: {e.msg} (line {e.lineno})"

    strategy_classes: list[ast.ClassDef] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if (
                    isinstance(base, ast.Attribute)
                    and base.attr == "Strategy"
                    and isinstance(base.value, ast.Name)
                    and base.value.id == "bt"
                ):
                    strategy_classes.append(node)

    if len(strategy_classes) == 0:
        return False, "no bt.Strategy subclass defined"
    if len(strategy_classes) > 1:
        names = [c.name for c in strategy_classes]
        return False, f"multiple bt.Strategy subclasses: {names}"

    cls = strategy_classes[0]
    method_names = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    if "next" not in method_names:
        return False, f"{cls.name} missing required `next` method"

    for node in tree.body:
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                return False, "relative import not allowed"
            modules = [node.module]
        for mod in modules:
            if not any(
                mod == prefix.rstrip(".") or mod.startswith(prefix)
                for prefix in ALLOWED_IMPORT_PREFIXES
            ):
                return False, f"disallowed import: {mod}"

    if current_text is not None and current_text.strip():
        try:
            current_tree = ast.parse(current_text)
            if (
                ast.dump(tree, include_attributes=False)
                == ast.dump(current_tree, include_attributes=False)
            ):
                return (
                    False,
                    "no-op edit: strategy.py AST is identical to HEAD "
                    "(comments/whitespace ignored). Propose a change that "
                    "alters strategy behavior.",
                )
        except SyntaxError:
            pass  # current is broken; don't block the edit on that

    return True, "ok"


# ---------------------------------------------------------------------------
# LLM round-trip — build prompt, call provider, parse JSON response
# ---------------------------------------------------------------------------


_PROMPT_TEMPLATE = """\
You are the autoresearch agent for a swing-trading strategy on US stocks.

Your goal: propose ONE concrete change to strategy.py that you believe will
improve the mean validation Sortino across walk-forward folds. You must NOT
modify any file other than strategy.py — the evaluator (prepare.py) is
immutable infrastructure.

You may use ONLY these imports:
  backtrader, math, numpy, pandas, datetime, __future__,
  data.* (price/macro/news ingest), llm.features (macro_regime, sentiment,
  events, news_volume).

The strategy class must be a single subclass of bt.Strategy and define
__init__ and next.

============================================================================
PROGRAM (the spec — read-only):
============================================================================
{program}

============================================================================
JOURNAL (your past attempts — append-only):
============================================================================
{journal_tail}

============================================================================
RECENT ATTEMPTS (last {n_attempts} iterations and how they scored):
============================================================================
{recent_attempts}

GUIDANCE on novelty: avoid TRIVIAL repeats of these. If you DO want to
revisit a previously-tried idea, your hypothesis MUST explicitly state
what's different now — a new combination with another idea, a fix that
addresses why the prior attempt failed, or a parameter regime that wasn't
explored. A bare repeat of a REVERTED idea (e.g. "tighten trailing stop
again, no other change") is wasted and will likely revert again.

============================================================================
CURRENT strategy.py:
============================================================================
{strategy}

============================================================================

Respond with STRICT JSON, no surrounding prose, no markdown fences:

{{
  "hypothesis": "one sentence stating the testable claim",
  "change_summary": "one sentence describing what you changed and why",
  "new_strategy_py": "the complete new strategy.py file as a string"
}}
"""


def build_prompt(
    program: str, journal: str, strategy_text: str, attempts: list[dict],
) -> str:
    journal_tail = journal[-8000:] if len(journal) > 8000 else journal
    if attempts:
        rendered = "\n".join(_format_attempt(a) for a in attempts)
    else:
        rendered = "(none yet — this is the first iteration)"
    return _PROMPT_TEMPLATE.format(
        program=program,
        journal_tail=journal_tail,
        recent_attempts=rendered,
        n_attempts=len(attempts) or 0,
        strategy=strategy_text,
    )


def _extract_json_obj(text: str) -> dict | None:
    """Best-effort JSON extraction from possibly-wrapped LLM output."""
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidates.insert(0, fence.group(1))
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        candidates.append(obj.group())
    for c in candidates:
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _coerce_valid_python(code: str) -> str:
    """Repair LLM-double-escaped code (2026-05-15 root cause).

    Codex sometimes emits its JSON with the strategy source double-escaped,
    so `new_strategy_py` arrives with literal two-char `\\n` / `\\t` / `\\"`
    instead of real newlines — written verbatim it's a line-1 SyntaxError
    and the iteration is wasted on a false reject. If the code as-received
    does NOT parse but its unicode_escape-decoded form DOES, use the decoded
    form. The dual guard (original invalid AND decoded valid) makes this
    safe — legitimate code is never altered.
    """
    try:
        ast.parse(code)
        return code
    except SyntaxError:
        pass
    try:
        decoded = code.encode("utf-8", "ignore").decode("unicode_escape")
        ast.parse(decoded)
        return decoded
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return code  # unrecoverable → validate_strategy_edit rejects cleanly


# ---------------------------------------------------------------------------
# prepare.py invocation — run as subprocess, parse JSON output
# ---------------------------------------------------------------------------


def evaluate_anti_overfit_gates(
    metrics: dict,
    *,
    iter_id: str,
    baseline_sortino: float | None,
    n_active_variants: int,
    baseline_hyperparams: int,
):
    """Build a StrategySummary from the immutable evaluator's anti_overfit
    block and run the full non-sealed gate suite (sealed reveal stays a
    human/promotion step). Returns (GateRun, one_line_reason).

    The sealed reveal is intentionally skipped here — the nightly research
    loop must NEVER touch the sealed 2025→2026 window; that is revealed once
    at the human promotion gate (CLAUDE.md hard constraint §9).
    """
    from backtest.anti_overfit import StrategySummary, run_all_gates

    ao = (metrics or {}).get("anti_overfit") or {}
    val_mean = float(ao.get("sortino_val_mean", 0.0))
    summary = StrategySummary(
        iter_id=iter_id,
        sortino_train_mean=val_mean,            # no separate train step here
        sortino_val_mean=val_mean,
        sortino_val_pvalue=float(ao.get("sortino_val_pvalue", 1.0)),
        aggregate_dd=float(ao.get("aggregate_dd", 0.0)),
        n_trades=int(ao.get("n_trades", 0)),
        n_hyperparameters=int(ao.get("n_hyperparameters", 0)),
        sub_period_sortinos=tuple(ao.get("sub_period_sortinos", []) or ()),
        rw_mc_null_pct=float(ao.get("rw_mc_null_pct", 0.0)),
        universe_respected=bool(ao.get("universe_respected", True)),
    )
    gate_run = run_all_gates(
        summary,
        baseline_sortino if baseline_sortino is not None else 0.0,
        n_active_variants,
        baseline_hyperparams=baseline_hyperparams,
        skip_sealed=True,
    )
    failed = [g for g in gate_run.results if not g.passed]
    reason = (
        "anti-overfit gates passed"
        if gate_run.passed
        else "anti-overfit FAILED: "
        + " · ".join(f"{g.name}({g.reason})" for g in failed)
    )
    return gate_run, reason


def run_prepare_research() -> dict:
    """Run prepare.evaluate() in-process. Reloads strategy + prepare modules
    so each iteration's edited strategy.py takes effect.

    Returns the full result dict including `all_trades` (DataFrame) — needed
    so we can persist per-iteration trades for the dashboard.
    """
    for mod_name in ("strategy", "prepare"):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
    import prepare
    import strategy
    return prepare.evaluate(strategy, mode="research")


def _prune_old_trade_dirs(keep: int = MAX_TRADE_HISTORY) -> None:
    """Remove iteration trade subdirs older than the most recent `keep`
    entries in iterations/log.csv. log.csv itself is never touched.
    """
    if not ITER_LOG_PATH.exists() or not ITER_DIR.exists():
        return
    try:
        with ITER_LOG_PATH.open(newline="") as f:
            rows = list(csv.DictReader(f))
        # Tolerate a stale/foreign header schema — housekeeping must NEVER
        # abort an iteration (this KeyError'd the whole loop on 2026-05-15).
        recent_ids = {
            (r.get("iteration_id") or r.get("iter_id") or "")
            for r in rows[-keep:]
        }
    except Exception as e:  # noqa: BLE001 — pure housekeeping, never fatal
        print(f"[loop] _prune_old_trade_dirs skipped (non-fatal): {e}",
              flush=True)
        return
    for p in ITER_DIR.iterdir():
        if not p.is_dir() or p.name in recent_ids:
            continue
        for child in p.iterdir():
            child.unlink()
        p.rmdir()


def persist_iteration(
    iteration_id: str, decision: str, hypothesis: str, metrics: dict | None,
    reason: str = "",
) -> None:
    """Save per-iteration artifacts:
      - iterations/<id>/trades.csv (full trade list across all folds)
      - append a row to iterations/log.csv
      - regenerate iterations/dashboard.html

    `metrics` may be None for REJECTED iterations where prepare.py never ran;
    we still write a log row so the dashboard sees the iteration.

    `reason` is the human-readable explanation of the decision (e.g.
    "sortino 0.42 did not improve on prev 0.55" or "calmar -1.12 < 0.7").
    Persisted to log.csv so the dashboard can surface it without re-parsing
    journal.md.
    """
    ITER_DIR.mkdir(parents=True, exist_ok=True)

    trade_count = 0
    sortino = ""
    calmar = ""
    risk_passed = ""
    if metrics is not None:
        sortino = metrics.get("validation_sortino_mean", "")
        side = metrics.get("side_panel", {}) or {}
        calmar = side.get("calmar_mean", "")
        trade_count = int(side.get("trade_count_total", 0) or 0)
        risk_passed = bool(metrics.get("risk", {}).get("passed", False))

        trades = metrics.get("all_trades")
        if trades is not None and len(trades) > 0:
            iter_subdir = ITER_DIR / iteration_id
            iter_subdir.mkdir(parents=True, exist_ok=True)
            trades.to_csv(iter_subdir / "trades.csv", index=False)

    # Append one row to iterations/log.csv
    # Self-heal a stale/foreign header. A committed log.csv with a different
    # column schema made DictWriter append misaligned rows and DictReader
    # crash _prune (2026-05-15). If the on-disk header != ITER_LOG_FIELDS,
    # rotate it aside and start a correctly-headed file.
    is_new_log = not ITER_LOG_PATH.exists()
    if not is_new_log:
        try:
            with ITER_LOG_PATH.open(newline="") as f:
                hdr = (f.readline().strip().split(",")
                       if f else [])
            if hdr != ITER_LOG_FIELDS:
                bak = ITER_LOG_PATH.with_suffix(
                    f".csv.bak-{datetime.now():%Y%m%d%H%M%S}")
                ITER_LOG_PATH.rename(bak)
                print(f"[loop] iterations/log.csv had a stale header; "
                      f"rotated to {bak.name}, starting fresh", flush=True)
                is_new_log = True
        except Exception as e:  # noqa: BLE001 — never fatal
            print(f"[loop] log.csv header check skipped: {e}", flush=True)
    with ITER_LOG_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ITER_LOG_FIELDS)
        if is_new_log:
            writer.writeheader()
        writer.writerow({
            "iteration_id": iteration_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "decision": decision,
            "sortino": sortino,
            "calmar": calmar,
            "trade_count": trade_count,
            "risk_passed": risk_passed,
            "hypothesis": (hypothesis or "")[:300],
            "reason": (reason or "")[:500],
        })

    # Bound disk: drop trade CSVs for iterations beyond the retention window.
    _prune_old_trade_dirs()

    # Regenerate the HTML dashboard so the slider sees this run immediately.
    render_dashboard(REPO_ROOT)


# ---------------------------------------------------------------------------
# Journal — read last accepted Sortino, append entry
# ---------------------------------------------------------------------------


def last_accepted_sortino(journal_text: str) -> float | None:
    """Return the most recent ACCEPTED iteration's validation_sortino_mean.

    An accepted entry is one whose body contains the literal token 'KEPT'
    (we mark accepted entries explicitly when we journal them).
    """
    return _last_accepted_value(journal_text, "validation_sortino_mean")


def last_accepted_aggregate_dd(journal_text: str) -> float | None:
    """Return the most recent ACCEPTED iteration's aggregate_max_dd.

    Used by the KEPT criterion's DD-regression guard: a new iteration that
    improves Sortino but balloons aggregate drawdown by >10pp gets reverted.
    Returns None for the first KEPT iteration (no comparison possible).
    """
    return _last_accepted_value(journal_text, "aggregate_max_dd")


def _last_accepted_value(journal_text: str, key: str) -> float | None:
    """Walk journal blocks newest-first and return the named metric from the
    most recent KEPT iteration.

    The KEPT check looks for the literal `**Decision:** KEPT` line that the
    loop writes — NOT a substring match for "KEPT". A REVERTED iteration's
    hypothesis text frequently mentions prior KEPT iters (e.g.
    "the only KEPT iteration so far was…"), and a substring check there
    falsely promotes a REVERTED block, causing the loop to compare against
    a worse Sortino baseline and silently regress. Observed on
    mean-reversion-aryan: 1.018 baseline lost when a REVERTED iter's
    hypothesis mentioning "KEPT iteration" got parsed as KEPT, resetting
    the baseline to 0.886.
    """
    pattern = re.compile(
        rf"{re.escape(key)}[:\s]+([-+]?\d+\.?\d*)",
    )
    blocks = re.split(r"\n## ", journal_text)
    for block in reversed(blocks):
        if "**Decision:** KEPT" not in block:
            continue
        m = pattern.search(block)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _format_pct(value: object) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "n/a"


def learning_summary(
    decision: str,
    reason: str,
    metrics: dict | None,
    previous_sortino: float | None = None,
    previous_aggregate_dd: float | None = None,
) -> str:
    """Summarize what this iteration teaches future runs.

    This is intentionally deterministic. The loop should never lose the
    post-run lesson because a second model call failed, timed out, or wandered
    into speculative advice. The summary is small, but it gives the next prompt
    a compressed conclusion rather than another blank journal section.
    """
    if metrics is None:
        return (
            "No scored strategy inference: the iteration failed before "
            f"prepare.py produced validation metrics. Treat this as an "
            f"implementation failure, not evidence about the hypothesis. "
            f"Failure reason: {reason}."
        )

    side = metrics.get("side_panel", {}) or {}
    signals = metrics.get("risk_signals", {}) or {}
    risk = metrics.get("risk", {}) or {}

    new_sortino_raw = metrics.get("validation_sortino_mean")
    try:
        new_sortino = float(new_sortino_raw)
    except (TypeError, ValueError):
        new_sortino = None

    if new_sortino is not None and previous_sortino is not None:
        delta_text = f"{new_sortino - previous_sortino:+.3f}"
        comparison = (
            f"Sortino changed from {previous_sortino:.3f} to "
            f"{new_sortino:.3f} ({delta_text})."
        )
    elif new_sortino is not None:
        comparison = f"Sortino scored {new_sortino:.3f} with no prior kept baseline."
    else:
        comparison = "Sortino was not available from the evaluator output."

    agg_dd = signals.get("aggregate_max_dd")
    if agg_dd is not None and previous_aggregate_dd is not None:
        risk_context = (
            f"Aggregate DD was {_format_pct(agg_dd)} versus previous kept "
            f"{_format_pct(previous_aggregate_dd)}; "
            f"negative folds were {signals.get('n_negative_folds')}/"
            f"{signals.get('n_folds')}; trades={side.get('trade_count_total')}."
        )
    else:
        risk_context = (
            f"Aggregate DD was {_format_pct(agg_dd)}; negative folds were "
            f"{signals.get('n_negative_folds')}/{signals.get('n_folds')}; "
            f"trades={side.get('trade_count_total')}."
        )

    if decision == "KEPT":
        conclusion = (
            "Keep compounding on this change, but future iterations should "
            "still explain whether the gain came from better return, lower "
            "downside, or fewer fragile folds."
        )
    elif not risk.get("passed", True):
        conclusion = (
            "Do not reuse this exact setup: it failed the catastrophe gate, "
            "so the result is not a usable edge even if the hypothesis was "
            "economically plausible."
        )
    else:
        conclusion = (
            "Do not repeat this exact idea without a materially different "
            "mechanism; the keep gate rejected it for the stated reason."
        )

    return f"{comparison} {risk_context} {conclusion} Decision reason: {reason}."


def journal_entry(
    iteration_id: str,
    hypothesis: str,
    change_summary: str,
    decision: str,           # "KEPT" | "REVERTED" | "REJECTED"
    reason: str,             # one-line explanation
    metrics: dict | None,    # may be None if we never ran prepare
    learning: str | None = None,
) -> str:
    parts = [
        f"\n## Iteration {iteration_id} — {decision}",
        "",
        f"**Hypothesis:** {hypothesis}",
        "",
        f"**Change:** {change_summary}",
        "",
        f"**Decision:** {decision} — {reason}",
        "",
    ]
    if metrics is not None:
        side = metrics.get("side_panel", {})
        risk = metrics.get("risk", {})
        signals = metrics.get("risk_signals", {})
        parts += [
            "**Result:**",
            f"- validation_sortino_mean: {metrics.get('validation_sortino_mean')}",
            f"- validation_folds: {metrics.get('validation_folds')}",
            f"- per_fold_sortinos: {metrics.get('per_fold_sortinos')}",
            f"- calmar_mean: {side.get('calmar_mean')}",
            f"- hit_rate_mean: {side.get('hit_rate_mean')}",
            f"- profit_factor_mean: {side.get('profit_factor_mean')}",
            f"- trade_count_total: {side.get('trade_count_total')}",
            f"- aggregate_max_dd: {signals.get('aggregate_max_dd')}",
            f"- worst_fold_max_dd: {signals.get('worst_fold_max_dd')}",
            f"- max_position_frac_peak: {signals.get('max_position_frac_peak')}",
            f"- lower_quartile_fold_calmar: {signals.get('lower_quartile_fold_calmar')}",
            f"- n_negative_folds: {signals.get('n_negative_folds')}/"
            f"{signals.get('n_folds')}",
            f"- risk.passed: {risk.get('passed')}",
            f"- risk.violations: {risk.get('violations')}",
            "",
        ]
    if learning is None:
        learning = learning_summary(decision, reason, metrics)
    parts += ["**Learning:** " + learning, "", "---"]
    return "\n".join(parts) + "\n"


def append_journal(text: str) -> None:
    with JOURNAL_PATH.open("a") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=check,
    )


def commit_kept(iteration_id: str, summary: str) -> None:
    _git("add", "strategy.py", "journal.md")
    _git("commit", "-m", f"iter {iteration_id}: {summary}")


def commit_reverted(iteration_id: str, reason: str) -> None:
    _git("checkout", "--", "strategy.py")
    _git("add", "journal.md")
    _git("commit", "-m", f"iter {iteration_id} reverted: {reason}")




# ---------------------------------------------------------------------------
# Main one-shot iteration
# ---------------------------------------------------------------------------


def make_provider(name: str) -> Provider:
    if name == "claude":
        # Opus for the meta-coder loop driver per CLAUDE.md tiering.
        return ClaudeCodeProvider(model="claude-opus-4-7")
    if name == "codex":
        return CodexProvider()
    raise ValueError(f"unknown provider {name!r}; expected claude|codex")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=["claude", "codex"], default="claude")
    p.add_argument(
        "--iteration-id",
        default=date.today().isoformat() + "-" + subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
        ).decode().strip(),
        help="Identifier written into the journal entry for this iteration.",
    )
    args = p.parse_args(argv)

    program = PROGRAM_PATH.read_text()
    journal = JOURNAL_PATH.read_text()
    strategy_text = STRATEGY_PATH.read_text()
    attempts = recent_attempts()

    # Parsimony baseline = hyperparameter count of the CURRENTLY COMMITTED
    # strategy (this iteration's starting point), captured BEFORE the edit is
    # applied. The parsimony gate then penalises only knobs the variant ADDS.
    try:
        import prepare as _prep
        import strategy as _cur_strat
        importlib.reload(_cur_strat)
        baseline_hyperparams = _prep.count_hyperparameters(
            _prep._find_strategy_class(_cur_strat)
        )
    except Exception:  # noqa: BLE001 — fall back to spec baseline
        from backtest.anti_overfit import BASELINE_HYPERPARAMS
        baseline_hyperparams = BASELINE_HYPERPARAMS

    print(f"[loop {args.iteration_id}] provider={args.provider}, "
          f"recent_attempts={len(attempts)}", flush=True)

    provider = make_provider(args.provider)
    prompt = build_prompt(program, journal, strategy_text, attempts)
    raw = provider.classify(prompt, timeout=600)
    parsed = _extract_json_obj(raw)
    if parsed is None or not all(
        k in parsed for k in ("hypothesis", "change_summary", "new_strategy_py")
    ):
        hyp = "(LLM response did not parse)"
        append_journal(journal_entry(
            args.iteration_id, hypothesis=hyp, change_summary="-",
            decision="REJECTED",
            reason=f"unparseable LLM output: {raw[:300]!r}",
            metrics=None,
        ))
        persist_iteration(
            args.iteration_id, "REJECTED", hyp, None,
            reason="unparseable LLM output",
        )
        commit_reverted(args.iteration_id, "unparseable LLM output")
        print("[loop] REJECTED: unparseable LLM output")
        return 2

    new_text = _coerce_valid_python(parsed["new_strategy_py"])
    ok, why = validate_strategy_edit(new_text, current_text=strategy_text)
    if not ok:
        append_journal(journal_entry(
            args.iteration_id,
            hypothesis=parsed["hypothesis"],
            change_summary=parsed["change_summary"],
            decision="REJECTED",
            reason=f"validation failed: {why}",
            metrics=None,
        ))
        persist_iteration(
            args.iteration_id, "REJECTED", parsed["hypothesis"], None,
            reason=f"invalid edit: {why}",
        )
        commit_reverted(args.iteration_id, f"invalid edit: {why}")
        print(f"[loop] REJECTED: {why}")
        return 2

    STRATEGY_PATH.write_text(new_text)
    try:
        metrics = run_prepare_research()
    except Exception as e:  # noqa: BLE001 — strategy bugs surface here
        append_journal(journal_entry(
            args.iteration_id,
            hypothesis=parsed["hypothesis"],
            change_summary=parsed["change_summary"],
            decision="REJECTED",
            reason=f"prepare.py crashed: {e}",
            metrics=None,
        ))
        persist_iteration(
            args.iteration_id, "REJECTED", parsed["hypothesis"], None,
            reason=f"prepare.py crashed: {e}",
        )
        commit_reverted(args.iteration_id, "prepare.py crashed")
        print(f"[loop] REJECTED: prepare.py crashed: {e}")
        return 2

    # KEPT criterion (multi-dimensional but Sortino-led):
    #   1. catastrophe gate passed (>100% gross / >50% agg DD / <20 trades fail)
    #   2. Sortino improved over previous KEPT
    #   3. Sortino > 0 — don't compound on a negative-edge baseline
    #   4. |Sortino| < 10 — extreme values are numerical artifacts (we saw -142
    #      and +90 outliers from low-trade-count folds before the dstd floor)
    #   5. aggregate_max_dd didn't regress >10pp vs previous KEPT — prevents
    #      "trade 15pp of DD for 0.05 of Sortino" local-max gaming. Skipped on
    #      the first KEPT (no prior baseline).
    new_sortino = float(metrics.get("validation_sortino_mean", 0.0))
    risk_passed = bool(metrics.get("risk", {}).get("passed", False))
    signals = metrics.get("risk_signals", {}) or {}
    new_agg_dd = float(signals.get("aggregate_max_dd", 0.0))

    last_sortino = last_accepted_sortino(journal)
    last_agg_dd = last_accepted_aggregate_dd(journal)
    improved = (last_sortino is None) or (new_sortino > last_sortino)
    sortino_in_range = abs(new_sortino) < 10.0
    sortino_positive = new_sortino > 0
    dd_regression_ok = (
        last_agg_dd is None or new_agg_dd <= last_agg_dd + 0.10
    )

    # Anti-overfit gate suite (the thing that was entirely UNWIRED before
    # 2026-05-15). A variant is KEPT only if every gate passes — this is the
    # whole defense against the loop hill-climbing validation noise.
    gate_run, gate_reason = evaluate_anti_overfit_gates(
        metrics,
        iter_id=args.iteration_id,
        baseline_sortino=last_sortino,
        n_active_variants=len(attempts) + 1,
        baseline_hyperparams=baseline_hyperparams,
    )
    gates_passed = gate_run.passed
    metrics["anti_overfit_gates"] = gate_run.to_dict()

    if (
        risk_passed
        and improved
        and sortino_positive
        and sortino_in_range
        and dd_regression_ok
        and gates_passed
    ):
        kept_reason = (
            f"sortino {new_sortino:.3f} > prev {last_sortino!r}, "
            f"agg_dd {new_agg_dd:.1%}, catastrophe gate clear, {gate_reason}"
        )
        append_journal(journal_entry(
            args.iteration_id,
            hypothesis=parsed["hypothesis"],
            change_summary=parsed["change_summary"],
            decision="KEPT",
            reason=kept_reason,
            metrics=metrics,
            learning=learning_summary(
                "KEPT", kept_reason, metrics,
                previous_sortino=last_sortino,
                previous_aggregate_dd=last_agg_dd,
            ),
        ))
        persist_iteration(
            args.iteration_id, "KEPT", parsed["hypothesis"], metrics,
            reason=kept_reason,
        )
        commit_kept(args.iteration_id, parsed["hypothesis"])
        print(f"[loop] KEPT: sortino={new_sortino:.3f} (prev={last_sortino}), "
              f"agg_dd={new_agg_dd:.1%}")
        return 0
    else:
        parts: list[str] = []
        if not improved:
            parts.append(
                f"sortino {new_sortino:.3f} did not improve on prev "
                f"{last_sortino!r}"
            )
        if not sortino_positive:
            parts.append(
                f"sortino {new_sortino:.3f} not positive — "
                "won't compound on losing baseline"
            )
        if not sortino_in_range:
            parts.append(
                f"sortino {new_sortino:.3f} outside sane range — "
                "likely numerical artifact"
            )
        if not dd_regression_ok:
            parts.append(
                f"aggregate DD regressed: {new_agg_dd:.1%} > prev "
                f"{last_agg_dd:.1%} + 10pp tolerance"
            )
        if not risk_passed:
            violations = metrics.get("risk", {}).get("violations", []) or []
            if violations:
                parts.append("catastrophe: " + " · ".join(violations))
            else:
                parts.append("catastrophe gate failed")
        if not gates_passed:
            parts.append(gate_reason)
        reason = " | ".join(parts) if parts else "no improvement"

        append_journal(journal_entry(
            args.iteration_id,
            hypothesis=parsed["hypothesis"],
            change_summary=parsed["change_summary"],
            decision="REVERTED",
            reason=reason,
            metrics=metrics,
            learning=learning_summary(
                "REVERTED", reason, metrics,
                previous_sortino=last_sortino,
                previous_aggregate_dd=last_agg_dd,
            ),
        ))
        persist_iteration(
            args.iteration_id, "REVERTED", parsed["hypothesis"], metrics,
            reason=reason,
        )
        commit_reverted(args.iteration_id, reason)
        print(f"[loop] REVERTED: {reason}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
