"""Seed / verify the live ledger's cash so it matches the real Dhan balance.

For dhan-live the ledger anchors cash at ₹0 (_INITIAL_DEPOSIT_BY_MODE), so the
opening capital — and any later top-up — must be recorded as a `deposit` row.
Otherwise `get_cash_balance` goes negative after the first buy and the
equity-curve / dashboard / P&L (all derived from the ledger) are WRONG, even
though the trades (sized off the live broker balance) are correct.

Run at funding time, BEFORE the first rebalance, when the difference equals
exactly the opening capital. After a later top-up, run it again right after
depositing (before the next rebalance).

Usage (on the VM, where the live token + ledger live):
    # read-only: compare ledger cash vs the real broker balance
    DHAN_MOCK=0 uv run python -m scripts.record_deposit check
    # seed the ledger to match the broker NOW (records the difference)
    DHAN_MOCK=0 uv run python -m scripts.record_deposit seed-to-broker
    # record an explicit amount (no broker call; e.g. a known deposit)
    uv run python -m scripts.record_deposit record --amount 50000

    # pooled account: record each contributor separately for an audit trail
    uv run python -m scripts.record_deposit record --amount 20000 --notes "Aryan"
    uv run python -m scripts.record_deposit record --amount 20000 --notes "Friend B"
    uv run python -m scripts.record_deposit record --amount 15000 --notes "Friend C"
    # a later solo top-up: ALSO note the account value before adding (for fair NAV split)
    uv run python -m scripts.record_deposit record --amount 50000 \
        --notes "Aryan top-up; acct value before add = Rs.X"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from storage import portfolio_db
from storage.portfolio_db import (
    _INITIAL_DEPOSIT_BY_MODE,
    connect,
    get_cash_balance,
    record_deposit,
)

MATCH_TOL = 1.0       # ₹ — tolerance for check / seed-to-broker "matched"
RECONCILE_TOL = 0.01  # ₹ — the daily reconcile keeps books exact to the paisa


def _broker_cash() -> float:
    from brokers.dhan import DhanBroker

    return float(DhanBroker().get_cash().get("availableBalance", 0.0))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed/verify live ledger cash vs broker.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "seed-to-broker", "reconcile", "record"):
        sp = sub.add_parser(name)
        sp.add_argument("--mode", default="dhan-live")
        sp.add_argument("--db", type=Path, default=portfolio_db.DEFAULT_DB_PATH)
        if name == "record":
            sp.add_argument("--amount", type=float, required=True,
                            help="deposit ₹ (negative for a withdrawal)")
            sp.add_argument("--notes", default=None,
                            help="audit tag, e.g. contributor name (+ pre-add "
                                 "account value for a mid-stream top-up)")
    args = p.parse_args(argv)

    anchor = _INITIAL_DEPOSIT_BY_MODE.get(args.mode, 0.0)
    if anchor != 0.0:
        print(f"[warn] mode {args.mode} already anchors ₹{anchor:,.0f} in code — "
              f"recording a deposit here DOUBLE-COUNTS. This tool is for ₹0-anchor "
              f"modes (dhan-live). Continuing only if you really meant to.")

    with connect(args.db) as conn:
        ledger = get_cash_balance(conn, mode=args.mode)

        if args.cmd == "record":
            eid = record_deposit(conn, amount_inr=args.amount, mode=args.mode,
                                 notes=args.notes)
            new = get_cash_balance(conn, mode=args.mode)
            print(f"recorded ₹{args.amount:,.2f} ({eid}); "
                  f"ledger cash ₹{ledger:,.2f} -> ₹{new:,.2f}")
            return 0

        # check / seed-to-broker need the live broker
        broker = _broker_cash()
        diff = broker - ledger
        print(f"mode={args.mode}")
        print(f"  broker availableBalance : ₹{broker:,.2f}")
        print(f"  ledger get_cash_balance : ₹{ledger:,.2f}")
        print(f"  difference (broker-ledger): ₹{diff:,.2f}")

        if args.cmd == "check":
            if abs(diff) < MATCH_TOL:
                print("  MATCH ✓ — ledger cash agrees with the broker")
                return 0
            print(f"  MISMATCH ✗ — run `reconcile` (or `seed-to-broker`) to record ₹{diff:,.2f}")
            return 2

        # seed-to-broker (funding true-up, kind=deposit) OR reconcile (the daily
        # broker-truth true-up that absorbs charge-model drift, kind=reconcile).
        # Both record (broker - ledger) so ledger == broker; reconcile uses a
        # tighter tolerance so the books stay exact to the paisa.
        is_reconcile = args.cmd == "reconcile"
        tol = RECONCILE_TOL if is_reconcile else MATCH_TOL
        if abs(diff) < tol:
            print("  in sync; nothing to record")
            return 0
        eid = record_deposit(
            conn, amount_inr=diff, mode=args.mode,
            kind="reconcile" if is_reconcile else "deposit",
            notes=("daily broker-truth reconcile (charge drift)" if is_reconcile
                   else "seed-to-broker: match availableBalance"),
        )
        new = get_cash_balance(conn, mode=args.mode)
        ok = abs(broker - new) < max(tol, 0.01)
        print(f"  recorded ₹{diff:,.2f} ({eid}); ledger now ₹{new:,.2f} "
              f"(broker ₹{broker:,.2f}) -> {'MATCH ✓' if ok else 'STILL OFF ✗'}")
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
