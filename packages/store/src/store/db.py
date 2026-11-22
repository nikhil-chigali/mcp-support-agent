"""Database settings, engine and session factory for the store."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DatabaseSettings(BaseSettings):
    """Read from environment variables prefixed STORE_, e.g. STORE_DATABASE_URL."""

    model_config = SettingsConfigDict(env_prefix="STORE_")

    # Default: the local docker compose database, as the store's own role.
    database_url: str = "postgresql+psycopg://store_app:store_app@localhost:5432/store"


settings = DatabaseSettings()

# create_engine does not connect yet; the first query does.
engine = create_engine(settings.database_url)

# expire_on_commit=False keeps loaded objects readable after commit,
# which API handlers rely on when they build a response from them.
SessionLocal = sessionmaker(engine, expire_on_commit=False)
