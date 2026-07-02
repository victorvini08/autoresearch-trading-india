"""End-to-end minimal example: a DataProvider + a StrategyBase run through the
library's backtest engine on synthetic data. Touches no real storage.

    uv run python examples/minimal/run.py
"""

from datetime import date

from autoresearch.backtest.engine import run_backtest

# Local example modules (this directory is on sys.path when run as a script).
from provider import SyntheticDataProvider
from strategy import MinimalMomentum


def main() -> None:
    provider = SyntheticDataProvider()
    universe = provider.pit_universe(date(2019, 1, 1), size=30)
    feeds = provider.read_prices(universe, date(2019, 1, 1), date(2022, 12, 31))

    result = run_backtest(MinimalMomentum, feeds, initial_cash=50_000.0)

    print(f"universe size : {len(feeds)} tickers")
    print(f"final value   : {result['final_value']:,.2f}")
    print(f"total return  : {result['final_value'] / 50_000.0 - 1:+.2%}")
    print(f"trades        : {result['trade_count']}")
    print("\nThis ran the MinimalMomentum(StrategyBase) through the engine using")
    print("bars from SyntheticDataProvider(DataProvider) — the two extension")
    print("points wired together. Swap either for your own market/strategy.")


if __name__ == "__main__":
    main()
