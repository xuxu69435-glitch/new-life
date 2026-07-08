import pytest

from app.application.game_command_service import GameCommandService
from app.application.save_migration_service import SaveMigrationService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState
from app.engine.simulation_engine import SimulationEngine
from app.modules.timeline.read_service import TimelineReadService


def _advance(service: GameCommandService, life_id: str, years: int = 1):
    last = None
    for _ in range(years):
        last = service.advance_one_year(life_id, {"annual_focus": "balanced_year"})
    return last


def test_create_life_generates_initial_save_record() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    record = service.save_service.get_save_record(state.life_id)
    assert record is not None
    assert record.life_id == state.life_id
    assert record.save_version == "v1"
    assert record.current_age == 0


def test_advance_one_year_generates_year_snapshot() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = service.save_service.get_year_snapshot(state.life_id, 1)
    assert snapshot is not None
    assert snapshot.age_before == 0
    assert snapshot.age_after == 1
    assert snapshot.snapshot_version == "v1"


def test_snapshot_contains_state_before_and_after() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = service.save_service.get_year_snapshot(state.life_id, 1)
    assert snapshot.state_before["age"] == 0
    assert snapshot.state_after["age"] == 1
    assert snapshot.state_before["life_id"] == state.life_id


def test_snapshot_contains_year_result() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    result = _advance(service, state.life_id, 1)
    snapshot = service.save_service.get_year_snapshot(state.life_id, 1)
    assert snapshot.year_result["age_after"] == 1
    assert snapshot.year_result["life_id"] == result.life_id


def test_snapshot_contains_narrative_result() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    snapshot = service.save_service.get_year_snapshot(state.life_id, 1)
    assert "narrative_text" in snapshot.year_result
    assert snapshot.narrative_result is not None or snapshot.year_result.get("narrative_text")


def test_random_event_generates_timeline_entry(life_state, rules) -> None:
    service = GameCommandService()
    state = service.save_service.create_life("v1", rules)
    from app.engine.simulation_context import YearResult

    year_result = YearResult(
        life_id=state.life_id,
        age_before=0,
        age_after=1,
        is_dead=False,
        triggered_random_events=[
            {"event_id": "E001", "name": "测试随机事件", "category": "life", "narrative_text": "随机事件叙事"}
        ],
    )
    next_state = state.model_copy(update={"age": 1})
    service.save_service.persist_year_record(state, next_state, year_result)
    entries = service.get_timeline_entries(state.life_id, entry_type="random_event")
    assert any(item["entry_type"] == "random_event" for item in entries)


def test_legal_event_generates_timeline_entry(life_state, rules) -> None:
    service = GameCommandService()
    legal = {**life_state.legal, "is_in_prison": True, "has_criminal_record": True}
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "legal": legal})
    service.save_service.save_life_state(state, rules=rules)
    service.advance_one_year(state.life_id, {"annual_focus": "balanced_year"})
    entries = service.get_timeline_entries(state.life_id, entry_type="legal_event")
    assert any(item["entry_type"] == "legal_event" for item in entries)


def test_mainline_completion_generates_timeline_entry(life_state, rules) -> None:
    service = GameCommandService()
    mainline = {**life_state.mainline, "completed_tasks": ["M001"]}
    state = life_state.model_copy(update={"age": 5, "life_stage": "childhood", "mainline": mainline})
    service.save_service.save_life_state(state, rules=rules)
    service.advance_one_year(state.life_id, {"annual_focus": "balanced_year"})
    entries = service.get_timeline_entries(state.life_id, entry_type="mainline_task")
    assert any(item["entry_type"] == "mainline_task" for item in entries)


def test_achievement_unlock_generates_timeline_entry() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    entries = service.get_timeline_entries(state.life_id, entry_type="achievement")
    assert any(item["entry_type"] == "achievement" for item in entries)


def test_milestone_generates_timeline_entry(life_state, rules) -> None:
    service = GameCommandService()
    family = {
        **life_state.family,
        "relationship_status": "married",
        "spouse": {"person_id": "s1", "name": "Spouse", "relation": "spouse", "playable": False},
    }
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "family": family})
    service.save_service.save_life_state(state, rules=rules)
    service.advance_one_year(state.life_id, {"annual_focus": "balanced_year"})
    entries = service.get_timeline_entries(state.life_id, entry_type="milestone")
    assert any(item["entry_type"] == "milestone" for item in entries)


