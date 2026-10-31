"""Application configuration loaded from environment variables."""

import logging
from pathlib import Path
from typing import Any, List
from urllib.parse import urlsplit
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_ROOT = str((Path(__file__).resolve().parent.parent.parent / "storage").resolve())

# Recognized boolean string values (case-insensitive).
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

# Names of Settings fields typed as ``bool`` that may be supplied via the
# environment. Kept in sync with the field definitions below.
_BOOLEAN_ENV_FIELDS = (
    "DEBUG",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_HTTPONLY",
    "RATE_LIMIT_ENABLED",
)


def _coerce_bool_like(name: str, value: Any) -> Any:
    """Return a strict bool for recognized boolean strings.

    Returns the sentinel ``_UNRECOGNIZED`` for values that are not valid
    booleans so the caller can decide how to handle them.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return _UNRECOGNIZED


_UNRECOGNIZED = object()


class Settings(BaseSettings):
    APP_NAME: str = "RESUMIND AI API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./resumind.db", repr=False)

    # Session Security & Cookie Configuration
    SESSION_COOKIE_NAME: str = "resumind_session"
    SESSION_COOKIE_SECURE: bool = False  # Set True in production HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_PATH: str = "/"
    SESSION_TTL_HOURS: int = 24
    SESSION_CLEANUP_INTERVAL_SECONDS: int = 3600

    # In-process rate limits; use one worker or an external shared limiter in production.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_API_PER_MINUTE: int = Field(default=60, gt=0)
    RATE_LIMIT_UPLOAD_COUNT: int = Field(default=5, gt=0)
    RATE_LIMIT_UPLOAD_WINDOW_SECONDS: int = Field(default=600, gt=0)
    RATE_LIMIT_AI_COUNT: int = Field(default=10, gt=0)
    RATE_LIMIT_AI_WINDOW_SECONDS: int = Field(default=300, gt=0)

    # Storage Root Directory
    STORAGE_ROOT: str = DEFAULT_STORAGE_ROOT

    # AI Model Configuration (Ollama)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", repr=False)
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_CONNECT_TIMEOUT_SEC: float = 5.0
    OLLAMA_GENERATE_TIMEOUT_SEC: float = 120.0
    OLLAMA_MAX_RETRIES: int = 1

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def storage_path(self) -> Path:
        return Path(self.STORAGE_ROOT).resolve()

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.APP_ENV.casefold() != "production":
            return self

        errors = []
        if self.DEBUG:
            errors.append("DEBUG must be false")
        if not self.SESSION_COOKIE_SECURE:
            errors.append("SESSION_COOKIE_SECURE must be true")
        if not self.SESSION_COOKIE_HTTPONLY:
            errors.append("SESSION_COOKIE_HTTPONLY must be true")
        if self.SESSION_COOKIE_SAMESITE.casefold() not in {"lax", "strict"}:
            errors.append("SESSION_COOKIE_SAMESITE must be lax or strict")
        if not self.RATE_LIMIT_ENABLED:
            errors.append("RATE_LIMIT_ENABLED must be true")
        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use the async PostgreSQL driver")

        origins = self.cors_origin_list
        if not origins or any(
            origin == "*"
            or urlsplit(origin).scheme != "https"
            or not urlsplit(origin).netloc
            or urlsplit(origin).path
            or urlsplit(origin).query
            or urlsplit(origin).fragment
            or urlsplit(origin).username
            or urlsplit(origin).password
            for origin in origins
        ):
            errors.append("CORS_ORIGINS must contain only explicit HTTPS origins")

        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def _sanitize_boolean_env_inputs(cls, data: Any) -> Any:
        """Harden boolean fields against stray ambient environment variables.

        Some machines export generic variables such as ``DEBUG=release`` (set by
        unrelated tooling). Because pydantic-settings matches field names
        case-insensitively, these would otherwise crash boolean parsing before
        any validation can run. Recognized boolean strings are coerced
        normally; unrecognized values are treated as "unset" (the field default
        is used) outside production, but rejected in production so security
        posture fails closed.
        """
        if not isinstance(data, dict):
            return data

        app_env = str(data.get("APP_ENV", "development")).strip().casefold()
        is_production = app_env == "production"

        for field_name in _BOOLEAN_ENV_FIELDS:
            if field_name not in data:
                continue
            coerced = _coerce_bool_like(field_name, data[field_name])
            if coerced is _UNRECOGNIZED:
                offending = data[field_name]
                if is_production:
                    raise ValueError(
                        f"{field_name} must be a valid boolean in production; "
                        f"got {offending!r}"
                    )
                logger.warning(
                    "Ignoring unrecognized boolean value for %s: %r; "
                    "falling back to the default.",
                    field_name,
                    offending,
                )
                data.pop(field_name, None)
            else:
                data[field_name] = coerced
        return data


settings = Settings()
