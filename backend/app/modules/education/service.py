from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.education.models import EducationState
from app.modules.legal.models import LegalState
from app.modules.legal.rules import blocks_normal_education
from app.modules.education.rules import resolve_stage_for_age


class EducationService:
    name = "education"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        legal = LegalState.from_life_state_dict(context.state.legal)
        if blocks_normal_education(legal, context.rules):
            return

        rules = context.rules
        age = context.state.age
        next_age = age + 1
        education = EducationState.from_life_state_dict(context.state.education, rules)
        stage_before = education.current_stage
        graduated_this_year = False

        stage = resolve_stage_for_age(next_age, rules)
        if stage is None:
            self._publish_state(context, education, stage_before, graduated_this_year)
            return

        if stage["id"] == "none":
            education.current_stage = "none"
            education.is_enrolled = False
            education.last_education_change = "not_in_school"
        else:
            education.current_stage = stage["id"]
            education.is_enrolled = True
            education.school_year += 1
            education.education_score += 1
            education.last_education_change = f"progressed_to_{stage['id']}"

            for attribute, delta in stage.get("annual_attribute_changes", {}).items():
                context.event_bus.publish(
                    SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
                    self.name,
                    {
                        "key": attribute,
                        "delta": int(delta),
                        "source_event_id": stage["id"],
                        "reason": f"Education stage {stage['id']}",
                    },
                )

            if context.player_choices.get("annual_focus") == "study_focus":
                context.event_bus.publish(
                    SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
                    self.name,
                    {
                        "key": "intelligence",
                        "delta": 1,
                        "source_event_id": "study_focus",
                        "reason": "Focused study",
                    },
                )

            graduation_age = int(stage.get("graduation_age", stage["max_age"]))
            if next_age >= graduation_age:
                education.is_graduated = True
                education.is_enrolled = False
                education.highest_level = str(stage.get("highest_level", stage["id"]))
                education.graduation_age = next_age
                education.last_education_change = f"graduated_{education.highest_level}"
                graduated_this_year = True
                education.history.append(
                    {
                        "age": next_age,
                        "stage": stage["id"],
                        "event": "graduated",
                        "highest_level": education.highest_level,
                    }
                )

        context.event_bus.publish(
            SimulationEventType.EDUCATION_PROGRESSED,
            self.name,
            {
                "stage": education.current_stage,
                "graduated": graduated_this_year,
                "highest_level": education.highest_level,
            },
        )
        self._publish_state(context, education, stage_before, graduated_this_year)

    def _publish_state(
        self,
        context: SimulationContext,
        education: EducationState,
        stage_before: str,
        graduated_this_year: bool,
    ) -> None:
        context.event_bus.publish(
            SimulationEventType.EDUCATION_STATE_UPDATE_REQUESTED,
            self.name,
            {
                "education": education.to_life_state_dict(),
                "education_stage_before": stage_before,
                "education_stage_after": education.current_stage,
                "education_graduated_this_year": graduated_this_year,
            },
        )
