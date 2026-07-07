from app.engine.simulation_context import SimulationEvent, SimulationEventType


class EventBus:
    def __init__(self) -> None:
        self._events: list[SimulationEvent] = []

    def publish(
        self,
        event_type: SimulationEventType,
        source_module: str,
        payload: dict | None = None,
    ) -> SimulationEvent:
        event = SimulationEvent(
            event_type=event_type,
            source_module=source_module,
            payload=payload or {},
        )
        self._events.append(event)
        return event

    def all(self) -> list[SimulationEvent]:
        return list(self._events)

    def by_type(self, event_type: SimulationEventType) -> list[SimulationEvent]:
        return [event for event in self._events if event.event_type == event_type]
