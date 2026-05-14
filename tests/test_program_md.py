from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_program_md_exists_and_substantial():
    p = ROOT / "program.md"
    assert p.exists()
    text = p.read_text()
    assert len(text) > 1000, f"program.md should be > 1KB, got {len(text)} bytes"
    assert "Sortino" in text
    assert "strategy.py" in text
    assert "prepare.py" in text


def test_program_md_states_immutability_rule():
    text = (ROOT / "program.md").read_text().lower()
    assert "must not edit" in text or "do not edit" in text or "read-only" in text


def test_program_md_lists_catastrophe_gates():
    """Phase-2 (2026-05-09): only catastrophe gates auto-reject. The agent
    needs to see all three gate values + the DD-regression guard threshold
    so it can reason about when its strategy will be auto-rejected."""
    text = (ROOT / "program.md").read_text()
    # Catastrophe gates (constants from backtest/risk.py)
    assert "100%" in text          # gross exposure
    assert "50%" in text           # aggregate drawdown
    assert "20 trades" in text     # min trades
    # DD-regression guard threshold (from scripts/loop.py KEPT criterion)
    assert "10pp" in text or "10 percentage points" in text
    # Sortino sanity-bounds visible to the agent
    assert "Sortino" in text and "10" in text


def test_journal_md_template_present():
    j = (ROOT / "journal.md").read_text().lower()
    for keyword in ("hypothesis", "change", "result", "learning"):
        assert keyword in j, f"journal.md missing '{keyword}' section"
