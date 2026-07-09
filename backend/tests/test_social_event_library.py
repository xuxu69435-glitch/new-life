import copy
from uuid import uuid4

import pytest

from app.engine.event_bus import EventBus
from app.engine.result_collector import ResultCollector
from app.engine.simulation_context import LifeState, SimulationContext, SimulationEventType
from app.infrastructure.rng import ServerRandom
from app.modules.legal.models import LegalState
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.choice_effect_resolver import RandomEventChoiceEffectResolver
from app.modules.random_events.draw_state import blocked_social_sub_categories
from app.modules.random_events.service import RandomEventsService
from app.modules.random_events.v1_draw import RandomEventV1DrawService
from app.modules.social.events import SocialEventProcessor
from app.modules.social.models import SocialPerson, SocialRelationship, SocialState
from app.modules.social.rules import build_default_social_state
from app.rules.data.social_event_builder import WEIGHT_MAP
from app.rules.social_event_library_loader import SocialEventLibraryLoader
from app.rules.social_event_library_validator import SocialEventLibraryValidator
from tests.conftest import make_context


@pytest.fixture
def social_library():
    return SocialEventLibraryLoader().load()


def _social_state_with(**kwargs) -> dict:
    social = build_default_social_state()
    for key, value in kwargs.items():
        setattr(social, key, value)
    return social.to_life_state_dict()


def _with_relationship(
    life_state: LifeState,
    *,
    relationship_type: str,
    closeness: int = 50,
    trust: int = 50,
    conflict: int = 0,
    familiarity: int = 40,
    status: str = "active",
    person_name: str = "测试人物",
) -> LifeState:
    person_id = f"person-{relationship_type}"
    rel_id = f"rel-{relationship_type}"
    life_state.social = SocialState(
        persons=[
            SocialPerson(person_id=person_id, name=person_name, role=relationship_type).to_dict()
        ],
        relationships=[
            SocialRelationship(
                relationship_id=rel_id,
                person_id=person_id,
                relationship_type=relationship_type,
                closeness=closeness,
                trust=trust,
                conflict=conflict,
                familiarity=familiarity,
                status=status,
            ).to_dict()
        ],
    ).to_life_state_dict()
    return life_state


def test_social_library_loads_s001_to_s060(social_library) -> None:
    assert social_library.version == "v1"
    assert social_library.event_count == 60
    assert len(social_library.events) == 60
    assert [event.event_id for event in social_library.events] == [f"S{i:03d}" for i in range(1, 61)]


def test_social_library_passes_validator(social_library) -> None:
    SocialEventLibraryValidator().validate(social_library)


def test_social_event_id_format(social_library) -> None:
    for event in social_library.events:
        assert event.event_id.startswith("S")
        assert len(event.event_id) == 4


def test_weight_mapping_matches_doc() -> None:
    assert WEIGHT_MAP["低概率"] == 1
    assert WEIGHT_MAP["中低概率"] == 3
    assert WEIGHT_MAP["中概率"] == 5
    assert WEIGHT_MAP["中高概率"] == 8
    assert WEIGHT_MAP["高概率"] == 12


def test_s001_creates_classmate_relationship(social_library, life_state) -> None:
    event = social_library.by_id()["S001"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={"default_attributes": {}})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    assert resolved[0][0] == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED
    social = SocialEventProcessor().process(
        resolved[0][0],
        resolved[0][1],
        SocialState.from_life_state_dict(life_state.social),
        life_state.age,
    )
    assert social.has_relationship_type("classmate")


def test_s002_not_eligible_without_classmate(social_library, life_state) -> None:
    life_state.education = {
        **life_state.education,
        "current_stage": "middle",
        "is_enrolled": True,
    }
    life_state.attributes["intelligence"] = 50
    event = social_library.by_id()["S002"]
    assert not RandomEventConditionMatcher().matches(event, life_state)


