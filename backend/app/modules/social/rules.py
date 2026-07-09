from app.modules.legal.models import LegalState
from app.modules.social.models import SocialState, clamp_score


DEFAULT_SOCIAL_RULES: dict = {
    "default_relationship_decay_by_age": 1,
    "school_relationship_chance": 0.18,
    "work_relationship_chance": 0.16,
    "friendship_decay_per_year": 2,
    "important_relationship_decay_per_year": 1,
    "trust_decay_per_year": 1,
    "conflict_decay_per_year": 1,
    "max_active_relationships": 25,
    "important_relationship_threshold": 75,
    "best_friend_threshold": 85,
    "rival_conflict_threshold": 70,
    "mentor_trust_threshold": 75,
    "benefactor_trust_threshold": 75,
    "legal_blocks_normal_social": True,
    "prison_social_mode": "decay_only",
    "fugitive_social_mode": "heavy_decay",
    "distant_closeness_threshold": 25,
    "broken_conflict_threshold": 85,
    "fugitive_decay_multiplier": 3,
}


def get_social_rules(rules: dict) -> dict:
    merged = dict(DEFAULT_SOCIAL_RULES)
    merged.update(rules.get("social", {}))
    return merged


def build_default_social_state(rules: dict | None = None) -> SocialState:
    _ = get_social_rules(rules or {})
    state = SocialState()
    state.social_summary = {
        "friend_count": 0,
        "important_relationship_count": 0,
        "active_relationship_count": 0,
        "recent_new_count": 0,
        "recent_changed_count": 0,
    }
    return state


def blocks_normal_social(legal: LegalState, rules: dict) -> bool:
    social_rules = get_social_rules(rules)
    if not social_rules.get("legal_blocks_normal_social", True):
        return False
    return legal.is_in_prison or legal.is_fugitive


def clamp_relationship_values(data: dict) -> dict:
    for key in ("closeness", "trust", "conflict", "familiarity", "importance"):
        if key in data:
            data[key] = clamp_score(data[key])
    return data
