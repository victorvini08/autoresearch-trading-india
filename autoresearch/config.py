"""Typed configuration for an autoresearch trading system.

The India/Dhan defaults reproduce the current locked behavior EXACTLY — every
field equals the constant it replaces (asserted in tests/test_config.py). A
downstream user overrides only what their market/broker/account requires.

Nothing here introduces a new strategy knob (respecting the parsimony budget);
these are deployment/wiring settings that were previously hardcoded across
prepare.py, strategy.py, the ingest modules, and the loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

@dataclass(frozen=True)
class Config:
    # --- account / market ---
    currency: str = "INR"
    initial_cash: float = 50_000.0          # == prepare.INITIAL_CASH
    universe_size: int = 200
    mock: bool = True                        # DHAN_MOCK default (paper)

    # --- strategy construction (defaults mirror strategy.py module constants) ---
    annual_vol_target: float = 0.12          # == strategy._ANNUAL_VOL_TARGET
    max_name_weight: float = 0.10            # == strategy._MAX_NAME_WEIGHT
    rebalance_parity: int = 0                # == strategy._REBALANCE_PARITY

    # --- evaluator window (defaults mirror prepare.py) ---
    backtest_start: date = date(2017, 7, 1)  # == prepare.BACKTEST_START
    backtest_end: date = date(2026, 5, 14)   # == prepare.BACKTEST_END
    test_boundary: date = date(2025, 1, 1)   # == prepare.TEST_BOUNDARY
    warmup_calendar_days: int = 520          # == prepare.WARMUP_CALENDAR_DAYS

    # --- editable user artifacts + storage ---
    # Resolved relative to the CURRENT working directory. So an installed user's
    # OWN project files are used when they run commands from their project dir (a
    # scaffolded project), and the reference repo — run from its root — resolves
    # to the repo's own files, exactly as the original layout did.
    repo_root: Path = Path(".")
    strategy_path: Path = Path("strategy.py")
    journal_path: Path = Path("journal.md")
    storage_dir: Path = Path("storage")

    def db(self, name: str) -> Path:
        """Path to a DuckDB/SQLite store under the storage dir (relative to CWD)."""
        return self.storage_dir / name


DEFAULT_CONFIG = Config()
