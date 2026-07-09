from uuid import uuid4

import pytest

from app.application.game_command_service import GameCommandService
from app.application.save_migration_service import SaveMigrationService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState, SimulationEventType
from app.infrastructure.rng import ServerRandom
from app.modules.legal.models import LegalState
from app.modules.random_events.choice_effect_resolver import RandomEventChoiceEffectResolver
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.library_models import AgeRange, V1EventChoice, V1EventDefinition
from app.modules.social.events import SocialEventProcessor
from app.modules.social.models import SocialPerson, SocialRelationship, SocialState, clamp_score
from app.modules.social.processor import SocialAnnualProcessor
from app.modules.social.rules import build_default_social_state, get_social_rules
from app.modules.social.service import SocialService
from app.modules.social.summary import build_social_summary
from app.modules.timeline.generator import TimelineGenerator
from app.modules.timeline.models import LifeYearSnapshot
from app.engine.simulation_context import YearResult


def _social_rules_high_chance(rules: dict) -> dict:
    patched = dict(rules)
    social = dict(get_social_rules(rules))
    social["school_relationship_chance"] = 1.0
    social["work_relationship_chance"] = 1.0
    patched["social"] = social
    return patched


def test_create_life_has_stable_social_state(rules) -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    social = SocialState.from_life_state_dict(state.social)
    assert social.persons == []
    assert social.relationships == []
    assert social.social_summary


def test_legacy_state_migration_adds_social(rules) -> None:
    legacy = {
        "life_id": str(uuid4()),
        "person_id": str(uuid4()),
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
    migrated = SaveMigrationService().ensure_life_state_shape(LifeState.model_validate(legacy), rules)
    assert migrated.social
    assert "persons" in migrated.social


def test_social_person_and_relationship_fields() -> None:
    person = SocialPerson(person_id="p1", name="测试", age=12)
    relationship = SocialRelationship(
        relationship_id="r1",
        person_id="p1",
        relationship_type="friend",
        closeness=120,
        trust=-5,
        conflict=150,
        familiarity=200,
        importance=300,
    ).clamp_values()
    assert relationship.closeness == 100
    assert relationship.trust == 0
    assert relationship.conflict == 100
    assert relationship.familiarity == 100
    assert relationship.importance == 100
    assert person.name == "测试"


def test_school_stage_can_generate_relationship(rules, life_state) -> None:
    social = build_default_social_state(rules)
    life_state.education = {
        **life_state.education,
        "current_stage": "middle",
        "is_enrolled": True,
    }
    processor = SocialAnnualProcessor(get_social_rules(_social_rules_high_chance(rules)), ServerRandom(3))
    social = processor.apply_annual_changes(social, life_state, _social_rules_high_chance(rules))
    assert social.new_relationships_this_year


def test_work_stage_can_generate_relationship(rules, life_state) -> None:
    social = build_default_social_state(rules)
    life_state.age = 25
    life_state.career = {
        **life_state.career,
        "employment_status": "employed",
        "career_path": "office",
    }
    processor = SocialAnnualProcessor(get_social_rules(_social_rules_high_chance(rules)), ServerRandom(5))
    social = processor.apply_annual_changes(social, life_state, _social_rules_high_chance(rules))
    assert social.new_relationships_this_year


def test_prison_blocks_new_social_relationships(rules, life_state) -> None:
    social = build_default_social_state(rules)
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.legal = {**LegalState(is_in_prison=True).to_life_state_dict()}
    processor = SocialAnnualProcessor(get_social_rules(_social_rules_high_chance(rules)), ServerRandom(1))
    social = processor.apply_restricted_decay(social, life_state.age + 1, "prison")
    assert not social.new_relationships_this_year


def test_fugitive_blocks_new_social_relationships(rules, life_state) -> None:
    social = build_default_social_state(rules)
    life_state.career = {**life_state.career, "employment_status": "employed"}
    life_state.legal = {**LegalState(is_fugitive=True).to_life_state_dict()}
    processor = SocialAnnualProcessor(get_social_rules(_social_rules_high_chance(rules)), ServerRandom(1))
    social = processor.apply_restricted_decay(social, life_state.age + 1, "fugitive")
    assert not social.new_relationships_this_year


def test_relationships_decay_over_years(rules) -> None:
    social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="friend",
                closeness=40,
                trust=40,
                conflict=10,
                familiarity=40,
                started_age=1,
            ).to_dict()
        ],
        persons=[SocialPerson(person_id="p1", name="朋友A").to_dict()],
    )
    processor = SocialAnnualProcessor(get_social_rules(rules), ServerRandom(1))
    social = processor.apply_annual_changes(
        social,
        LifeState(
            life_id="life-1",
            person_id="p1",
            age=5,
            education={"current_stage": "none", "is_enrolled": False},
            career={"employment_status": "unemployed"},
        ),
        rules,
    )
    rel = social.get_relationship_models()["r1"]
    assert rel.closeness < 40


