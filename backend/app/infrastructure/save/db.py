from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config import settings


@lru_cache
def get_engine():
    return create_engine(settings.resolved_database_url(), future=True, pool_pre_ping=True)


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(create_tables: bool = True) -> None:
    from app.infrastructure.save.orm_models import Base

    engine = get_engine()
    if create_tables:
        Base.metadata.create_all(bind=engine)
