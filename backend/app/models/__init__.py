"""SQLAlchemy ORM models for the research platform."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Exchange(Base, TimestampMixin):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    stocks: Mapped[list["Stock"]] = relationship(back_populates="exchange")


class Sector(Base, TimestampMixin):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    stocks: Mapped[list["Stock"]] = relationship(back_populates="sector")


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("exchange_id", "symbol", name="uq_stock_exchange_symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False)
    sector_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sectors.id"))
    isin: Mapped[Optional[str]] = mapped_column(String(16))
    instrument_type: Mapped[str] = mapped_column(String(32), default="EQUITY")  # EQUITY|INDEX
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_liquid: Mapped[bool] = mapped_column(Boolean, default=True)
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    exchange: Mapped[Exchange] = relationship(back_populates="stocks")
    sector: Mapped[Optional[Sector]] = relationship(back_populates="stocks")


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_price_stock_date"),
        Index("ix_prices_stock_date", "stock_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    adjusted_close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CorporateAction(Base, TimestampMixin):
    __tablename__ = "corporate_actions"
    __table_args__ = (Index("ix_ca_stock_exdate", "stock_id", "ex_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SPLIT|DIVIDEND|BONUS
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    ratio: Mapped[Optional[str]] = mapped_column(String(32))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Fundamental(Base, TimestampMixin):
    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("stock_id", "as_of_date", name="uq_fund_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    pe: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    pb: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    eps_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    profit_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    roce: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    debt_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    free_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))


class NewsItem(Base, TimestampMixin):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stocks.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(128), default="unknown")
    url: Mapped[Optional[str]] = mapped_column(String(1024))


class SentimentScore(Base, TimestampMixin):
    __tablename__ = "sentiment_scores"
    __table_args__ = (UniqueConstraint("stock_id", "as_of_date", name="uq_sent_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)  # -1..1
    label: Mapped[str] = mapped_column(String(16), nullable=False)  # POSITIVE|NEGATIVE|NEUTRAL
    news_count: Mapped[int] = mapped_column(Integer, default=0)
    momentum: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))


class TechnicalFeature(Base):
    __tablename__ = "technical_features"
    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", "feature_set_version", name="uq_feat"),
        Index("ix_feat_stock_date", "stock_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(32), default="v1")
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelRun(Base, TimestampMixin):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features: Mapped[list] = mapped_column(JSON, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    validation_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    test_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_location: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="EXPERIMENTAL")
    # EXPERIMENTAL|VALIDATED|PAPER_TRADING|RETIRED
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(64))
    train_start: Mapped[Optional[date]] = mapped_column(Date)
    train_end: Mapped[Optional[date]] = mapped_column(Date)
    valid_start: Mapped[Optional[date]] = mapped_column(Date)
    valid_end: Mapped[Optional[date]] = mapped_column(Date)
    test_start: Mapped[Optional[date]] = mapped_column(Date)
    test_end: Mapped[Optional[date]] = mapped_column(Date)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (Index("ix_pred_stock_ts", "stock_id", "as_of_ts"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"), nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # UP|DOWN|NEUTRAL
    probability: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    expected_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    expected_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    expected_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    probability_of_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    expected_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    predicted_volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    confidence_label: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    result_channel: Mapped[str] = mapped_column(String(32), default="BACKTEST")
    # BACKTEST|PAPER|LIVE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradeSignal(Base):
    __tablename__ = "trade_signals"
    __table_args__ = (Index("ix_signal_stock_ts", "stock_id", "generated_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    prediction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model_predictions.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal: Mapped[str] = mapped_column(String(16), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    expected_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    expected_downside: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    entry_low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    entry_high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    risk_reward: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    position_size_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    holding_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    market_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    result_channel: Mapped[str] = mapped_column(String(32), default="PAPER")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Backtest(Base, TimestampMixin):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    universe: Mapped[dict] = mapped_column(JSON, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    equity_curve: Mapped[list] = mapped_column(JSON, default=list)
    drawdown_curve: Mapped[list] = mapped_column(JSON, default=list)
    monthly_returns: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    benchmark_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    result_channel: Mapped[str] = mapped_column(String(32), default="BACKTEST")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    __table_args__ = (Index("ix_bt_trade_backtest", "backtest_id", "entry_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtests.id"), nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[Optional[date]] = mapped_column(Date)
    side: Mapped[str] = mapped_column(String(8), default="LONG")
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    costs: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    return_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    exit_reason: Mapped[Optional[str]] = mapped_column(String(64))


class PortfolioPosition(Base, TimestampMixin):
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[str] = mapped_column(String(64), default="paper")
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    result_channel: Mapped[str] = mapped_column(String(32), default="PAPER")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (UniqueConstraint("account", "as_of_ts", name="uq_snap_account_ts"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account: Mapped[str] = mapped_column(String(64), default="paper")
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    result_channel: Mapped[str] = mapped_column(String(32), default="PAPER")
    positions: Mapped[list] = mapped_column(JSON, default=list)


class RiskMetric(Base):
    __tablename__ = "risk_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[str] = mapped_column(String(64), default="paper")
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_channel: Mapped[str] = mapped_column(String(32), default="PAPER")


class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stock_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stocks.id"))
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # INFO|WARN|ERROR
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class MarketRegimeSnapshot(Base):
    __tablename__ = "market_regime_snapshots"
    __table_args__ = (UniqueConstraint("as_of_date", name="uq_regime_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    regime: Mapped[str] = mapped_column(String(32), nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
