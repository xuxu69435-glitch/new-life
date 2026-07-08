from typing import Any

from app.engine.simulation_context import LifeState
from app.modules.achievement.models import AchievementState
from app.modules.career.models import CareerState
from app.modules.education.models import EducationState
from app.modules.family.models import FamilyState
from app.modules.legal.models import LegalState
from app.modules.mainline.models import MainlineState


class AchievementConditionError(ValueError):
    pass


class AchievementConditionEvaluator:
    SUPPORTED_KEYS = {
        "age_min",
        "age_max",
        "is_dead",
        "health_score_min",
        "health_level_in",
        "cash_min",
        "net_worth_min",
        "education_highest_level_in",
        "education_stage_in",
        "career_status_in",
        "career_years_worked_min",
        "career_annual_income_min",
        "relationship_status_in",
        "children_count_min",
        "has_criminal_record",
        "is_in_prison_ever",
        "is_released",
        "years_after_release_min",
        "consecutive_rehabilitation_years_min",
        "mainline_completed_count_min",
        "inheritance_net_estate_min",
        "narrative_tag_in",
        "major_event_tag_in",
        "flag_exists",
        "flag_not_exists",
        "attribute_min",
        "turbulent_life_categories_min",
        "calm_life_on_death",
        "generation_min",
    }

    def matches(
        self,
        conditions: dict[str, Any],
        state: LifeState,
        achievement_state: AchievementState,
        *,
        narrative_tags: list[str] | None = None,
        inheritance_result: dict[str, Any] | None = None,
    ) -> bool:
        if not conditions:
            return False
        self._validate_keys(conditions)
        for key, expected in conditions.items():
            if not self._evaluate(
                key,
                expected,
                state,
                achievement_state,
                narrative_tags=narrative_tags or [],
                inheritance_result=inheritance_result,
            ):
                return False
        return True

    def _validate_keys(self, conditions: dict[str, Any]) -> None:
        for key in conditions:
            if key not in self.SUPPORTED_KEYS:
                raise AchievementConditionError(f"Unsupported achievement condition key: {key}")

    def _evaluate(
        self,
        key: str,
        expected: Any,
        state: LifeState,
        achievement_state: AchievementState,
        *,
        narrative_tags: list[str],
        inheritance_result: dict[str, Any] | None,
    ) -> bool:
        family = FamilyState.from_life_state_dict(state.family)
        legal = LegalState.from_life_state_dict(state.legal)
        education = EducationState.from_life_state_dict(state.education, {})
        career = CareerState.from_life_state_dict(state.career, {})
        mainline = MainlineState.from_life_state_dict(state.mainline)
        flags = {**state.flags, **achievement_state.achievement_flags}

        if key == "age_min":
            return state.age >= int(expected)
        if key == "age_max":
            return state.age <= int(expected)
        if key == "is_dead":
            return state.is_dead is bool(expected)
        if key == "health_score_min":
            return int(state.health.get("health_score", 0)) >= int(expected)
        if key == "health_level_in":
            values = expected if isinstance(expected, list) else [expected]
            return str(state.health.get("health_level", "")) in values
        if key == "cash_min":
            return float(state.assets.get("cash", 0.0)) >= float(expected)
        if key == "net_worth_min":
            return float(state.assets.get("net_worth", 0.0)) >= float(expected)
        if key == "education_highest_level_in":
            values = expected if isinstance(expected, list) else [expected]
            return education.highest_level in values
        if key == "education_stage_in":
            values = expected if isinstance(expected, list) else [expected]
            return education.current_stage in values
        if key == "career_status_in":
            values = expected if isinstance(expected, list) else [expected]
            return career.employment_status in values
        if key == "career_years_worked_min":
            return career.years_worked >= int(expected)
        if key == "career_annual_income_min":
            return float(career.annual_income) >= float(expected)
        if key == "relationship_status_in":
            values = expected if isinstance(expected, list) else [expected]
            return family.relationship_status in values
        if key == "children_count_min":
            return family.children_count >= int(expected)
        if key == "has_criminal_record":
            return legal.has_criminal_record is bool(expected)
        if key == "is_in_prison_ever":
            return bool(flags.get("ever_in_prison")) is bool(expected)
        if key == "is_released":
            released = (
                legal.has_criminal_record
                and not legal.is_in_prison
                and not legal.is_fugitive
                and not legal.is_under_supervision
                and legal.years_served > 0
            )
            return released is bool(expected)
        if key == "years_after_release_min":
            return legal.years_after_release >= int(expected)
        if key == "consecutive_rehabilitation_years_min":
            return legal.consecutive_rehabilitation_years >= int(expected)
        if key == "mainline_completed_count_min":
            return len(mainline.completed_tasks) >= int(expected)
        if key == "inheritance_net_estate_min":
            if inheritance_result is None:
                return False
            return float(inheritance_result.get("net_estate", 0.0)) >= float(expected)
        if key == "narrative_tag_in":
            values = expected if isinstance(expected, list) else [expected]
            return any(tag in narrative_tags for tag in values)
        if key == "major_event_tag_in":
            values = expected if isinstance(expected, list) else [expected]
            return any(tag in narrative_tags for tag in values)
        if key == "flag_exists":
            return bool(flags.get(str(expected)))
        if key == "flag_not_exists":
            return not bool(flags.get(str(expected)))
        if key == "attribute_min":
            attr_key, threshold = self._pair(expected)
            return int(state.attributes.get(attr_key, 0)) >= int(threshold)
        if key == "turbulent_life_categories_min":
            categories = 0
            if flags.get("ever_married"):
                categories += 1
            if flags.get("ever_children"):
                categories += 1
            if flags.get("ever_in_prison"):
                categories += 1
            if flags.get("ever_released"):
                categories += 1
            return categories >= int(expected)
        if key == "calm_life_on_death":
            if not state.is_dead:
                return False
            return not legal.has_criminal_record and state.age >= int(expected.get("age_min", 70))
        if key == "generation_min":
            return int(family.generation) >= int(expected)
        raise AchievementConditionError(f"Unhandled achievement condition key: {key}")

    def _pair(self, expected: Any) -> tuple[str, int]:
        if isinstance(expected, dict):
            return str(expected["key"]), int(expected["value"])
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            return str(expected[0]), int(expected[1])
        raise AchievementConditionError(f"Invalid attribute condition payload: {expected}")
