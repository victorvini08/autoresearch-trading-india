"""Price-only baseline ablation.

Runs prepare.py research twice on the current strategy.py:
  (a) gate-on   — strategy.py unchanged, with the macro_regime risk_off gate
  (b) gate-off  — strategy.py with the gate line + import temporarily stripped

Both results are appended to journal.md as the floor every Phase 3 iteration
is measured against. strategy.py is restored at the end (non-destructive).

Run as:
    uv run python scripts/baseline_ablation.py
"""
from __future__ import annotations

import importlib
import re
import shutil
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_PATH = REPO_ROOT / "strategy.py"
JOURNAL_PATH = REPO_ROOT / "journal.md"

# Make root-level modules (strategy.py, prepare.py) importable when this
# script is run as `uv run python scripts/baseline_ablation.py`.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _strip_macro_gate(text: str) -> str:
    """Replace `from llm.features import macro_regime` with a noop stub that
    always returns None. The strategy's gate condition
    (`macro_regime(today) == "risk_off"`) then always evaluates False, so the
    gate never fires. This is more robust than regex-stripping the gate line
    because it survives any restructuring of WHERE the check happens.
    """
    return re.sub(
        r"^from llm\.features import macro_regime\s*$",
        (
            "def macro_regime(_d):  # ablation: gate-off, always None\n"
            "    return None"
        ),
        text,
        count=1,
        flags=re.MULTILINE,
    )


def _format_journal_entry(label: str, result: dict) -> str:
    side = result.get("side_panel", {})
    risk = result.get("risk", {})
    return (
        f"\n## {label}\n\n"
        f"**Hypothesis:** N/A — ablation baseline, not a hypothesis test.\n\n"
        f"**Change:** {label}.\n\n"
        f"**Result:**\n"
        f"- validation_sortino_mean: {result.get('validation_sortino_mean'):.3f}\n"
        f"- validation_folds: {result.get('validation_folds')}\n"
        f"- calmar_mean: {side.get('calmar_mean'):.3f}\n"
        f"- max_dd_worst: {side.get('max_dd_worst'):.3f}\n"
        f"- hit_rate_mean: {side.get('hit_rate_mean'):.3f}\n"
        f"- profit_factor_mean: {side.get('profit_factor_mean'):.3f}\n"
        f"- turnover_mean: {side.get('turnover_mean'):.3f}\n"
        f"- trade_count_total: {side.get('trade_count_total')}\n"
        f"- pre_tax_return_mean: {side.get('pre_tax_return_mean'):.3f}\n"
        f"- post_tax_return_mean_stcg15: {side.get('post_tax_return_mean_stcg15'):.3f}\n"
        f"- risk.passed: {risk.get('passed')}\n"
        f"- risk.violations: {risk.get('violations')}\n\n"
        f"**Learning:** Floor reference for Phase 3 iterations. "
        f"Compare future iteration scores against this baseline.\n\n---\n"
    )


def _run_prepare_research() -> dict:
    """Reload strategy and prepare modules so the ablation picks up our edits."""
    for mod_name in ("strategy", "prepare"):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
    import prepare
    import strategy
    return prepare.evaluate(strategy, mode="research")


def main() -> int:
    if not STRATEGY_PATH.exists():
        print(f"strategy.py not found at {STRATEGY_PATH}")
        return 1

    original_text = STRATEGY_PATH.read_text()
    backup_path = STRATEGY_PATH.with_suffix(".py.ablation_backup")
    shutil.copy2(STRATEGY_PATH, backup_path)

    try:
        # (a) gate-on — strategy.py unchanged
        print("=== Run 1/2: macro_regime gate ON (strategy.py unchanged) ===")
        result_on = _run_prepare_research()
        print(f"  validation_sortino_mean = {result_on['validation_sortino_mean']:.3f}")

        # (b) gate-off — strip the gate
        stripped_text = _strip_macro_gate(original_text)
        if stripped_text == original_text:
            print(
                "WARNING: macro_regime gate not found in strategy.py — "
                "ablation will run identical strategies."
            )
        STRATEGY_PATH.write_text(stripped_text)

        print("\n=== Run 2/2: macro_regime gate OFF (gate + import stripped) ===")
        result_off = _run_prepare_research()
        print(f"  validation_sortino_mean = {result_off['validation_sortino_mean']:.3f}")

    finally:
        # Always restore. Defensive: copy from backup, not from the in-memory
        # original_text, in case anything corrupted the variable.
        shutil.copy2(backup_path, STRATEGY_PATH)
        backup_path.unlink()

    today = date.today().isoformat()
    entry = (
        f"\n<!-- Baseline ablation generated {today} -->\n"
        + _format_journal_entry(
            f"Baseline A — gate-on (current strategy.py, {today})",
            result_on,
        )
        + _format_journal_entry(
            f"Baseline B — gate-off (price-only, {today})",
            result_off,
        )
    )
    with JOURNAL_PATH.open("a") as f:
        f.write(entry)

    delta = result_on["validation_sortino_mean"] - result_off["validation_sortino_mean"]
    print(f"\nDone. Sortino delta (gate-on minus gate-off) = {delta:+.3f}")
    print(f"Both baselines appended to {JOURNAL_PATH.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
