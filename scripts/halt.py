"""Set or clear the system-wide halt flag at state/halt.json.

The halt flag is honored by:
  - scripts/risk_check.check()  — gate 1, short-circuits everything else
  - scripts/executors/paper.py  — raises PreflightSkipped before any DB write
  - scripts/run_live.py         — checks before invoking any executor
  - (future) scripts/executor_ibkr.py

It is intentionally GLOBAL across modes per the docstring in risk_check.py
(I-5): a paper-mode halt blocks real-mode execution too.

Usage:
    # Set with a human-readable reason. Resume-token is auto-generated.
    python -m scripts.halt set "manual halt before market open"

    # Clear (only works if the file exists and a token is supplied OR --force).
    python -m scripts.halt clear --token <token>
    python -m scripts.halt clear --force

    # Inspect.
    python -m scripts.halt show
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from storage.portfolio_db import HALT_FILE_PATH


def set_halt(reason: str, *, set_by: str = "manual") -> dict:
    """Write halt.json with a fresh resume_token. Overwrites any existing
    halt. Returns the written payload so the caller can echo the token."""
    payload = {
        "reason": reason,
        "set_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "set_by": set_by,
        "resume_token": uuid.uuid4().hex,
    }
    HALT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HALT_FILE_PATH.write_text(json.dumps(payload, indent=2))
    return payload


def clear_halt(*, token: str | None = None, force: bool = False) -> bool:
    """Remove halt.json. Token must match the stored resume_token unless
    `force=True`. Returns True if cleared, False if no halt was set."""
    if not HALT_FILE_PATH.exists():
        return False
    if not force:
        try:
            stored = json.loads(HALT_FILE_PATH.read_text()).get("resume_token")
        except (OSError, ValueError):
            stored = None
        if stored and token != stored:
            raise ValueError(
                f"resume_token mismatch — refusing to clear. "
                f"Expected: {stored!r}; got: {token!r}. "
                "Pass --force to override."
            )
    HALT_FILE_PATH.unlink()
    return True


def show_halt() -> dict | None:
    if not HALT_FILE_PATH.exists():
        return None
    try:
        return json.loads(HALT_FILE_PATH.read_text())
    except (OSError, ValueError) as e:
        return {"_error": f"cannot parse halt.json: {e}"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="set the halt flag")
    p_set.add_argument("reason", help="human-readable explanation")
    p_set.add_argument("--by", default="manual", help="who set this halt")

    p_clr = sub.add_parser("clear", help="clear the halt flag")
    p_clr.add_argument("--token", help="resume_token from when halt was set")
    p_clr.add_argument("--force", action="store_true",
                       help="clear without token (use only after manual review)")

    sub.add_parser("show", help="print current halt state, or 'clear'")

    args = p.parse_args(argv)

    if args.cmd == "set":
        payload = set_halt(args.reason, set_by=args.by)
        print(f"[halt] SET → {HALT_FILE_PATH}")
        print(f"[halt] reason: {payload['reason']}")
        print(f"[halt] resume_token: {payload['resume_token']}")
        print(f"[halt] clear with: python -m scripts.halt clear --token {payload['resume_token']}")
        return 0

    if args.cmd == "clear":
        try:
            cleared = clear_halt(token=args.token, force=args.force)
        except ValueError as e:
            print(f"[halt] {e}", file=sys.stderr)
            return 2
        if cleared:
            print(f"[halt] CLEARED → {HALT_FILE_PATH}")
            return 0
        print("[halt] no halt was set; nothing to clear.")
        return 0

    if args.cmd == "show":
        payload = show_halt()
        if payload is None:
            print("[halt] clear (no halt.json)")
            return 1
        print(json.dumps(payload, indent=2))
        return 0

    return 0  # unreachable due to required=True


if __name__ == "__main__":
    sys.exit(main())
