"""Step 2.b — daily safety-state evaluation.

Reads the equity curve from portfolio.duckdb, calls the pure state machine
in data/safety_state.py, persists the result to state/safety_state.json.
Side-effect files (state/risk_multiplier.json, state/halt.json) are written
ONLY when the state requires them.

Folded into scripts/daily_report.main() — no separate launchd job. Non-fatal
by contract: a hiccup here must never block the daily report.

CLI (for ad-hoc / dry-run):
    uv run python -m scripts.safety_evaluator
    uv run python -m scripts.safety_evaluator --mode dhan-paper
    uv run python -m scripts.safety_evaluator --as-of 2026-05-28 --dry-run
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from data.safety_state import SafetyState, evaluate_state
from storage import portfolio_db

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
SAFETY_STATE_PATH = STATE_DIR / "safety_state.json"
RISK_MULTIPLIER_PATH = STATE_DIR / "risk_multiplier.json"
HALT_PATH = REPO_ROOT / "halt.json"  # consistent with scripts/halt.py


# === SafetyState ↔ JSON =====================================================

def _safety_state_to_json(s: SafetyState) -> dict:
    """JSON-safe representation. date fields become ISO strings."""
    out = asdict(s)
    out["as_of"] = s.as_of.isoformat()
    out["entered_state_at"] = s.entered_state_at.isoformat()
    return out


def _safety_state_from_json(raw: dict) -> SafetyState:
    return SafetyState(
        state=raw["state"],
        as_of=date.fromisoformat(raw["as_of"]),
        today_equity=float(raw["today_equity"]),
        peak_equity=float(raw["peak_equity"]),
        dd_pct=float(raw["dd_pct"]),
        risk_multiplier=float(raw["risk_multiplier"]),
        halted=bool(raw["halted"]),
        transitioned_today=bool(raw["transitioned_today"]),
        entered_state_at=date.fromisoformat(raw["entered_state_at"]),
        days_in_state=int(raw["days_in_state"]),
        reason=str(raw["reason"]),
    )


def load_prior_state(path: Path = SAFETY_STATE_PATH) -> SafetyState | None:
    if not path.exists():
        return None
    try:
        return _safety_state_from_json(json.loads(path.read_text()))
    except (json.JSONDecodeError, KeyError, ValueError):
        # Corrupt file → treat as no prior state. The next evaluation
        # bootstraps from history. This avoids a stuck-bad-state on disk.
        return None


def save_state(s: SafetyState, path: Path = SAFETY_STATE_PATH) -> None:
    """Atomic write: tmp file + rename, so a crash mid-write doesn't
    corrupt the on-disk state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_safety_state_to_json(s), indent=2) + "\n")
    tmp.replace(path)


def write_risk_multiplier(
    s: SafetyState, path: Path = RISK_MULTIPLIER_PATH
) -> None:
    """The executor reads this. Always write it (idempotent), so a manual
    delete or filesystem hiccup self-heals on the next safety eval."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "multiplier": s.risk_multiplier,
        "state": s.state,
        "as_of": s.as_of.isoformat(),
        "reason": s.reason,
        "written_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_halt(s: SafetyState, path: Path = HALT_PATH) -> None:
    """Write halt.json with halted=true on HALTED_REVIEW. Does NOT auto-clear:
    once the safety machine halts, the user must explicitly resume (per the
    absorbing-state design)."""
    if not s.halted:
        return  # safety eval never clears halt — manual user action only
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "halted": True,
        "reason": f"safety_state={s.state}: {s.reason}",
        "set_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


# === Equity history loader ==================================================

def _load_equity_history(
    db_path: Path, mode: str,
) -> list[tuple[date, float]]:
    """All (snapshot_date, mark_equity) pairs from broker_positions + cash,
    ordered ascending by date.

    Uses portfolio_db.get_equity_curve so the math matches
    cash_balance_through(D) + sum(mark_value(D)) — the same definition
    the dashboard + reconciliation Q5 use.
    """
    with portfolio_db.connect(db_path) as conn:
        df = portfolio_db.get_equity_curve(conn, mode=mode)
    if df.empty:
        return []
    return [
        (row.snapshot_date, float(row.mark_equity))
        for row in df.itertuples(index=False)
    ]


# === Public entrypoint ======================================================

def evaluate_and_persist(
    *,
    mode: str = "dhan-paper",
    db_path: Path | None = None,
    state_dir: Path | None = None,
    dry_run: bool = False,
) -> SafetyState | None:
    """Evaluate today's safety state and persist all the side-effect files.

    Returns the new SafetyState, or None if no equity history exists yet
    (typical for a brand-new ledger pre-first-trade).
    """
    db_path = db_path or portfolio_db.DEFAULT_DB_PATH
    state_dir = state_dir or STATE_DIR

    history = _load_equity_history(db_path, mode)
    if not history:
        return None

    prior = load_prior_state(state_dir / "safety_state.json")
    new_state = evaluate_state(history, prior_state=prior)

    if dry_run:
        return new_state

    save_state(new_state, state_dir / "safety_state.json")
    write_risk_multiplier(new_state, state_dir / "risk_multiplier.json")
    write_halt(new_state)  # only writes if halted=True
    return new_state


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", default="dhan-paper")
    p.add_argument(
        "--db-path", type=Path, default=None,
        help="override portfolio.duckdb location",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="evaluate + print but do NOT write any state files",
    )
    args = p.parse_args(argv)

    s = evaluate_and_persist(
        mode=args.mode, db_path=args.db_path, dry_run=args.dry_run,
    )
    if s is None:
        print("[safety] no equity history yet; state not written.")
        return 0
    flag = " [DRY-RUN]" if args.dry_run else ""
    print(
        f"[safety]{flag} state={s.state} dd={s.dd_pct*100:.2f}% "
        f"mult={s.risk_multiplier} day_{s.days_in_state} "
        f"of state · {s.reason}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
