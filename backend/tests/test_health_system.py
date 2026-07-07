from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.modules.death.service import DeathService
from app.modules.health.models import HealthState
from app.modules.health.rules import (
    build_default_health_state,
    calculate_natural_death_probability,
    get_annual_decay,
    has_natural_death_foreshadowing,
    resolve_health_level,
)
from app.modules.health.service import HealthService

from conftest import make_context


def _elder_state(life_state, rules, age: int, **health_overrides):
    health = build_default_health_state(rules).to_life_state_dict()
    health.update(health_overrides)
    if "health_score" in health_overrides:
        level_rule = resolve_health_level(int(health["health_score"]), rules)
        health["health_level"] = level_rule["name"]
        health["natural_life_floor"] = int(level_rule["natural_life_floor"])
        health["natural_death_eligible_age"] = int(level_rule["natural_death_eligible_age"])
    return life_state.model_copy(
        update={
            "age": age,
            "life_stage": "elder",
            "health": health,
        }
    )


def _run_health_and_collect(life_state, rules, seed: int = 1):
    context = make_context(life_state, rules, seed=seed)
    HealthService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())
    return context


def test_annual_health_decay_follows_rules(life_state, rules) -> None:
    elder = _elder_state(life_state, rules, age=70)
    expected_decay = get_annual_decay("elder", rules)
    score_before = elder.health["health_score"]

    context = _run_health_and_collect(elder, rules)

    assert context.result_collector.changed_health["health_score"] == -expected_decay
    assert context.result_collector.health_score_after == score_before - expected_decay


def test_health_level_comes_from_rule_thresholds(rules) -> None:
    assert resolve_health_level(95, rules)["name"] == "excellent"
    assert resolve_health_level(80, rules)["name"] == "good"
    assert resolve_health_level(60, rules)["name"] == "normal"
    assert resolve_health_level(30, rules)["name"] == "poor"
    assert resolve_health_level(10, rules)["name"] == "critical"


def test_excellent_health_can_enter_high_longevity_zone(life_state, rules) -> None:
    elder = _elder_state(life_state, rules, age=95, health_score=95, health_level="excellent")
    probability = calculate_natural_death_probability(95, "excellent", rules)

    assert elder.health["natural_death_eligible_age"] == 90
    assert probability > 0


def test_no_natural_death_candidate_before_life_floor(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=75,
        health_score=80,
        health_level="good",
        last_disease_warning_age=73,
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)

    assert not context.event_bus.by_type(SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED)


def test_natural_death_candidate_when_elderly_and_foreshadowed(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=93,
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)

    assert context.event_bus.by_type(SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED)


def test_probability_hit_without_foreshadowing_creates_warning_not_candidate(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)

    assert not context.event_bus.by_type(SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED)
    assert context.event_bus.by_type(SimulationEventType.HEALTH_WARNING_CREATED)


def test_disease_warning_within_three_years_allows_candidate(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=93,
    )

    health_state = HealthState.from_life_state_dict(elder.health, rules)
    assert has_natural_death_foreshadowing(95, health_state, rules) is True


def test_decline_warning_last_year_allows_candidate(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_decline_warning_age=94,
    )

    health_state = HealthState.from_life_state_dict(elder.health, rules)
    assert has_natural_death_foreshadowing(95, health_state, rules) is True


def test_health_module_does_not_set_is_dead(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=93,
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)

    assert elder.is_dead is False
    assert context.result_collector.death_confirmed is False


def test_health_module_only_publishes_candidate_not_confirms_death(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=93,
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)
    DeathService().run(context)

    assert context.event_bus.by_type(SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED)
    assert context.result_collector.death_confirmed is True


def test_death_module_is_only_module_confirming_natural_death(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=95,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=93,
    )
    context = make_context(elder, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)

    HealthService().run(context)
    assert context.result_collector.death_confirmed is False

    DeathService().run(context)
    next_state = context.result_collector.apply_to_state(elder)

    assert context.result_collector.death_confirmed is True
    assert context.result_collector.death_type == "natural_death"
    assert next_state.is_dead is True


def test_direct_death_candidate_has_priority_over_natural_death(life_state, rules) -> None:
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


def test_year_result_includes_health_changes_and_death_type(life_state, rules) -> None:
    elder = _elder_state(
        life_state,
        rules,
        age=94,
        health_score=95,
        health_level="excellent",
        last_disease_warning_age=92,
    )
    engine = SimulationEngine(rng_seed=1)

    next_state, result, _inheritance = engine.advance_one_year(
        elder,
        {"annual_focus": "balanced_year"},
        rules,
    )

    assert result.health_score_before == 95
    assert result.health_score_after is not None
    assert result.health_score_delta != 0 or result.health_score_after == 95
    assert result.health_level_before == "excellent"
    if result.is_dead:
        assert result.death_type in {"natural_death", "direct_death"}
    assert next_state.health.get("health_score") is not None


def test_natural_death_probability_at_ninety_reads_from_rules(rules) -> None:
    probability = calculate_natural_death_probability(90, "excellent", rules)
    natural_death = rules["health_lifetime"]["natural_death"]

    assert probability == pytest.approx(float(natural_death["base_probability_at_90"]))


def test_natural_death_probability_increases_after_ninety(rules) -> None:
    natural_death = rules["health_lifetime"]["natural_death"]
    at_90 = calculate_natural_death_probability(90, "excellent", rules)
    at_92 = calculate_natural_death_probability(92, "excellent", rules)

    expected = float(natural_death["base_probability_at_90"]) + 2 * float(
        natural_death["probability_increment_per_year_after_90"]
    )
    assert at_90 == pytest.approx(float(natural_death["base_probability_at_90"]))
    assert at_92 == pytest.approx(expected)
