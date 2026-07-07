from app.engine.simulation_context import SimulationContext, SimulationEventType


class DeathService:
    name = "death"
    can_confirm_death = True

    def run(self, context: SimulationContext) -> None:
        candidates = []
        candidates.extend(context.event_bus.by_type(SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED))
        candidates.extend(context.event_bus.by_type(SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED))

        for candidate in candidates:
            probability = float(candidate.payload.get("probability", 1.0))
            if context.rng.random() <= probability:
                reason = str(candidate.payload.get("reason", "unknown"))
                context.result_collector.confirm_death(reason)
                context.event_bus.publish(
                    SimulationEventType.INHERITANCE_REQUESTED,
                    self.name,
                    {"reason": reason},
                )
                break
