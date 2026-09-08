from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StockOut(BaseModel):
    id: int
    symbol: str
    name: str
    instrument_type: str
    is_liquid: bool
    is_active: bool
    market_cap: Optional[float] = None

    model_config = {"from_attributes": True}


class PredictionOut(BaseModel):
    symbol: str
    direction: str
    probability: float
    expected_return: float
    risk_score: float
    confidence: str
    horizon_days: int
    model_version: str
    explanations: list[dict] = []
    result_channel: str = "PAPER"
    disclaimer: str = "Predictions are probabilistic research outputs, not guarantees."


class SignalOut(BaseModel):
    symbol: str
    current_price: float
    signal: str
    probability: float
    expected_return: float
    expected_downside: float
    entry_low: float
    entry_high: float
    stop_loss: float
    target_price: float
    risk_reward: float
    position_size_pct: float
    holding_period_days: int
    market_regime: str
    model_version: str
    risk_score: float
    confidence: str
    timestamp: str
    explanations: list[dict] = []
    result_channel: str = "PAPER"


class ScreenerQuery(BaseModel):
    min_probability: float = 0.7
    min_expected_return: float = 0.02
    max_risk_score: float = 0.4
    min_avg_volume: Optional[float] = None
    sector: Optional[str] = None
    max_rsi: Optional[float] = None


class BacktestCreate(BaseModel):
    name: str = "example"
    strategy: str = "ensemble_momentum"
    symbols: list[str] = Field(default_factory=lambda: ["RELIANCE", "TCS", "INFY", "HDFCBANK"])
    start_date: date
    end_date: date
    initial_capital: float = 1_000_000
    risk_per_trade: float = 0.005
    max_position_size: float = 0.05


class BacktestOut(BaseModel):
    id: int
    name: str
    strategy: str
    metrics: dict
    benchmark_metrics: dict
    warnings: list
    equity_curve: list
    drawdown_curve: list
    monthly_returns: dict
    result_channel: str
    disclaimer: str = "Backtested results are not guarantees of future performance."

    model_config = {"from_attributes": True}


class ModelOut(BaseModel):
    model_id: str
    model_type: str
    version: str
    status: str
    validation_metrics: dict
    test_metrics: dict
    warnings: list
    training_date: datetime
    features: list

    model_config = {"from_attributes": True}


class RegimeOut(BaseModel):
    as_of_date: date
    regime: str
    features: dict


class PortfolioOut(BaseModel):
    account: str
    cash: float
    equity: float
    unrealized_pnl: float
    realized_pnl: float
    drawdown: float
    positions: list
    trades: list
    result_channel: str
    disclaimer: str


class HealthOut(BaseModel):
    status: str
    app: str
    env: str
