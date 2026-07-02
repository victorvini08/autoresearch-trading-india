"""Config defaults reproduce the current locked constants exactly (no drift)."""

from datetime import date

from autoresearch.config import Config, DEFAULT_CONFIG
import autoresearch.research.prepare as prep
import strategy as strat


def test_defaults_match_prepare_constants():
    c = Config()
    assert c.initial_cash == prep.INITIAL_CASH == 50_000.0
    assert c.backtest_start == prep.BACKTEST_START == date(2017, 7, 1)
    assert c.backtest_end == prep.BACKTEST_END == date(2026, 5, 14)
    assert c.test_boundary == prep.TEST_BOUNDARY == date(2025, 1, 1)
    assert c.warmup_calendar_days == prep.WARMUP_CALENDAR_DAYS == 520


def test_defaults_match_strategy_constants():
    c = Config()
    assert c.annual_vol_target == strat._ANNUAL_VOL_TARGET == 0.12
    assert c.max_name_weight == strat._MAX_NAME_WEIGHT == 0.10
    assert c.rebalance_parity == strat._REBALANCE_PARITY == 0


def test_db_paths_resolve_under_storage():
    c = Config()
    assert c.db("prices.duckdb").name == "prices.duckdb"
    assert c.db("prices.duckdb").parent == c.storage_dir
    assert c.storage_dir == c.repo_root / "storage"


def test_editable_artifacts_at_repo_root():
    c = Config()
    assert c.strategy_path == c.repo_root / "strategy.py"
    assert c.journal_path == c.repo_root / "journal.md"


def test_ingest_paths_now_absolute_under_repo_storage():
    # The ingest modules were CWD-relative; they must now point at repo-root storage.
    from autoresearch.data import ingest_prices, universe
    assert ingest_prices.DB_PATH == DEFAULT_CONFIG.db("prices.duckdb")
    assert universe.DEFAULT_UNIVERSE_DB == DEFAULT_CONFIG.db("universe.duckdb")
