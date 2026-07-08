"""SQLite persistence adapter placeholder for Phase 13+.

Wire this repository when ORM models and migrations are ready.
"""

from app.infrastructure.save.in_memory_repository import InMemorySaveRepository


class SqliteSaveRepository(InMemorySaveRepository):
    """Temporary fallback to in-memory until SQLAlchemy models are implemented."""

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.database_url = database_url
