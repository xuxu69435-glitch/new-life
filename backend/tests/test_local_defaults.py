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
    common = (PROJECT_ROOT / "scripts" / "_local_common.ps1").read_text(encoding="utf-8")
    combined = script + common
    assert "http://127.0.0.1:1234" in combined
    assert "http://127.0.0.1:4321" in combined
    assert "http://127.0.0.1:4321/health" in combined
    assert "50001" not in combined
    assert "50002" not in combined
    assert "ncgw1503677.bohrium.tech" not in combined


def test_launcher_scripts_exist() -> None:
    for name in (
        "local_start.ps1",
        "local_stop.ps1",
        "start_game.ps1",
        "local_status.ps1",
        "local_open.ps1",
        "local_backup_data.ps1",
        "local_reset_data.ps1",
    ):
        assert (PROJECT_ROOT / "scripts" / name).exists()


def test_launcher_scripts_use_local_ports_only() -> None:
    script_names = (
        "local_start.ps1",
        "local_stop.ps1",
        "start_game.ps1",
        "local_status.ps1",
        "local_open.ps1",
        "_local_common.ps1",
    )
    for name in script_names:
        content = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "50001" not in content
        assert "50002" not in content
        assert "5173" not in content
        assert "8000" not in content
        assert "ncgw1503677.bohrium.tech" not in content


def test_start_game_waits_for_health_and_opens_browser() -> None:
    script = (PROJECT_ROOT / "scripts" / "start_game.ps1").read_text(encoding="utf-8")
    assert "Wait-BackendHealth" in script
    assert "Wait-FrontendAccessible" in script
    assert "Open-GameBrowser" in script
    assert "TimeoutSeconds 60" in script or "TimeoutSeconds = 60" in script


def test_gitignore_ignores_local_run_and_save_data() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".local-run/" in gitignore
    assert "backend/data/" in gitignore
    assert "backend/backups/" in gitignore
    assert "*.sqlite3" in gitignore


def test_env_example_uses_local_defaults() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "SAVE_REPOSITORY_TYPE=sqlite" in env_example
    assert "BACKEND_PORT=4321" in env_example
    assert "VITE_API_BASE_URL=http://127.0.0.1:4321" in env_example
    assert "127.0.0.1:1234" in env_example
