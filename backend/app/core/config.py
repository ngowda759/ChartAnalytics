from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_VERSION: str = "v1"
    APP_NAME: str = "AI Trading Assistant"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://tradingassistant.com",
    ]

    # Database - Firestore
    FIRESTORE_EMULATOR_HOST: str = "localhost:8080"
    FIRESTORE_PROJECT_ID: str = "trading-assistant-dev"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI/LLM
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4-turbo"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2000

    # External APIs
    NSE_API_KEY: str = ""
    NSE_API_URL: str = "https://api.nseindia.com"
    YAHOO_FINANCE_URL: str = "https://query1.finance.yahoo.com"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
