from typing import Any

from app.modules.career.models import CareerState

CAREER_RULE_NAMESPACE = "career"


def get_career_rules(rules: dict) -> dict[str, Any]:
    return rules.get(CAREER_RULE_NAMESPACE, {})


def get_career_paths(rules: dict) -> list[dict[str, Any]]:
    return list(get_career_rules(rules).get("paths", []))


def get_path_by_id(path_id: str, rules: dict) -> dict[str, Any] | None:
    for path in get_career_paths(rules):
        if path["id"] == path_id:
            return path
    return None


def build_default_career_state(rules: dict) -> CareerState:
    return CareerState(
        employment_status="student",
        career_path="",
        position_level="",
        annual_income=0.0,
        years_worked=0,
        is_retired=False,
        last_income_change=0.0,
        history=[],
    )


def get_available_paths_for_education(highest_level: str, rules: dict) -> list[str]:
    mapping = get_career_rules(rules).get("education_to_career_mapping", {})
    return list(mapping.get(highest_level, mapping.get("none", ["general_worker"])))


def select_career_path(highest_level: str, rules: dict) -> str:
    available = get_available_paths_for_education(highest_level, rules)
    default_path = str(get_career_rules(rules).get("default_path", available[0]))
    if default_path in available:
        return default_path
    return available[-1]


def get_education_income_multiplier(highest_level: str, rules: dict) -> float:
    multipliers = get_career_rules(rules).get("education_income_multiplier", {})
    return float(multipliers.get(highest_level, multipliers.get("none", 1.0)))


def calculate_annual_income(path: dict[str, Any], years_worked: int, highest_level: str, rules: dict) -> float:
    base = float(path["base_annual_income"])
    growth = float(path.get("income_growth_per_year", 0.0))
    multiplier = get_education_income_multiplier(highest_level, rules)
    return (base + growth * years_worked) * multiplier


def resolve_position_level(path: dict[str, Any], years_worked: int) -> str:
    levels = list(path.get("position_levels", ["junior"]))
    if years_worked >= 10:
        return levels[-1]
    if years_worked >= 3 and len(levels) > 1:
        return levels[min(1, len(levels) - 1)]
    return levels[0]
