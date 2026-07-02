# Minimal example

The smallest end-to-end wiring of the two most common extension points, on
**synthetic data** (no real market data, no credentials, touches no `storage/`):

- `strategy.py` — `MinimalMomentum(StrategyBase)`: toy cross-sectional momentum,
  trading only through `order_target_percent`.
- `provider.py` — `SyntheticDataProvider(DataProvider)`: implements `read_prices`
  and `pit_universe` against the deterministic synthetic generator.
- `run.py` — wires them through `autoresearch.backtest.engine.run_backtest` and
  prints the result.

Run it:

```bash
uv run python examples/minimal/run.py
```

Expected output is a few lines: universe size, final value, total return, and
trade count. To build your own system, replace `SyntheticDataProvider` with a
`DataProvider` for your market and `MinimalMomentum` with your own
`StrategyBase` subclass.
