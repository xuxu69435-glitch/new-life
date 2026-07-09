from app.infrastructure.errors import RuleValidationError
from app.modules.random_events.library_models import RandomEventLibraryV1

WEIGHT_TIER_TO_WEIGHT = {
    "低概率": 1,
    "中低概率": 3,
    "中概率": 5,
    "中高概率": 8,
    "高概率": 12,
    "极低概率": 1,
    "系统事件": 0,
}

ALLOWED_CONDITION_KEYS = {
    "min_age",
    "max_age",
    "age_equals",
    "life_stages",
    "health_below",
    "health_above",
    "asset_below",
    "asset_above",
    "education_stage_in",
    "highest_level_in",
    "employment_status_in",
    "career_path_in",
    "has_flag",
    "not_has_flag",
    "attribute_below",
    "attribute_above",
    "family_state",
    "relationship_state",
    "system_only",
    "unsupported_condition",
    "pool",
    "relationship_status_in",
    "relationship_status",
    "partner_relation_min",
    "partner_relation_max",
    "has_spouse",
    "has_children",
    "children_count_min",
    "children_count_max",
    "family_pressure_min",
    "family_pressure_max",
    "parent_child_relation_min",
    "parent_child_relation_max",
    "father_relation_min",
    "mother_relation_min",
    "age_min",
    "age_max",
    "has_friend",
    "has_best_friend",
    "friend_count_min",
    "relationship_type_exists",
    "social_closeness_min",
    "social_trust_min",
    "social_conflict_min",
    "has_mentor",
    "has_rival",
    "has_benefactor",
    "social_flag_exists",
    "social_flag_not_exists",
    "active_relationship_count_min",
    "active_relationship_count_max",
    "has_romantic_candidate",
    "has_current_romantic_relationship",
    "is_dating",
    "is_single",
    "romance_favor_min",
    "romance_trust_min",
    "romance_intimacy_min",
    "romance_conflict_min",
    "romance_stability_min",
    "years_single_min",
    "years_in_relationship_min",
    "romance_flag_exists",
    "romance_flag_not_exists",
}

ALLOWED_EFFECT_TYPES = {
    "attribute_change",
    "health_change",
    "asset_change",
    "direct_death_candidate",
    "narrative_tag",
    "flag_set",
    "unsupported_effect",
    "family_relation_change",
    "relationship_status_change",
    "partner_relation_change",
    "parent_relation_change",
    "family_pressure_change",
    "child_created",
    "child_relation_change",
    "spouse_created",
    "marriage_created",
    "divorce_created",
    "family_history_recorded",
    "partner_created",
    "social_person_created",
    "social_relationship_created",
    "social_relationship_change",
    "social_relationship_status_change",
    "social_flag_set",
    "social_flag_remove",
    "romance_candidate_created",
    "romance_candidate_change",
    "romance_relationship_started",
    "romance_relationship_change",
    "romance_relationship_status_change",
    "romance_relationship_ended",
    "romance_flag_set",
    "romance_flag_remove",
}

DIRECT_DEATH_EVENT_IDS = {"E067", "E068", "E070"}
SYSTEM_EVENT_IDS = {"E065", "E080"}


class RandomEventLibraryValidator:
    def validate(self, library: RandomEventLibraryV1) -> None:
        if library.event_count != 80:
            raise RuleValidationError(
                f"V1 library event_count must be 80, got {library.event_count}."
            )
        if len(library.events) != 80:
            raise RuleValidationError(
                f"V1 library must contain 80 events, got {len(library.events)}."
            )

        seen_ids: set[str] = set()
        for index in range(1, 81):
            expected_id = f"E{index:03d}"
            if expected_id not in {event.event_id for event in library.events}:
                raise RuleValidationError(
                    f"Missing required event id: {expected_id}."
                )

        for event in library.events:
            if event.event_id in seen_ids:
                raise RuleValidationError(
                    f"Duplicate event id in V1 library: {event.event_id}."
                )
            seen_ids.add(event.event_id)
            self._validate_event(event)

    def _validate_event(self, event) -> None:
        if not event.event_text.strip():
            raise RuleValidationError(
                f"Event '{event.event_id}' must include event_text."
            )
        if not event.choices:
            raise RuleValidationError(
                f"Event '{event.event_id}' must include at least one choice."
            )

        for choice in event.choices:
            if not choice.effects_text.strip():
                raise RuleValidationError(
                    f"Choice '{choice.choice_id}' must include effects_text."
                )
            for effect in choice.effects:
                effect_type = str(effect.get("type", "")).strip()
                if effect_type not in ALLOWED_EFFECT_TYPES:
                    raise RuleValidationError(
                        f"Unknown effect type '{effect_type}' in choice '{choice.choice_id}'."
                    )

        for key in event.conditions:
            if key not in ALLOWED_CONDITION_KEYS:
                raise RuleValidationError(
                    f"Unknown condition field '{key}' in event '{event.event_id}'."
                )

        if event.weight_tier in WEIGHT_TIER_TO_WEIGHT:
            expected_weight = WEIGHT_TIER_TO_WEIGHT[event.weight_tier]
            if event.weight != expected_weight:
                raise RuleValidationError(
                    f"Event '{event.event_id}' weight mismatch for tier "
                    f"'{event.weight_tier}': expected {expected_weight}, got {event.weight}."
                )

        if event.pool_type == "direct_death":
            if event.event_id not in DIRECT_DEATH_EVENT_IDS:
                raise RuleValidationError(
                    f"Only E067/E068/E070 may use direct_death pool_type, got {event.event_id}."
                )
            if event.weight_tier != "极低概率":
                raise RuleValidationError(
                    f"Direct death event '{event.event_id}' must use 极低概率 tier."
                )
            for choice in event.choices:
                if not choice.is_system_choice:
                    raise RuleValidationError(
                        f"Direct death event '{event.event_id}' choices must be system choices."
                    )

        if event.event_id in DIRECT_DEATH_EVENT_IDS and event.pool_type != "direct_death":
            raise RuleValidationError(
                f"Event '{event.event_id}' must be in direct_death pool."
            )

        if event.event_id in SYSTEM_EVENT_IDS:
            if event.pool_type != "system":
                raise RuleValidationError(
                    f"System event '{event.event_id}' must use pool_type=system."
                )
            if event.conditions.get("system_only") is not True:
                raise RuleValidationError(
                    f"System event '{event.event_id}' must set conditions.system_only=true."
                )

        if event.pool_type == "system" and event.weight != 0:
            raise RuleValidationError(
                f"System event '{event.event_id}' must have weight 0."
            )

        if event.weight_tier == "极低概率" and event.pool_type != "direct_death":
            raise RuleValidationError(
                f"Event '{event.event_id}' with 极低概率 must be in direct_death pool."
            )

        if event.weight_tier == "系统事件" and event.pool_type != "system":
            raise RuleValidationError(
                f"Event '{event.event_id}' with 系统事件 tier must be system pool."
            )

        for choice in event.choices:
            for effect in choice.effects:
                if effect.get("type") == "direct_death_candidate":
                    if event.pool_type != "direct_death":
                        raise RuleValidationError(
                            f"direct_death_candidate only allowed in direct_death pool "
                            f"for event '{event.event_id}'."
                        )
