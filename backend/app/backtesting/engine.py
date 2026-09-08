"""Event-driven backtesting engine with costs, stops, and position limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

import pandas as pd

from app.backtesting.costs import estimate_costs, load_cost_config
from app.backtesting.metrics import overfitting_warnings, trading_metrics
from app.core.config import get_settings
from app.risk.sizing import PortfolioRiskState, check_portfolio_limits, size_position


@dataclass
class OpenPosition:
    symbol: str
    qty: int
    entry_date: date
    entry_price: float
    stop_loss: float
    take_profit: float
    costs: float
    sector: str = "UNKNOWN"


@dataclass
class BacktestResult:
    equity_curve: list[dict]
    drawdown_curve: list[dict]
    trades: list[dict]
    metrics: dict
    benchmark_metrics: dict
    warnings: list[str]
    monthly_returns: dict
    config: dict


SignalFn = Callable[[str, date, pd.Series], Optional[dict]]
# returns dict with keys: action (BUY/SELL/HOLD), stop, target, confidence


class EventDrivenBacktester:
    def __init__(
        self,
        prices: dict[str, pd.DataFrame],
        *,
        initial_capital: Optional[float] = None,
        cost_config: Optional[dict] = None,
        risk_per_trade: Optional[float] = None,
        max_position_pct: Optional[float] = None,
        benchmark_symbol: str = "NIFTY_50",
    ):
        settings = get_settings()
        self.prices = {k: v.sort_values("trade_date").copy() for k, v in prices.items()}
        self.initial_capital = initial_capital or settings.initial_capital
        self.cost_config = cost_config or load_cost_config()
        self.risk_per_trade = risk_per_trade or settings.max_risk_per_trade
        self.max_position_pct = max_position_pct or settings.max_position_size
        self.benchmark_symbol = benchmark_symbol

    def _price_on(self, symbol: str, d: date) -> Optional[float]:
        df = self.prices.get(symbol)
        if df is None:
            return None
        row = df.loc[df["trade_date"] == d]
        if row.empty:
            return None
        return float(row.iloc[0]["close"])

    def run(
        self,
        start: date,
        end: date,
        signal_fn: SignalFn,
        symbols: Optional[list[str]] = None,
    ) -> BacktestResult:
        symbols = symbols or [s for s in self.prices if not s.startswith("NIFTY")]
        # trading calendar from union of dates
        all_dates = sorted(
            {
                d
                for s in symbols + ([self.benchmark_symbol] if self.benchmark_symbol in self.prices else [])
                for d in self.prices[s]["trade_date"].tolist()
                if start <= d <= end
            }
        )

        cash = float(self.initial_capital)
        positions: dict[str, OpenPosition] = {}
        trades: list[dict] = []
        equity_curve: list[dict] = []
        peak = cash

        for d in all_dates:
            # mark-to-market + stop/target exits
            to_close = []
            for sym, pos in positions.items():
                px = self._price_on(sym, d)
                if px is None:
                    continue
                if px <= pos.stop_loss:
                    to_close.append((sym, px, "STOP_LOSS"))
                elif px >= pos.take_profit:
                    to_close.append((sym, px, "TAKE_PROFIT"))

            for sym, px, reason in to_close:
                pos = positions.pop(sym)
                notional = pos.qty * px
                costs = estimate_costs(notional, "SELL", is_sell_delivery=True, config=self.cost_config)
                proceeds = notional - costs.total
                cash += proceeds
                pnl = proceeds - (pos.qty * pos.entry_price + pos.costs)
                trades.append(
                    {
                        "symbol": sym,
                        "entry_date": pos.entry_date.isoformat(),
                        "exit_date": d.isoformat(),
                        "qty": pos.qty,
                        "entry_price": pos.entry_price,
                        "exit_price": px,
                        "costs": pos.costs + costs.total,
                        "pnl": pnl,
                        "return_pct": pnl / (pos.qty * pos.entry_price) if pos.entry_price else 0,
                        "exit_reason": reason,
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                    }
                )

            # entries — signal uses only data available up to date d (caller responsibility)
            mtm = cash
            sector_exp: dict[str, float] = {}
            for sym, pos in positions.items():
                px = self._price_on(sym, d) or pos.entry_price
                mtm += pos.qty * px
                sector_exp[pos.sector] = sector_exp.get(pos.sector, 0.0) + (pos.qty * px) / mtm

            dd = 0.0 if peak <= 0 else max(0.0, (peak - mtm) / peak)
            state = PortfolioRiskState(
                open_positions=len(positions),
                sector_exposure=sector_exp,
                current_drawdown=dd,
                daily_pnl_pct=0.0,
            )
            blocks = check_portfolio_limits(state)

            if not blocks:
                for sym in symbols:
                    if sym in positions:
                        continue
                    df = self.prices[sym]
                    hist = df[df["trade_date"] <= d]
                    if hist.empty:
                        continue
                    row = hist.iloc[-1]
                    sig = signal_fn(sym, d, row)
                    if not sig or sig.get("action") not in {"BUY", "STRONG_BUY"}:
                        continue
                    px = float(row["close"])
                    stop = float(sig.get("stop") or px * 0.97)
                    target = float(sig.get("target") or px * 1.06)
                    sizing = size_position(
                        mtm,
                        px,
                        stop,
                        method="risk_per_trade",
                        risk_per_trade=self.risk_per_trade,
                        max_position_pct=self.max_position_pct,
                    )
                    if sizing.shares <= 0:
                        continue
                    notional = sizing.shares * px
                    costs = estimate_costs(notional, "BUY", config=self.cost_config)
                    if cash < notional + costs.total:
                        continue
                    cash -= notional + costs.total
                    positions[sym] = OpenPosition(
                        symbol=sym,
                        qty=sizing.shares,
                        entry_date=d,
                        entry_price=px,
                        stop_loss=stop,
                        take_profit=target,
                        costs=costs.total,
                        sector=str(sig.get("sector") or "UNKNOWN"),
                    )

            # end-of-day equity
            equity = cash
            for sym, pos in positions.items():
                px = self._price_on(sym, d) or pos.entry_price
                equity += pos.qty * px
            peak = max(peak, equity)
            dd = 0.0 if peak <= 0 else (peak - equity) / peak
            equity_curve.append({"date": d.isoformat(), "equity": equity, "cash": cash})

        # force close remaining at last date
        if all_dates:
            last = all_dates[-1]
            for sym, pos in list(positions.items()):
                px = self._price_on(sym, last) or pos.entry_price
                notional = pos.qty * px
                costs = estimate_costs(notional, "SELL", is_sell_delivery=True, config=self.cost_config)
                cash += notional - costs.total
                pnl = (notional - costs.total) - (pos.qty * pos.entry_price + pos.costs)
                trades.append(
                    {
                        "symbol": sym,
                        "entry_date": pos.entry_date.isoformat(),
                        "exit_date": last.isoformat(),
                        "qty": pos.qty,
                        "entry_price": pos.entry_price,
                        "exit_price": px,
                        "costs": pos.costs + costs.total,
                        "pnl": pnl,
                        "return_pct": pnl / (pos.qty * pos.entry_price) if pos.entry_price else 0,
                        "exit_reason": "END",
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                    }
                )
            positions.clear()
            if equity_curve:
                equity_curve[-1]["equity"] = cash
                equity_curve[-1]["cash"] = cash

        metrics = trading_metrics(equity_curve, trades)
        benchmark_metrics = self._benchmark_metrics(start, end)
        dd_curve = []
        peak_e = 0.0
        for pt in equity_curve:
            peak_e = max(peak_e, pt["equity"])
            dd_curve.append(
                {
                    "date": pt["date"],
                    "drawdown": 0.0 if peak_e <= 0 else (peak_e - pt["equity"]) / peak_e,
                }
            )

        monthly = {}
        if equity_curve:
            s = pd.Series(
                {pd.to_datetime(p["date"]): p["equity"] for p in equity_curve}
            ).sort_index()
            m = s.resample("ME").last().pct_change().dropna()
            monthly = {k.strftime("%Y-%m"): float(v) for k, v in m.items()}

        warnings = overfitting_warnings(
            {"accuracy": 0.6},
            {"accuracy": 0.55, "sharpe": metrics.get("sharpe"), "max_drawdown": metrics.get("max_drawdown")},
            n_samples=len(trades),
        )
        if metrics.get("n_trades", 0) < 20:
            warnings.append("LOW_SAMPLE_SIZE")

        return BacktestResult(
            equity_curve=equity_curve,
            drawdown_curve=dd_curve,
            trades=trades,
            metrics=metrics,
            benchmark_metrics=benchmark_metrics,
            warnings=sorted(set(warnings)),
            monthly_returns=monthly,
            config={
                "initial_capital": self.initial_capital,
                "risk_per_trade": self.risk_per_trade,
                "max_position_pct": self.max_position_pct,
                "costs": self.cost_config,
                "result_channel": "BACKTEST",
                "disclaimer": "Backtested results are not guarantees of future performance.",
            },
        )

    def _benchmark_metrics(self, start: date, end: date) -> dict:
        if self.benchmark_symbol not in self.prices:
            return {"name": "Buy&Hold NIFTY_50", "available": False}
        df = self.prices[self.benchmark_symbol]
        df = df[(df["trade_date"] >= start) & (df["trade_date"] <= end)]
        if len(df) < 2:
            return {"name": "Buy&Hold NIFTY_50", "available": False}
        eq0 = float(df.iloc[0]["close"])
        curve = [
            {"date": r.trade_date.isoformat(), "equity": self.initial_capital * (float(r.close) / eq0)}
            for r in df.itertuples()
        ]
        return {
            "name": "Buy&Hold NIFTY_50",
            "available": True,
            "metrics": trading_metrics(curve, []),
            "result_channel": "BACKTEST",
        }
