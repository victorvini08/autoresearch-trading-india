"""Smoke test: confirms pytest discovers tests and core deps import cleanly."""


def test_pytest_discovers_tests():
    assert True


def test_core_deps_importable():
    import backtrader  # noqa: F401
    import duckdb  # noqa: F401
    # FRED is consumed via direct `requests` calls (not the `fredapi` wrapper)
    import requests  # noqa: F401
    import pandas  # noqa: F401
    import yfinance  # noqa: F401
