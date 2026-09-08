from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "indian-stock-ai"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://stockai:stockai@localhost:5432/stockai"
    redis_url: str = "redis://localhost:6379/0"

    market_data_provider: str = "csv_sample"
    yahoo_enabled: bool = False

    universe_config: str = "/config/universe.yaml"
    min_avg_daily_volume: int = 500_000
    min_price_history_days: int = 252

    initial_capital: float = 1_000_000
    max_risk_per_trade: float = 0.005
    max_position_size: float = 0.05
    max_sector_exposure: float = 0.20
    max_open_positions: int = 20
    max_portfolio_drawdown: float = 0.15
    daily_loss_limit: float = 0.02

    transaction_cost_config: str = "/config/transaction_costs.yaml"
    slippage_bps: float = 5.0
    spread_bps: float = 5.0

    model_artifact_dir: str = "/artifacts/models"
    default_prediction_horizons: str = "1,3,5,10,20"
    random_seed: int = 42

    auth_enabled: bool = False
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    rate_limit_per_minute: int = 120

    sample_data_dir: str = "/data/sample"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def horizons(self) -> List[int]:
        return [int(x) for x in self.default_prediction_horizons.split(",") if x.strip()]

    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.exists():
            return p
        # backend/app/core -> repo root is parents[3]
        repo_root = Path(__file__).resolve().parents[3]
        candidates = [
            repo_root / path.lstrip("/"),
            repo_root / path.replace("/config/", "config/").lstrip("/"),
            Path.cwd() / path.lstrip("/"),
            Path.cwd().parent / path.lstrip("/"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]


@lru_cache
def get_settings() -> Settings:
    return Settings()
