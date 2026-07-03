"""`autoresearch-init` scaffolds a project that runs out of the box."""

import subprocess
import sys

import pytest

from autoresearch.scaffold import scaffold

_EXPECTED = [
    "strategy.py", "provider.py", "run.py", "config.py",
    "journal.md", "README.md", ".gitignore", ".env.example",
]


def test_scaffold_writes_all_files(tmp_path):
    proj = tmp_path / "myproj"
    scaffold(proj)
    for name in _EXPECTED:
        assert (proj / name).exists(), f"missing {name}"
    assert (proj / "storage").is_dir()


def test_scaffold_refuses_nonempty_dir(tmp_path):
    existing = tmp_path / "taken"
    existing.mkdir()
    (existing / "keep.txt").write_text("hi")
    with pytest.raises(SystemExit):
        scaffold(existing)


def test_scaffolded_project_runs(tmp_path):
    proj = tmp_path / "myproj"
    scaffold(proj)
    r = subprocess.run(
        [sys.executable, "run.py"], cwd=proj, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    assert "final value" in r.stdout
