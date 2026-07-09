from typing import Final

CANDIDATE_SOURCES: Final[set[str]] = {
    "school",
    "university",
    "work",
    "social",
    "random_event",
    "family_introduction",
    "system",
}

CANDIDATE_STATUSES: Final[set[str]] = {
    "candidate",
    "crush",
    "ambiguous",
    "rejected",
    "inactive",
}

RELATIONSHIP_STATUSES: Final[set[str]] = {
    "none",
    "crush",
    "ambiguous",
    "dating",
    "cooling_off",
    "broken_up",
    "reconciled",
    "engagement_intent",
    "ended",
}

ROMANCE_CONDITION_KEYS: Final[set[str]] = {
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

ROMANCE_EFFECT_TYPES: Final[set[str]] = {
    "romance_candidate_created",
    "romance_candidate_change",
    "romance_relationship_started",
    "romance_relationship_change",
    "romance_relationship_status_change",
    "romance_relationship_ended",
    "romance_flag_set",
    "romance_flag_remove",
}