def test_best_friend_upgrade(rules) -> None:
    social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="friend",
                closeness=90,
                trust=88,
                conflict=0,
                familiarity=80,
                started_age=1,
            ).to_dict()
        ],
        persons=[SocialPerson(person_id="p1", name="挚友候选").to_dict()],
    )
    processor = SocialAnnualProcessor(get_social_rules(rules), ServerRandom(1))
    processor._upgrade_and_break_relationships(social, 10)
    rel = social.get_relationship_models()["r1"]
    assert rel.relationship_type == "best_friend"


def test_high_conflict_becomes_rival(rules) -> None:
    social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="coworker",
                closeness=30,
                trust=20,
                conflict=75,
                familiarity=40,
                started_age=1,
            ).to_dict()
        ],
        persons=[SocialPerson(person_id="p1", name="竞争同事").to_dict()],
    )
    processor = SocialAnnualProcessor(get_social_rules(rules), ServerRandom(1))
    processor._upgrade_and_break_relationships(social, 10)
    rel = social.get_relationship_models()["r1"]
    assert rel.relationship_type == "rival"


def test_random_event_creates_friend_relationship() -> None:
    processor = SocialEventProcessor()
    social = build_default_social_state()
    social = processor.process(
        SimulationEventType.SOCIAL_RELATIONSHIP_CREATED,
        {
            "name": "事件朋友",
            "relationship_type": "friend",
            "role": "friend",
            "source": "random_event",
            "closeness": 70,
            "trust": 65,
        },
        social,
        12,
    )
    assert social.new_relationships_this_year
    assert social.friend_count() == 1


def test_random_event_creates_mentor_relationship() -> None:
    processor = SocialEventProcessor()
    social = build_default_social_state()
    social = processor.process(
        SimulationEventType.SOCIAL_RELATIONSHIP_CREATED,
        {
            "name": "贵人",
            "relationship_type": "mentor",
            "role": "mentor",
            "source": "random_event",
            "closeness": 55,
            "trust": 80,
        },
        social,
        30,
    )
    assert social.has_relationship_type("mentor")


def test_random_event_changes_relationship_values() -> None:
    processor = SocialEventProcessor()
    social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="friend",
                closeness=50,
                trust=50,
                conflict=10,
            ).to_dict()
        ],
        persons=[SocialPerson(person_id="p1", name="朋友").to_dict()],
    )
    social = processor.process(
        SimulationEventType.SOCIAL_RELATIONSHIP_CHANGE_REQUESTED,
        {"relationship_id": "r1", "closeness_delta": 15, "trust_delta": 10, "conflict_delta": 5},
        social,
        12,
    )
    rel = social.get_relationship_models()["r1"]
    assert rel.closeness == 65
    assert rel.trust == 60
    assert rel.conflict == 15


