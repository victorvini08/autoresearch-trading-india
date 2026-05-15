"""Unit tests for brokers.dhan_token — .env rewrite + response parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from brokers.dhan_token import (
    RenewResult,
    TokenStatus,
    read_env_var,
    renew_token,
    update_env_var,
    validate_token,
)


# ── .env atomic rewrite ──


def test_update_env_replaces_only_target_key(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "FRED_API_KEY=abc123\n"
        "DHAN_ACCESS_TOKEN=old_token\n"
        "DHAN_MOCK=1\n"
        "# a comment\n"
    )
    update_env_var(env, "DHAN_ACCESS_TOKEN", "new_token")
    content = env.read_text()
    assert "DHAN_ACCESS_TOKEN=new_token" in content
    assert "FRED_API_KEY=abc123" in content      # preserved
    assert "DHAN_MOCK=1" in content              # preserved
    assert "# a comment" in content              # comment preserved
    assert "old_token" not in content


def test_update_env_appends_when_key_absent(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FRED_API_KEY=abc\n")
    update_env_var(env, "DHAN_CLIENT_ID", "1111664515")
    assert "DHAN_CLIENT_ID=1111664515" in env.read_text()
    assert "FRED_API_KEY=abc" in env.read_text()


def test_update_env_creates_file_if_missing(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    update_env_var(env, "DHAN_ACCESS_TOKEN", "tok")
    assert env.exists()
    assert read_env_var(env, "DHAN_ACCESS_TOKEN") == "tok"


def test_read_env_var(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("A=1\nB = 2\nDHAN_ACCESS_TOKEN=jwt.here\n")
    assert read_env_var(env, "DHAN_ACCESS_TOKEN") == "jwt.here"
    assert read_env_var(env, "A") == "1"
    assert read_env_var(env, "MISSING") is None


def test_update_env_atomic_no_partial_on_repeated_writes(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("DHAN_ACCESS_TOKEN=t0\nKEEP=yes\n")
    for i in range(1, 6):
        update_env_var(env, "DHAN_ACCESS_TOKEN", f"t{i}")
    # Only the final value should be present, exactly once
    lines = [l for l in env.read_text().splitlines() if l.startswith("DHAN_ACCESS_TOKEN=")]
    assert lines == ["DHAN_ACCESS_TOKEN=t5"]
    assert read_env_var(env, "KEEP") == "yes"


# ── validate_token response parsing (network mocked) ──


def _mock_resp(status_code: int, json_body: dict | None = None, text: str = ""):
    m = MagicMock()
    m.status_code = status_code
    m.text = text
    if json_body is not None:
        m.json.return_value = json_body
    else:
        m.json.side_effect = ValueError("no json")
    return m


def test_validate_token_parses_profile() -> None:
    with patch("brokers.dhan_token.requests.get") as g:
        g.return_value = _mock_resp(
            200, {"dhanClientId": "1111664515", "tokenValidity": "16/05/2026 13:36"}
        )
        st = validate_token("sometoken")
    assert st.valid
    assert st.dhan_client_id == "1111664515"
    assert st.token_validity == "16/05/2026 13:36"
    assert st.expires_at is not None
    assert st.expires_at.year == 2026 and st.expires_at.month == 5 and st.expires_at.day == 16


def test_validate_token_401_is_invalid() -> None:
    with patch("brokers.dhan_token.requests.get") as g:
        g.return_value = _mock_resp(401, text="unauthorized")
        st = validate_token("expiredtoken")
    assert not st.valid
    assert "401" in (st.error or "")


def test_validate_token_network_error_is_invalid() -> None:
    import requests

    with patch("brokers.dhan_token.requests.get", side_effect=requests.ConnectionError("down")):
        st = validate_token("tok")
    assert not st.valid
    assert "network" in (st.error or "")


# ── renew_token: GET method + `token` field parsing ──


def test_renew_token_uses_get_and_parses_token_field() -> None:
    with patch("brokers.dhan_token.requests.get") as g:
        g.return_value = _mock_resp(
            200,
            {
                "createTime": "2026-05-15T13:52:37",
                "expiryTime": "2026-05-16T13:52:37",
                "token": "new.jwt.value",
            },
        )
        res = renew_token("oldtoken", "1111664515")
    # Must be a GET (RenewToken is a GET despite the name)
    g.assert_called_once()
    assert res.ok
    assert res.new_access_token == "new.jwt.value"
    assert res.expiry_time == "2026-05-16T13:52:37"


def test_renew_token_http_400_returns_error() -> None:
    with patch("brokers.dhan_token.requests.get") as g:
        g.return_value = _mock_resp(
            400,
            text='{"errorCode":"DH-905","errorMessage":"Missing required fields"}',
        )
        res = renew_token("tok", "cid")
    assert not res.ok
    assert "400" in (res.error or "")


def test_renew_token_missing_token_field() -> None:
    with patch("brokers.dhan_token.requests.get") as g:
        g.return_value = _mock_resp(200, {"createTime": "x", "expiryTime": "y"})
        res = renew_token("tok", "cid")
    assert not res.ok
    assert "missing token" in (res.error or "")
