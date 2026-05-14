"""Read-only Dhan smoke test.

Calls `get_cash`, `get_positions`, `get_holdings`, `list_today_orders` —
no order placement, no state mutation. Useful for confirming the access
token + client ID + scrip-master cache are working before the first
live-paper run.

Usage:
    DHAN_MOCK=0 uv run python -m scripts.dhan_smoke    # against real Dhan
    DHAN_MOCK=1 uv run python -m scripts.dhan_smoke    # against mock

Returns non-zero exit code if any call raises.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    use_mock = os.environ.get("DHAN_MOCK", "1") in ("1", "true", "True")
    if use_mock:
        from brokers.dhan_mock import DhanMock
        from pathlib import Path

        broker = DhanMock(
            prices_db=Path(os.environ.get("PRICES_DB", "storage/prices.duckdb")),
            initial_cash_inr=float(os.environ.get("PAPER_INITIAL_CASH", "50000")),
        )
        print("== DhanMock (paper) ==")
    else:
        from brokers.dhan import DhanBroker

        broker = DhanBroker()
        print("== Dhan (live) ==")

    try:
        broker.connect()
    except Exception as e:
        print(f"connect failed: {e}", file=sys.stderr)
        return 2

    try:
        cash = broker.get_cash()
        print("\n--- cash ---")
        print(json.dumps(cash, indent=2, default=str))

        print("\n--- positions ---")
        for p in broker.get_positions():
            print(json.dumps(asdict(p), indent=2, default=str))

        print("\n--- holdings ---")
        for p in broker.get_holdings():
            print(json.dumps(asdict(p), indent=2, default=str))

        print("\n--- today's orders ---")
        for o in broker.list_today_orders():
            print(f"{o.order_id:24s} {o.status}")
    except Exception as e:
        print(f"smoke test failed: {e}", file=sys.stderr)
        return 3
    finally:
        broker.disconnect()

    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
