"""Run the canonical prepare.py research-mode gates on a module at a chosen
capital, dumping the full result JSON under a distinct name (never clobbers
the eval_variant outputs).

CAPITAL NOTE: prepare.INITIAL_CASH is monkeypatched in THIS process only.
Spawned fold workers re-import prepare (INITIAL_CASH reverts to 50k there),
so any capital other than 50000 REQUIRES PREPARE_MAX_WORKERS=1 — enforced
here with a hard fail rather than a silent wrong-capital run.

Usage:
    PREPARE_MAX_WORKERS=4 uv run python -m experiments.run_gates strategy 50000
    PREPARE_MAX_WORKERS=1 uv run python -m experiments.run_gates strategy 500000
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

import prepare
from prepare import EVALUATOR_VERSION, evaluate

RESULTS = Path("experiments/results")


def main() -> int:
    mod_name = sys.argv[1]
    cash = float(sys.argv[2]) if len(sys.argv) > 2 else 50_000.0
    if cash != 50_000.0 and os.environ.get("PREPARE_MAX_WORKERS") != "1":
        raise SystemExit(
            "capital != 50k requires PREPARE_MAX_WORKERS=1 (spawned fold "
            "workers re-import prepare and would silently run at 50k)"
        )
    prepare.INITIAL_CASH = cash

    mod = importlib.import_module(mod_name)
    res = evaluate(mod, mode="research")

    out = {
        k: v for k, v in res.items()
        if not isinstance(v, (pd.DataFrame, pd.Series))
    }
    out["_module"] = mod_name
    out["_cash"] = cash
    out["_evaluator_version"] = EVALUATOR_VERSION

    RESULTS.mkdir(parents=True, exist_ok=True)
    safe = mod_name.replace(".", "_")
    path = RESULTS / f"gates_ext_{safe}_{int(cash)}.json"
    path.write_text(json.dumps(out, default=str, indent=2))

    ao = res.get("anti_overfit", {})
    print(f"=== EXTENDED-WINDOW GATES: {mod_name} @ Rs{cash:,.0f} "
          f"({EVALUATOR_VERSION}) ===")
    print(f"  validation_sortino_mean : {res.get('validation_sortino_mean')}")
    print(f"  validation_folds        : {res.get('validation_folds')}")
    print(f"  per_fold_sortinos       : {res.get('per_fold_sortinos')}")
    for k in sorted(ao):
        v = ao[k]
        if isinstance(v, float):
            v = round(v, 4)
        print(f"  ao.{k:30}: {v}")
    risk = res.get("risk")
    if risk is not None:
        print(f"  risk                    : {risk}")
    print(f"  written -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
