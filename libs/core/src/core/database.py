from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine
    from sqlalchemy.engine.interfaces import DBAPIConnection


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL must be set")
    if not value.startswith(
        (
            "postgresql+psycopg://",
            "postgresql+asyncpg://",
            "postgresql://",
            "sqlite://",
            "sqlite:///",
        )
    ):
        raise RuntimeError("DATABASE_URL must use PostgreSQL or SQLite")
    return value


def make_engine(url: str | None = None) -> Engine:
    resolved_url = sync_database_url(url or database_url())
    return configure_engine(create_engine(resolved_url, pool_pre_ping=True))


def configure_engine(engine: Engine) -> Engine:
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection: DBAPIConnection, _: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def sync_database_url(url: str) -> str:
    resolved_url = url
    if resolved_url.startswith("postgresql+asyncpg://"):
        resolved_url = resolved_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://", 1
        )
    elif resolved_url.startswith("postgresql://"):
        resolved_url = resolved_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return resolved_url


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session]:
    factory = session_factory(configured_engine())
    with factory() as session:
        yield session


@lru_cache(maxsize=1)
def configured_engine() -> Engine:
    return make_engine()
