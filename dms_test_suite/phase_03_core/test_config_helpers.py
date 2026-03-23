import os

import pytest

from app.core import config as config_module


def test_parse_csv_and_bool_helpers() -> None:
    assert config_module._parse_csv("a, b,, ,c") == ["a", "b", "c"]
    assert config_module._parse_csv("   ") == []

    assert config_module._parse_bool("true", default=False) is True
    assert config_module._parse_bool("0", default=True) is False
    assert config_module._parse_bool("unknown", default=True) is True


def test_build_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_CREDENTIALS", raising=False)

    settings = config_module._build_settings()
    assert settings.app_env == "development"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.jwt_secret
    assert settings.cors_allow_origins
    assert settings.cors_allow_credentials is True


def test_build_settings_requires_prod_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        config_module._build_settings()

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    with pytest.raises(RuntimeError):
        config_module._build_settings()

    monkeypatch.setenv("JWT_SECRET", "secret")
    settings = config_module._build_settings()
    assert settings.database_url == "postgresql://example"
    assert settings.jwt_secret == "secret"
