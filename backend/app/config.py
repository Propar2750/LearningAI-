"""Application settings.

Secrets live in the repo-root ``.env`` (already present, gitignored). Only the
DB password is secret; the Supabase session-pooler host/port/db/user are
non-secret defaults that can still be overridden via env vars.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

# backend/app/config.py -> parents[2] is the repo root, where .env lives.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        case_sensitive=False,
        extra="ignore",  # root .env also holds SUPABASE_SECRET_API_KEY etc.
    )

    # Secret (root .env: DATABASE_PWD).
    database_pwd: str

    # Supabase session pooler (IPv4 + prepared-statement safe). Defaults match
    # the confirmed project; override via env if the project moves.
    db_host: str = "aws-1-ap-northeast-1.pooler.supabase.com"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres.lpbvvqnxoqoedmciukkv"

    # Vite dev server origins for CORS (comma-separated).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def _url(self, drivername: str, query: dict | None = None) -> URL:
        # URL.create escapes the password correctly (passwords often contain
        # characters that would break a hand-built URL string).
        return URL.create(
            drivername,
            username=self.db_user,
            password=self.database_pwd,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query=query or {},
        )

    @property
    def database_url_async(self) -> URL:
        # asyncpg rejects libpq's ?sslmode=...; SSL is set via connect_args.
        return self._url("postgresql+asyncpg")

    @property
    def database_url_sync(self) -> URL:
        # psycopg (used only by Alembic) honors libpq sslmode.
        return self._url("postgresql+psycopg", {"sslmode": "require"})


settings = Settings()
