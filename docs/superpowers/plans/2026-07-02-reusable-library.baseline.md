# Pinned test baseline — reusable-library refactor

Captured 2026-07-02 on branch `library-refactor` **before any source changes**
(only spec + plan docs added). The suite is **red for pre-existing reasons**
(confirmed by the user: stale local DB/data state, not logic). Per user decision
(option 1), the refactor's behavior-preservation gate is:

> **No NEW failures beyond this pinned set.** These exact tests may stay red;
> everything else that passes now must keep passing. Do NOT delete these tests.

## Known-failing (13) — pinned, allowed to remain red

- tests/test_ingest_prices_legacy.py::test_legacy_parse_returns_1502_eq_bars
- tests/test_ingest_prices_legacy.py::test_legacy_parse_excludes_non_eq_series
- tests/test_precompute_macro.py::test_trading_days_filters_to_nifty
- tests/test_precompute_macro.py::test_main_processes_all_days_via_chunked_calls
- tests/test_precompute_macro.py::test_main_continues_on_per_chunk_failure_and_returns_2
- tests/test_precompute_macro.py::test_main_exits_1_when_no_trading_days_found
- tests/test_reconciliation.py::test_drawdown_thresholds[0.09-warn-WATCH]
- tests/test_reconciliation.py::test_drawdown_thresholds[0.13-flag-RISK_REDUCED]
- tests/test_reconciliation.py::test_construction_drag_zero_when_targets_match_positions
- tests/test_run_live.py::test_outside_window_skips_in_live_mode
- tests/test_safety_evaluator.py::test_RISK_REDUCED_writes_multiplier_half
- tests/test_strategy_reversion.py::test_single_strategy_class_is_residual_reversal
- tests/test_warmup_scoring.py::test_strategy_trades_when_warmed

## Also pre-existing (not failures, informational)
- XFAIL: tests/test_engine.py::test_trade_recorder_populates_rows_on_uptrend
- XPASS: tests/test_e2e.py::test_e2e_research_mode_runs_end_to_end
- SKIPPED: classify_* (need CLI/API keys), strategy_earn_tilt, strategy_pead_gate

## How to check "no new failures" cheaply
Run the full suite ONCE and diff the FAILED set against the 13 above:
`uv run pytest -q 2>&1 | grep -E "^FAILED" | sort`
The set must be a subset of the pinned list. Avoid re-running repeatedly.
