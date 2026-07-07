from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.infrastructure.errors import RandomEventEffectError, RuleValidationError
from app.modules.death.service import DeathService
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.models import RandomEventDefinition
from app.modules.random_events.service import RandomEventsService
from app.rules.rule_validator import RuleValidator

from conftest import make_context


def _event(**overrides) -> RandomEventDefinition:
    payload = {
        "id": "test_event",
        "name": "Test Event",
        "category": "growth",
        "stage": "any",
        "probability": 1.0,
        "direct_death": False,
        "weight": 1.0,
        "conditions": {},
        "effects": [],
        "narrative_text": "Test narrative",
    }
    payload.update(overrides)
    return RandomEventDefinition.model_validate(payload)


def test_effect_resolver_parses_attribute_change(life_state, rules) -> None:
    event_def = _event(
        effects=[
            {
                "type": "attribute_change",
                "target": "intelligence",
                "value": 2,
                "reason": "Study boost",
                "source_event_id": "test_event",
                "source_event_name": "Test Event",
            }
        ]
    )
    context = make_context(life_state, rules)
    resolved = RandomEventEffectResolver().resolve(event_def, context)

    assert resolved[0][0] == SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED
    assert resolved[0][1]["key"] == "intelligence"
    assert resolved[0][1]["delta"] == 2


def test_effect_resolver_parses_health_change(life_state, rules) -> None:
    event_def = _event(
        effects=[
            {
                "type": "health_change",
                "target": "health_score",
                "value": -2,
                "reason": "Minor illness",
                "source_event_id": "test_event",
                "source_event_name": "Test Event",
            }
        ]
    )
    context = make_context(life_state, rules)
    resolved = RandomEventEffectResolver().resolve(event_def, context)

    assert resolved[0][0] == SimulationEventType.HEALTH_CHANGE_REQUESTED
    assert resolved[0][1]["delta"] == -2


def test_effect_resolver_parses_asset_change(life_state, rules) -> None:
    event_def = _event(
        category="wealth",
        effects=[
            {
                "type": "asset_change",
                "target": "cash",
                "value": 100,
                "reason": "Small bonus",
                "source_event_id": "test_event",
                "source_event_name": "Test Event",
            }
        ],
    )
    context = make_context(life_state, rules)
    resolved = RandomEventEffectResolver().resolve(event_def, context)

    assert resolved[0][0] == SimulationEventType.ASSET_CHANGE_REQUESTED
    assert resolved[0][1]["key"] == "cash"
    assert resolved[0][1]["delta"] == 100.0


def test_effect_resolver_parses_direct_death_candidate(life_state, rules) -> None:
    event_def = _event(
        category="direct_death",
        direct_death=True,
        effects=[
            {
                "type": "direct_death_candidate",
                "target": "death",
                "value": 1,
                "reason": "Fatal accident",
                "source_event_id": "test_event",
                "source_event_name": "Test Event",
            }
        ],
    )
    context = make_context(life_state, rules)
    resolved = RandomEventEffectResolver().resolve(event_def, context)

    assert resolved[0][0] == SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED
    assert resolved[0][1]["death_type"] == "direct_death"


def test_unknown_effect_type_raises_clear_error(life_state, rules) -> None:
    event_def = _event(
        effects=[
            {
                "type": "unknown_effect",
                "target": "x",
                "value": 1,
                "reason": "bad",
                "source_event_id": "test_event",
                "source_event_name": "Test Event",
            }
        ]
    )
    context = make_context(life_state, rules)

    with pytest.raises(RandomEventEffectError, match="Unknown random event effect type"):
        RandomEventEffectResolver().resolve(event_def, context)


def test_random_event_service_does_not_modify_life_state_directly(life_state, rules) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "boost_event",
            "name": "Boost Event",
            "category": "growth",
            "stage": "any",
            "probability": 1.0,
            "direct_death": False,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "attribute_change",
                    "target": "intelligence",
                    "value": 5,
                    "reason": "Boost",
                    "source_event_id": "boost_event",
                    "source_event_name": "Boost Event",
                }
            ],
        }
    ]
    before_attributes = dict(life_state.attributes)
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    RandomEventsService().run(context)

    assert life_state.attributes == before_attributes
    assert life_state.is_dead is False


def test_random_event_health_change_only_publishes_health_change_requested(life_state, rules) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "health_event",
            "name": "Health Event",
            "category": "health",
            "stage": "any",
            "probability": 1.0,
            "direct_death": False,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "health_change",
                    "target": "health_score",
                    "value": 3,
                    "reason": "Recovery",
                    "source_event_id": "health_event",
                    "source_event_name": "Health Event",
                }
            ],
        }
    ]
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    RandomEventsService().run(context)

    health_events = context.event_bus.by_type(SimulationEventType.HEALTH_CHANGE_REQUESTED)
    assert health_events
    assert all(event.source_module == "random_events" for event in health_events)