def test_condition_matcher_has_friend(rules, life_state) -> None:
    life_state.social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="friend",
                closeness=60,
                trust=60,
            ).to_dict()
        ]
    ).to_life_state_dict()
    event = V1EventDefinition(
        event_id="TEST",
        name="test",
        category="primary",
        age_range=AgeRange(min=0, max=99),
        conditions={"has_friend": True},
        event_text="",
        choices=[],
    )
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_condition_matcher_friend_count_min(rules, life_state) -> None:
    life_state.social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="friend",
                closeness=60,
                trust=60,
            ).to_dict(),
            SocialRelationship(
                relationship_id="r2",
                person_id="p2",
                relationship_type="friend",
                closeness=60,
                trust=60,
            ).to_dict(),
        ]
    ).to_life_state_dict()
    event = V1EventDefinition(
        event_id="TEST",
        name="test",
        category="primary",
        age_range=AgeRange(min=0, max=99),
        conditions={"friend_count_min": 2},
        event_text="",
        choices=[],
    )
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_condition_matcher_relationship_type_exists(rules, life_state) -> None:
    life_state.social = SocialState(
        relationships=[
            SocialRelationship(
                relationship_id="r1",
                person_id="p1",
                relationship_type="mentor",
                closeness=60,
                trust=80,
            ).to_dict()
        ]
    ).to_life_state_dict()
    event = V1EventDefinition(
        event_id="TEST",
        name="test",
        category="primary",
        age_range=AgeRange(min=0, max=99),
        conditions={"relationship_type_exists": "mentor"},
        event_text="",
        choices=[],
    )
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_choice_effect_resolver_supports_social_effects() -> None:
    resolver = RandomEventChoiceEffectResolver()
    event = V1EventDefinition(
        event_id="E016",
        name="结交好朋友",
        category="primary",
        age_range=AgeRange(min=6, max=18),
        event_text="",
        choices=[],
    )
    choice = V1EventChoice(
        choice_id="E016_A",
        label="结交",
        choice_text="结交",
        effects_text="结交新朋友",
        effects=[
            {"type": "social_relationship_created", "name": "朋友", "relationship_type": "friend"},
        ],
    )
    resolved = resolver.resolve_choice(event, choice, None)  # type: ignore[arg-type]
    assert resolved[0][0] == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED


def test_year_result_includes_social_changes(rules) -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    patched_rules = _social_rules_high_chance(rules)
    state.education = {**state.education, "current_stage": "middle", "is_enrolled": True}
    next_state, result, _ = service.engine.advance_one_year(
        state,
        {"annual_focus": "balanced_year"},
        patched_rules,
    )
    assert next_state.social
    assert result.social_changes or result.new_social_relationships or result.social_narrative


def test_timeline_generates_social_entry() -> None:
    result = YearResult(
        life_id="life-1",
        age_before=10,
        age_after=11,
        is_dead=False,
        new_social_relationships=[
            {"person_name": "林晓", "relationship_type": "friend"},
        ],
    )
    snapshot = LifeYearSnapshot(
        snapshot_id="snap-1",
        life_id="life-1",
        age_before=10,
        age_after=11,
        year_index=11,
        rule_version="v1",
        state_before={"age": 10},
        state_after={"age": 11},
        year_result={},
    )
    entries = TimelineGenerator().generate(result, snapshot)
    assert any(item.entry_type == "social" for item in entries)


def test_sqlite_persists_social_state(rules, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "social.sqlite3"))
    from app.infrastructure.config import get_settings
    from app.infrastructure.save.sqlite_db import clear_sqlite_caches
    from app.infrastructure.save.factory import create_save_repository

    get_settings.cache_clear()
    clear_sqlite_caches()
    repo = create_save_repository()
    service = SaveService(repository=repo)
    state = service.create_life("v1", rules)
    state.social = build_default_social_state(rules).to_life_state_dict()
    processor = SocialEventProcessor()
    social = SocialState.from_life_state_dict(state.social)
    social = processor.process(
        SimulationEventType.SOCIAL_RELATIONSHIP_CREATED,
        {"name": "存档朋友", "relationship_type": "friend", "closeness": 70, "trust": 65},
        social,
        1,
    )
    state.social = social.to_life_state_dict()
    service.save_life_state(state, rules=rules)
    loaded = service.get_life_state(state.life_id, rules=rules)
    assert loaded.social.get("relationships")
