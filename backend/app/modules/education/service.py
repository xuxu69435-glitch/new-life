from app.engine.simulation_context import SimulationContext, SimulationEventType


class EducationService:
    name = "education"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if context.player_choices.get("annual_focus") == "study_focus":
            context.event_bus.publish(
                SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
                self.name,
                {"key": "intelligence", "delta": 1},
            )
