from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config import get_settings


@lru_cache
def get_sqlite_engine():
    path = get_settings().resolved_sqlite_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path.as_posix()}"
    return create_engine(url, future=True, connect_args={"check_same_thread": False})


@lru_cache
def get_sqlite_session_factory():
    return sessionmaker(bind=get_sqlite_engine(), autoflush=False, autocommit=False, future=True)


@contextmanager
def sqlite_session_scope() -> Iterator[Session]:
    session = get_sqlite_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_sqlite_database(create_tables: bool = True) -> None:
    from sqlalchemy import text

    from app.infrastructure.save.sqlite_orm_models import SqliteBase

    engine = get_sqlite_engine()
    if create_tables:
        SqliteBase.metadata.create_all(bind=engine)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))


def clear_sqlite_caches() -> None:
    get_sqlite_engine.cache_clear()
    get_sqlite_session_factory.cache_clear()
