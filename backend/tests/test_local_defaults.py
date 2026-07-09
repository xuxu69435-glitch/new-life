from pathlib import Path

from app.infrastructure.config import Settings
from app.infrastructure.save.factory import create_save_repository
from app.infrastructure.save.in_memory_repository import InMemorySaveRepository
from app.infrastructure.save.sqlite_repository import SQLiteSaveRepository


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _fresh_settings(monkeypatch) -> Settings:
    from app.infrastructure.config import get_settings
    from app.infrastructure.save.sqlite_db import clear_sqlite_caches

    get_settings.cache_clear()
    clear_sqlite_caches()
    return get_settings()


def test_default_save_repository_type_is_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("SAVE_REPOSITORY_TYPE", raising=False)
    settings = _fresh_settings(monkeypatch)
    assert settings.save_repository_type == "sqlite"


def test_default_backend_port_is_4321(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_PORT", raising=False)
    settings = _fresh_settings(monkeypatch)
    assert settings.backend_port == 4321


def test_default_backend_host_is_localhost(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_HOST", raising=False)
    settings = _fresh_settings(monkeypatch)
    assert settings.backend_host == "127.0.0.1"


def test_default_environment_is_local(monkeypatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = _fresh_settings(monkeypatch)
    assert settings.environment == "local"


def test_default_cors_allows_local_frontend(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    settings = _fresh_settings(monkeypatch)
    origins = settings.cors_origin_list()
    assert "http://127.0.0.1:1234" in origins
    assert "http://localhost:1234" in origins


def test_default_sqlite_database_path(monkeypatch) -> None:
    monkeypatch.delenv("SQLITE_DATABASE_PATH", raising=False)
    settings = _fresh_settings(monkeypatch)
    assert settings.resolved_sqlite_database_path().name == "local_save.sqlite3"
    assert settings.resolved_sqlite_database_path().parent.name == "data"


def test_create_save_repository_defaults_to_sqlite(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SAVE_REPOSITORY_TYPE", raising=False)
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "factory.sqlite3"))
    _fresh_settings(monkeypatch)
    repo = create_save_repository()
    assert isinstance(repo, SQLiteSaveRepository)


def test_create_save_repository_memory(monkeypatch) -> None:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "memory")
    _fresh_settings(monkeypatch)
    repo = create_save_repository()
    assert isinstance(repo, InMemorySaveRepository)


def test_frontend_client_default_api_base_url() -> None:
    client_source = (PROJECT_ROOT / "frontend" / "src" / "api" / "client.ts").read_text(encoding="utf-8")
    assert "http://127.0.0.1:4321" in client_source
    assert "8000" not in client_source
    assert "ncgw1503677.bohrium.tech" not in client_source


def test_vite_default_port_is_1234() -> None:
    vite_source = (PROJECT_ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert "port: 1234" in vite_source
    assert "5173" not in vite_source


def test_local_start_script_outputs_local_urls() -> None:
    script = (PROJECT_ROOT / "scripts" / "local_start.ps1").read_text(encoding="utf-8")
    assert "http://127.0.0.1:1234" in script
    assert "http://127.0.0.1:4321" in script
    assert "http://127.0.0.1:4321/health" in script
    assert "50001" not in script
    assert "50002" not in script
    assert "ncgw1503677.bohrium.tech" not in script


def test_env_example_uses_local_defaults() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "SAVE_REPOSITORY_TYPE=sqlite" in env_example
    assert "BACKEND_PORT=4321" in env_example
    assert "VITE_API_BASE_URL=http://127.0.0.1:4321" in env_example
    assert "127.0.0.1:1234" in env_example
