"""Indian equity transaction cost model (configurable)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from app.core.config import get_settings


@dataclass
class CostBreakdown:
    brokerage: float
    stt: float
    exchange: float
    sebi: float
    stamp: float
    gst: float
    dp: float
    slippage: float
    spread: float
    total: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def load_cost_config(path: Optional[str] = None) -> dict:
    settings = get_settings()
    cfg_path = Path(path or settings.resolve_path(settings.transaction_cost_config))
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "brokerage_per_order": 20.0,
        "stt_buy_pct": 0.001,
        "stt_sell_pct": 0.001,
        "exchange_txn_pct": 0.0000297,
        "sebi_fee_pct": 0.000001,
        "stamp_duty_buy_pct": 0.00015,
        "gst_pct": 0.18,
        "dp_charge_sell": 15.93,
        "slippage_bps": settings.slippage_bps,
        "spread_bps": settings.spread_bps,
    }


def estimate_costs(
    notional: float,
    side: str,
    *,
    is_sell_delivery: bool = False,
    config: Optional[dict] = None,
) -> CostBreakdown:
    cfg = config or load_cost_config()
    brokerage = float(cfg.get("brokerage_per_order", 20.0)) + notional * float(
        cfg.get("brokerage_pct", 0.0)
    )
    if side.upper() == "BUY":
        stt = notional * float(cfg.get("stt_buy_pct", 0.0))
        stamp = notional * float(cfg.get("stamp_duty_buy_pct", 0.0))
        dp = 0.0
    else:
        stt = notional * float(cfg.get("stt_sell_pct", 0.0))
        stamp = 0.0
        dp = float(cfg.get("dp_charge_sell", 0.0)) if is_sell_delivery else 0.0

    exchange = notional * float(cfg.get("exchange_txn_pct", 0.0))
    sebi = notional * float(cfg.get("sebi_fee_pct", 0.0))
    gst = (brokerage + exchange + sebi) * float(cfg.get("gst_pct", 0.18))
    slip = notional * float(cfg.get("slippage_bps", 5)) / 10000.0
    spread = notional * float(cfg.get("spread_bps", 5)) / 10000.0 / 2.0
    total = brokerage + stt + exchange + sebi + stamp + gst + dp + slip + spread
    return CostBreakdown(
        brokerage=brokerage,
        stt=stt,
        exchange=exchange,
        sebi=sebi,
        stamp=stamp,
        gst=gst,
        dp=dp,
        slippage=slip,
        spread=spread,
        total=total,
    )
