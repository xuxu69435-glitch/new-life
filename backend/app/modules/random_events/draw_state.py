from typing import Any

from app.engine.simulation_context import LifeState, SimulationContext


BLOCKED_SOCIAL_SUB_CATEGORIES_PRISON = {
    "school_social",
    "university_social",
    "workplace_social",
    "family_social",
    "neighborhood_or_adult_social",
}


def blocked_social_sub_categories(legal_state) -> set[str]:
    if legal_state.is_in_prison or legal_state.is_fugitive:
        return set(BLOCKED_SOCIAL_SUB_CATEGORIES_PRISON)
    return set()


def build_draw_state(context: SimulationContext) -> LifeState:
    """Merge in-year module updates so social event matching sees current education/social state."""
    state = context.state.model_copy(deep=True)
    collector = context.result_collector

    if collector.education_state_update is not None:
        state.education = dict(collector.education_state_update)
    if collector._social_working is not None:
        state.social = collector._social_working.to_life_state_dict()
    if collector._family_working is not None:
        state.family = collector._family_working.to_life_state_dict()
    if collector.changed_attributes:
        merged = dict(state.attributes)
        merged.update(collector.changed_attributes)
        state.attributes = merged
    if collector.changed_assets:
        merged = dict(state.assets)
        merged.update(collector.changed_assets)
        state.assets = merged
    return state
