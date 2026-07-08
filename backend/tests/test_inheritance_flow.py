from app.engine.simulation_context import SimulationEventType
from app.modules.inheritance.service import InheritanceService

from conftest import make_context


def test_inheritance_module_only_runs_after_death_confirmed(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})

    InheritanceService().run(context)

    assert context.result_collector.inheritance_result is None

    context.result_collector.confirm_death("test death", death_type="natural_death")
    InheritanceService().run(context)

    assert context.result_collector.inheritance_result is not None
    assert context.result_collector.inheritance_result["status"] in {
        "settled",
        "zero_estate",
        "unclaimed",
    }