def test_random_event_attribute_change_only_publishes_attribute_change_requested(
    life_state, rules
) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "attr_event",
            "name": "Attr Event",
            "category": "growth",
            "stage": "any",
            "probability": 1.0,
            "direct_death": False,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "attribute_change",
                    "target": "charm",
                    "value": 2,
                    "reason": "Charm up",
                    "source_event_id": "attr_event",
                    "source_event_name": "Attr Event",
                }
            ],
        }
    ]
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    RandomEventsService().run(context)

    assert context.event_bus.by_type(SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED)


def test_random_event_asset_change_only_publishes_asset_change_requested(life_state, rules) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "cash_event",
            "name": "Cash Event",
            "category": "wealth",
            "stage": "any",
            "probability": 1.0,
            "direct_death": False,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "asset_change",
                    "target": "cash",
                    "value": 250,
                    "reason": "Found money",
                    "source_event_id": "cash_event",
                    "source_event_name": "Cash Event",
                }
            ],
        }
    ]
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    RandomEventsService().run(context)

    assert context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)


def test_direct_death_event_only_publishes_candidate(life_state, rules) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "fatal_placeholder",
            "name": "Fatal placeholder",
            "category": "direct_death",
            "stage": "any",
            "probability": 1.0,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "Fatal placeholder",
                    "source_event_id": "fatal_placeholder",
                    "source_event_name": "Fatal placeholder",
                }
            ],
        }
    ]
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    RandomEventsService().run(context)

    assert life_state.is_dead is False
    assert context.result_collector.death_confirmed is False
    assert context.event_bus.by_type(SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED)


def test_direct_death_probability_over_limit_still_fails(rules) -> None:
    invalid_rules = deepcopy(rules)
    invalid_rules["random_events"]["event_pool"] = [
        {
            "id": "death_a",
            "name": "Death A",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.02,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "A",
                    "source_event_id": "death_a",
                    "source_event_name": "Death A",
                }
            ],
        },
        {
            "id": "death_b",
            "name": "Death B",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.02,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "B",
                    "source_event_id": "death_b",
                    "source_event_name": "Death B",
                }
            ],
        },
    ]

    with pytest.raises(RuleValidationError, match="exceeds limit"):
        RuleValidator().validate(invalid_rules)


def test_year_result_returns_random_event_changes(life_state, rules) -> None:
    rules = deepcopy(rules)
    rules["random_events"]["event_pool"] = [
        {
            "id": "combo_event",
            "name": "Combo Event",
            "category": "growth",
            "stage": "any",
            "probability": 1.0,
            "direct_death": False,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "attribute_change",
                    "target": "intelligence",
                    "value": 2,
                    "reason": "Smarter",
                    "source_event_id": "combo_event",
                    "source_event_name": "Combo Event",
                },
                {
                    "type": "health_change",
                    "target": "health_score",
                    "value": 1,
                    "reason": "Healthier",
                    "source_event_id": "combo_event",
                    "source_event_name": "Combo Event",
                },
                {
                    "type": "asset_change",
                    "target": "cash",
                    "value": 50,
                    "reason": "Cash",
                    "source_event_id": "combo_event",
                    "source_event_name": "Combo Event",
                },
            ],
        }
    ]
    engine = SimulationEngine(rng_seed=1)
    engine.annual_modules = [RandomEventsService()]
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    for module in engine.annual_modules:
        module.run(context)
        context.result_collector.collect_from_events(context.event_bus.all())

    next_state = context.result_collector.apply_to_state(life_state, rules)
    result = context.result_collector.to_year_result(
        life_state,
        next_state,
        context.event_bus.all(),
        [],
    )

    assert result.triggered_random_events
    assert result.random_event_attribute_changes == {"intelligence": 2}
    assert result.random_event_health_changes == {"health_score": 1}
    assert result.random_event_asset_changes == {"cash": 50.0}


def test_death_service_direct_death_priority_unbroken(life_state, rules) -> None:
    context = make_context(life_state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)
    context.event_bus.publish(
        SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
        "random_events",
        {"reason": "accident", "death_type": "direct_death", "probability": 1.0},
    )
    context.event_bus.publish(
        SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED,
        "health",
        {"reason": "natural aging", "death_type": "natural_death", "probability": 1.0},
    )

    DeathService().run(context)

    assert context.result_collector.death_reason == "accident"
    assert context.result_collector.death_type == "direct_death"


def test_validator_rejects_unknown_effect_type_in_rules(rules) -> None:
    invalid_rules = deepcopy(rules)
    invalid_rules["random_events"]["event_pool"][0]["effects"] = [
        {
            "type": "bad_effect",
            "target": "x",
            "value": 1,
            "reason": "bad",
            "source_event_id": "x",
            "source_event_name": "x",
        }
    ]

    with pytest.raises(RuleValidationError, match="unsupported effect type"):
        RuleValidator().validate(invalid_rules)
