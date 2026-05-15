"""Daily cron entry-point: keep the DhanHQ access token alive.

DhanHQ self-generated tokens expire after 24h but can be renewed any time
while still active, yielding a fresh 24h token. This script:

  1. Reads DHAN_ACCESS_TOKEN from .env
  2. Validates it via /v2/profile (also yields dhanClientId + expiry)
  3. Renews it via /v2/RenewToken
  4. Atomically writes the new token back into .env
  5. (optional) also persists DHAN_CLIENT_ID if it wasn't set

Run it daily, comfortably inside the 24h window — the launchd plist fires
at ~08:45 IST, before the 09:00 premarket scan. If the token has already
lapsed (laptop off > 24h), renewal fails with a clear message and you must
regenerate manually at web.dhan.co — then this resumes automatically.

Exit codes:
  0  token valid and renewed (or already fresh and renewed)
  1  token expired/invalid — manual regeneration required
  2  network / unexpected error (cron should alert, retry next run)
  3  .env missing DHAN_ACCESS_TOKEN

Usage:
  uv run python -m scripts.dhan_token_refresh
  uv run python -m scripts.dhan_token_refresh --check-only   # validate, don't renew
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from brokers.dhan_token import (
    read_env_var,
    renew_token,
    update_env_var,
    validate_token,
)

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", default=str(ENV_PATH), help="path to .env")
    p.add_argument(
        "--check-only",
        action="store_true",
        help="validate the token and print its expiry; do not renew",
    )
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    env_path = Path(args.env)

    token = read_env_var(env_path, "DHAN_ACCESS_TOKEN")
    if not token or token.startswith("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.example"):
        logger.error(
            "DHAN_ACCESS_TOKEN not set (or still the placeholder) in %s — "
            "generate one at https://web.dhan.co and paste it in.",
            env_path,
        )
        return 3

    # 1. Validate
    status = validate_token(token)
    if not status.valid:
        logger.error(
            "token validation failed: %s. The 24h token has likely lapsed; "
            "regenerate at https://web.dhan.co and re-paste into .env, then "
            "this cron resumes automatically.",
            status.error,
        )
        return 1

    now = datetime.now()
    if status.expires_at:
        remaining = status.expires_at - now
        hrs = remaining.total_seconds() / 3600.0
        logger.info(
            "token valid; client=%s expires=%s (~%.1fh remaining)",
            status.dhan_client_id, status.token_validity, hrs,
        )
    else:
        logger.info(
            "token valid; client=%s (expiry unparseable: %r)",
            status.dhan_client_id, status.token_validity,
        )

    # Persist client id if absent (RenewToken needs it; profile gave it to us)
    if status.dhan_client_id and not read_env_var(env_path, "DHAN_CLIENT_ID"):
        update_env_var(env_path, "DHAN_CLIENT_ID", status.dhan_client_id)
        logger.info("wrote DHAN_CLIENT_ID=%s to .env", status.dhan_client_id)

    if args.check_only:
        print(
            f"VALID  client={status.dhan_client_id}  "
            f"expires={status.token_validity}"
        )
        return 0

    # 2. Renew
    client_id = status.dhan_client_id or read_env_var(env_path, "DHAN_CLIENT_ID")
    if not client_id:
        logger.error("cannot renew: no dhanClientId from profile or .env")
        return 2
    result = renew_token(token, client_id)
    if not result.ok:
        logger.error("renew failed: %s", result.error)
        # Token is still valid (renew failed, not expired) — not fatal; the
        # existing token works until its original expiry. Next cron retries.
        return 2

    # 3. Persist new token atomically
    update_env_var(env_path, "DHAN_ACCESS_TOKEN", result.new_access_token)
    logger.info(
        "token renewed and written to .env; new expiry=%s", result.expiry_time
    )
    print(f"RENEWED  client={result.dhan_client_id}  new_expiry={result.expiry_time}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
