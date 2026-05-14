"""CLI for the system-wide halt flag."""
from __future__ import annotations

import json

import pytest

from scripts import halt
from storage import portfolio_db


@pytest.fixture
def halt_isolation(tmp_path, monkeypatch):
    """Redirect halt.json to a tmp file so tests don't touch real state."""
    halt_file = tmp_path / "halt.json"
    monkeypatch.setattr(halt, "HALT_FILE_PATH", halt_file)
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)
    return halt_file


def test_set_writes_json_with_token(halt_isolation):
    payload = halt.set_halt("test halt")
    assert halt_isolation.exists()
    on_disk = json.loads(halt_isolation.read_text())
    assert on_disk["reason"] == "test halt"
    assert on_disk["resume_token"] == payload["resume_token"]
    assert "set_at" in on_disk
    assert on_disk["set_by"] == "manual"


def test_clear_with_matching_token(halt_isolation):
    payload = halt.set_halt("test")
    assert halt.clear_halt(token=payload["resume_token"]) is True
    assert not halt_isolation.exists()


def test_clear_with_mismatching_token_refuses(halt_isolation):
    halt.set_halt("test")
    with pytest.raises(ValueError, match="resume_token mismatch"):
        halt.clear_halt(token="WRONG")
    assert halt_isolation.exists()


def test_clear_with_force_bypasses_token(halt_isolation):
    halt.set_halt("test")
    assert halt.clear_halt(force=True) is True
    assert not halt_isolation.exists()


def test_clear_when_no_halt_returns_false(halt_isolation):
    assert halt.clear_halt(force=True) is False


def test_show_returns_none_when_clear(halt_isolation):
    assert halt.show_halt() is None


def test_show_returns_payload_when_set(halt_isolation):
    halt.set_halt("inspect me")
    payload = halt.show_halt()
    assert payload is not None
    assert payload["reason"] == "inspect me"


def test_cli_set_then_clear(halt_isolation, capsys):
    rc = halt.main(["set", "via CLI"])
    assert rc == 0
    out = capsys.readouterr().out
    # token is printed; extract it
    token_line = next(line for line in out.splitlines() if "resume_token:" in line)
    token = token_line.split("resume_token:")[1].strip()

    rc = halt.main(["clear", "--token", token])
    assert rc == 0
    assert not halt_isolation.exists()


def test_cli_clear_wrong_token_returns_nonzero(halt_isolation):
    halt.set_halt("first")
    rc = halt.main(["clear", "--token", "bogus"])
    assert rc == 2
    assert halt_isolation.exists()  # still set


def test_cli_show_when_clear_returns_1(halt_isolation):
    # `halt show` exits 1 when no halt is set — useful for scripting
    rc = halt.main(["show"])
    assert rc == 1
