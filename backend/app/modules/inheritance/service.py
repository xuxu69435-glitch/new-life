from app.engine.simulation_context import SimulationContext, SimulationEventType


class InheritanceService:
    name = "inheritance"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if not context.result_collector.death_confirmed:
            return
        if not context.event_bus.by_type(SimulationEventType.INHERITANCE_REQUESTED):
            return

        inheritance_rules = context.rules.get("inheritance", {})
        tax_rate = float(inheritance_rules.get("tax_rate", 0.2))
        cash = float(context.state.assets.get("cash", 0.0))
        debt = float(context.state.assets.get("debt", 0.0))
        pending_cash_delta = context.result_collector.changed_assets.get("cash", 0.0)
        gross_assets = max(cash + pending_cash_delta - debt, 0.0)
        tax = gross_assets * tax_rate
        heirs = list(inheritance_rules.get("default_heirs", ["partner", "descendants"]))
        context.result_collector.set_inheritance_result(
            {
                "gross_assets": gross_assets,
                "tax": tax,
                "net_assets": gross_assets - tax,
                "heirs": heirs,
                "status": "placeholder",
            }
        )
