"""Typed configuration for an autoresearch trading system.

The India/Dhan defaults reproduce the current locked behavior EXACTLY — every
field equals the constant it replaces (asserted in tests/test_config.py). A
downstream user overrides only what their market/broker/account requires.

Nothing here introduces a new strategy knob (respecting the parsimony budget);
these are deployment/wiring settings that were previously hardcoded across
prepare.py, strategy.py, the ingest modules, and the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Repo root = parent of the autoresearch package (this file is autoresearch/config.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent


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

    # --- editable user artifacts (autoresearch loop targets) ---
    repo_root: Path = _REPO_ROOT
    strategy_path: Path = _REPO_ROOT / "strategy.py"
    journal_path: Path = _REPO_ROOT / "journal.md"

    # --- storage (data stores live at repo-root storage/) ---
    storage_dir: Path = _REPO_ROOT / "storage"

    def db(self, name: str) -> Path:
        """Absolute path to a DuckDB/SQLite store under the storage dir."""
        return self.storage_dir / name


DEFAULT_CONFIG = Config()
