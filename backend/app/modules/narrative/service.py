from app.engine.simulation_context import SimulationContext
from app.modules.narrative.templates import annual_summary


class NarrativeService:
    name = "narrative"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        health_score_delta = 0
        if (
            context.result_collector.health_score_before is not None
            and context.result_collector.health_score_after is not None
        ):
            health_score_delta = (
                context.result_collector.health_score_after
                - context.result_collector.health_score_before
            )

        context.result_collector.add_narrative(
            annual_summary(
                context.state.age + 1,
                context.result_collector.death_confirmed,
                context.result_collector.death_reason,
                context.result_collector.death_type,
                health_score_delta=health_score_delta,
                health_warnings=context.result_collector.new_health_warnings,
            )
        )
