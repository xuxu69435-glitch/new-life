from app.engine.simulation_context import SimulationContext


class FamilyService:
    name = "family"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        return None
