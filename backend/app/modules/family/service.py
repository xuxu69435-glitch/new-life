from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.family.events import FamilyEventProcessor
from app.modules.family.models import FamilyState
from app.modules.family.rules import get_family_rules
from app.modules.legal.models import LegalState
from app.modules.legal.rules import blocks_family_progression


class FamilyService:
    name = "family"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        legal = LegalState.from_life_state_dict(context.state.legal)
        if blocks_family_progression(legal):
            return

        context.result_collector.bind_family_context(context.state, context.rules)
        working = context.result_collector._family_working
        if working is None:
            return

        family_rules = get_family_rules(context.rules)
        for child in working.children:
            child.age += 1

        pressure_decay = int(family_rules.get("annual_pressure_decay", 0))
        if pressure_decay and working.family_pressure > 0:
            working.family_pressure = max(0, working.family_pressure - pressure_decay)
            context.event_bus.publish(
                SimulationEventType.FAMILY_PRESSURE_CHANGE_REQUESTED,
                self.name,
                {"delta": -pressure_decay, "reason": "annual_family_relaxation"},
            )

        working.clamp_scores()
        context.event_bus.publish(
            SimulationEventType.FAMILY_STATE_UPDATE_REQUESTED,
            self.name,
            {"family": working.to_life_state_dict(), "reason": "annual_family_tick"},
        )
