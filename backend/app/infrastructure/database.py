"""Legacy SQLAlchemy module kept for compatibility.

PostgreSQL persistence uses app.infrastructure.save.db instead.
"""

from app.infrastructure.save.db import get_engine, get_session_factory

__all__ = ["get_engine", "get_session_factory", "engine", "SessionLocal"]


def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    if name == "SessionLocal":
        return get_session_factory()
    raise AttributeError(name)
