from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.life_stage.rules import resolve_life_stage


class LifeStageService:
    name = "life_stage"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        next_stage = resolve_life_stage(context.state.age + 1, context.rules)
        if next_stage != context.state.life_stage:
            context.event_bus.publish(
                SimulationEventType.LIFE_STAGE_CHANGED,
                self.name,
                {"life_stage": next_stage},
            )
