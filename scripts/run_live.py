"""Daily trading-pipeline orchestrator. Single entry point.

Flow:
    1. Pre-flight: halt.json clear? (Indian modes — dhan-paper and
       dhan-live — are both intraday: they enforce the 10:00-15:00 IST
       window.)
    2. Resolve target signal-date based on mode (today_ist for all modes).
    3. Load premarket scan output (may be absent — that's fine).
    4. Apply soft adjustments from the scan (gap skips, VIX scale-down)
       — logged for the report; never gates the executor itself.
    5. Pick executor by EXECUTION_MODE env var. Default: dhan-paper.
    6. executor.execute_day(target_date) — atomic ledger write inside.
    7. Generate the daily markdown report.
    8. Exit 0 on success / skipped, 1 on halt or executor error.

Operationally this is what launchd fires once a day. Same script works
in dhan-paper mode (today, against brokers.dhan_mock) and dhan-live
mode (post 4-week paper validation, against real Dhan); only the
executor class changes, and that's resolved from EXECUTION_MODE.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts import daily_report, dashboard, premarket_scan
# DhanExecutor lands in scripts.executors after Phase 4 (handoff §3,
# scripts/executors/dhan.py NEW). For now import only the protocol-level
# symbols; _build_executor() defers the DhanExecutor import to call-time
# so module import doesn't break before Phase 4.
from scripts.executors.protocol import Executor, ExecutionSummary, PreflightSkipped
from storage.portfolio_db import HALT_FILE_PATH

IST = ZoneInfo("Asia/Kolkata")

# Indian execution window: NSE trades 09:15-15:30 IST. We fire at 10:15,
# 15 min after premarket_scan @ 10:00 fetches today's NSE open via
# yfinance (15-min Yahoo delay → today's 09:15 open is reliably published
# by ~09:30, premarket_scan reads it at 10:00, run_live consumes the JSON
# at 10:15). Refuse new orders past 15:00 to leave a 30-min buffer before
# market close.
EXECUTION_WINDOW_IST: tuple[time, time] = (time(10, 15), time(15, 0))

# launchd may fire late (laptop just woke up). For LIVE modes only,
# refuse to trade if we're more than this many minutes past the
# scheduled window start. Paper mode ignores this (it's a backfill).
LATE_WINDOW_TOLERANCE_MIN = 30

# Supported EXECUTION_MODE env strings. dhan-paper runs against the
# brokers.dhan_mock in-memory mock; dhan-live runs against the real
# Dhan REST API. Both share scripts/executors/dhan.DhanExecutor; the
# mode string is forwarded to the executor so it can pick the client.
_SUPPORTED_MODES: tuple[str, ...] = ("dhan-paper", "dhan-live")


def _build_executor(mode: str) -> Executor:
    if mode in _SUPPORTED_MODES:
        # Lazy import: scripts/executors/dhan.py lands in Phase 4.
        from scripts.executors.dhan import DhanExecutor  # type: ignore[import-not-found]

        return DhanExecutor(mode=mode)
    raise NotImplementedError(
        f"EXECUTION_MODE={mode!r} is not implemented yet. "
        f"Supported: {sorted(_SUPPORTED_MODES)}"
    )


def _resolve_target_date(mode: str, today_ist: date, prices_db: Path | None = None) -> date:
    """Determine which signal-date this run will process.

    dhan-paper / dhan-live:  today_ist (signal-on-T, fills-on-T intraday).
                             User is in IST; market is open while this
                             script fires — no overnight wait, no
                             yesterday-backfill needed.
    """
    return today_ist


def _within_execution_window(now_ist: datetime, tolerance_min: int = LATE_WINDOW_TOLERANCE_MIN) -> bool:
    start, stop = EXECUTION_WINDOW_IST
    grace_start = (datetime.combine(now_ist.date(), start) - timedelta(minutes=0)).time()
    grace_stop = (datetime.combine(now_ist.date(), stop)).time()
    # Late tolerance only affects the start: we'll still refuse if it's
    # already past the official close-of-window time.
    late_start = (datetime.combine(now_ist.date(), start) + timedelta(minutes=tolerance_min)).time()
    t = now_ist.time()
    return grace_start <= t <= grace_stop and t <= late_start


def _halt_payload() -> dict | None:
    if not HALT_FILE_PATH.exists():
        return None
    try:
        return json.loads(HALT_FILE_PATH.read_text())
    except (OSError, ValueError) as e:
        return {"_error": f"halt.json unreadable: {e}"}


def _log_skip_summary(s: ExecutionSummary) -> None:
    print(f"[run_live] mode={s.mode} as_of={s.as_of_date} "
          f"status={'HALTED' if s.halt_set else 'SKIPPED' if s.skipped else 'OK'}")
    if s.skipped_reason:
        print(f"[run_live] reason: {s.skipped_reason}")
    if s.halt_reason:
        print(f"[run_live] halt reason: {s.halt_reason}")


def run(
    *,
    mode: str | None = None,
    today_ist: date | None = None,
    prices_db: Path | None = None,
) -> tuple[int, ExecutionSummary]:
    """Programmatic entry point. Returns (exit_code, summary)."""
    mode = mode or os.environ.get("EXECUTION_MODE", "dhan-paper")
    today_ist = today_ist or datetime.now(IST).date()

    # Pre-flight: halt.json
    halt = _halt_payload()
    if halt is not None:
        skip_summary = ExecutionSummary(
            mode=mode,
            as_of_date=today_ist,
            fill_date=None,
            skipped=True,
            skipped_reason=(
                f"halt.json is set: reason={halt.get('reason')!r}, "
                f"set_by={halt.get('set_by')!r}. "
                "Run `python -m scripts.halt clear --token <token>` to resume."
            ),
            halt_set=True,
            halt_reason=halt.get("reason"),
        )
        _log_skip_summary(skip_summary)
        _safe_report(skip_summary, premarket_payload=None)
        return 1, skip_summary

    # Pre-flight: execution window. Both Indian modes (dhan-paper and
    # dhan-live) are intraday signal-on-T fills-on-T; enforce window on
    # both. (In the US repo this gate was skipped for paper-mode because
    # paper there backfilled yesterday's signal overnight.)
    now_ist = datetime.now(IST)
    if not _within_execution_window(now_ist):
        skip_summary = ExecutionSummary(
            mode=mode,
            as_of_date=today_ist,
            fill_date=None,
            skipped=True,
            skipped_reason=(
                f"Outside execution window {EXECUTION_WINDOW_IST[0]}-"
                f"{EXECUTION_WINDOW_IST[1]} IST (now: {now_ist.time()}; "
                f"late tolerance: {LATE_WINDOW_TOLERANCE_MIN} min)."
            ),
        )
        _log_skip_summary(skip_summary)
        _safe_report(skip_summary, premarket_payload=None)
        return 0, skip_summary

    # Resolve signal date
    try:
        target_date = _resolve_target_date(mode, today_ist, prices_db=prices_db)
    except RuntimeError as e:
        skip_summary = ExecutionSummary(
            mode=mode, as_of_date=today_ist, fill_date=None,
            skipped=True, skipped_reason=str(e),
        )
        _log_skip_summary(skip_summary)
        _safe_report(skip_summary, premarket_payload=None)
        return 1, skip_summary

    print(f"[run_live] mode={mode} today_ist={today_ist} signal_date={target_date}")

    # Load premarket scan (today's gap signals from yfinance, fired at 10:00)
    premarket_payload = premarket_scan.load(today_ist)
    skips: set[str] = set()
    if premarket_payload:
        skips = premarket_scan.tickers_to_skip(premarket_payload)
        if skips:
            print(f"[run_live] premarket gap-flagged tickers: {sorted(skips)} "
                  "— orders touching these names will be dropped")
        if (premarket_payload.get("vix") or {}).get("flag"):
            print("[run_live] premarket VIX flag set — review report after run")

    # Build and run the executor
    executor = _build_executor(mode)
    notes: list[str] = []
    if premarket_payload:
        notes.append(
            f"premarket scan: {len(premarket_payload.get('tickers', {}))} held "
            f"tickers, {len(premarket_payload.get('halt_recommendations', []))} "
            "halt-recommendations"
        )
    try:
        summary = executor.execute_day(target_date, skips=skips)
    except PreflightSkipped as e:
        skip_summary = ExecutionSummary(
            mode=mode, as_of_date=target_date, fill_date=None,
            skipped=True, skipped_reason=e.reason,
            halt_set=e.set_halt,
            halt_reason=(_halt_payload() or {}).get("reason") if e.set_halt else None,
            notes=notes,
        )
        _log_skip_summary(skip_summary)
        _safe_report(skip_summary, premarket_payload=premarket_payload)
        return 0 if not e.set_halt else 1, skip_summary
    except Exception as e:  # noqa: BLE001 — top-level catch for any executor failure
        err_summary = ExecutionSummary(
            mode=mode, as_of_date=target_date, fill_date=None,
            skipped=True,
            skipped_reason=f"executor raised {type(e).__name__}: {e}",
            notes=notes + ["traceback:\n" + traceback.format_exc()],
        )
        _log_skip_summary(err_summary)
        _safe_report(err_summary, premarket_payload=premarket_payload)
        return 2, err_summary

    # Carry premarket scan notes into the summary for the report.
    if notes or summary.notes:
        summary = _augment_notes(summary, notes)
    _log_skip_summary(summary)
    _safe_report(summary, premarket_payload=premarket_payload)
    return (1 if summary.halt_set else 0), summary


def _augment_notes(s: ExecutionSummary, notes: list[str]) -> ExecutionSummary:
    """ExecutionSummary is frozen — return a copy with combined notes."""
    from dataclasses import replace

    return replace(s, notes=list(s.notes) + notes)


def _safe_report(summary: ExecutionSummary, *, premarket_payload: dict | None) -> None:
    """Generate the daily report + HTML dashboard. Never let either failure crash the run."""
    try:
        ctx = daily_report.ReportContext(premarket_payload=premarket_payload)
        out = daily_report.generate(summary, context=ctx)
        print(f"[run_live] wrote daily report → {out}")
    except Exception as e:  # noqa: BLE001
        print(f"[run_live] daily_report.generate failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
    # Dashboard refresh is a separate try-block — a broken dashboard
    # should never block the daily-report write that happens before it.
    try:
        # dashboard always builds both paper + real tabs from one DB scan.
        out = dashboard.build()
        print(f"[run_live] refreshed dashboard → {out}")
    except Exception as e:  # noqa: BLE001
        print(f"[run_live] dashboard.build failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", default=None,
                   help="Override EXECUTION_MODE env (default: dhan-paper)")
    p.add_argument("--date", type=date.fromisoformat, default=None,
                   help="Override 'today in IST' (for backfill / replay)")
    args = p.parse_args(argv)
    code, _ = run(mode=args.mode, today_ist=args.date)
    return code


if __name__ == "__main__":
    sys.exit(main())
