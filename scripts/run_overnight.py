"""Overnight autoresearch harness.

Runs scripts/loop.py repeatedly, isolating per-iteration crashes so one bad
LLM call doesn't kill the whole night. Bounded by iteration count or
wall-clock budget; honors Ctrl+C cleanly.

Run as:
    uv run python scripts/run_overnight.py                        # 50 iter / 8 hr
    uv run python scripts/run_overnight.py --iterations 100
    uv run python scripts/run_overnight.py --max-hours 4
    uv run python scripts/run_overnight.py --provider codex
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Make `from scripts import loop` work when invoked as `uv run python
# scripts/run_overnight.py`; sys.path[0] is the script's directory, not
# the repo root, so `scripts` isn't importable without this shim.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import loop  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--iterations", type=int, default=50)
    p.add_argument("--max-hours", type=float, default=8.0)
    p.add_argument("--provider", choices=["claude", "codex"], default="claude")
    p.add_argument(
        "--model",
        default=None,
        help="Override the LLM model for every iteration (e.g. "
        "claude-sonnet-4-6). Default: Opus 4.7 (claude) / codex default.",
    )
    args = p.parse_args(argv)

    deadline = time.time() + args.max_hours * 3600
    counts = {"kept": 0, "reverted": 0, "rejected": 0, "crashed": 0}

    print(
        f"=== overnight start: {datetime.now().isoformat()} ===\n"
        f"  iterations={args.iterations}, max_hours={args.max_hours}, "
        f"provider={args.provider}{('/' + args.model) if args.model else ''}"
    )

    try:
        for i in range(1, args.iterations + 1):
            if time.time() >= deadline:
                print(f"  hit wall-clock budget after {i - 1} iterations")
                break
            t0 = time.time()
            try:
                loop_argv = ["--provider", args.provider]
                if args.model:
                    loop_argv += ["--model", args.model]
                rc = loop.main(loop_argv)
            except KeyboardInterrupt:
                raise
            except Exception:  # noqa: BLE001 — harness must not die
                counts["crashed"] += 1
                print(f"  [iter {i}] CRASHED:\n{traceback.format_exc()}")
                continue

            if rc == 0:
                counts["kept"] += 1
                tag = "KEPT"
            elif rc == 1:
                counts["reverted"] += 1
                tag = "REVERTED"
            else:
                counts["rejected"] += 1
                tag = "REJECTED"
            print(f"  [iter {i}] {tag} ({time.time() - t0:.0f}s)")
    except KeyboardInterrupt:
        print("\n  interrupted by user")

    print(
        f"\n=== overnight end: {datetime.now().isoformat()} ===\n"
        f"  kept={counts['kept']}  reverted={counts['reverted']}  "
        f"rejected={counts['rejected']}  crashed={counts['crashed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
