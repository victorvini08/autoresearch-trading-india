"""Promotion gate for `EXECUTION_MODE=dhan-live`.

Closes the documentation-only "4-week paper-validation" requirement from
CLAUDE.md (hard constraint #1). Before this script existed, going live
needed only `EXECUTION_MODE=dhan-live` + a valid `DHAN_ACCESS_TOKEN` —
no programmatic check enforced the paper-validation pre-requisite.

What this enforces:
  1. The exact strategy.py that was consent-granted is the one going live
     (sha256 captured at grant; re-validated by run_live every day).
  2. Consent has not expired (default 30 days from grant).
  3. SEBI_ALGO_ID is set in env (otherwise the broker construction fails
     anyway — listed here as a reminder).

Paper-day count and unresolved-discrepancy count are RECORDED in the
consent payload for audit, but they don't gate `grant` — the user
opted out of the 4-week paper-validation requirement on 2026-05-26.

`run_live.py` calls `check_consent_for_live()` before constructing the
live broker. Failing any check refuses the live run with a clear reason.

Usage:
    # Grant consent (no paper-day requirement; can be run any time)
    uv run python -m scripts.promote_live grant

    # Show current consent state
    uv run python -m scripts.promote_live show

    # Revoke consent (returns the system to "live blocked")
    uv run python -m scripts.promote_live revoke
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSENT_PATH = REPO_ROOT / "state" / "live_consent.json"
STRATEGY_PY = REPO_ROOT / "strategy.py"
PORTFOLIO_DB = REPO_ROOT / "storage" / "portfolio.duckdb"

CONSENT_VALID_DAYS = 30
LOOKBACK_DAYS = 60  # window for the audit numbers recorded in the consent payload


def _strategy_hash() -> str:
    return hashlib.sha256(STRATEGY_PY.read_bytes()).hexdigest()


def _audit_window(db: Path, lookback_days: int = LOOKBACK_DAYS) -> tuple[int, int]:
    """Count (clean paper days, unresolved discrepancies) in the lookback."""
    if not db.exists():
        return 0, -1
    conn = duckdb.connect(str(db), read_only=True)
    try:
        floor = date.today() - timedelta(days=lookback_days)
        n_days = conn.execute(
            "SELECT COUNT(DISTINCT snapshot_date) FROM broker_positions "
            "WHERE mode = 'dhan-paper' AND snapshot_date >= ?",
            (floor,),
        ).fetchone()[0]
        n_disc = conn.execute(
            "SELECT COUNT(*) FROM discrepancies "
            "WHERE mode = 'dhan-paper' "
            "AND as_of_date >= ? "
            "AND (resolution IS NULL OR resolution = '')",
            (floor,),
        ).fetchone()[0]
    finally:
        conn.close()
    return int(n_days or 0), int(n_disc or 0)


def grant_consent() -> dict:
    """Write `state/live_consent.json` and return the payload.

    No data gates: paper-day count and unresolved discrepancies are recorded
    in the payload (for audit) but don't refuse the grant. The protections
    that DO matter — strategy.py hash binding, 30-day expiry, and the
    SEBI_ALGO_ID broker-construction requirement — stay in force.
    """
    n_days, n_disc = _audit_window(PORTFOLIO_DB)
    now = datetime.now(timezone.utc)
    payload = {
        "granted_at": now.isoformat(timespec="seconds"),
        "granted_by": "manual",
        "paper_days_validated": n_days,
        "discrepancies_in_window": n_disc,
        "strategy_hash": _strategy_hash(),
        "consent_token": uuid.uuid4().hex,
        "valid_until_utc": (
            now + timedelta(days=CONSENT_VALID_DAYS)
        ).isoformat(timespec="seconds"),
    }
    CONSENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONSENT_PATH.write_text(json.dumps(payload, indent=2))
    return payload


def revoke_consent() -> bool:
    if not CONSENT_PATH.exists():
        return False
    CONSENT_PATH.unlink()
    return True


def show_consent() -> dict | None:
    if not CONSENT_PATH.exists():
        return None
    try:
        return json.loads(CONSENT_PATH.read_text())
    except (OSError, ValueError) as e:
        return {"_error": str(e)}


def check_consent_for_live() -> tuple[bool, str]:
    """Called by run_live.py before constructing the live broker.

    Returns (allowed, reason). `allowed=False` blocks live execution.
    """
    consent = show_consent()
    if consent is None:
        return (
            False,
            "no state/live_consent.json — run "
            "`uv run python -m scripts.promote_live grant` after 4 weeks of "
            "clean paper trading.",
        )
    if "_error" in consent:
        return False, f"live_consent.json unreadable: {consent['_error']}"
    if not consent.get("consent_token"):
        return False, "live_consent.json missing consent_token"
    try:
        valid_until = datetime.fromisoformat(consent["valid_until_utc"])
    except (KeyError, ValueError):
        return False, "live_consent.json valid_until_utc missing/invalid"
    if datetime.now(timezone.utc) > valid_until:
        return False, (
            f"consent expired {valid_until.isoformat(timespec='seconds')} — "
            "re-grant after re-validation."
        )
    current = _strategy_hash()
    granted_hash = consent.get("strategy_hash", "")
    if granted_hash != current:
        return False, (
            f"strategy.py changed since consent was granted "
            f"(consent hash={granted_hash[:12]}, current={current[:12]}). "
            "Re-run `promote_live grant` to reaffirm the production strategy."
        )
    return True, (
        f"consent valid (granted {consent.get('granted_at')}; "
        f"paper_days={consent.get('paper_days_validated')}; "
        f"expires {valid_until.isoformat(timespec='seconds')})"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("grant", help="grant live-mode consent (no data gates)")
    sub.add_parser("show", help="print current consent state")
    sub.add_parser("revoke", help="remove consent and re-block live")

    args = p.parse_args(argv)

    if args.cmd == "grant":
        payload = grant_consent()
        print(f"[promote_live] granted live consent → {CONSENT_PATH}")
        print(json.dumps(payload, indent=2))
        return 0

    if args.cmd == "show":
        consent = show_consent()
        if consent is None:
            print("[promote_live] no live consent set — live mode is blocked.")
            return 1
        allowed, reason = check_consent_for_live()
        print(json.dumps(consent, indent=2))
        print(f"[promote_live] status: {'ALLOWED' if allowed else 'BLOCKED'}")
        print(f"[promote_live] reason: {reason}")
        return 0 if allowed else 1

    if args.cmd == "revoke":
        cleared = revoke_consent()
        print(
            f"[promote_live] {'REVOKED' if cleared else 'nothing to revoke'}"
        )
        return 0

    p.print_help()
    return 1


__all__ = [
    "CONSENT_PATH",
    "CONSENT_VALID_DAYS",
    "check_consent_for_live",
    "grant_consent",
    "revoke_consent",
    "show_consent",
]


if __name__ == "__main__":
    sys.exit(main())
