"""Promotion gate — manual, you-run-only.

Reads journal.md, ranks KEPT iterations whose validation Sortino clears the
2.0 threshold AND risk passed, prompts you to confirm the top candidate,
checks out THAT iteration's strategy.py via git, runs prepare.py promotion
(unsealing the test set), reports the test scores, and restores HEAD.

The autoresearch agent never runs this.

Run as:
    uv run python scripts/promote.py
"""
from __future__ import annotations

import importlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_PATH = REPO_ROOT / "journal.md"
STRATEGY_PATH = REPO_ROOT / "strategy.py"

VALIDATION_PROMOTION_THRESHOLD = 2.0


@dataclass
class JournalEntry:
    iteration_id: str
    hypothesis: str
    sortino: float
    risk_passed: bool
    commit_sha: str | None  # the commit where this iteration's strategy.py landed


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
    ).stdout.strip()


def _find_kept_commit_sha(iteration_id: str) -> str | None:
    """Search git log for the KEPT commit matching this iteration_id.

    Loop commits look like `iter <iteration_id>: <hypothesis>`.
    """
    log = _git("log", "--all", "--pretty=format:%H %s")
    for line in log.splitlines():
        sha, _, subject = line.partition(" ")
        if subject.startswith(f"iter {iteration_id}:"):
            return sha
    return None


def parse_journal(text: str) -> list[JournalEntry]:
    """Pull every KEPT iteration entry out of journal.md."""
    entries: list[JournalEntry] = []
    blocks = re.split(r"\n## ", text)
    for block in blocks:
        m = re.match(
            r"Iteration\s+(\S+)\s+—\s+KEPT", block, re.IGNORECASE,
        )
        if not m:
            continue
        iteration_id = m.group(1)

        hyp_m = re.search(
            r"\*\*Hypothesis:\*\*\s*(.+?)(?=\n\s*\n|\n\*\*)",
            block, re.DOTALL,
        )
        hypothesis = hyp_m.group(1).strip() if hyp_m else "(no hypothesis)"

        sort_m = re.search(
            r"validation_sortino_mean[:\s]+([-+]?\d+\.?\d*)", block,
        )
        if not sort_m:
            continue
        sortino = float(sort_m.group(1))

        risk_m = re.search(r"risk\.passed[:\s]+(True|False)", block)
        risk_passed = risk_m.group(1) == "True" if risk_m else False

        entries.append(JournalEntry(
            iteration_id=iteration_id,
            hypothesis=hypothesis,
            sortino=sortino,
            risk_passed=risk_passed,
            commit_sha=_find_kept_commit_sha(iteration_id),
        ))
    return entries


def rank_candidates(entries: list[JournalEntry]) -> list[JournalEntry]:
    eligible = [
        e for e in entries
        if e.risk_passed
        and e.sortino >= VALIDATION_PROMOTION_THRESHOLD
        and e.commit_sha is not None
    ]
    return sorted(eligible, key=lambda e: e.sortino, reverse=True)


def run_prepare_promotion() -> dict:
    """Reload strategy + prepare so changes from `git checkout` take effect."""
    for mod_name in ("strategy", "prepare"):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
    import prepare
    import strategy
    return prepare.evaluate(strategy, mode="promotion")


def main() -> int:
    if not JOURNAL_PATH.exists():
        print(f"journal.md not found at {JOURNAL_PATH}")
        return 1

    text = JOURNAL_PATH.read_text()
    entries = parse_journal(text)
    candidates = rank_candidates(entries)

    if not candidates:
        print(
            f"No KEPT iterations clear validation Sortino "
            f">= {VALIDATION_PROMOTION_THRESHOLD} with risk passed. "
            f"Nothing to promote yet."
        )
        return 0

    print(f"Promotion candidates (sorted by validation Sortino):\n")
    for i, e in enumerate(candidates[:5]):
        sha_short = e.commit_sha[:7] if e.commit_sha else "?"
        print(
            f"  [{i + 1}] iter {e.iteration_id} ({sha_short})  "
            f"sortino={e.sortino:.3f}\n      hypothesis: {e.hypothesis[:120]}"
        )

    top = candidates[0]
    answer = input(
        f"\nPromote top candidate iter {top.iteration_id} "
        f"(sortino {top.sortino:.3f})? [y/N]: "
    ).strip().lower()
    if answer != "y":
        print("aborted, no changes made.")
        return 0

    head_sha_before = _git("rev-parse", "HEAD")
    print(f"\nchecking out strategy.py from commit {top.commit_sha[:7]}...")
    subprocess.run(
        ["git", "checkout", top.commit_sha, "--", "strategy.py"],
        cwd=str(REPO_ROOT), check=True,
    )

    try:
        print(f"running prepare.py promotion (this unseals the test set)...")
        result = run_prepare_promotion()
        print("\n=== Promotion result ===")
        print(f"  validation_sortino_mean: {result.get('validation_sortino_mean')}")
        print(f"  test_sortino:            {result.get('test_sortino')}")
        print(f"  test_calmar:             {result.get('test_calmar')}")
        print(f"  test_max_dd:             {result.get('test_max_dd')}")
        print(f"  test_hit_rate:           {result.get('test_hit_rate')}")
        print(f"  test_trade_count:        {result.get('test_trade_count')}")
        print(f"  risk.passed (validation): {result.get('risk', {}).get('passed')}")

        test_sortino = result.get("test_sortino")
        if test_sortino is not None:
            if test_sortino >= 1.0:
                print(
                    f"\n  test Sortino {test_sortino:.3f} >= 1.0 — "
                    f"eligible for paper-trade promotion"
                )
            else:
                print(
                    f"\n  test Sortino {test_sortino:.3f} < 1.0 — "
                    f"strategy does NOT clear the sealed-test gate"
                )
    finally:
        print(f"\nrestoring strategy.py to HEAD ({head_sha_before[:7]})...")
        subprocess.run(
            ["git", "checkout", head_sha_before, "--", "strategy.py"],
            cwd=str(REPO_ROOT), check=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
