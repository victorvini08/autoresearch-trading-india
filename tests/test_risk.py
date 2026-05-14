import pandas as pd

from backtest.risk import (
    MAX_DRAWDOWN_FRAC,
    MAX_GROSS_EXPOSURE,
    MIN_TRADES,
    validate,
)


def _equity_with_dd(peak: float, trough: float, n: int = 100) -> pd.Series:
    half = n // 2
    return pd.Series([peak] * half + [trough] * (n - half))


def _ok_equity(n: int = 100) -> pd.Series:
    """Monotonic-up equity. CAGR ~26%, DD = 0. Clean baseline curve."""
    return pd.Series([100_000.0 + i * 100 for i in range(n)])


def _ok_trades(n_trades: int = 25, max_pos: float = 0.05) -> pd.DataFrame:
    return pd.DataFrame({
        "pnl": [1.0] * n_trades,
        "order_value_usd": [5000] * n_trades,
        "max_position_frac": [max_pos] * n_trades,
    })


def _ok_positions(max_gross: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame({"max_gross_frac": [max_gross]})


def test_passes_when_clean():
    result = validate(_ok_trades(), _ok_equity(), _ok_positions())
    assert result == {"passed": True, "violations": []}


def test_too_few_trades():
    trades = _ok_trades(n_trades=5)  # 5 < MIN_TRADES (20)
    result = validate(trades, _equity_with_dd(100_000, 95_000), _ok_positions())
    assert result["passed"] is False
    assert any("min trades" in v.lower() for v in result["violations"])


def test_drawdown_violation_only_on_catastrophe():
    """A 60% drawdown crosses the 50% catastrophe gate."""
    eq = _equity_with_dd(100_000, 40_000)  # 60% DD > 50% catastrophe cap
    result = validate(_ok_trades(), eq, _ok_positions())
    assert result["passed"] is False
    assert any("drawdown" in v.lower() for v in result["violations"])


def test_drawdown_below_catastrophe_passes():
    """A 30% drawdown is in the comfort zone — informational, not a gate."""
    eq = _equity_with_dd(100_000, 70_000)  # 30% DD < 50% catastrophe cap
    result = validate(_ok_trades(), eq, _ok_positions())
    assert result["passed"] is True


def test_gross_exposure_violation():
    positions = _ok_positions(max_gross=1.50)  # 150% > 100% — leverage error
    result = validate(_ok_trades(), _ok_equity(), positions)
    assert result["passed"] is False
    assert any("gross" in v.lower() for v in result["violations"])


def test_position_concentration_no_longer_a_gate():
    """Phase-2 (2026-05-09): position concentration is informational only.
    A trade with 30% peak position frac would have rejected under v1; now
    it passes as long as catastrophe gates clear."""
    trades = _ok_trades()
    trades.loc[0, "max_position_frac"] = 0.30  # well past old 10% cap
    result = validate(trades, _ok_equity(), _ok_positions())
    assert result["passed"] is True


def test_calmar_no_longer_a_gate():
    """Phase-2: Calmar is informational only. A flat-then-drop curve with
    negative CAGR (would have triggered v1's MIN_CALMAR=0.7 gate) passes
    as long as DD is below catastrophe."""
    eq = _equity_with_dd(100_000, 95_000)  # 5% DD, ends -5% → negative Calmar
    result = validate(_ok_trades(), eq, _ok_positions())
    assert result["passed"] is True


def test_multiple_catastrophes_all_reported():
    eq = _equity_with_dd(100_000, 40_000)  # 60% DD
    trades = _ok_trades(n_trades=5)        # also too few trades
    result = validate(trades, eq, _ok_positions())
    assert result["passed"] is False
    assert len(result["violations"]) >= 2


def test_constants_match_phase2_spec():
    """Lock the phase-2 catastrophe-only constants."""
    assert MAX_GROSS_EXPOSURE == 1.00
    assert MAX_DRAWDOWN_FRAC == 0.50
    assert MIN_TRADES == 20


def test_trade_count_override_bypasses_len_trades():
    """When trades is a placeholder DataFrame, prepare.py passes the real
    count via trade_count= so the gate fires correctly."""
    placeholder_trades = pd.DataFrame({
        "pnl": [], "order_value_usd": [], "max_position_frac": []
    })
    eq = _ok_equity()
    positions = _ok_positions()

    # Without override: len(placeholder)=0 < 20, fails
    r = validate(placeholder_trades, eq, positions)
    assert r["passed"] is False

    # With override saying 25 trades happened: passes
    r = validate(placeholder_trades, eq, positions, trade_count=25)
    assert r["passed"] is True


def test_max_dd_override_bypasses_curve_calc():
    """prepare.py supplies the chained-fold aggregate DD via override."""
    eq = _ok_equity()                       # passes natural DD
    positions = _ok_positions()
    trades = _ok_trades()

    # Override with 60% DD → fails the catastrophe gate
    r = validate(trades, eq, positions, max_dd=0.60)
    assert r["passed"] is False
    assert any("drawdown" in v.lower() for v in r["violations"])

    # Override with 30% DD → passes
    r = validate(trades, eq, positions, max_dd=0.30)
    assert r["passed"] is True
