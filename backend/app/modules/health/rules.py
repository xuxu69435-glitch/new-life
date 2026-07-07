from typing import Any

from app.modules.health.models import HealthState, NO_WARNING_YET

HEALTH_RULE_NAMESPACE = "health_lifetime"


def get_health_rules(rules: dict) -> dict[str, Any]:
    return rules.get(HEALTH_RULE_NAMESPACE, {})


def get_health_score_config(rules: dict) -> dict[str, Any]:
    return get_health_rules(rules).get("health_score", {})


def get_health_levels(rules: dict) -> list[dict[str, Any]]:
    return list(get_health_rules(rules).get("health_levels", []))


def resolve_health_level(score: int, rules: dict) -> dict[str, Any]:
    for level in get_health_levels(rules):
        if int(level["min_score"]) <= score <= int(level["max_score"]):
            return level
    levels = get_health_levels(rules)
    if not levels:
        raise ValueError("Health level rules are missing.")
    return levels[-1]


def build_default_health_state(rules: dict) -> HealthState:
    defaults = dict(rules.get("default_health", {}))
    score_config = get_health_score_config(rules)
    score = int(defaults.get("health_score", score_config.get("initial", 100)))
    level_rule = resolve_health_level(score, rules)
    return HealthState(
        health_score=score,
        health_level=level_rule["name"],
        diseases=list(defaults.get("diseases", [])),
        warnings=list(defaults.get("warnings", [])),
        natural_life_floor=int(level_rule["natural_life_floor"]),
        natural_death_eligible_age=int(level_rule["natural_death_eligible_age"]),
        last_health_change=0,
        years_with_disease_warning=int(defaults.get("years_with_disease_warning", NO_WARNING_YET)),
        years_with_decline_warning=int(defaults.get("years_with_decline_warning", NO_WARNING_YET)),
        last_disease_warning_age=defaults.get("last_disease_warning_age"),
        last_decline_warning_age=defaults.get("last_decline_warning_age"),
        physical=int(defaults.get("physical", score)),
        mental=int(defaults.get("mental", score)),
    )


def get_annual_decay(life_stage: str, rules: dict) -> int:
    health_rules = get_health_rules(rules)
    decay_by_stage = health_rules.get("annual_decay_by_stage", {})
    return int(decay_by_stage.get(life_stage, health_rules.get("default_annual_decay", 0)))


def get_rest_focus_recovery(rules: dict) -> int:
    return int(get_health_rules(rules).get("rest_focus_recovery", 1))


def get_warning_config(rules: dict) -> dict[str, Any]:
    return get_health_rules(rules).get("warnings", {})


def get_disease_pool(rules: dict) -> list[dict[str, Any]]:
    return list(get_health_rules(rules).get("disease_pool", []))


def get_longevity_config(rules: dict) -> dict[str, Any]:
    return get_health_rules(rules).get("longevity", {})


def get_natural_death_config(rules: dict) -> dict[str, Any]:
    return get_health_rules(rules).get("natural_death", {})


def can_enter_high_longevity(health_level: str, rules: dict) -> bool:
    for level in get_health_levels(rules):
        if level["name"] == health_level:
            return bool(level.get("can_enter_high_longevity", False))
    return False


def calculate_natural_death_probability(age: int, health_level: str, rules: dict) -> float:
    natural_death = get_natural_death_config(rules)
    longevity = get_longevity_config(rules)
    high_age = int(longevity.get("high_longevity_check_age", 90))

    if age >= high_age and can_enter_high_longevity(health_level, rules):
        years_after = age - high_age
        probability = float(natural_death.get("base_probability_at_90", 0.05))
        probability += years_after * float(
            natural_death.get("probability_increment_per_year_after_90", 0.0)
        )
        return min(probability, float(natural_death.get("max_probability", 1.0)))

    by_level = natural_death.get("pre_longevity_probability_by_level", {})
    return float(by_level.get(health_level, 0.0))


def has_natural_death_foreshadowing(age: int, health_state: HealthState, rules: dict) -> bool:
    warning_config = get_warning_config(rules)
    disease_window = int(warning_config.get("disease_warning_years", 3))

    if health_state.last_disease_warning_age is not None:
        years_since = age - health_state.last_disease_warning_age
        if years_since < disease_window:
            return True

    if warning_config.get("require_decline_warning_last_year", True):
        if health_state.last_decline_warning_age is not None:
            if age - health_state.last_decline_warning_age == 1:
                return True

    return False


def sync_warning_counters(age: int, health_state: HealthState) -> None:
    if health_state.last_disease_warning_age is None:
        health_state.years_with_disease_warning = NO_WARNING_YET
    else:
        health_state.years_with_disease_warning = age - health_state.last_disease_warning_age

    if health_state.last_decline_warning_age is None:
        health_state.years_with_decline_warning = NO_WARNING_YET
    else:
        health_state.years_with_decline_warning = age - health_state.last_decline_warning_age
