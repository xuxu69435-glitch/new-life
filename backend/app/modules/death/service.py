from app.engine.simulation_context import SimulationContext, SimulationEventType


class DeathService:
    name = "death"
    can_confirm_death = True

    def run(self, context: SimulationContext) -> None:
        direct_candidates = context.event_bus.by_type(
            SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED
        )
        natural_candidates = context.event_bus.by_type(
            SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED
        )

        for candidate in direct_candidates:
            if self._try_confirm_death(context, candidate, "direct_death"):
                return

        for candidate in natural_candidates:
            if self._try_confirm_death(context, candidate, "natural_death"):
                return

    def _try_confirm_death(
        self,
        context: SimulationContext,
        candidate,
        default_death_type: str,
    ) -> bool:
        probability = float(candidate.payload.get("probability", 1.0))
        if context.rng.random() > probability:
            return False

        death_type = str(candidate.payload.get("death_type", default_death_type))
        reason = str(candidate.payload.get("reason", "unknown"))
        context.result_collector.confirm_death(reason, death_type=death_type)
        context.event_bus.publish(
            SimulationEventType.INHERITANCE_REQUESTED,
            self.name,
            {"reason": reason, "death_type": death_type},
        )
        return True
