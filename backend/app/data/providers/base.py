"""Market data provider interfaces and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Bar:
    symbol: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int


class MarketDataProvider(ABC):
    @abstractmethod
    def list_symbols(self) -> list[str]:
        raise NotImplementedError


class HistoricalDataProvider(ABC):
    @abstractmethod
    def get_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Return columns: trade_date, open, high, low, close, adjusted_close, volume."""
        raise NotImplementedError


class FundamentalDataProvider(ABC):
    @abstractmethod
    def get_fundamentals(self, symbol: str, as_of: date) -> dict:
        raise NotImplementedError


class NewsDataProvider(ABC):
    @abstractmethod
    def get_news(self, symbol: str, start: date, end: date) -> list[dict]:
        raise NotImplementedError


class CorporateActionProvider(ABC):
    @abstractmethod
    def get_actions(self, symbol: str, start: date, end: date) -> list[dict]:
        raise NotImplementedError


class CSVSampleProvider(MarketDataProvider, HistoricalDataProvider, CorporateActionProvider):
    """Deterministic offline sample for CI/demo. Never claims live-market accuracy."""

    def __init__(self, data_dir: Optional[Path] = None):
        settings = get_settings()
        self.data_dir = Path(data_dir or settings.resolve_path(settings.sample_data_dir))

    def list_symbols(self) -> list[str]:
        files = sorted(self.data_dir.glob("*.csv"))
        return [f.stem for f in files if f.stem != "corporate_actions"]

    def get_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        path = self.data_dir / f"{symbol}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Sample data missing for {symbol}: {path}")
        df = pd.read_csv(path, parse_dates=["trade_date"])
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        mask = (df["trade_date"] >= start) & (df["trade_date"] <= end)
        out = df.loc[mask].copy()
        out["source"] = "csv_sample"
        return out.reset_index(drop=True)

    def get_actions(self, symbol: str, start: date, end: date) -> list[dict]:
        path = self.data_dir / "corporate_actions.csv"
        if not path.exists():
            return []
        df = pd.read_csv(path, parse_dates=["ex_date"])
        df["ex_date"] = pd.to_datetime(df["ex_date"]).dt.date
        rows = df[(df["symbol"] == symbol) & (df["ex_date"] >= start) & (df["ex_date"] <= end)]
        return rows.to_dict(orient="records")


class YahooFinanceProvider(MarketDataProvider, HistoricalDataProvider):
    """Optional convenience provider. Not an exchange primary source."""

    def __init__(self, symbols: Optional[list[str]] = None):
        self._symbols = symbols or []

    def list_symbols(self) -> list[str]:
        return list(self._symbols)

    def get_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf

        ticker = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        if symbol.startswith("NIFTY"):
            mapping = {"NIFTY_50": "^NSEI", "NIFTY_BANK": "^NSEBANK"}
            ticker = mapping.get(symbol, ticker)

        raw = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
            progress=False,
        )
        if raw.empty:
            return pd.DataFrame(
                columns=["trade_date", "open", "high", "low", "close", "adjusted_close", "volume"]
            )
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [c[0] for c in raw.columns]
        raw = raw.reset_index()
        raw.rename(
            columns={
                "Date": "trade_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            },
            inplace=True,
        )
        raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.date
        raw["source"] = "yahoo"
        return raw[
            ["trade_date", "open", "high", "low", "close", "adjusted_close", "volume", "source"]
        ]


class NseOfficialProvider(HistoricalDataProvider):
    """Stub for paid NSE EOD/SFTP feed. Requires commercial credentials."""

    def get_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        raise NotImplementedError(
            "Configure NSE official EOD credentials. See docs/research/data-providers.md"
        )


class NullFundamentalProvider(FundamentalDataProvider):
    def get_fundamentals(self, symbol: str, as_of: date) -> dict:
        return {}


class NullNewsProvider(NewsDataProvider):
    def get_news(self, symbol: str, start: date, end: date) -> list[dict]:
        return []


def get_historical_provider() -> HistoricalDataProvider:
    settings = get_settings()
    name = settings.market_data_provider.lower()
    if name == "yahoo" and settings.yahoo_enabled:
        logger.info("using_yahoo_provider")
        return YahooFinanceProvider()
    logger.info("using_csv_sample_provider")
    return CSVSampleProvider()


def get_market_provider() -> MarketDataProvider:
    hist = get_historical_provider()
    if isinstance(hist, MarketDataProvider):
        return hist
    return CSVSampleProvider()
