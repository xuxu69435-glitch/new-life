from typing import Any

from app.engine.simulation_context import LifeState
from app.modules.career.models import CareerState
from app.modules.education.models import EducationState
from app.modules.family.models import FamilyState
from app.modules.legal.models import LegalState
from app.modules.mainline.models import MainlineState


class MainlineConditionError(ValueError):
    pass


class MainlineConditionEvaluator:
    SUPPORTED_KEYS = {
        "age_min",
        "age_max",
        "life_stages",
        "is_dead",
        "health_score_min",
        "health_score_max",
        "attribute_min",
        "attribute_max",
        "any_attribute_min",
        "education_stage",
        "education_stage_in",
        "highest_level_in",
        "education_score_min",
        "college_years_min",
        "employment_status",
        "employment_status_in",
        "annual_income_min",
        "cash_min",
        "years_worked_min",
        "relationship_status_in",
        "children_count_min",
        "has_spouse",
        "has_children",
        "has_flag",
        "family_pressure_max",
        "is_in_prison",
        "is_fugitive",
        "is_under_supervision",
        "has_criminal_record",
        "not_is_in_prison",
        "not_is_fugitive",
        "consecutive_rehabilitation_years_min",
        "years_after_release_min",
        "released_from_prison",
        "supervision_ended",
        "or_conditions",
    }

    def matches(self, conditions: dict[str, Any], state: LifeState, mainline: MainlineState) -> bool:
        if not conditions:
            return True
        self._validate_keys(conditions)
        if "or_conditions" in conditions:
            groups = conditions["or_conditions"]
            if not isinstance(groups, list) or not groups:
                raise MainlineConditionError("or_conditions must be a non-empty list.")
            return any(self.matches(group, state, mainline) for group in groups)
        for key, expected in conditions.items():
            if not self._evaluate(key, expected, state, mainline):
                return False
        return True

    def _validate_keys(self, conditions: dict[str, Any]) -> None:
        for key in conditions:
            if key not in self.SUPPORTED_KEYS:
                raise MainlineConditionError(f"Unsupported mainline condition key: {key}")

    def _evaluate(
        self,
        key: str,
        expected: Any,
        state: LifeState,
        mainline: MainlineState,
    ) -> bool:
        family = FamilyState.from_life_state_dict(state.family)
        legal = LegalState.from_life_state_dict(state.legal)
        education = EducationState.from_life_state_dict(state.education, {})
        career = CareerState.from_life_state_dict(state.career, {})

        if key == "age_min":
            return state.age >= int(expected)
        if key == "age_max":
            return state.age <= int(expected)
        if key == "life_stages":
            values = expected if isinstance(expected, list) else [expected]
            stage = {"child": "childhood"}.get(state.life_stage, state.life_stage)
            return stage in values
        if key == "is_dead":
            return state.is_dead is bool(expected)
        if key == "health_score_min":
            return self._health_score(state) >= int(expected)
        if key == "health_score_max":
            return self._health_score(state) <= int(expected)
        if key == "attribute_min":
            attr_key, threshold = self._pair(expected)
            return int(state.attributes.get(attr_key, 0)) >= int(threshold)
        if key == "attribute_max":
            attr_key, threshold = self._pair(expected)
            return int(state.attributes.get(attr_key, 0)) <= int(threshold)
        if key == "any_attribute_min":
            items = expected if isinstance(expected, list) else [expected]
            return any(
                int(state.attributes.get(self._pair(item)[0], 0)) >= int(self._pair(item)[1])
                for item in items
            )
        if key == "education_stage":
            return str(education.current_stage) == str(expected)
        if key == "education_stage_in":
            values = expected if isinstance(expected, list) else [expected]
            return education.current_stage in values
        if key == "highest_level_in":
            values = expected if isinstance(expected, list) else [expected]
            return education.highest_level in values
        if key == "education_score_min":
            return education.education_score >= int(expected)
        if key == "college_years_min":
            task_id = str(expected.get("task_id", "M009"))
            progress = mainline.task_progress.get(task_id, {})
            return int(progress.get("college_years", 0)) >= int(expected.get("years", 1))
        if key == "employment_status":
            return career.employment_status == str(expected)
        if key == "employment_status_in":
            values = expected if isinstance(expected, list) else [expected]
            return career.employment_status in values
        if key == "annual_income_min":
            return float(career.annual_income) > float(expected)
        if key == "cash_min":
            return float(state.assets.get("cash", 0.0)) >= float(expected)
        if key == "years_worked_min":
            return career.years_worked >= int(expected)
        if key == "relationship_status_in":
            values = expected if isinstance(expected, list) else [expected]
            return family.relationship_status in values
        if key == "children_count_min":
            return family.children_count >= int(expected)
        if key == "has_spouse":
            return family.has_spouse() is bool(expected)
        if key == "has_children":
            return family.has_children() is bool(expected)
        if key == "has_flag":
            return bool(state.flags.get(str(expected)))
        if key == "family_pressure_max":
            return family.family_pressure < int(expected)
        if key == "is_in_prison":
            return legal.is_in_prison is bool(expected)
        if key == "is_fugitive":
            return legal.is_fugitive is bool(expected)
        if key == "is_under_supervision":
            return legal.is_under_supervision is bool(expected)
        if key == "has_criminal_record":
            return legal.has_criminal_record is bool(expected)
        if key == "not_is_in_prison":
            return legal.is_in_prison is not bool(expected)
        if key == "not_is_fugitive":
            return legal.is_fugitive is not bool(expected)
        if key == "consecutive_rehabilitation_years_min":
            return legal.consecutive_rehabilitation_years >= int(expected)
        if key == "years_after_release_min":
            return legal.years_after_release >= int(expected)
        if key == "released_from_prison":
            return (
                not legal.is_in_prison
                and legal.has_criminal_record
                and legal.years_served > 0
            ) is bool(expected)
        if key == "supervision_ended":
            return (not legal.is_under_supervision) is bool(expected)
        raise MainlineConditionError(f"Unhandled condition key: {key}")

    def _pair(self, expected: Any) -> tuple[str, int]:
        if isinstance(expected, dict):
            return str(expected["key"]), int(expected["value"])
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            return str(expected[0]), int(expected[1])
        raise MainlineConditionError(f"Invalid attribute condition payload: {expected}")

    def _health_score(self, state: LifeState) -> int:
        return int(state.health.get("health_score", 0))
