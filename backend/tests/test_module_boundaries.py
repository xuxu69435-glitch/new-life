from app.engine.simulation_context import SimulationEventType
from app.modules.assets.service import AssetsService
from app.modules.career.service import CareerService
from app.modules.health.service import HealthService
from app.modules.random_events.service import RandomEventsService

from conftest import make_context


def test_health_module_does_not_set_death(life_state, rules) -> None:
    old_state = life_state.model_copy(update={"age": 95, "life_stage": "elder"})
    old_state.health["last_disease_warning_age"] = 93
    context = make_context(old_state, rules)

    HealthService().run(context)

    assert old_state.is_dead is False
    assert context.result_collector.death_confirmed is False


def test_random_event_module_does_not_set_death(life_state, rules) -> None:
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
        }
    ]
    context = make_context(life_state, rules)

    RandomEventsService().run(context)

    assert life_state.is_dead is False
    assert context.result_collector.death_confirmed is False
    assert context.event_bus.by_type(SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED)


def test_career_requests_income_and_assets_module_applies_asset_change(life_state, rules) -> None:
    adult_state = life_state.model_copy(update={"age": 30, "life_stage": "adult"})
    context = make_context(adult_state, rules)

    CareerService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.event_bus.by_type(SimulationEventType.INCOME_CHANGE_REQUESTED)
    assert context.result_collector.changed_assets == {}

    AssetsService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.result_collector.changed_assets == {"cash": rules["career"]["placeholder_income"]}
