"""Ensemble of technical / fundamental / regime / sentiment heads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.ml.train import TrainedModel, feature_contributions, predict_proba_row


@dataclass
class EnsemblePrediction:
    symbol: str
    direction: str
    probability: float
    expected_return: float
    risk_score: float
    confidence: str
    proba: dict
    explanations: list[dict]
    heads: dict


def _confidence(prob: float, margin: float) -> str:
    if prob >= 0.7 and margin >= 0.15:
        return "HIGH"
    if prob >= 0.55 and margin >= 0.05:
        return "MEDIUM"
    return "LOW"


class EnsemblePredictor:
    def __init__(
        self,
        technical: Optional[TrainedModel] = None,
        fundamental: Optional[TrainedModel] = None,
        sentiment: Optional[TrainedModel] = None,
        weights: Optional[dict[str, float]] = None,
    ):
        self.technical = technical
        self.fundamental = fundamental
        self.sentiment = sentiment
        self.weights = weights or {"technical": 0.7, "fundamental": 0.15, "sentiment": 0.05, "regime": 0.1}

    def predict(
        self,
        symbol: str,
        features: dict,
        *,
        regime: str = "SIDEWAYS",
        expected_return_hint: Optional[float] = None,
    ) -> EnsemblePrediction:
        heads = {}
        blended = {"UP": 0.0, "DOWN": 0.0, "NEUTRAL": 0.0}
        w_sum = 0.0
        explanations: list[dict] = []

        if self.technical is not None:
            p = predict_proba_row(self.technical, features)
            heads["technical"] = p
            w = self.weights.get("technical", 0.7)
            for k, v in p["proba"].items():
                blended[k] = blended.get(k, 0.0) + w * v
            w_sum += w
            explanations.extend(feature_contributions(self.technical, features))

        # regime prior (not a trained model — transparent heuristic)
        regime_prior = {"UP": 1 / 3, "DOWN": 1 / 3, "NEUTRAL": 1 / 3}
        if regime == "BULL":
            regime_prior = {"UP": 0.45, "DOWN": 0.25, "NEUTRAL": 0.30}
        elif regime == "BEAR":
            regime_prior = {"UP": 0.25, "DOWN": 0.45, "NEUTRAL": 0.30}
        elif regime == "HIGH_VOLATILITY":
            regime_prior = {"UP": 0.30, "DOWN": 0.30, "NEUTRAL": 0.40}
        heads["regime"] = {"direction": max(regime_prior, key=regime_prior.get), "proba": regime_prior}
        w = self.weights.get("regime", 0.1)
        for k, v in regime_prior.items():
            blended[k] = blended.get(k, 0.0) + w * v
        w_sum += w

        if self.fundamental is not None:
            p = predict_proba_row(self.fundamental, features)
            heads["fundamental"] = p
            w = self.weights.get("fundamental", 0.15)
            for k, v in p["proba"].items():
                blended[k] = blended.get(k, 0.0) + w * v
            w_sum += w

        if self.sentiment is not None:
            p = predict_proba_row(self.sentiment, features)
            heads["sentiment"] = p
            w = self.weights.get("sentiment", 0.05)
            for k, v in p["proba"].items():
                blended[k] = blended.get(k, 0.0) + w * v
            w_sum += w

        if w_sum > 0:
            blended = {k: v / w_sum for k, v in blended.items()}

        direction = max(blended, key=blended.get)
        prob = blended[direction]
        sorted_p = sorted(blended.values(), reverse=True)
        margin = sorted_p[0] - sorted_p[1] if len(sorted_p) > 1 else sorted_p[0]

        # expected return heuristic from direction probability & recent momentum
        mom = float(features.get("ret_5") or 0.0)
        if expected_return_hint is not None:
            exp_ret = expected_return_hint
        else:
            sign = 1 if direction == "UP" else -1 if direction == "DOWN" else 0
            exp_ret = sign * abs(mom) * 0.5 + sign * (prob - 1 / 3) * 0.05

        vol = float(features.get("vol_20") or 0.02)
        risk_score = min(1.0, max(0.0, vol * 10 + (0.3 if regime == "HIGH_VOLATILITY" else 0.0)))

        signal_dir = {
            "UP": "BUY",
            "DOWN": "SELL",
            "NEUTRAL": "HOLD",
        }[direction]

        return EnsemblePrediction(
            symbol=symbol,
            direction=signal_dir,
            probability=float(prob),
            expected_return=float(exp_ret),
            risk_score=float(risk_score),
            confidence=_confidence(prob, margin),
            proba=blended,
            explanations=explanations[:8],
            heads=heads,
        )
