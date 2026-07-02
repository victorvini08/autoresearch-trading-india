"""DhanHQ access-token lifecycle: validate + renew + persist to .env.

DhanHQ self-generated tokens (from web.dhan.co) are valid **24 hours**. There
is a renewal endpoint that, given a *currently-active* token, returns a fresh
token with another 24h of validity and expires the old one:

  Validate / get expiry:  GET  https://api.dhan.co/v2/profile
                          header: access-token
                          → {dhanClientId, tokenValidity ("DD/MM/YYYY HH:MM")}

  Renew:                  GET  https://api.dhan.co/v2/RenewToken
                          headers: access-token, dhanClientId
                          → {createTime, expiryTime, token}
                          (NOTE: it's a GET despite "renew" semantics, and
                           the new JWT is the `token` field — verified live
                           2026-05-15. The docs' curl example has no -X/-d,
                           which curl treats as GET.)

Constraint: renewal works ONLY on an active token. An expired token cannot be
renewed — it must be regenerated manually at web.dhan.co. Therefore the cron
must refresh well within the 24h window (we run it daily ~08:45 IST).

This module is intentionally dependency-light (requests only) so the refresh
cron can run even if other parts of the system are broken.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DHAN_BASE = "https://api.dhan.co"
PROFILE_ENDPOINT = f"{DHAN_BASE}/v2/profile"
RENEW_ENDPOINT = f"{DHAN_BASE}/v2/RenewToken"

_TOKEN_VALIDITY_FMT = "%d/%m/%Y %H:%M"


@dataclass(frozen=True)
class TokenStatus:
    valid: bool
    dhan_client_id: str | None
    token_validity: str | None        # raw "DD/MM/YYYY HH:MM" from /v2/profile
    expires_at: datetime | None       # parsed; None if unparseable
    error: str | None = None


@dataclass(frozen=True)
class RenewResult:
    ok: bool
    new_access_token: str | None
    expiry_time: str | None
    dhan_client_id: str | None
    error: str | None = None


def validate_token(access_token: str, timeout: int = 15) -> TokenStatus:
    """Call /v2/profile to confirm the token is live and read its expiry.

    Read-only. Never mutates anything. Returns TokenStatus(valid=False, ...)
    on any HTTP / parse error rather than raising — the caller (cron) decides
    how to react.
    """
    try:
        resp = requests.get(
            PROFILE_ENDPOINT,
            headers={"access-token": access_token, "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        return TokenStatus(False, None, None, None, error=f"network: {e}")

    if resp.status_code == 401:
        return TokenStatus(False, None, None, None, error="401 unauthorized (token expired/invalid)")
    if resp.status_code >= 400:
        return TokenStatus(
            False, None, None, None,
            error=f"HTTP {resp.status_code}: {resp.text[:200]}",
        )
    try:
        body = resp.json()
    except ValueError:
        return TokenStatus(False, None, None, None, error="non-JSON profile response")

    client_id = body.get("dhanClientId")
    validity = body.get("tokenValidity")
    expires_at: datetime | None = None
    if validity:
        try:
            expires_at = datetime.strptime(validity, _TOKEN_VALIDITY_FMT)
        except ValueError:
            logger.warning("could not parse tokenValidity %r", validity)
    return TokenStatus(
        valid=True,
        dhan_client_id=str(client_id) if client_id is not None else None,
        token_validity=validity,
        expires_at=expires_at,
    )


def renew_token(
    access_token: str,
    dhan_client_id: str,
    timeout: int = 15,
) -> RenewResult:
    """Call /v2/RenewToken with the (active) token. Returns the fresh token.

    Per Dhan docs this expires the supplied token and issues a new one with
    another 24h of validity. Only works while the supplied token is active.
    """
    try:
        # RenewToken is a GET (the docs' curl example has no -X/-d → GET).
        resp = requests.get(
            RENEW_ENDPOINT,
            headers={
                "access-token": access_token,
                "dhanClientId": str(dhan_client_id),
                "Accept": "application/json",
            },
            timeout=timeout,
        )
    except requests.RequestException as e:
        return RenewResult(False, None, None, None, error=f"network: {e}")

    if resp.status_code >= 400:
        return RenewResult(
            False, None, None, None,
            error=f"HTTP {resp.status_code}: {resp.text[:300]}",
        )
    try:
        body = resp.json()
    except ValueError:
        return RenewResult(False, None, None, None, error="non-JSON renew response")

    # Live response shape (verified 2026-05-15):
    #   {"createTime": "...", "expiryTime": "...", "token": "<new JWT>"}
    new_token = body.get("token") or body.get("accessToken")
    if not new_token:
        return RenewResult(
            False, None, None, None,
            error=f"renew response missing token: {body}",
        )
    return RenewResult(
        ok=True,
        new_access_token=new_token,
        expiry_time=body.get("expiryTime"),
        dhan_client_id=str(body.get("dhanClientId") or dhan_client_id),
    )


# ──────────────────────────────────────────────────────────────────────
# .env persistence
# ──────────────────────────────────────────────────────────────────────


def update_env_var(env_path: Path, key: str, value: str) -> None:
    """Atomically rewrite a single KEY=value line in `env_path`.

    Preserves all other lines (comments, blank lines, other vars). If the key
    isn't present, appends it. Atomic via temp-file + os.replace so a crash
    mid-write never corrupts .env.
    """
    lines: list[str] = []
    found = False
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    content = "\n".join(out) + "\n"

    fd, tmp = tempfile.mkstemp(
        dir=str(env_path.parent), prefix=".env.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, env_path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_env_var(env_path: Path, key: str) -> str | None:
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        s = line.strip()
        if s.startswith(f"{key}="):
            return s.split("=", 1)[1].strip()
    return None


__all__ = [
    "TokenStatus",
    "RenewResult",
    "validate_token",
    "renew_token",
    "update_env_var",
    "read_env_var",
    "PROFILE_ENDPOINT",
    "RENEW_ENDPOINT",
]
