"""
Application configuration loaded from environment variables.
All settings are declared explicitly — no implicit defaults for security-sensitive values.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


class LogFormat(str, Enum):
    console = "console"
    json = "json"


class LLMProvider(str, Enum):
    anthropic = "anthropic"
    ollama = "ollama"


class StorageBackend(str, Enum):
    local = "local"
    s3 = "s3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: AppEnv = AppEnv.development
    app_debug: bool = False
    app_secret_key: str = Field(..., min_length=32)
    app_host: str = "0.0.0.0"
    app_port: int = Field(8000, ge=1, le=65535)
    app_workers: int = Field(1, ge=1)

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(..., pattern=r"^postgresql\+asyncpg://")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fdis"
    postgres_user: str = "fdis_user"
    postgres_password: str = Field(...)

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # ── LLM (provider selection) ──────────────────────────────────────────────
    llm_provider: LLMProvider = LLMProvider.anthropic

    # ── LLM (Anthropic) — required only when llm_provider=anthropic ──────────
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = Field(4096, ge=256, le=8192)
    anthropic_timeout_seconds: int = Field(60, ge=10, le=300)
    anthropic_max_retries: int = Field(3, ge=0, le=10)

    # ── LLM (Ollama) — required only when llm_provider=ollama ────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    ollama_timeout_seconds: int = Field(120, ge=10, le=600)
    ollama_max_retries: int = Field(2, ge=0, le=5)
    ollama_temperature: float = Field(0.0, ge=0.0, le=2.0)
    ollama_num_ctx: int = Field(8192, ge=2048, le=131072)

    # ── PII / Encryption ──────────────────────────────────────────────────────
    # 32-byte base64-encoded AES-256 key
    pii_encryption_key: str = Field(..., min_length=44)

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_backend: StorageBackend = StorageBackend.local
    storage_local_root: Path = Path("/data/documents")
    storage_max_file_size_mb: int = Field(50, ge=1, le=500)

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(60, ge=5, le=1440)

    # ── Risk thresholds ───────────────────────────────────────────────────────
    risk_large_transfer_threshold: float = Field(50_000.0, ge=0)
    risk_round_number_threshold: float = Field(10_000.0, ge=0)
    risk_velocity_window_hours: int = Field(24, ge=1)
    risk_velocity_max_transactions: int = Field(20, ge=1)

    # ── Observability ─────────────────────────────────────────────────────────
    otel_service_name: str = "fdis-api"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    enable_metrics: bool = True
    enable_tracing: bool = False

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.console

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.production

    @property
    def storage_max_file_size_bytes(self) -> int:
        return self.storage_max_file_size_mb * 1024 * 1024

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


def get_settings() -> Settings:
    """Return the application settings singleton.

    In tests, override by patching this function or using dependency injection.
    """
    return Settings()  # type: ignore[call-arg]