def test_s002_eligible_with_classmate(social_library, life_state) -> None:
    life_state.age = 12
    life_state.life_stage = "childhood"
    life_state = _with_relationship(
        life_state,
        relationship_type="classmate",
        closeness=35,
    )
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.attributes["intelligence"] = 50
    event = social_library.by_id()["S002"]
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_s005_upgrades_classmate_to_friend(social_library, life_state) -> None:
    life_state = _with_relationship(
        life_state,
        relationship_type="classmate",
        closeness=50,
        conflict=10,
    )
    event = social_library.by_id()["S005"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type.name.startswith("SOCIAL_"):
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert any(item.get("relationship_type") == "friend" for item in social.relationships)


def test_s006_eligible_with_low_charm(social_library, life_state) -> None:
    life_state.age = 12
    life_state.life_stage = "childhood"
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.attributes["charm"] = 40
    event = social_library.by_id()["S006"]
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_s013_creates_rival(social_library, life_state) -> None:
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.attributes["intelligence"] = 65
    event = social_library.by_id()["S013"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("rival")


def test_s016_teacher_relationship_change(social_library, life_state) -> None:
    life_state = _with_relationship(life_state, relationship_type="teacher", trust=40)
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.attributes["intelligence"] = 65
    event = social_library.by_id()["S016"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CHANGE_REQUESTED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    rel = next(item for item in social.relationships if item["relationship_type"] == "teacher")
    assert rel["trust"] >= 45


def test_s021_creates_roommate(social_library, life_state) -> None:
    life_state.age = 18
    life_state.life_stage = "adult"
    life_state.education = {
        **life_state.education,
        "current_stage": "college",
        "is_enrolled": True,
        "school_year": 0,
    }
    event = social_library.by_id()["S021"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("roommate") or social.has_relationship_type("classmate")


def test_s024_creates_friend(social_library, life_state) -> None:
    life_state.age = 19
    life_state.education = {**life_state.education, "current_stage": "college", "is_enrolled": True}
    event = social_library.by_id()["S024"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("friend")


def test_s026_creates_mentor(social_library, life_state) -> None:
    life_state.age = 20
    life_state.education = {**life_state.education, "current_stage": "college", "is_enrolled": True}
    life_state.attributes["intelligence"] = 75
    event = social_library.by_id()["S026"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("mentor")


def test_s031_creates_coworker(social_library, life_state) -> None:
    life_state.age = 22
    life_state.career = {**life_state.career, "employment_status": "employed", "years_worked": 0}
    event = social_library.by_id()["S031"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("coworker")


def test_s037_creates_leader(social_library, life_state) -> None:
    life_state.age = 24
    life_state.career = {**life_state.career, "employment_status": "employed", "years_worked": 1}
    event = social_library.by_id()["S037"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("leader")


def test_s041_creates_benefactor(social_library, life_state) -> None:
    life_state.age = 28
    life_state.career = {**life_state.career, "employment_status": "employed", "years_worked": 3}
    event = social_library.by_id()["S041"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("benefactor") or social.has_relationship_type("mentor")


def test_s056_creates_neighbor(social_library, life_state) -> None:
    life_state.age = 20
    event = social_library.by_id()["S056"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_A"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    social = SocialState.from_life_state_dict(life_state.social)
    for event_type, payload in resolved:
        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            social = SocialEventProcessor().process(event_type, payload, social, life_state.age)
    assert social.has_relationship_type("neighbor")


def test_s060_acquaintance_fraud_reduces_assets(social_library, life_state) -> None:
    life_state = _with_relationship(
        life_state,
        relationship_type="acquaintance",
        trust=40,
    )
    life_state.age = 25
    life_state.assets = {**life_state.assets, "cash": 10000.0, "net_worth": 10000.0}
    event = social_library.by_id()["S060"]
    choice = next(item for item in event.choices if item.choice_id.endswith("_B"))
    context = make_context(life_state, rules={})
    context.rules = __import__("app.rules.rule_loader", fromlist=["RuleLoader"]).RuleLoader().load("v1")
    resolved = RandomEventChoiceEffectResolver().resolve_choice(event, choice, context)
    assert any(item[0] == SimulationEventType.ASSET_CHANGE_REQUESTED for item in resolved)


def test_prison_blocks_school_social_events(social_library, life_state) -> None:
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    life_state.legal = LegalState(is_in_prison=True).to_life_state_dict()
    draw = RandomEventV1DrawService()
    blocked = blocked_social_sub_categories(LegalState.from_life_state_dict(life_state.legal))
    eligible = draw.eligible_social_events(
        social_library.events,
        life_state,
        {},
        blocked_sub_categories=blocked,
    )
    assert not any(event.event_id == "S001" for event in eligible)


def test_fugitive_blocks_workplace_social_events(social_library, life_state) -> None:
    life_state.career = {**life_state.career, "employment_status": "employed", "years_worked": 1}
    life_state.legal = LegalState(is_fugitive=True).to_life_state_dict()
    draw = RandomEventV1DrawService()
    blocked = blocked_social_sub_categories(LegalState.from_life_state_dict(life_state.legal))
    eligible = draw.eligible_social_events(
        social_library.events,
        life_state,
        {},
        blocked_sub_categories=blocked,
    )
    assert not any(event.event_id == "S031" for event in eligible)


def test_dead_state_blocks_social_draw(social_library, life_state, rules) -> None:
    life_state.is_dead = True
    service = RandomEventsService()
    context = make_context(life_state, rules)
    context.rules = rules
    context.rules = copy.deepcopy(rules)
    context.rules["random_events"]["use_v1_library"] = True
    context.rules["random_events"]["use_social_library"] = True
    service.run(context)
    assert context.result_collector.pending_random_event is None


def test_cooldown_prevents_repeat(social_library, life_state) -> None:
    event = social_library.by_id()["S001"]
    draw = RandomEventV1DrawService()
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    history = {"S001": {"last_age": life_state.age}}
    eligible = draw.eligible_social_events(social_library.events, life_state, history)
    assert event not in eligible


def test_once_event_not_repeatable(social_library, life_state) -> None:
    event = social_library.by_id()["S021"]
    assert event.repeat_policy == "once"
    draw = RandomEventV1DrawService()
    life_state.age = 18
    life_state.education = {**life_state.education, "current_stage": "college", "is_enrolled": True, "school_year": 0}
    history = {"S021": {"last_age": 18}}
    eligible = draw.eligible_social_events(social_library.events, life_state, history)
    assert event not in eligible


def test_s041_can_unlock_a035(rules, life_state) -> None:
    from app.modules.achievement.condition_evaluator import AchievementConditionEvaluator
    from app.modules.achievement.models import AchievementState

    life_state = _with_relationship(life_state, relationship_type="mentor", trust=80)
    assert AchievementConditionEvaluator().matches(
        {"has_mentor": True},
        life_state,
        AchievementState.from_life_state_dict(life_state.achievements),
    )


def test_sqlite_persists_social_event_relationship(rules, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "social_events.sqlite3"))
    from app.application.save_service import SaveService
    from app.infrastructure.config import get_settings
    from app.infrastructure.save.factory import create_save_repository
    from app.infrastructure.save.sqlite_db import clear_sqlite_caches

    get_settings.cache_clear()
    clear_sqlite_caches()
    repo = create_save_repository()
    service = SaveService(repository=repo)
    state = service.create_life("v1", rules)
    social = SocialState.from_life_state_dict(state.social)
    social = SocialEventProcessor().process(
        SimulationEventType.SOCIAL_RELATIONSHIP_CREATED,
        {
            "name": "S001同桌",
            "relationship_type": "classmate",
            "role": "classmate",
            "source": "social_event",
            "closeness": 8,
            "trust": 5,
            "familiarity": 20,
        },
        social,
        state.age,
    )
    state.social = social.to_life_state_dict()
    service.save_life_state(state, rules=rules)
    loaded = service.get_life_state(state.life_id, rules=rules)
    assert loaded.social.get("relationships")
