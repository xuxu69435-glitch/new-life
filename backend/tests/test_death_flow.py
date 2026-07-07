from app.engine.simulation_context import SimulationEventType
from app.modules.death.service import DeathService

from conftest import make_context


def test_death_module_is_only_module_that_confirms_death(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(
        SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
        "random_events",
        {"reason": "first candidate", "death_type": "direct_death", "probability": 1.0},
    )
    context.event_bus.publish(
        SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED,
        "health",
        {"reason": "second candidate", "death_type": "natural_death", "probability": 1.0},
    )

    DeathService().run(context)
    next_state = context.result_collector.apply_to_state(life_state)

    assert DeathService.can_confirm_death is True
    assert context.result_collector.death_reason == "first candidate"
    assert context.result_collector.death_type == "direct_death"
    assert next_state.is_dead is True
    assert next_state.death_reason == "first candidate"
    assert len(context.event_bus.by_type(SimulationEventType.INHERITANCE_REQUESTED)) == 1
