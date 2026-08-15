from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    PORT: int = 8000

    # PostgreSQL Database URL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "restaurant_waiter_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_waiter_db"
    # Fallback/sync database URL for Alembic if needed
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/restaurant_waiter_db"

    # Security & Dashboard Auth
    SECRET_KEY: str = "development_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Admin Seeder Credentials (loaded from .env or environment)
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_FULL_NAME: str = "System Administrator"

    # Timeouts (as per approved spec)
    SESSION_AUTO_TERMINATE_MINUTES: int = 30
    PAYMENT_TIMEOUT_MINUTES: int = 10

    # Telegram Bot Integration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = "restu_waiter_bot"
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # Google AI / Gemini API
    GEMINI_API_KEY: str = ""
    GOOGLE_GENAI_USE_VERTEXAI: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
