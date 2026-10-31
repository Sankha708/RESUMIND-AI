import pytest
from pydantic import ValidationError

from app.config import Settings


def test_valid_production_settings_accept_https_and_async_postgres():
    settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        SESSION_COOKIE_SECURE=True,
        DATABASE_URL="postgresql+asyncpg://user:placeholder@db.example.com/resumind",
        CORS_ORIGINS="https://app.example.com",
    )

    assert settings.APP_ENV == "production"


@pytest.mark.parametrize(
    "overrides",
    [
        {"DEBUG": True},
        {"SESSION_COOKIE_SECURE": False},
        {"SESSION_COOKIE_HTTPONLY": False},
        {"SESSION_COOKIE_SAMESITE": "none"},
        {"RATE_LIMIT_ENABLED": False},
        {"DATABASE_URL": "sqlite+aiosqlite:///./resumind.db"},
        {"CORS_ORIGINS": "*"},
        {"CORS_ORIGINS": "http://app.example.com"},
        {"CORS_ORIGINS": "https://app.example.com/path"},
    ],
)
def test_invalid_production_settings_fail_closed(overrides):
    values = {
        "APP_ENV": "production",
        "DEBUG": False,
        "SESSION_COOKIE_SECURE": True,
        "DATABASE_URL": "postgresql+asyncpg://user:placeholder@db.example.com/resumind",
        "CORS_ORIGINS": "https://app.example.com",
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_validation_error_does_not_disclose_database_url():
    secret = "synthetic-password-must-not-leak"
    with pytest.raises(ValidationError) as captured:
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SESSION_COOKIE_SECURE=True,
            DATABASE_URL=f"postgresql://user:{secret}@db.example.com/resumind",
            CORS_ORIGINS="https://app.example.com",
        )

    assert secret not in str(captured.value)


def test_stray_non_boolean_debug_env_falls_back_to_default_in_development():
    # Machines with unrelated tooling may export DEBUG=release; the app must
    # not crash in development. The field default (True) is used instead.
    settings = Settings(APP_ENV="development", DEBUG="release")
    assert settings.DEBUG is True


@pytest.mark.parametrize("raw,expected", [("true", True), ("0", False), (" yes ", True)])
def test_recognized_boolean_strings_are_coerced(raw, expected):
    settings = Settings(APP_ENV="development", DEBUG=raw)
    assert settings.DEBUG is expected


def test_stray_non_boolean_debug_env_fails_closed_in_production():
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DEBUG="release",
            SESSION_COOKIE_SECURE=True,
            DATABASE_URL="postgresql+asyncpg://user:placeholder@db.example.com/resumind",
            CORS_ORIGINS="https://app.example.com",
        )
