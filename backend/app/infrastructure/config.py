import os
from functools import lru_cache

from pydantic import BaseModel, Field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings(BaseModel):
    environment: str = Field(default_factory=lambda: _env("ENVIRONMENT", "development"))
    log_level: str = Field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    save_repository_type: str = Field(
        default_factory=lambda: _env("SAVE_REPOSITORY_TYPE", "memory").lower()
    )
    database_url: str = Field(default_factory=lambda: _env("DATABASE_URL", ""))
    postgres_host: str = Field(default_factory=lambda: _env("POSTGRES_HOST", "localhost"))
    postgres_port: int = Field(default_factory=lambda: int(_env("POSTGRES_PORT", "5432")))
    postgres_db: str = Field(default_factory=lambda: _env("POSTGRES_DB", "monirensheng"))
    postgres_user: str = Field(default_factory=lambda: _env("POSTGRES_USER", "monirensheng"))
    postgres_password: str = Field(default_factory=lambda: _env("POSTGRES_PASSWORD", "monirensheng"))
    default_rule_version: str = Field(default_factory=lambda: _env("DEFAULT_RULE_VERSION", "v1"))
    backend_host: str = Field(default_factory=lambda: _env("BACKEND_HOST", "0.0.0.0"))
    backend_port: int = Field(default_factory=lambda: int(_env("BACKEND_PORT", "8000")))
    cors_allowed_origins: str = Field(
        default_factory=lambda: _env(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )
    enable_dev_routes: bool = Field(
        default_factory=lambda: _env("ENABLE_DEV_ROUTES", "true").lower() in {"1", "true", "yes"}
    )
    auto_create_tables: bool = Field(
        default_factory=lambda: _env("AUTO_CREATE_TABLES", "false").lower() in {"1", "true", "yes"}
    )

    def resolved_database_url(self) -> str:
        explicit = self.database_url.strip()
        if explicit:
            if explicit.startswith("postgresql://"):
                return explicit.replace("postgresql://", "postgresql+psycopg://", 1)
            return explicit
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
