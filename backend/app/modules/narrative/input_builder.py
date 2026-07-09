from typing import Any

from app.engine.simulation_context import SimulationContext
from app.modules.mainline.models import MainlineState
from app.modules.narrative.models import AnnualNarrativeInput
from app.modules.romance.summary import build_romance_narrative_lines, build_romance_summary
from app.modules.social.summary import build_social_narrative_lines, build_social_summary


def build_annual_narrative_input(context: SimulationContext) -> AnnualNarrativeInput:
    collector = context.result_collector
    state = context.state
    after_stage = collector.life_stage or state.life_stage

    health_score_delta = 0
    if collector.health_score_before is not None and collector.health_score_after is not None:
        health_score_delta = collector.health_score_after - collector.health_score_before

    legal_after = dict(collector.legal_changes or state.legal)
    mainline_after = dict(collector.mainline_changes or state.mainline)

    has_notable = bool(
        collector.death_confirmed
        or collector.triggered_random_events
        or collector.inheritance_result
        or legal_after.get("is_in_prison")
        or legal_after.get("is_fugitive")
        or collector.education_graduated_this_year
        or collector.completed_mainline_tasks_this_year
        or collector.changed_attributes
        or collector.changed_assets
        or collector.family_processor.married_this_year
        or collector.family_processor.child_born_this_year
        or abs(health_score_delta) >= 1
    )

    social_changes: dict[str, Any] = {}
    social_narrative: list[str] = []
    if collector._social_working is not None:
        social_changes = {
            "summary": build_social_summary(collector._social_working, state.age + 1),
        }
        social_narrative = build_social_narrative_lines(collector._social_working)

    romance_changes: dict[str, Any] = {}
    romance_narrative: list[str] = []
    if collector._romance_working is not None:
        romance_changes = {
            "summary": build_romance_summary(collector._romance_working, state.age + 1),
        }
        romance_narrative = build_romance_narrative_lines(collector._romance_working)

    return AnnualNarrativeInput(
        life_id=state.life_id,
        age_before=state.age,
        age_after=state.age + 1,
        life_stage=after_stage,
        is_dead=collector.death_confirmed,
        death_type=collector.death_type,
        death_reason=collector.death_reason,
        triggered_random_events=list(collector.triggered_random_events),
        pending_random_event=collector.pending_random_event,
        random_event_choice_result=collector.random_event_choice_result,
        education_changes={
            "stage_before": collector.education_stage_before,
            "stage_after": collector.education_stage_after,
            "graduated": collector.education_graduated_this_year,
        },
        career_changes={
            "status_before": collector.career_status_before,
            "status_after": collector.career_status_after,
            "career_path": collector.career_path,
            "position_level": collector.position_level,
            "annual_income": collector.annual_income,
            "career_income_change": collector.career_income_change,
        },
        family_changes=collector.family_processor.summary(),
        health_changes={
            "health_score_before": collector.health_score_before,
            "health_score_after": collector.health_score_after,
            "health_score_delta": health_score_delta,
            "health_level_before": collector.health_level_before,
            "health_level_after": collector.health_level_after,
            "warnings": list(collector.new_health_warnings),
        },
        asset_changes=dict(collector.changed_assets),
        attribute_changes=dict(collector.changed_attributes),
        legal_changes=legal_after,
        legal_before=dict(state.legal),
        pending_legal_event=collector.pending_legal_event,
        mainline_changes=mainline_after,
        completed_tasks_this_year=list(collector.completed_mainline_tasks_this_year),
        mainline_narrative=list(collector.mainline_narrative),
        inheritance_result=collector.inheritance_result,
        major_flags={"has_notable_events": has_notable},
        married_this_year=collector.family_processor.married_this_year,
        child_born_this_year=collector.family_processor.child_born_this_year,
        relationship_status_before=collector.family_processor.relationship_status_before,
        relationship_status_after=collector.family_processor.relationship_status_after,
        social_changes=social_changes,
        social_narrative=social_narrative,
        romance_changes=romance_changes,
        romance_narrative=romance_narrative,
    )
