from app.engine.simulation_context import SimulationContext
from app.modules.narrative.templates import annual_summary


class NarrativeService:
    name = "narrative"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        context.result_collector.add_narrative(
            annual_summary(
                context.state.age + 1,
                context.result_collector.death_confirmed,
                context.result_collector.death_reason,
            )
        )
