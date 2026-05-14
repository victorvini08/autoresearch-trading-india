import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from llm.provider import ClaudeCodeProvider, CodexProvider


def test_claude_provider_uses_subprocess(monkeypatch):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = '{"regime": "risk_off"}\n'
    fake.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)

    p = ClaudeCodeProvider(claude_bin="/usr/bin/fake-claude")
    out = p.classify("test prompt")
    assert out == '{"regime": "risk_off"}'


def test_claude_provider_raises_on_missing_cli(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="not found on PATH"):
        ClaudeCodeProvider()


def test_claude_provider_raises_on_nonzero_exit(monkeypatch):
    fake = MagicMock()
    fake.returncode = 2
    fake.stdout = ""
    fake.stderr = "auth required"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)

    p = ClaudeCodeProvider(claude_bin="/usr/bin/fake-claude")
    with pytest.raises(RuntimeError, match="exit 2"):
        p.classify("test")


def test_claude_provider_raises_on_timeout(monkeypatch):
    def raises_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=5)
    monkeypatch.setattr("subprocess.run", raises_timeout)

    p = ClaudeCodeProvider(claude_bin="/usr/bin/fake-claude")
    with pytest.raises(RuntimeError, match="timed out"):
        p.classify("test", timeout=5)


def test_claude_provider_passes_model_flag_to_cli(monkeypatch):
    """`model=` kwarg → `--model X` appended to subprocess argv. The model_id
    must include the model name so cache rows from different model tiers do
    not collide."""
    captured: dict = {}

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        out = MagicMock()
        out.returncode = 0
        out.stdout = "ok"
        out.stderr = ""
        return out

    monkeypatch.setattr("subprocess.run", fake_run)

    p = ClaudeCodeProvider(claude_bin="/usr/bin/fake-claude", model="claude-sonnet-4-6")
    assert p.model_id == "claude-code-claude-sonnet-4-6"

    p.classify("hi")
    cmd = captured["cmd"]
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-4-6"


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="`claude` CLI not on PATH",
)
def test_claude_provider_real_shellout_returns_nonempty():
    """Live integration: a real `claude -p` call returns a non-empty string."""
    p = ClaudeCodeProvider()
    out = p.classify('Reply with the single word "ok" and nothing else.')
    assert isinstance(out, str)
    assert len(out) > 0


def test_codex_provider_returns_last_message_file_contents(monkeypatch):
    """Codex's stdout is the agent transcript (verbose, hard to parse). Our
    design uses --output-last-message FILE to get just the final message;
    classify() reads that file. This test protects that contract: if someone
    later switches to stdout parsing, this fails and forces a deliberate
    decision."""
    written_path = {}

    def fake_run(cmd, *a, **kw):
        # Find the --output-last-message FILE pair in argv and write our
        # canned final message there, simulating what codex would do.
        idx = cmd.index("--output-last-message")
        path = Path(cmd[idx + 1])
        path.write_text("FINAL MESSAGE FROM CODEX\n")
        written_path["path"] = path

        out = MagicMock()
        out.returncode = 0
        out.stdout = "(verbose agent transcript that we ignore)"
        out.stderr = ""
        return out

    monkeypatch.setattr("subprocess.run", fake_run)

    p = CodexProvider(codex_bin="/usr/bin/fake-codex")
    out = p.classify("hi")
    assert out == "FINAL MESSAGE FROM CODEX"

    # Also: the tempfile must be cleaned up after the call (no leaks).
    assert not written_path["path"].exists()


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("codex") is None,
    reason="`codex` CLI not on PATH",
)
def test_codex_provider_real_shellout_returns_nonempty():
    """Live integration: a real `codex exec` call returns a non-empty string."""
    p = CodexProvider()
    out = p.classify('Reply with the single word "ok" and nothing else.')
    assert isinstance(out, str)
    assert len(out) > 0
