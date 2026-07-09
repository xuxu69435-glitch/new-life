from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.legal.models import LegalState
from app.modules.social.events import SocialEventProcessor
from app.modules.social.models import SocialState
from app.modules.social.processor import SocialAnnualProcessor
from app.modules.social.rules import blocks_normal_social, get_social_rules
from app.modules.social.summary import build_social_summary


class SocialService:
    name = "social"
    can_confirm_death = False

    def __init__(self) -> None:
        self.processor = SocialEventProcessor()

    def run(self, context: SimulationContext) -> None:
        if context.state.is_dead:
            return

        social_rules = get_social_rules(context.rules)
        social = SocialState.from_life_state_dict(context.state.social)
        social = self.processor.initialize(social)
        social.clear_year_tracking()

        legal = LegalState.from_life_state_dict(context.state.legal)
        annual_processor = SocialAnnualProcessor(social_rules, context.rng)
        next_age = context.state.age + 1

        if blocks_normal_social(legal, context.rules):
            mode = "prison" if legal.is_in_prison else "fugitive"
            social = annual_processor.apply_restricted_decay(social, next_age, mode)
        else:
            social = annual_processor.apply_annual_changes(social, context.state, context.rules)

        social.social_summary = build_social_summary(social, next_age)
        social.validate_roles()

        context.event_bus.publish(
            SimulationEventType.SOCIAL_STATE_UPDATE_REQUESTED,
            self.name,
            {"social": social.to_life_state_dict()},
        )
