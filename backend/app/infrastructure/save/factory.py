from app.infrastructure.config import get_settings
from app.infrastructure.save.in_memory_repository import InMemorySaveRepository
from app.infrastructure.save.postgres_repository import PostgresSaveRepository
from app.infrastructure.save.repository import SaveRepository
from app.infrastructure.save.sqlite_repository import SQLiteSaveRepository


def create_save_repository() -> SaveRepository:
    settings = get_settings()
    repo_type = settings.save_repository_type.strip().lower()
    if repo_type == "memory":
        return InMemorySaveRepository()
    if repo_type == "postgres":
        return PostgresSaveRepository(auto_init=settings.auto_create_tables)
    return SQLiteSaveRepository()
