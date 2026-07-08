import copy

import pytest

from app.engine.event_bus import EventBus
from app.engine.result_collector import ResultCollector
from app.engine.simulation_context import LifeState, SimulationContext, SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.infrastructure.errors import PendingRandomEventError, RuleValidationError
from app.infrastructure.rng import ServerRandom
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.library_models import V1EventDefinition
from app.modules.random_events.service import RandomEventsService
from app.modules.random_events.v1_draw import RandomEventV1DrawService
from app.rules.random_event_library_loader import RandomEventLibraryLoader
from app.rules.random_event_library_validator import RandomEventLibraryValidator
from tests.conftest import make_context


@pytest.fixture
def v1_library():
    return RandomEventLibraryLoader().load()


def test_can_load_random_event_library_v1(v1_library) -> None:
    assert v1_library.version == "v1"
    assert v1_library.event_count == 80
    assert len(v1_library.events) == 80


def test_v1_event_ids_are_continuous(v1_library) -> None:
    ids = [event.event_id for event in v1_library.events]
    assert ids == [f"E{index:03d}" for index in range(1, 81)]


def test_each_event_has_text_and_choices(v1_library) -> None:
    for event in v1_library.events:
        assert event.event_text.strip()
        assert event.choices
        for choice in event.choices:
            assert choice.effects_text.strip()


def test_weight_tier_mapping(v1_library) -> None:
    mapping = {
        "低概率": 1,
        "中低概率": 3,
        "中概率": 5,
        "中高概率": 8,
        "高概率": 12,
        "极低概率": 1,
        "系统事件": 0,
    }
    for event in v1_library.events:
        assert event.weight == mapping[event.weight_tier]


def test_extremely_low_probability_not_in_normal_pool(v1_library) -> None:
    for event in v1_library.events:
        if event.weight_tier == "极低概率":
            assert event.pool_type == "direct_death"


def test_system_events_not_in_normal_pool(v1_library) -> None:
    for event in v1_library.events:
        if event.weight_tier == "系统事件":
            assert event.pool_type == "system"
            assert event.conditions.get("system_only") is True


def test_direct_death_events_in_independent_pool(v1_library) -> None:
    direct_death_ids = {event.event_id for event in v1_library.events if event.pool_type == "direct_death"}
    assert direct_death_ids == {"E067", "E068", "E070"}


def test_direct_death_total_probability_limit_from_rules(rules) -> None:
    assert rules["random_events"]["direct_death_probability_limit"] <= 0.03


def test_normal_events_do_not_set_is_dead_effect(v1_library) -> None:
    for event in v1_library.events:
        if event.pool_type != "direct_death":
            for choice in event.choices:
                for effect in choice.effects:
                    assert effect.get("type") != "direct_death_candidate"


def test_e001_has_three_choices(v1_library) -> None:
    event = v1_library.by_id()["E001"]
    assert len(event.choices) == 3


def test_e012_has_four_choices(v1_library) -> None:
    event = v1_library.by_id()["E012"]
    assert len(event.choices) == 4


def test_e067_is_direct_death_event(v1_library) -> None:
    event = v1_library.by_id()["E067"]
    assert event.pool_type == "direct_death"
    assert event.choices[0].is_system_choice is True


def test_e080_is_system_only_event(v1_library) -> None:
    event = v1_library.by_id()["E080"]
    assert event.pool_type == "system"
    assert event.conditions.get("system_only") is True


def test_planned_events_not_drawable(v1_library) -> None:
    planned = [event for event in v1_library.events if event.implementation_status == "planned"]
    draw_service = RandomEventV1DrawService()
    state = LifeState(
        life_id="life-test",
        person_id="person-test",
        age=30,
        life_stage="adult",
    )
    eligible = draw_service.eligible_normal_events(planned, state, {})
    assert eligible == []


def test_unknown_condition_field_fails_validation(v1_library) -> None:
    invalid = copy.deepcopy(v1_library)
    invalid.events[0].conditions["unknown_field"] = True
    with pytest.raises(RuleValidationError, match="Unknown condition field"):
        RandomEventLibraryValidator().validate(invalid)


def test_unsupported_effect_preserved_in_library(v1_library) -> None:
    event = v1_library.by_id()["E001"]
    unsupported = [
        effect
        for choice in event.choices
        for effect in choice.effects
        if effect.get("type") == "unsupported_effect"
    ]
    assert unsupported


