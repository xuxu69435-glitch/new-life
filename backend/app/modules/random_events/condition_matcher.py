from typing import Any

from app.engine.simulation_context import LifeState
from app.modules.family.models import FamilyState
from app.modules.random_events.library_models import V1EventDefinition


class RandomEventConditionMatcher:
    def matches(self, event: V1EventDefinition, state: LifeState) -> bool:
        conditions = event.conditions or {}
        if conditions.get("system_only") is True:
            return False

        if not self._matches_age(event, state):
            return False

        family = FamilyState.from_life_state_dict(state.family)

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
            if not self._evaluate_condition(key, expected, state, family):
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
        if key in {"family_state", "relationship_state", "unsupported_condition"}:
            return True
        return True

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
