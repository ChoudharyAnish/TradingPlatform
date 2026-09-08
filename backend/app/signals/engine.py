"""Signal generation with full risk metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from app.ml.ensemble.combiner import EnsemblePrediction
from app.risk.sizing import atr_stop, size_position, take_profit_rr


@dataclass
class TradeSignalDTO:
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
    explanations: list
    result_channel: str = "PAPER"


def strengthen(direction: str, probability: float, confidence: str) -> str:
    if direction == "BUY":
        if probability >= 0.72 and confidence == "HIGH":
            return "STRONG BUY"
        return "BUY"
    if direction == "SELL":
        if probability >= 0.72 and confidence == "HIGH":
            return "STRONG SELL"
        return "SELL"
    return "HOLD"


def build_signal(
    pred: EnsemblePrediction,
    *,
    price: float,
    atr: float,
    equity: float,
    horizon: int,
    regime: str,
    model_version: str,
    result_channel: str = "PAPER",
) -> TradeSignalDTO:
    stop = atr_stop(price, max(atr, price * 0.01), multiplier=2.0, side="LONG" if pred.direction != "SELL" else "SHORT")
    if pred.direction == "SELL":
        target = take_profit_rr(price, stop, rr=2.0, side="SHORT")
        side = "SHORT"
    else:
        target = take_profit_rr(price, stop, rr=2.4, side="LONG")
        side = "LONG"

    risk = abs(price - stop)
    reward = abs(target - price)
    rr = (reward / risk) if risk > 0 else 0.0
    sizing = size_position(equity, price, stop, method="risk_per_trade")
    expected_downside = -risk / price if price else 0.0

    return TradeSignalDTO(
        symbol=pred.symbol,
        current_price=price,
        signal=strengthen(pred.direction, pred.probability, pred.confidence),
        probability=pred.probability,
        expected_return=pred.expected_return,
        expected_downside=expected_downside,
        entry_low=price * 0.995,
        entry_high=price * 1.005,
        stop_loss=stop,
        target_price=target,
        risk_reward=rr,
        position_size_pct=sizing.position_pct,
        holding_period_days=horizon,
        market_regime=regime,
        model_version=model_version,
        risk_score=pred.risk_score,
        confidence=pred.confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        explanations=pred.explanations,
        result_channel=result_channel,
    )


def signal_to_dict(sig: TradeSignalDTO) -> dict:
    return asdict(sig)
