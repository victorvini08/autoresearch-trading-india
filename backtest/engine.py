"""Backtrader cerebro wrapper. Configures the broker with the Dhan delivery
cost model and a percentage-slippage adjustment, runs the strategy across all
feeds, and returns a structured result dict.
"""
from __future__ import annotations

import backtrader as bt
import pandas as pd

from .costs import DEFAULT_SLIPPAGE_BPS, commission_inr


class DhanDeliveryCommission(bt.CommInfoBase):
    """Dhan CNC (delivery) cost model: brokerage ₹0, STT 0.1% (sell),
    DP ₹14.75/scrip (sell), NSE exchange 0.00345%, GST 18%, stamp 0.015%
    (buy). Computed by `backtest.costs.commission_inr`. Applied to every
    simulated fill so the walk-forward Sortino is net of real Indian costs.
    """

    params = (
        ("commtype", bt.CommInfoBase.COMM_FIXED),
        ("stocklike", True),
    )

    def _getcommission(self, size, price, pseudoexec):  # type: ignore[override]
        order_value = abs(size * price)
        side = "BUY" if size >= 0 else "SELL"
        return commission_inr(order_value, side)


class TradeRecorder(bt.Analyzer):
    """Capture one row per closed trade. Hooks notify_trade(isclosed=True).

    Columns (in get_analysis() output):
      ticker, entry_date, exit_date, pnl, pnl_pct, order_value_usd, max_position_frac

    `max_position_frac` is approximate: order_value / (equity_at_close - pnl).
    For 5-day swings on a non-leveraged book this drift is well under 1%.
    """

    def __init__(self) -> None:
        self.trades_list: list[dict] = []

    def notify_trade(self, trade: bt.Trade) -> None:
        if not trade.isclosed:
            return

        # trade.value is 0 once the trade closes (size returned to 0). The entry
        # size lives in trade.history[0]; trade.price holds the avg entry price.
        if not trade.history:
            return
        entry_size = abs(int(trade.history[0].event.size))
        entry_price = float(trade.price)
        order_value = entry_size * entry_price
        if order_value <= 0:
            return

        ticker = trade.data._name
        entry_dt = bt.num2date(trade.dtopen).date()
        exit_dt = bt.num2date(trade.dtclose).date()
        pnl_net = float(trade.pnlcomm)
        pnl_pct = pnl_net / order_value

        equity_at_close = float(self.strategy.broker.get_value())
        equity_at_entry = max(equity_at_close - pnl_net, 1.0)
        pos_frac = order_value / equity_at_entry

        self.trades_list.append({
            "ticker": ticker,
            "entry_date": entry_dt,
            "exit_date": exit_dt,
            "pnl": pnl_net,
            "pnl_pct": pnl_pct,
            "order_value_usd": order_value,
            "max_position_frac": pos_frac,
        })

    def get_analysis(self) -> list[dict]:
        return self.trades_list


class GrossExposureRecorder(bt.Analyzer):
    """Records per-bar gross exposure as a fraction of broker value.

    Long-only cash account should never exceed 1.0; this is the engine-bug /
    accidental-leverage tripwire feeding backtest/risk.py's catastrophe gate
    (the gate was a no-op until this analyzer existed)."""

    def __init__(self) -> None:
        self.daily: list[tuple[object, float]] = []

    def next(self) -> None:
        broker_value = float(self.strategy.broker.get_value())
        if broker_value <= 0:
            return
        gross = 0.0
        for d in self.strategy.datas:
            pos = self.strategy.broker.getposition(d)
            if pos.size == 0:
                continue
            gross += abs(pos.size) * float(d.close[0])
        self.daily.append((
            bt.num2date(self.strategy.data.datetime[0]).date(),
            gross / broker_value,
        ))

    def get_analysis(self) -> list[tuple[object, float]]:
        return self.daily


_TRADE_COLUMNS = [
    "ticker", "entry_date", "exit_date",
    "pnl", "pnl_pct", "order_value_usd", "max_position_frac",
]


def run_backtest(
    strategy_cls: type,
    feeds: dict[str, pd.DataFrame],
    initial_cash: float = 100_000.0,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict:
    """Run a backtest. `feeds` is {ticker: ohlcv_df indexed by date}.

    Returns: dict with equity_curve, daily_returns, trades, trade_count, final_value.
    """
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(strategy_cls)
    cerebro.broker.set_cash(initial_cash)
    cerebro.broker.addcommissioninfo(DhanDeliveryCommission())

    if slippage_bps > 0:
        cerebro.broker.set_slippage_perc(slippage_bps / 10_000, slip_open=True)

    for tkr, df in feeds.items():
        feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(feed, name=tkr)

    cerebro.addanalyzer(
        bt.analyzers.TimeReturn, _name="returns", timeframe=bt.TimeFrame.Days
    )
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades_a")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    cerebro.addanalyzer(TradeRecorder, _name="trade_recorder")
    cerebro.addanalyzer(GrossExposureRecorder, _name="gross_recorder")

    # tradehistory=True populates trade.history per Trade so TradeRecorder
    # can recover entry size after close (trade.value zeroes when size→0).
    # runonce=False: bar-by-bar indicator computation. Slower than the
    # vectorized "once" path, but robust when an agent-proposed strategy uses
    # an indicator period longer than the validation fold (e.g. 200-day MA
    # on a 126-day fold). The "once" path crashes with "array assignment
    # index out of range" there; bar-by-bar just leaves the indicator NaN
    # until enough bars accumulate, which the strategy's len-checks handle.
    results = cerebro.run(tradehistory=True, runonce=False)
    strat = results[0]

    daily = pd.Series(strat.analyzers.returns.get_analysis()).sort_index()
    equity_curve = (1 + daily).cumprod() * initial_cash
    trade_a = strat.analyzers.trades_a.get_analysis()
    trade_count = int(trade_a.get("total", {}).get("closed", 0))

    trade_rows = strat.analyzers.trade_recorder.get_analysis()
    if trade_rows:
        trades_df = pd.DataFrame(trade_rows, columns=_TRADE_COLUMNS)
    else:
        trades_df = pd.DataFrame(columns=_TRADE_COLUMNS)

    gross_pairs = strat.analyzers.gross_recorder.get_analysis()
    gross_series = (
        pd.Series({d: g for d, g in gross_pairs}).sort_index()
        if gross_pairs else pd.Series(dtype=float)
    )

    return {
        "equity_curve": equity_curve,
        "daily_returns": daily,
        "trades": trades_df,
        "trade_count": trade_count,
        "final_value": float(cerebro.broker.get_value()),
        "gross_exposure_daily": gross_series,
    }
