from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.assets.models import AssetState
from app.modules.family.models import FamilyState
from app.modules.inheritance.rules import get_inheritance_rules, settle_estate


class InheritanceService:
    name = "inheritance"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if not context.result_collector.death_confirmed:
            return
        if not context.event_bus.by_type(SimulationEventType.INHERITANCE_REQUESTED):
            return

        inheritance_rules = get_inheritance_rules(context.rules)
        if not inheritance_rules.get("default_rules_enabled", True):
            return

        assets = AssetState.from_life_state_dict(context.state.assets, context.rules)
        assets.apply_deltas(context.result_collector.changed_assets)
        family = FamilyState.from_life_state_dict(context.state.family)

        result = settle_estate(
            life_id=context.state.life_id,
            deceased_person_id=context.state.person_id,
            assets=assets,
            family=family,
            inheritance_rules=inheritance_rules,
            death_type=context.result_collector.death_type,
        )
        context.result_collector.set_inheritance_result(result.model_dump())
