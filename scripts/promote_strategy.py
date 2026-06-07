"""Manual strategy promotion — Step 5.f.

The ONLY code path that writes the live strategy.py, and it is deliberately a
hand-run, human-in-the-loop command — never auto-fired. You run it after
inspecting a challenger's shadow evidence (scripts.realworld_shadow). It:

  1. refuses unless the version actually ran a shadow trial (SHADOW_ACTIVE),
     unless you explicitly --force;
  2. re-validates the challenger snapshot through the SAME AST/import sandbox
     the loop uses, so a corrupted snapshot can never reach the live file;
  3. backs up the current incumbent for one-command rollback;
  4. swaps strategy.py ATOMICALLY (os.replace);
  5. records the lifecycle: challenger → PROMOTED, any prior PROMOTED → RETIRED,
     the originating hypothesis → VALIDATOR_KEPT; appends a journal entry.

It does NOT git-commit. You review the diff and commit yourself (the repo's git
identity / commit discipline stays in human hands).

    uv run python -m scripts.promote_strategy <version_hash>
    uv run python -m scripts.promote_strategy <version_hash> --force   # skip shadow gate
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from storage import realworld_db


@dataclass(frozen=True)
class PromoteResult:
    ok: bool
    version_hash: str
    message: str
    backup_path: str | None


def _append_journal(path: Path, *, now: datetime, version_hash: str, v: dict) -> None:
    lines = [
        f"\n## {now.date().isoformat()} — PROMOTED {version_hash} ({v.get('mode')})\n",
        f"- from hypothesis **{v.get('hypothesis_id')}**\n",
        "- the challenger cleared the gates, ran a shadow trial, and was "
        "manually promoted into live strategy.py\n",
        f"- previous strategy.py backed up; rollback by restoring the backup snapshot\n",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(lines)


def promote_challenger(
    version_hash: str,
    *,
    mode: str = "dhan-paper",
    realworld_db_path: Path | str | None = None,
    strategy_path: Path | str | None = None,
    snapshot_dir: Path | str | None = None,
    journal_path: Path | str | None = None,
    now: datetime | None = None,
    require_shadow: bool = True,
) -> PromoteResult:
    from scripts.loop import validate_strategy_edit
    from scripts.realworld_validator import JOURNAL_PATH, SNAPSHOT_DIR, STRATEGY_PATH

    now = now or datetime.now()
    strategy_path = Path(strategy_path) if strategy_path is not None else STRATEGY_PATH
    snapshot_dir = Path(snapshot_dir) if snapshot_dir is not None else SNAPSHOT_DIR
    journal_path = Path(journal_path) if journal_path is not None else JOURNAL_PATH
    db_path = (Path(realworld_db_path) if realworld_db_path is not None
               else realworld_db.DEFAULT_DB_PATH)

    conn = realworld_db.connect(db_path)
    try:
        v = realworld_db.get_strategy_version(conn, version_hash)
        if v is None:
            return PromoteResult(False, version_hash, "version not found", None)
        if v["mode"] != mode:
            return PromoteResult(
                False, version_hash,
                f"version mode {v['mode']!r} != requested {mode!r}", None)
        if require_shadow and v["status"] != "SHADOW_ACTIVE":
            return PromoteResult(
                False, version_hash,
                f"status is {v['status']}, expected SHADOW_ACTIVE — run a shadow "
                "trial first (scripts.realworld_shadow) or pass require_shadow=False",
                None)

        challenger_text = Path(v["snapshot_path"]).read_text()
        current = Path(strategy_path).read_text()
        ok, why = validate_strategy_edit(challenger_text, current_text=current)
        if not ok:
            return PromoteResult(
                False, version_hash,
                f"challenger snapshot failed validation, refusing to swap: {why}",
                None)

        # 1) back up the incumbent for rollback
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        backup = snapshot_dir / f"incumbent-before-{version_hash}.py"
        backup.write_text(current, encoding="utf-8")

        # 2) atomic swap of the live file
        tmp = strategy_path.with_name(strategy_path.name + ".promote-tmp")
        tmp.write_text(challenger_text, encoding="utf-8")
        os.replace(tmp, strategy_path)

        # 3) lifecycle writeback
        for other in realworld_db.get_strategy_versions(conn, mode):
            if other["status"] == "PROMOTED" and other["version_hash"] != version_hash:
                realworld_db.update_strategy_version_status(
                    conn, other["version_hash"], "RETIRED", updated_at=now)
        realworld_db.update_strategy_version_status(
            conn, version_hash, "PROMOTED", updated_at=now)
        if v.get("hypothesis_id"):
            realworld_db.update_hypothesis_state(
                conn, v["hypothesis_id"], "VALIDATOR_KEPT", updated_at=now)

        _append_journal(journal_path, now=now, version_hash=version_hash, v=v)
        return PromoteResult(
            True, version_hash,
            f"promoted {version_hash} into live strategy.py (backup at {backup})",
            str(backup))
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote a shadow-tested challenger into live strategy.py.")
    ap.add_argument("version_hash")
    ap.add_argument("--mode", default="dhan-paper")
    ap.add_argument("--force", action="store_true",
                    help="skip the SHADOW_ACTIVE requirement (use with care)")
    args = ap.parse_args(argv)
    res = promote_challenger(
        args.version_hash, mode=args.mode, require_shadow=not args.force)
    print(f"[promote_strategy] {'OK' if res.ok else 'REFUSED'}: {res.message}")
    if res.ok:
        print("  Review the diff and commit strategy.py yourself when ready.")
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
