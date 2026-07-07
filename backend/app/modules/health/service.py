from app.engine.simulation_context import SimulationContext, SimulationEventType


class HealthService:
    name = "health"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if context.player_choices.get("annual_focus") == "rest_focus":
            context.event_bus.publish(
                SimulationEventType.HEALTH_CHANGE_REQUESTED,
                self.name,
                {"key": "physical", "delta": 1},
            )

        health_rules = context.rules.get("health_lifetime", {})
        check_age = int(health_rules.get("natural_death_check_age", 90))
        if context.state.age >= check_age:
            context.event_bus.publish(
                SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED,
                self.name,
                {
                    "reason": "natural aging",
                    "probability": float(health_rules.get("natural_death_probability", 0.0)),
                },
            )
