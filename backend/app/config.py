"""All configuration comes from environment variables, with safe defaults for local work.

In production we refuse to start with a weak setup instead of quietly running insecurely.
"""
import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

DEFAULT_SECRET = "dev-only-secret-change-me"


class ConfigError(RuntimeError):
    """Raised when the environment is missing something or has something unsafe."""


@dataclass
class Settings:
    environment: str = "development"
    database_url: str = "sqlite:///./bugtracker.db"
    secret_key: str = DEFAULT_SECRET
    access_token_minutes: int = 60
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 5 * 1024 * 1024
    cors_origins: list = field(default_factory=lambda: ["http://localhost:5173"])


def _normalise_database_url(url: str) -> str:
    # Railway and friends hand out "postgres://..." but SQLAlchemy wants a driver name.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}") from None


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env
    defaults = Settings()

    environment = env.get("ENVIRONMENT", defaults.environment).strip().lower()
    database_url = _normalise_database_url(env.get("DATABASE_URL", defaults.database_url))
    secret_key = env.get("SECRET_KEY", defaults.secret_key)

    origins_raw = env.get("CORS_ORIGINS")
    if origins_raw is None:
        cors_origins = list(defaults.cors_origins)
    else:
        cors_origins = [o.strip().rstrip("/") for o in origins_raw.split(",") if o.strip()]

    if environment == "production":
        if secret_key == DEFAULT_SECRET or len(secret_key) < 32:
            raise ConfigError("SECRET_KEY must be set to a random string of at least 32 characters in production")
        if database_url.startswith("sqlite"):
            raise ConfigError("Production needs a real database (set DATABASE_URL to PostgreSQL)")

    return Settings(
        environment=environment,
        database_url=database_url,
        secret_key=secret_key,
        access_token_minutes=_int(env, "ACCESS_TOKEN_MINUTES", defaults.access_token_minutes),
        upload_dir=env.get("UPLOAD_DIR", defaults.upload_dir),
        max_upload_bytes=_int(env, "MAX_UPLOAD_BYTES", defaults.max_upload_bytes),
        cors_origins=cors_origins,
    )


settings = load_settings()
