from typing import Any

from app.modules.health.models import HealthState
from app.modules.health.rules import resolve_health_level


def apply_post_health_changes(
    health_data: dict[str, Any],
    deltas: dict[str, int],
    rules: dict,
) -> dict[str, Any]:
    if not deltas:
        return dict(health_data)

    health_state = HealthState.from_life_state_dict(health_data, rules)
    for key, delta in deltas.items():
        if key == "health_score":
            health_state.health_score += int(delta)
            health_state.last_health_change = int(delta)
        elif hasattr(health_state, key):
            current = getattr(health_state, key)
            if isinstance(current, int):
                setattr(health_state, key, current + int(delta))

    health_state.clamp_score(rules)
    level_rule = resolve_health_level(health_state.health_score, rules)
    health_state.health_level = level_rule["name"]
    health_state.natural_life_floor = int(level_rule["natural_life_floor"])
    health_state.natural_death_eligible_age = int(level_rule["natural_death_eligible_age"])
    health_state.physical = health_state.health_score
    health_state.mental = health_state.health_score
    return health_state.to_life_state_dict()
