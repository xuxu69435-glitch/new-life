from typing import Final

PERSON_ROLES: Final[set[str]] = {
    "friend",
    "classmate",
    "coworker",
    "teacher",
    "leader",
    "mentor",
    "neighbor",
    "acquaintance",
    "rival",
    "benefactor",
    "romantic_candidate",
    "roommate",
    "sibling",
    "parent",
    "partner",
    "child",
    "unknown",
}

RELATIONSHIP_TYPES: Final[set[str]] = {
    "friend",
    "best_friend",
    "classmate",
    "coworker",
    "teacher",
    "leader",
    "mentor",
    "acquaintance",
    "rival",
    "benefactor",
    "romantic_candidate",
    "neighbor",
    "roommate",
    "sibling",
    "parent",
    "partner",
    "child",
    "other",
}

RELATIONSHIP_STATUSES: Final[set[str]] = {
    "active",
    "distant",
    "broken",
    "important",
    "inactive",
}

SCHOOL_STAGES: Final[set[str]] = {"primary", "middle", "high", "college"}

SOCIAL_CONDITION_KEYS: Final[set[str]] = {
    "has_friend",
    "has_best_friend",
    "friend_count_min",
    "relationship_type_exists",
    "social_closeness_min",
    "social_trust_min",
    "social_conflict_min",
    "social_familiarity_min",
    "social_conflict_max",
    "has_mentor",
    "has_rival",
    "has_benefactor",
    "social_flag_exists",
    "social_flag_not_exists",
    "active_relationship_count_min",
    "active_relationship_count_max",
}

SOCIAL_EFFECT_TYPES: Final[set[str]] = {
    "social_person_created",
    "social_relationship_created",
    "social_relationship_change",
    "social_relationship_status_change",
    "social_flag_set",
    "social_flag_remove",
}
