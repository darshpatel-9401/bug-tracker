import pytest

from app.config import DEFAULT_SECRET, ConfigError, load_settings


def test_defaults_are_safe_for_local_development():
    s = load_settings({})
    assert s.environment == "development"
    assert s.database_url.startswith("sqlite")
    assert s.cors_origins == ["http://localhost:5173"]


def test_heroku_style_postgres_url_is_rewritten_for_sqlalchemy():
    s = load_settings({"DATABASE_URL": "postgres://u:p@host:5432/db"})
    assert s.database_url == "postgresql+psycopg2://u:p@host:5432/db"


def test_plain_postgresql_url_is_rewritten_too():
    s = load_settings({"DATABASE_URL": "postgresql://u:p@host/db"})
    assert s.database_url == "postgresql+psycopg2://u:p@host/db"


def test_cors_origins_are_split_and_trailing_slashes_removed():
    s = load_settings({"CORS_ORIGINS": "https://a.app/, https://b.app ,,"})
    assert s.cors_origins == ["https://a.app", "https://b.app"]


def test_production_refuses_the_default_secret():
    with pytest.raises(ConfigError):
        load_settings({"ENVIRONMENT": "production", "DATABASE_URL": "postgres://u:p@h/d", "SECRET_KEY": DEFAULT_SECRET})


def test_production_refuses_a_short_secret():
    with pytest.raises(ConfigError):
        load_settings({"ENVIRONMENT": "production", "DATABASE_URL": "postgres://u:p@h/d", "SECRET_KEY": "short"})


def test_production_refuses_sqlite():
    with pytest.raises(ConfigError):
        load_settings({"ENVIRONMENT": "production", "SECRET_KEY": "x" * 40})


def test_production_with_good_values_loads():
    s = load_settings({"ENVIRONMENT": "production", "DATABASE_URL": "postgres://u:p@h/d", "SECRET_KEY": "x" * 40})
    assert s.environment == "production"


def test_bad_number_is_a_clear_error():
    with pytest.raises(ConfigError):
        load_settings({"ACCESS_TOKEN_MINUTES": "soon"})
