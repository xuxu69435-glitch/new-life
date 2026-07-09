from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.legal.models import LegalState
from app.modules.romance.events import RomanceEventProcessor
from app.modules.romance.models import RomanceState
from app.modules.romance.processor import RomanceAnnualProcessor
from app.modules.romance.rules import blocks_normal_romance, get_romance_rules
from app.modules.romance.summary import build_romance_summary


class RomanceService:
    name = "romance"
    can_confirm_death = False

    def __init__(self) -> None:
        self.processor = RomanceEventProcessor()

    def run(self, context: SimulationContext) -> None:
        if context.state.is_dead:
            return

        romance_rules = get_romance_rules(context.rules)
        romance = RomanceState.from_life_state_dict(context.state.romance)
        romance = self.processor.initialize(romance)
        romance.clear_year_tracking()

        legal = LegalState.from_life_state_dict(context.state.legal)
        annual_processor = RomanceAnnualProcessor(romance_rules, context.rng)
        next_age = context.state.age + 1

        if blocks_normal_romance(legal, context.rules):
            mode = "prison" if legal.is_in_prison else "fugitive"
            romance = annual_processor.apply_restricted_decay(romance, next_age, context.rules, mode=mode)
        else:
            romance = annual_processor.apply_annual_changes(romance, context.state, context.rules)

        romance.romance_summary = build_romance_summary(romance, next_age)
        romance.validate_statuses()

        family_signal = annual_processor.build_family_signal(romance)
        payload: dict = {"romance": romance.to_life_state_dict()}
        if family_signal:
            payload["romance_to_family_signal"] = family_signal

        context.event_bus.publish(
            SimulationEventType.ROMANCE_STATE_UPDATE_REQUESTED,
            self.name,
            payload,
        )
