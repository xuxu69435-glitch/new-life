from app.modules.legal.models import LegalState


def get_legal_rules(rules: dict) -> dict:
    return rules.get("legal", {})


def build_default_legal_state(rules: dict | None = None) -> LegalState:
    return LegalState()


def blocks_normal_education(legal: LegalState, rules: dict) -> bool:
    legal_rules = get_legal_rules(rules)
    if legal_rules.get("prison_blocks_normal_life", True) and legal.is_in_prison:
        return True
    if legal_rules.get("fugitive_blocks_normal_work", True) and legal.is_fugitive:
        return True
    return legal.education_locked


def blocks_normal_career(legal: LegalState, rules: dict) -> bool:
    legal_rules = get_legal_rules(rules)
    if legal_rules.get("prison_blocks_normal_life", True) and legal.is_in_prison:
        return True
    if legal_rules.get("fugitive_blocks_normal_work", True) and legal.is_fugitive:
        return True
    if legal.is_under_supervision and legal_rules.get("supervision_blocks_normal_work", True):
        return True
    return legal.normal_job_locked or legal.career_locked


def blocks_normal_random_events(legal: LegalState) -> bool:
    return legal.is_in_prison or legal.is_fugitive or legal.is_under_supervision


def blocks_family_progression(legal: LegalState) -> bool:
    return legal.is_in_prison or legal.is_fugitive
