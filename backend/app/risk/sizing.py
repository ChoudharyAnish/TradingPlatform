"""Risk management: position sizing and portfolio controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings


@dataclass
class PositionSizeResult:
    shares: int
    position_pct: float
    risk_amount: float
    method: str
    capped: bool
    reason: str


def size_position(
    equity: float,
    price: float,
    stop_loss: float,
    *,
    method: str = "risk_per_trade",
    risk_per_trade: Optional[float] = None,
    max_position_pct: Optional[float] = None,
    atr: Optional[float] = None,
) -> PositionSizeResult:
    settings = get_settings()
    risk_pct = risk_per_trade if risk_per_trade is not None else settings.max_risk_per_trade
    max_pos = max_position_pct if max_position_pct is not None else settings.max_position_size

    if price <= 0 or equity <= 0:
        return PositionSizeResult(0, 0.0, 0.0, method, True, "invalid_price_or_equity")

    risk_per_share = abs(price - stop_loss)
    if method == "fixed_percentage":
        notional = equity * max_pos
        shares = int(notional // price)
        return PositionSizeResult(
            shares, shares * price / equity if equity else 0, equity * risk_pct, method, False, "ok"
        )

    if method == "volatility" and atr and atr > 0:
        risk_per_share = max(risk_per_share, 2 * atr)

    if risk_per_share <= 0:
        return PositionSizeResult(0, 0.0, 0.0, method, True, "zero_risk_per_share")

    risk_amount = equity * risk_pct
    shares = int(risk_amount // risk_per_share)
    notional = shares * price
    capped = False
    if notional > equity * max_pos:
        shares = int((equity * max_pos) // price)
        capped = True
    pos_pct = (shares * price / equity) if equity else 0.0
    return PositionSizeResult(shares, pos_pct, risk_amount, method, capped, "ok")


def atr_stop(price: float, atr: float, multiplier: float = 2.0, side: str = "LONG") -> float:
    if side == "LONG":
        return price - multiplier * atr
    return price + multiplier * atr


def percentage_stop(price: float, pct: float = 0.03, side: str = "LONG") -> float:
    if side == "LONG":
        return price * (1 - pct)
    return price * (1 + pct)


def take_profit_rr(entry: float, stop: float, rr: float = 2.0, side: str = "LONG") -> float:
    risk = abs(entry - stop)
    if side == "LONG":
        return entry + rr * risk
    return entry - rr * risk


@dataclass
class PortfolioRiskState:
    open_positions: int
    sector_exposure: dict[str, float]
    current_drawdown: float
    daily_pnl_pct: float


def check_portfolio_limits(state: PortfolioRiskState) -> list[str]:
    settings = get_settings()
    blocks: list[str] = []
    if state.open_positions >= settings.max_open_positions:
        blocks.append("MAX_OPEN_POSITIONS")
    for sector, exp in state.sector_exposure.items():
        if exp > settings.max_sector_exposure:
            blocks.append(f"SECTOR_LIMIT:{sector}")
    if state.current_drawdown >= settings.max_portfolio_drawdown:
        blocks.append("PORTFOLIO_DRAWDOWN")
    if state.daily_pnl_pct <= -settings.daily_loss_limit:
        blocks.append("DAILY_LOSS_LIMIT")
    return blocks
