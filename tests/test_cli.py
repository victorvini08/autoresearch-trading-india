"""The unified `autoresearch` CLI is the post-install front door."""

import subprocess
import sys

from autoresearch import __version__
from autoresearch.cli import main


def test_bare_command_prints_getting_started(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Get started" in out
    assert "autoresearch init" in out


def test_version_subcommand(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == __version__


def test_unknown_command_shows_help_and_errors(capsys):
    rc = main(["frobnicate"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "unknown command" in out


def test_python_m_autoresearch_runs():
    r = subprocess.run(
        [sys.executable, "-m", "autoresearch"], capture_output=True, text=True
    )
    assert r.returncode == 0
    assert "Get started" in r.stdout
