"""Paper trading engine — simulated fills only. No live broker execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.backtesting.costs import estimate_costs
from app.core.config import get_settings
from app.risk.sizing import PortfolioRiskState, check_portfolio_limits


@dataclass
class PaperOrder:
    symbol: str
    side: str
    qty: int
    limit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class PaperAccount:
    name: str = "paper"
    cash: float = 0.0
    positions: dict = field(default_factory=dict)  # symbol -> {qty, avg_cost, stop, target}
    realized_pnl: float = 0.0
    trades: list = field(default_factory=list)
    equity_peak: float = 0.0
    result_channel: str = "PAPER"

    def mark_equity(self, marks: dict[str, float]) -> float:
        eq = self.cash
        for sym, pos in self.positions.items():
            eq += pos["qty"] * marks.get(sym, pos["avg_cost"])
        self.equity_peak = max(self.equity_peak, eq)
        return eq


class PaperBroker:
    """Simulated broker adapter. Live brokers should implement the same interface later."""

    def __init__(self, initial_capital: Optional[float] = None):
        settings = get_settings()
        capital = initial_capital or settings.initial_capital
        self.account = PaperAccount(cash=capital, equity_peak=capital)

    def place_order(self, order: PaperOrder, fill_price: float, sector: str = "UNKNOWN") -> dict:
        acc = self.account
        if order.side.upper() == "BUY":
            notional = order.qty * fill_price
            costs = estimate_costs(notional, "BUY")
            total = notional + costs.total
            if total > acc.cash:
                return {"status": "REJECTED", "reason": "INSUFFICIENT_CASH", "channel": "PAPER"}
            eq = acc.mark_equity({})
            state = PortfolioRiskState(
                open_positions=len(acc.positions),
                sector_exposure={},
                current_drawdown=0.0 if acc.equity_peak <= 0 else max(0, (acc.equity_peak - eq) / acc.equity_peak),
                daily_pnl_pct=0.0,
            )
            blocks = check_portfolio_limits(state)
            if blocks and order.symbol not in acc.positions:
                return {"status": "REJECTED", "reason": blocks[0], "channel": "PAPER"}
            acc.cash -= total
            pos = acc.positions.get(order.symbol, {"qty": 0, "avg_cost": 0.0, "stop": None, "target": None, "sector": sector})
            new_qty = pos["qty"] + order.qty
            pos["avg_cost"] = ((pos["avg_cost"] * pos["qty"]) + notional) / new_qty if new_qty else fill_price
            pos["qty"] = new_qty
            pos["stop"] = order.stop_loss
            pos["target"] = order.take_profit
            pos["sector"] = sector
            acc.positions[order.symbol] = pos
            trade = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": order.symbol,
                "side": "BUY",
                "qty": order.qty,
                "price": fill_price,
                "costs": costs.total,
                "channel": "PAPER",
            }
            acc.trades.append(trade)
            return {"status": "FILLED", **trade}

        # SELL
        pos = acc.positions.get(order.symbol)
        if not pos or pos["qty"] < order.qty:
            return {"status": "REJECTED", "reason": "NO_POSITION", "channel": "PAPER"}
        notional = order.qty * fill_price
        costs = estimate_costs(notional, "SELL", is_sell_delivery=True)
        proceeds = notional - costs.total
        cost_basis = pos["avg_cost"] * order.qty
        pnl = proceeds - cost_basis
        acc.cash += proceeds
        acc.realized_pnl += pnl
        pos["qty"] -= order.qty
        if pos["qty"] == 0:
            del acc.positions[order.symbol]
        else:
            acc.positions[order.symbol] = pos
        trade = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": order.symbol,
            "side": "SELL",
            "qty": order.qty,
            "price": fill_price,
            "costs": costs.total,
            "pnl": pnl,
            "channel": "PAPER",
        }
        acc.trades.append(trade)
        return {"status": "FILLED", **trade}

    def snapshot(self, marks: dict[str, float]) -> dict:
        eq = self.account.mark_equity(marks)
        unreal = 0.0
        positions = []
        for sym, pos in self.account.positions.items():
            m = marks.get(sym, pos["avg_cost"])
            u = (m - pos["avg_cost"]) * pos["qty"]
            unreal += u
            positions.append({**pos, "symbol": sym, "mark": m, "unrealized_pnl": u})
        dd = 0.0 if self.account.equity_peak <= 0 else (self.account.equity_peak - eq) / self.account.equity_peak
        return {
            "account": self.account.name,
            "cash": self.account.cash,
            "equity": eq,
            "unrealized_pnl": unreal,
            "realized_pnl": self.account.realized_pnl,
            "drawdown": dd,
            "positions": positions,
            "trades": self.account.trades[-50:],
            "result_channel": "PAPER",
            "disclaimer": "Paper-trading results are simulated and not live-market performance.",
        }


class LiveBrokerAdapter:
    """Placeholder for future broker integration. Do not implement live orders in v1."""

    def place_order(self, *args, **kwargs):
        raise NotImplementedError(
            "Live trading is intentionally disabled. Implement a broker adapter behind this interface later."
        )
