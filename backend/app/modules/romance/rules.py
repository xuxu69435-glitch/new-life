from app.modules.legal.models import LegalState
from app.modules.romance.models import RomanceState, clamp_score


DEFAULT_ROMANCE_RULES: dict = {
    "min_candidate_age": 14,
    "min_crush_age": 14,
    "min_formal_dating_age": 18,
    "min_engagement_age": 20,
    "min_marriage_signal_age": 20,
    "candidate_from_social_chance": 0.35,
    "school_crush_chance": 0.12,
    "university_romance_chance": 0.16,
    "workplace_romance_chance": 0.10,
    "friend_to_candidate_chance": 0.06,
    "single_year_candidate_bonus": 0.02,
    "relationship_decay_per_year": 2,
    "stable_relationship_decay_per_year": 1,
    "conflict_decay_per_year": 1,
    "conflict_breakup_threshold": 75,
    "dating_favor_threshold": 60,
    "dating_trust_threshold": 45,
    "dating_attraction_threshold": 50,
    "engagement_stability_threshold": 75,
    "engagement_trust_threshold": 70,
    "max_active_candidates": 5,
    "legal_blocks_romance": True,
    "prison_romance_mode": "decay_only",
    "fugitive_romance_mode": "heavy_decay",
    "fugitive_decay_multiplier": 3,
    "cooling_off_conflict_threshold": 55,
}


def get_romance_rules(rules: dict) -> dict:
    merged = dict(DEFAULT_ROMANCE_RULES)
    romance_rules = dict(rules.get("romance", {}))
    family = rules.get("family", {})
    marriage = family.get("marriage", {})
    dating = family.get("dating", {})
    if "min_formal_dating_age" not in romance_rules and dating.get("min_age") is not None:
        merged["min_formal_dating_age"] = int(dating["min_age"])
    if "min_marriage_signal_age" not in romance_rules and marriage.get("min_age") is not None:
        merged["min_marriage_signal_age"] = int(marriage["min_age"])
    merged.update(romance_rules)
    return merged


def build_default_romance_state(rules: dict | None = None) -> RomanceState:
    _ = get_romance_rules(rules or {})
    state = RomanceState()
    state.romance_summary = {
        "status": "single",
        "candidate_count": 0,
        "current_partner_name": "",
        "years_single": 0,
        "years_in_current_relationship": 0,
    }
    return state


def blocks_normal_romance(legal: LegalState, rules: dict) -> bool:
    romance_rules = get_romance_rules(rules)
    if not romance_rules.get("legal_blocks_romance", True):
        return False
    return legal.is_in_prison or legal.is_fugitive


def can_formal_dating(age: int, rules: dict) -> bool:
    return age >= int(get_romance_rules(rules).get("min_formal_dating_age", 18))


def can_engagement(age: int, rules: dict) -> bool:
    return age >= int(get_romance_rules(rules).get("min_engagement_age", 20))


def can_marriage_signal(age: int, rules: dict) -> bool:
    return age >= int(get_romance_rules(rules).get("min_marriage_signal_age", 20))


def clamp_romance_values(data: dict) -> dict:
    for key in ("favor", "trust", "attraction", "conflict", "familiarity", "intimacy", "stability", "breakup_risk", "family_approval"):
        if key in data:
            data[key] = clamp_score(data[key])
    return data
