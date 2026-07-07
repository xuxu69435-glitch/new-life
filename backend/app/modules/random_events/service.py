from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.models import RandomEventDefinition
from app.modules.random_events.rules import eligible_event_pool


class RandomEventsService:
    name = "random_events"
    can_confirm_death = False

    def __init__(self, effect_resolver: RandomEventEffectResolver | None = None) -> None:
        self.effect_resolver = effect_resolver or RandomEventEffectResolver()

    def run(self, context: SimulationContext) -> None:
        for event_def in eligible_event_pool(context.state.life_stage, context.rules):
            if not self._should_trigger(event_def, context):
                continue

            context.event_bus.publish(
                SimulationEventType.RANDOM_EVENT_TRIGGERED,
                self.name,
                event_def.to_event_payload(),
            )
            self._apply_effects(event_def, context)

    def _apply_effects(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> None:
        for event_type, payload in self.effect_resolver.resolve(event_def, context):
            context.event_bus.publish(event_type, self.name, payload)

    def _should_trigger(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> bool:
        probability = float(event_def.probability)
        if probability <= 0:
            return False
        return context.rng.random() <= probability
