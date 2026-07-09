from typing import Any

from app.engine.simulation_context import LifeState
from app.modules.family.models import FamilyState
from app.modules.romance.constants import ROMANCE_CONDITION_KEYS, ROMANCE_EFFECT_TYPES
from app.modules.social.constants import SOCIAL_CONDITION_KEYS
from app.modules.romance.models import RomanceState
from app.modules.social.models import SocialState
from app.modules.random_events.library_models import V1EventDefinition


class RandomEventConditionMatcher:
    def matches(self, event: V1EventDefinition, state: LifeState) -> bool:
        conditions = event.conditions or {}
        if conditions.get("system_only") is True:
            return False

        if not self._matches_age(event, state):
            return False

        family = FamilyState.from_life_state_dict(state.family)
        social = SocialState.from_life_state_dict(state.social)
        romance = RomanceState.from_life_state_dict(state.romance)

        for key, expected in conditions.items():
            if key in {
                "min_age",
                "max_age",
                "age_equals",
                "age_min",
                "age_max",
                "life_stages",
                "system_only",
                "unsupported_condition",
                "pool",
            }:
                continue
            if not self._evaluate_condition(key, expected, state, family, social, romance):
                return False
        return True

    def _matches_age(self, event: V1EventDefinition, state: LifeState) -> bool:
        age = state.age
        if age < event.age_range.min or age > event.age_range.max:
            return False

        conditions = event.conditions or {}
        min_age = conditions.get("min_age", conditions.get("age_min"))
        max_age = conditions.get("max_age", conditions.get("age_max"))
        if min_age is not None and age < int(min_age):
            return False
        if max_age is not None and age > int(max_age):
            return False
        if "age_equals" in conditions and age != int(conditions["age_equals"]):
            return False

        stage_filter = conditions.get("life_stages") or event.life_stages
        if stage_filter:
            normalized_stage = {"child": "childhood"}.get(
                state.life_stage,
                state.life_stage,
            )
            if normalized_stage not in stage_filter:
                return False
        return True

    def _evaluate_condition(
        self,
        key: str,
        expected: Any,
        state: LifeState,
        family: FamilyState,
        social: SocialState,
        romance: RomanceState,
    ) -> bool:
        if key == "health_below":
            return self._health_score(state) < int(expected)
        if key == "health_above":
            return self._health_score(state) > int(expected)
        if key == "asset_below":
            return self._cash(state) < float(expected)
        if key == "asset_above":
            return self._cash(state) > float(expected)
        if key == "education_stage_in":
            current = str(state.education.get("current_stage", ""))
            values = expected if isinstance(expected, list) else [expected]
            return current in values
        if key == "highest_level_in":
            current = str(state.education.get("highest_level", ""))
            values = expected if isinstance(expected, list) else [expected]
            return current in values
        if key == "employment_status_in":
            current = str(state.career.get("employment_status", ""))
            values = expected if isinstance(expected, list) else [expected]
            return current in values
        if key == "career_path_in":
            current = str(state.career.get("career_path", ""))
            values = expected if isinstance(expected, list) else [expected]
            return current in values
        if key == "has_flag":
            return bool(state.flags.get(str(expected)))
        if key == "not_has_flag":
            return not bool(state.flags.get(str(expected)))
        if key == "attribute_below":
            attr_key, threshold = self._pair(expected)
            return int(state.attributes.get(attr_key, 0)) < int(threshold)
        if key == "attribute_above":
            attr_key, threshold = self._pair(expected)
            return int(state.attributes.get(attr_key, 0)) > int(threshold)
        if key == "relationship_status_in":
            values = expected if isinstance(expected, list) else [expected]
            return family.relationship_status in values
        if key == "relationship_status":
            return family.relationship_status == str(expected)
        if key == "partner_relation_min":
            return family.partner_relation >= int(expected)
        if key == "partner_relation_max":
            return family.partner_relation <= int(expected)
        if key == "has_spouse":
            return family.has_spouse() is bool(expected)
        if key == "has_children":
            return family.has_children() is bool(expected)
        if key == "children_count_min":
            return family.children_count >= int(expected)
        if key == "children_count_max":
            return family.children_count <= int(expected)
        if key == "family_pressure_min":
            return family.family_pressure >= int(expected)
        if key == "family_pressure_max":
            return family.family_pressure <= int(expected)
        if key == "parent_child_relation_min":
            return family.parent_child_relation >= int(expected)
        if key == "parent_child_relation_max":
            return family.parent_child_relation <= int(expected)
        if key == "father_relation_min":
            return family.father_relation >= int(expected)
        if key == "mother_relation_min":
            return family.mother_relation >= int(expected)
        if key in SOCIAL_CONDITION_KEYS:
            return self._evaluate_social_condition(key, expected, social)
        if key in ROMANCE_CONDITION_KEYS:
            return self._evaluate_romance_condition(key, expected, romance)
        if key == "is_enrolled":
            return bool(state.education.get("is_enrolled", False)) is bool(expected)
        if key == "years_worked_min":
            return int(state.career.get("years_worked", 0)) >= int(expected)
        if key == "years_worked_max":
            return int(state.career.get("years_worked", 0)) <= int(expected)
        if key == "school_year_min":
            return int(state.education.get("school_year", 0)) >= int(expected)
        if key == "school_year_max":
            return int(state.education.get("school_year", 0)) <= int(expected)
        if key == "education_graduated_this_year":
            graduated = str(state.education.get("last_education_change", "")).startswith("graduated_")
            return graduated is bool(expected)
        if key == "parents_alive":
            parents = state.family.get("parents", [])
            alive = any(parent.get("is_alive", True) for parent in parents) if parents else False
            return alive is bool(expected)
        if key == "has_sibling":
            has_sibling = social.has_relationship_type("sibling")
            return has_sibling is bool(expected)
        if key == "net_worth_above":
            return self._net_worth(state) > float(expected)
        if key == "net_worth_below":
            return self._net_worth(state) < float(expected)
        if key in {"family_state", "relationship_state", "unsupported_condition", "sub_category"}:
            return True
        if key.startswith("social_"):
            return False
        if key.startswith("romance_"):
            return False
        return True

    def _evaluate_romance_condition(self, key: str, expected: Any, romance: RomanceState) -> bool:
        if key == "has_romantic_candidate":
            return romance.has_romantic_candidate() if bool(expected) else not romance.has_romantic_candidate()
        if key == "has_current_romantic_relationship":
            has_rel = romance.get_current_relationship() is not None
            return has_rel if bool(expected) else not has_rel
        if key == "is_dating":
            return romance.is_dating() is bool(expected)
        if key == "is_single":
            return romance.is_single() is bool(expected)
        if key == "romance_favor_min":
            rel = romance.get_current_relationship()
            return rel is not None and rel.favor >= int(expected)
        if key == "romance_trust_min":
            rel = romance.get_current_relationship()
            return rel is not None and rel.trust >= int(expected)
        if key == "romance_intimacy_min":
            rel = romance.get_current_relationship()
            return rel is not None and rel.intimacy >= int(expected)
        if key == "romance_conflict_min":
            rel = romance.get_current_relationship()
            return rel is not None and rel.conflict >= int(expected)
        if key == "romance_stability_min":
            rel = romance.get_current_relationship()
            return rel is not None and rel.stability >= int(expected)
        if key == "years_single_min":
            return romance.years_single >= int(expected)
        if key == "years_in_relationship_min":
            return romance.years_in_current_relationship >= int(expected)
        if key == "romance_flag_exists":
            return str(expected) in romance.romance_flags
        if key == "romance_flag_not_exists":
            return str(expected) not in romance.romance_flags
        return False

    def _evaluate_social_condition(self, key: str, expected: Any, social: SocialState) -> bool:
        if key == "has_friend":
            return social.friend_count() > 0 if bool(expected) else social.friend_count() == 0
        if key == "has_best_friend":
            has_best = social.has_relationship_type("best_friend")
            return has_best if bool(expected) else not has_best
        if key == "friend_count_min":
            return social.friend_count() >= int(expected)
        if key == "relationship_type_exists":
            return social.has_relationship_type(str(expected))
        if key == "social_closeness_min":
            rel_type, threshold = self._social_metric_pair(expected)
            return any(
                item.get("relationship_type") == rel_type
                and int(item.get("closeness", 0)) >= threshold
                for item in social.relationships
            )
        if key == "social_trust_min":
            rel_type, threshold = self._social_metric_pair(expected)
            return any(
                item.get("relationship_type") == rel_type
                and int(item.get("trust", 0)) >= threshold
                for item in social.relationships
            )
        if key == "social_conflict_min":
            rel_type, threshold = self._social_metric_pair(expected)
            return any(
                item.get("relationship_type") == rel_type
                and int(item.get("conflict", 0)) >= threshold
                for item in social.relationships
            )
        if key == "has_mentor":
            has_mentor = social.has_relationship_type("mentor")
            return has_mentor if bool(expected) else not has_mentor
        if key == "has_rival":
            has_rival = social.has_relationship_type("rival")
            return has_rival if bool(expected) else not has_rival
        if key == "has_benefactor":
            has_benefactor = social.has_relationship_type("benefactor")
            return has_benefactor if bool(expected) else not has_benefactor
        if key == "social_flag_exists":
            return str(expected) in social.social_flags
        if key == "social_flag_not_exists":
            return str(expected) not in social.social_flags
        if key == "active_relationship_count_min":
            return social.active_relationship_count() >= int(expected)
        if key == "active_relationship_count_max":
            return social.active_relationship_count() <= int(expected)
        if key == "social_familiarity_min":
            rel_type, threshold = self._social_metric_pair(expected)
            return any(
                item.get("relationship_type") == rel_type
                and int(item.get("familiarity", 0)) >= threshold
                for item in social.relationships
            )
        if key == "social_conflict_max":
            rel_type, threshold = self._social_metric_pair(expected)
            return any(
                item.get("relationship_type") == rel_type
                and int(item.get("conflict", 0)) <= threshold
                for item in social.relationships
            )
        return False

    def _social_metric_pair(self, expected: Any) -> tuple[str, int]:
        if isinstance(expected, dict):
            return str(expected.get("type", "")), int(expected.get("value", 0))
        raise ValueError(f"Invalid social metric condition payload: {expected}")

    def _pair(self, expected: Any) -> tuple[str, int]:
        if isinstance(expected, dict):
            return str(expected["key"]), int(expected["value"])
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            return str(expected[0]), int(expected[1])
        raise ValueError(f"Invalid attribute condition payload: {expected}")

    def _health_score(self, state: LifeState) -> int:
        return int(state.health.get("health_score", 0))

    def _cash(self, state: LifeState) -> float:
        return float(state.assets.get("cash", 0.0))

    def _net_worth(self, state: LifeState) -> float:
        assets = state.assets or {}
        return float(assets.get("net_worth", assets.get("cash", 0.0)))
