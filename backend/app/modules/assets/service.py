from app.engine.simulation_context import SimulationContext, SimulationEventType


class AssetsService:
    name = "assets"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        income_events = context.event_bus.by_type(SimulationEventType.INCOME_CHANGE_REQUESTED)
        for event in income_events:
            context.event_bus.publish(
                SimulationEventType.ASSET_CHANGE_REQUESTED,
                self.name,
                {
                    "key": event.payload.get("asset_key", "cash"),
                    "delta": float(event.payload.get("amount", 0.0)),
                    "source_event": event.event_type.value,
                },
            )