def test_death_entry_has_highest_importance(life_state, rules) -> None:
    from unittest.mock import MagicMock

    from app.engine.simulation_context import SimulationEventType
    from app.modules.death.service import DeathService
    from app.modules.inheritance.service import InheritanceService
    from conftest import make_context

    service = GameCommandService()
    state = life_state.model_copy(
        update={
            "age": 70,
            "life_stage": "elder",
            "assets": {"cash": 50000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 50000.0},
            "family": {
                **life_state.family,
                "spouse": {"person_id": "s1", "name": "Spouse", "relation": "spouse", "playable": False},
            },
        }
    )
    service.save_service.save_life_state(state, rules=rules)
    context = make_context(state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)
    context.event_bus.publish(
        SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
        "random_events",
        {"reason": "accident", "death_type": "direct_death", "probability": 1.0},
    )
    DeathService().run(context)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    InheritanceService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())
    next_state = context.result_collector.apply_to_state(state, rules)
    year_result = context.result_collector.to_year_result(state, next_state, context.event_bus.all(), [])
    service.save_service.persist_year_record(state, next_state, year_result, context.result_collector.inheritance_result)

    entries = service.get_timeline_entries(state.life_id, entry_type="death")
    assert entries
    death_importance = entries[0]["importance"]
    other_entries = service.get_timeline_entries(state.life_id)
    assert all(death_importance >= item["importance"] for item in other_entries)


def test_inheritance_generates_timeline_entry(life_state, rules) -> None:
    service = GameCommandService()
    state = life_state.model_copy(
        update={
            "age": 70,
            "is_dead": True,
            "death_reason": "natural",
            "assets": {"cash": 20000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 20000.0},
        }
    )
    from app.modules.inheritance.rules import settle_estate
    from app.modules.assets.models import AssetState
    from app.modules.family.models import FamilyState
    from app.engine.simulation_context import YearResult

    inheritance = settle_estate(
        state.life_id,
        state.person_id,
        AssetState.from_life_state_dict(state.assets),
        FamilyState.from_life_state_dict(state.family),
        rules["inheritance"],
        "natural_death",
    ).model_dump()
    year_result = YearResult(
        life_id=state.life_id,
        age_before=69,
        age_after=70,
        is_dead=True,
        inheritance_result=inheritance,
    )
    service.save_service.persist_year_record(state, state, year_result, inheritance)
    entries = service.get_timeline_entries(state.life_id, entry_type="inheritance")
    assert any(item["entry_type"] == "inheritance" for item in entries)


def test_filter_timeline_by_age_range() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 3)
    entries = service.get_timeline_entries(state.life_id, age_min=2, age_max=3)
    assert entries
    assert all(2 <= item["age"] <= 3 for item in entries)


def test_filter_timeline_by_entry_type() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    entries = service.get_timeline_entries(state.life_id, entry_type="milestone")
    assert all(item["entry_type"] == "milestone" for item in entries)


def test_read_year_snapshot_by_age() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 2)
    snapshot = service.get_year_snapshot(state.life_id, 2)
    assert snapshot["age_after"] == 2


def test_read_snapshot_does_not_recalculate() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    before = service.get_year_snapshot(state.life_id, 1)
    after = service.get_year_snapshot(state.life_id, 1)
    assert before == after


def test_legacy_state_missing_fields_can_be_migrated(rules) -> None:
    migration = SaveMigrationService()
    legacy = {
        "life_id": "legacy-1",
        "person_id": "p1",
        "age": 10,
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
    migrated = migration.ensure_life_state_shape(LifeState.model_validate(legacy), rules)
    assert migrated.legal
    assert migrated.mainline
    assert migrated.achievements


def test_year_detail_returns_backend_payload() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    _advance(service, state.life_id, 1)
    detail = service.get_year_detail(state.life_id, 1)
    assert detail["age"] == 1
    assert "year_result" in detail
    assert "events" in detail


def test_timeline_read_service_is_read_only(life_state, rules) -> None:
    save_service = SaveService()
    state = save_service.create_life("v1", rules)
    engine = SimulationEngine(rng_seed=1)
    progress = __import__("app.application.life_progress_service", fromlist=["LifeProgressService"]).LifeProgressService(
        save_service, __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader(), engine
    )
    progress.advance_one_year(state.life_id, {"annual_focus": "balanced_year"})
    reader = TimelineReadService(save_service.repository)
    entries_before = reader.get_timeline_entries(state.life_id)
    entries_after = reader.get_timeline_entries(state.life_id)
    assert entries_before == entries_after
