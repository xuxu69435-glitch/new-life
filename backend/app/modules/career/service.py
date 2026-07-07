from app.engine.simulation_context import SimulationContext, SimulationEventType


class CareerService:
    name = "career"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if context.state.age < 18:
            return
        amount = float(context.rules.get("career", {}).get("placeholder_income", 0.0))
        context.event_bus.publish(
            SimulationEventType.INCOME_CHANGE_REQUESTED,
            self.name,
            {"asset_key": "cash", "amount": amount},
        )
