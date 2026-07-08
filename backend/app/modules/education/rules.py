from typing import Any

from app.modules.education.models import EducationState

EDUCATION_RULE_NAMESPACE = "education"


def get_education_rules(rules: dict) -> dict[str, Any]:
    return rules.get(EDUCATION_RULE_NAMESPACE, {})


def get_education_stages(rules: dict) -> list[dict[str, Any]]:
    return list(get_education_rules(rules).get("stages", []))


def get_none_stage(rules: dict) -> dict[str, Any]:
    return get_education_rules(rules).get("none_stage", {"id": "none", "min_age": 22, "max_age": 200})


def resolve_stage_for_age(age: int, rules: dict) -> dict[str, Any] | None:
    for stage in get_education_stages(rules):
        if int(stage["min_age"]) <= age <= int(stage["max_age"]):
            return stage
    none_stage = get_none_stage(rules)
    if int(none_stage.get("min_age", 999)) <= age <= int(none_stage.get("max_age", 999)):
        return none_stage
    return None


def build_default_education_state(rules: dict) -> EducationState:
    education_rules = get_education_rules(rules)
    stage = resolve_stage_for_age(0, rules) or get_education_stages(rules)[0]
    return EducationState(
        current_stage=stage["id"],
        current_track=str(education_rules.get("default_track", "standard")),
        school_year=1 if stage["id"] != "none" else 0,
        highest_level="none",
        is_enrolled=stage["id"] != "none",
        is_graduated=False,
        graduation_age=None,
        education_score=0,
        history=[],
        last_education_change="initialized",
    )
