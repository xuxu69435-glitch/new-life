import os

import pytest

from app.application.game_command_service import GameCommandService
from app.application.save_migration_service import SaveMigrationService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState
from app.infrastructure.config import Settings
from app.infrastructure.save.sqlite_repository import SQLiteSaveRepository


@pytest.fixture
def sqlite_settings(monkeypatch, tmp_path) -> Settings:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    from app.infrastructure.config import get_settings
    from app.infrastructure.save.sqlite_db import clear_sqlite_caches

    get_settings.cache_clear()
    clear_sqlite_caches()
    return get_settings()


@pytest.fixture
def sqlite_repository(sqlite_settings) -> SQLiteSaveRepository:
    return SQLiteSaveRepository(auto_init=True)


@pytest.fixture
def sqlite_service(sqlite_repository) -> SaveService:
    return SaveService(repository=sqlite_repository)


def _advance(service: GameCommandService, life_id: str, years: int = 1):
    last = None
    for _ in range(years):
        last = service.advance_one_year(life_id, {"annual_focus": "balanced_year"})
    return last


def test_sqlite_repository_initializes_database(sqlite_repository, sqlite_settings) -> None:
    assert sqlite_repository is not None
    assert sqlite_settings.resolved_sqlite_database_path().exists()


def test_sqlite_create_life_persists_save_and_state(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    record = sqlite_service.get_save_record(state.life_id)
    loaded = sqlite_service.get_life_state(state.life_id)
    assert record is not None
    assert record.life_id == state.life_id
    assert loaded.life_id == state.life_id


def test_sqlite_advance_persists_snapshot_logs_and_timeline(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = sqlite_service.get_year_snapshot(state.life_id, 1)
    entries = sqlite_service.get_timeline_entries(state.life_id)
    logs = sqlite_service.get_event_logs(state.life_id)
    assert snapshot is not None
    assert snapshot.state_before["age"] == 0
    assert snapshot.state_after["age"] == 1
    assert entries
    assert logs


def test_sqlite_rebuilt_repository_reads_existing_data(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 2)
    rebuilt = SQLiteSaveRepository(auto_init=False)
    reread = SaveService(repository=rebuilt)
    record = reread.get_save_record(state.life_id)
    timeline = reread.get_timeline_entries(state.life_id)
    snapshot = reread.get_year_snapshot(state.life_id, 2)
    assert record is not None
    assert timeline
    assert snapshot is not None


def test_sqlite_filter_timeline_by_age_and_type(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 2)
    rebuilt = SaveService(repository=SQLiteSaveRepository(auto_init=False))
    entries = rebuilt.get_timeline_entries(state.life_id, age_min=1, age_max=1)
    achievements = rebuilt.get_timeline_entries(state.life_id, entry_type="achievement")
    assert entries
    assert all(1 <= item.age <= 1 for item in entries)
    assert all(item.entry_type == "achievement" for item in achievements)


def test_sqlite_get_snapshot_by_age(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = sqlite_service.get_year_snapshot(state.life_id, 1)
    assert snapshot is not None
    assert snapshot.age_after == 1


def test_sqlite_save_inheritance_and_heir_continuation(sqlite_service) -> None:
    service = GameCommandService(save_service=sqlite_service)
    state, _ = service.create_life()
    inheritance = {"status": "settled", "total_assets": 1000}
    heir = {"source_life_id": state.life_id, "heir_life_id": "heir-1"}
    sqlite_service.repository.save_inheritance(state.life_id, inheritance)
    sqlite_service.repository.save_heir_continuation(state.life_id, heir)
    rebuilt = SQLiteSaveRepository(auto_init=False)
    assert rebuilt.get_inheritance(state.life_id) == inheritance
    assert rebuilt.get_heir_continuation(state.life_id) == heir


def test_sqlite_legacy_state_migration_on_read(sqlite_service, rules) -> None:
    from uuid import uuid4

    life_id = str(uuid4())
    person_id = str(uuid4())
    legacy = {
        "life_id": life_id,
        "person_id": person_id,
        "age": 8,
        "life_stage": "childhood",
        "attributes": dict(rules["default_attributes"]),
        "health": dict(rules["default_health"]),
        "family": {},
        "education": {},
        "career": {},
        "assets": dict(rules["default_assets"]),
        "flags": {},
        "rule_version": "v1",
    }
    migrated = SaveMigrationService().ensure_life_state_shape(LifeState.model_validate(legacy), rules)
    sqlite_service.save_life_state(migrated, rules=rules)
    loaded = sqlite_service.get_life_state(life_id, rules=rules)
    assert loaded.legal
    assert loaded.mainline
    assert loaded.achievements
