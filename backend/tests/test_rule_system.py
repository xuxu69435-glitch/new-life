from copy import deepcopy
from unittest.mock import patch

import pytest

from app.application.game_command_service import GameCommandService
from app.engine.simulation_context import SimulationEventType
from app.infrastructure.errors import RuleLoadError, RuleValidationError
from app.modules.random_events.service import RandomEventsService
from app.rules.default_rules import DEFAULT_RULE_VERSION
from app.rules.rule_loader import RuleLoader
from app.rules.rule_validator import RuleValidator
from app.rules.rule_version_manager import RuleVersionManager

from conftest import make_context


def test_rule_loader_loads_v1_rules() -> None:
    rules = RuleLoader().load("v1")

    assert rules["version"] == "v1"
    assert rules["life_stages"]
    assert rules["default_attributes"]
    assert rules["health_lifetime"]
    assert rules["random_events"]["event_pool"]
    assert rules["inheritance"]["tax_rate"] == 0.2


def test_rule_loader_caches_loaded_rules() -> None:
    loader = RuleLoader()
    first = loader.load("v1")
    second = loader.load("v1")

    assert first == second
    assert first is not second


def test_rule_version_manager_returns_default_rule_version() -> None:
    manager = RuleVersionManager()

    assert manager.get_default_version() == DEFAULT_RULE_VERSION
    assert manager.get_version_for_new_life() == DEFAULT_RULE_VERSION
    assert manager.exists("v1") is True
    assert "v1" in manager.list_versions()


def test_create_life_binds_default_rule_version() -> None:
    service = GameCommandService()
    state, _choices = service.create_life()

    assert state.rule_version == DEFAULT_RULE_VERSION


def test_advance_one_year_uses_bound_rule_version() -> None:
    loader = RuleLoader()
    service = GameCommandService(rule_loader=loader)
    state, choices = service.create_life()

    with patch.object(loader, "load", wraps=loader.load) as load_mock:
        service.advance_one_year(
            state.life_id,
            {"annual_focus": choices[0]["id"]},
        )

    assert load_mock.call_args_list[-1].args[0] == state.rule_version


def test_missing_rule_version_returns_clear_error() -> None:
    with pytest.raises(RuleValidationError, match="Unsupported rule version: v99"):
        RuleLoader().load("v99")


def test_duplicate_random_event_id_fails_validation(rules) -> None:
    invalid_rules = deepcopy(rules)
    invalid_rules["random_events"]["event_pool"].append(
        {
            "id": "infant_growth_milestone",
            "name": "Duplicate event",
            "category": "normal",
            "stage": "any",
            "probability": 0.0,
            "direct_death": False,
            "weight": 1.0,
        }
    )

    with pytest.raises(RuleValidationError, match="Duplicate random event id"):
        RuleValidator().validate(invalid_rules)


def test_random_event_probability_below_zero_fails_validation(rules) -> None:
    invalid_rules = deepcopy(rules)
    invalid_rules["random_events"]["event_pool"][0]["probability"] = -0.01

    with pytest.raises(RuleValidationError, match="cannot be less than 0"):
        RuleValidator().validate(invalid_rules)


def test_random_event_probability_above_one_fails_validation(rules) -> None:
    invalid_rules = deepcopy(rules)
    invalid_rules["random_events"]["event_pool"][0]["probability"] = 1.01

    with pytest.raises(RuleValidationError, match="cannot be greater than 1"):
        RuleValidator().validate(invalid_rules)


def test_direct_death_probability_equal_to_three_percent_passes(rules) -> None:
    valid_rules = deepcopy(rules)
    valid_rules["random_events"]["event_pool"] = [
        {
            "id": "death_a",
            "name": "Death A",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.015,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "Death A",
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
            "probability": 0.015,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "Death B",
                    "source_event_id": "death_b",
                    "source_event_name": "Death B",
                }
            ],
        },
    ]

    RuleValidator().validate(valid_rules)


def test_direct_death_probability_over_three_percent_fails(rules) -> None:
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
                    "reason": "Death A",
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
                    "reason": "Death B",
                    "source_event_id": "death_b",
                    "source_event_name": "Death B",
                }
            ],
        },
    ]

    with pytest.raises(RuleValidationError, match="exceeds limit"):
        RuleValidator().validate(invalid_rules)


def test_random_event_direct_death_publishes_candidate_only(life_state, rules) -> None:
    rules["random_events"]["event_pool"] = [
        {
            "id": "fatal_placeholder",
            "name": "Fatal placeholder",
            "category": "direct_death",
            "stage": "any",
            "probability": 1.0,
            "direct_death": True,
            "weight": 1.0,
            "death_reason": "Fatal placeholder",
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
    context = make_context(life_state, rules)

    RandomEventsService().run(context)

    assert life_state.is_dead is False
    assert context.result_collector.death_confirmed is False
    assert context.event_bus.by_type(SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED)
    assert context.event_bus.by_type(SimulationEventType.RANDOM_EVENT_TRIGGERED)


def test_rule_loader_rejects_invalid_json(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    bad_file = data_dir / "rule_set_v1.json"
    bad_file.write_text("{invalid", encoding="utf-8")

    loader = RuleLoader(version_manager=RuleVersionManager(data_dir=data_dir))

    with pytest.raises(RuleLoadError, match="Rule file format error"):
        loader.load("v1")


def test_rule_loader_rejects_missing_file(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    loader = RuleLoader(version_manager=RuleVersionManager(data_dir=data_dir))

    with pytest.raises(RuleValidationError, match="Unsupported rule version"):
        loader.load("v1")