def test_v1_pending_random_event_returned_without_applying_effects(life_state, rules, v1_library) -> None:
    rules = copy.deepcopy(rules)
    rules["random_events"]["use_v1_library"] = True
    life_state.age = 10
    life_state.life_stage = "childhood"
    life_state.attributes["intelligence"] = 70

    draw_service = RandomEventV1DrawService()
    eligible = draw_service.eligible_normal_events(v1_library.events, life_state, {})
    assert eligible, "Expected drawable partial/active events at age 10"

    service = RandomEventsService()
    context = make_context(life_state, rules, seed=42)

    for seed in range(200):
        context.event_bus = EventBus()
        context.result_collector = ResultCollector()
        context.rng = ServerRandom(seed)
        service.run(context)
        if context.result_collector.pending_random_event is not None:
            break
    else:
        pytest.fail(f"No pending event drawn from {len(eligible)} eligible events")

    assert context.result_collector.pending_random_event["event_text"]
    assert context.result_collector.pending_random_event["choices"]
    assert all(
        "effects" not in choice
        for choice in context.result_collector.pending_random_event["choices"]
    )
    assert not context.result_collector.random_event_health_changes


def test_submit_choice_applies_effects(life_state, rules) -> None:
    rules = copy.deepcopy(rules)
    rules["random_events"]["use_v1_library"] = True
    life_state.age = 10
    life_state.life_stage = "childhood"
    life_state.attributes["intelligence"] = 70
    life_state.pending_random_event = {
        "event_id": "E014",
        "name": "考试表现优秀",
        "category": "primary_school",
        "event_text": "测试事件",
        "choices": [
            {
                "choice_id": "E014_A",
                "label": "选项一",
                "choice_text": "继续保持",
                "requires_confirmation": False,
                "is_system_choice": False,
            }
        ],
        "year_age": 10,
        "pool_type": "normal",
    }

    engine = SimulationEngine(rng_seed=1)
    next_state, choice_result = engine.submit_random_event_choice(
        life_state,
        "E014_A",
        rules,
    )
    assert choice_result["choice_id"] == "E014_A"
    assert next_state.pending_random_event is None
    assert next_state.attributes["intelligence"] >= life_state.attributes["intelligence"]


def test_direct_death_event_only_publishes_candidate(life_state, rules) -> None:
    rules = copy.deepcopy(rules)
    rules["random_events"]["use_v1_library"] = True
    life_state.age = 30
    life_state.life_stage = "adult"

    service = RandomEventsService()
    service.draw_service.should_enter_direct_death_pool = lambda _limit, _rng: True
    context = make_context(life_state, rules, seed=7)
    service.run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.result_collector.direct_death_candidate_created
    assert context.state.is_dead is False


def test_random_events_module_does_not_modify_life_state_directly_v1(life_state, rules) -> None:
    rules = copy.deepcopy(rules)
    rules["random_events"]["use_v1_library"] = True
    before = life_state.model_copy(deep=True)
    service = RandomEventsService()
    context = make_context(life_state, rules, seed=99)
    service.run(context)
    assert life_state.model_dump() == before.model_dump()


def test_advance_blocked_when_pending_random_event_exists(life_state, rules) -> None:
    life_state.pending_random_event = {
        "event_id": "E014",
        "name": "考试表现优秀",
        "category": "primary_school",
        "event_text": "pending",
        "choices": [],
        "year_age": 10,
        "pool_type": "normal",
    }
    engine = SimulationEngine(rng_seed=1)
    with pytest.raises(PendingRandomEventError):
        engine.advance_one_year(life_state, {"annual_focus": "balanced_year"}, rules)


def test_condition_matcher_supports_basic_fields(life_state) -> None:
    matcher = RandomEventConditionMatcher()
    event = V1EventDefinition(
        event_id="E059",
        name="普通感冒",
        category="health",
        age_range={"min": 0, "max": 90},
        conditions={"health_below": 90},
        event_text="感冒",
        choices=[],
        implementation_status="partial",
    )
    life_state.age = 20
    life_state.health["health_score"] = 80
    assert matcher.matches(event, life_state) is True

    life_state.health["health_score"] = 95
    assert matcher.matches(event, life_state) is False
