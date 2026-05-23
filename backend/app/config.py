from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "postgresql://fraudstream:fraudstream_dev@localhost:5432/fraudstream"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Model
    model_path: str = "./models/xgboost_fraud_v1.pkl"
    model_metadata_path: str = "./models/model_metadata.json"
    fraud_threshold: float = 0.5
    high_risk_threshold: float = 0.75

    # CORS — set to "*" in production until Vercel URL is known,
    # then lock down to "https://your-app.vercel.app"
    allowed_origins: str = "*"

    # Rate limiting
    rate_limit_per_minute: int = 1000

    # Monitoring
    enable_metrics: bool = True

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def model_dir(self) -> Path:
        return Path(self.model_path).parent


@lru_cache()
def get_settings() -> Settings:
    return Settings()
