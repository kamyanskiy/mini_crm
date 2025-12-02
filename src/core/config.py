import logging
from logging import config as logging_config
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = Field(default="mini_crm", description="Project name for Swagger docs")

    # Database settings
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="crm_database", description="PostgreSQL database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")

    redis_host: str = Field(default="127.0.0.1", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")

    unit_cache_expire_in_seconds: int = Field(default=300, description="Cache expire: 5 min")
    view_cache_expire_in_seconds: int = Field(default=3600, description="Cache expire: 1 hour")

    # JWT settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT encoding",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # Initial admin settings
    create_admin_on_startup: bool = Field(
        default=False, description="Create admin user on startup if not exists"
    )
    admin_email: str = Field(default="admin@example.com", description="Default admin email")
    admin_password: str = Field(default="changeme123", description="Default admin password")
    admin_name: str = Field(default="System Administrator", description="Default admin name")
    admin_organization: str = Field(
        default="Default Organization", description="Default admin organization"
    )

    # CORS settings
    cors_origins: str = Field(default="*", description="Allowed CORS origins (comma-separated)")
    cors_methods: str = Field(default="*", description="Allowed CORS methods (comma-separated)")
    cors_headers: str = Field(default="*", description="Allowed CORS headers (comma-separated)")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def cors_methods_list(self) -> list[str]:
        """Parse CORS methods from comma-separated string."""
        return [method.strip() for method in self.cors_methods.split(",")]

    @property
    def cors_headers_list(self) -> list[str]:
        """Parse CORS headers from comma-separated string."""
        return [header.strip() for header in self.cors_headers.split(",")]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Синхронный URL для миграций Alembic."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)

# Создаем логгер для использования по всему проекту
logger = logging.getLogger("mini_crm")
