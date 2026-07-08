import os

import pytest

from app.application.game_command_service import GameCommandService
from app.application.save_migration_service import SaveMigrationService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState
from app.infrastructure.config import Settings
from app.infrastructure.save.postgres_repository import PostgresSaveRepository


def _postgres_enabled() -> bool:
    return os.environ.get("RUN_POSTGRES_TESTS", "").lower() in {"1", "true", "yes"}


pytestmark = pytest.mark.skipif(not _postgres_enabled(), reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests")


@pytest.fixture
def postgres_settings(monkeypatch) -> Settings:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "postgres")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://monirensheng:monirensheng@localhost:5432/monirensheng_test",
        ),
    )
    from app.infrastructure.config import get_settings

    get_settings.cache_clear()
    from app.infrastructure.save.db import get_engine, get_session_factory

    get_engine.cache_clear()
    get_session_factory.cache_clear()
    return get_settings()


@pytest.fixture
def postgres_repository(postgres_settings) -> PostgresSaveRepository:
    repo = PostgresSaveRepository(auto_init=True)
    return repo


@pytest.fixture
def postgres_service(postgres_repository) -> SaveService:
    return SaveService(repository=postgres_repository)


def _advance(service: GameCommandService, life_id: str, years: int = 1):
    last = None
    for _ in range(years):
        last = service.advance_one_year(life_id, {"annual_focus": "balanced_year"})
    return last


def test_postgres_repository_initializes_tables(postgres_repository) -> None:
    assert postgres_repository is not None


def test_create_life_persists_save_and_state(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    record = postgres_service.get_save_record(state.life_id)
    loaded = postgres_service.get_life_state(state.life_id)
    assert record is not None
    assert record.life_id == state.life_id
    assert loaded.life_id == state.life_id


def test_advance_persists_snapshot_logs_and_timeline(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = postgres_service.get_year_snapshot(state.life_id, 1)
    entries = postgres_service.get_timeline_entries(state.life_id)
    logs = postgres_service.get_event_logs(state.life_id)
    assert snapshot is not None
    assert snapshot.state_before["age"] == 0
    assert snapshot.state_after["age"] == 1
    assert entries
    assert logs


def test_rebuilt_repository_reads_existing_data(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 2)
    rebuilt = PostgresSaveRepository(auto_init=False)
    reread = SaveService(repository=rebuilt)
    record = reread.get_save_record(state.life_id)
    timeline = reread.get_timeline_entries(state.life_id)
    snapshot = reread.get_year_snapshot(state.life_id, 2)
    assert record is not None
    assert timeline
    assert snapshot is not None


def test_filter_timeline_by_age_and_type(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    _advance(service, state.life_id, 2)
    rebuilt = SaveService(repository=PostgresSaveRepository(auto_init=False))
    entries = rebuilt.get_timeline_entries(state.life_id, age_min=1, age_max=1)
    achievements = rebuilt.get_timeline_entries(state.life_id, entry_type="achievement")
    assert entries
    assert all(1 <= item.age <= 1 for item in entries)
    assert all(item.entry_type == "achievement" for item in achievements)


def test_duplicate_state_save_does_not_duplicate_records(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    postgres_service.save_life_state(state)
    postgres_service.save_life_state(state)
    records = postgres_service.list_saves()
    assert len([item for item in records if item.life_id == state.life_id]) == 1


def test_duplicate_year_snapshot_upserts(postgres_service) -> None:
    service = GameCommandService(save_service=postgres_service)
    state, _ = service.create_life()
    result = _advance(service, state.life_id, 1)
    state_after = postgres_service.get_life_state(state.life_id)
    postgres_service.persist_year_record(state, state_after, result)
    snapshots = postgres_service.repository.get_snapshots(state.life_id)
    age_one = [item for item in snapshots if item.age_after == 1]
    assert len(age_one) == 1


def test_legacy_state_migration_on_read(postgres_service, rules) -> None:
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
    postgres_service.save_life_state(migrated, rules=rules)
    loaded = postgres_service.get_life_state(life_id, rules=rules)
    assert loaded.legal
    assert loaded.mainline
    assert loaded.achievements
