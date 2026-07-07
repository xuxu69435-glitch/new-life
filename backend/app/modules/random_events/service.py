from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.random_events.models import RandomEventDefinition
from app.modules.random_events.rules import eligible_event_pool


class RandomEventsService:
    name = "random_events"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        for event_def in eligible_event_pool(context.state.life_stage, context.rules):
            if not self._should_trigger(event_def, context):
                continue

            context.event_bus.publish(
                SimulationEventType.RANDOM_EVENT_TRIGGERED,
                self.name,
                event_def.to_event_payload(),
            )
            if event_def.direct_death:
                context.event_bus.publish(
                    SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
                    self.name,
                    {
                        "reason": event_def.death_reason or event_def.display_name(),
                        "death_type": "direct_death",
                        "probability": 1.0,
                        "event_id": event_def.id,
                        "category": event_def.category,
                    },
                )

    def _should_trigger(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> bool:
        probability = float(event_def.probability)
        if probability <= 0:
            return False
        return context.rng.random() <= probability
