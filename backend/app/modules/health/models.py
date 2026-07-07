from typing import Any

from pydantic import BaseModel, Field


NO_WARNING_YET = 999


class HealthState(BaseModel):
    health_score: int = 100
    health_level: str = "excellent"
    diseases: list[str] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    natural_life_floor: int = 90
    natural_death_eligible_age: int = 90
    last_health_change: int = 0
    years_with_disease_warning: int = NO_WARNING_YET
    years_with_decline_warning: int = NO_WARNING_YET
    last_disease_warning_age: int | None = None
    last_decline_warning_age: int | None = None
    physical: int = 100
    mental: int = 100

    @classmethod
    def from_life_state_dict(cls, health_data: dict[str, Any], rules: dict) -> "HealthState":
        from app.modules.health.rules import (
            build_default_health_state,
            resolve_health_level,
        )

        score_config = rules.get("health_lifetime", {}).get("health_score", {})
        initial_score = int(score_config.get("initial", 100))
        score = int(health_data.get("health_score", health_data.get("physical", initial_score)))

        payload = {
            "health_score": score,
            "health_level": health_data.get("health_level"),
            "diseases": list(health_data.get("diseases", [])),
            "warnings": list(health_data.get("warnings", [])),
            "natural_life_floor": health_data.get("natural_life_floor"),
            "natural_death_eligible_age": health_data.get("natural_death_eligible_age"),
            "last_health_change": int(health_data.get("last_health_change", 0)),
            "years_with_disease_warning": int(
                health_data.get("years_with_disease_warning", NO_WARNING_YET)
            ),
            "years_with_decline_warning": int(
                health_data.get("years_with_decline_warning", NO_WARNING_YET)
            ),
            "last_disease_warning_age": health_data.get("last_disease_warning_age"),
            "last_decline_warning_age": health_data.get("last_decline_warning_age"),
            "physical": int(health_data.get("physical", score)),
            "mental": int(health_data.get("mental", score)),
        }

        state = cls.model_validate(payload)
        if not payload["health_level"]:
            level_rule = resolve_health_level(state.health_score, rules)
            state.health_level = level_rule["name"]
            state.natural_life_floor = int(level_rule["natural_life_floor"])
            state.natural_death_eligible_age = int(level_rule["natural_death_eligible_age"])
        else:
            if payload["natural_life_floor"] is None or payload["natural_death_eligible_age"] is None:
                level_rule = resolve_health_level(state.health_score, rules)
                state.natural_life_floor = int(level_rule["natural_life_floor"])
                state.natural_death_eligible_age = int(level_rule["natural_death_eligible_age"])
            else:
                state.natural_life_floor = int(payload["natural_life_floor"])
                state.natural_death_eligible_age = int(payload["natural_death_eligible_age"])

        if not health_data:
            return build_default_health_state(rules)
        return state

    def to_life_state_dict(self) -> dict[str, Any]:
        return {
            "health_score": self.health_score,
            "health_level": self.health_level,
            "physical": self.physical,
            "mental": self.mental,
            "diseases": list(self.diseases),
            "warnings": list(self.warnings),
            "natural_life_floor": self.natural_life_floor,
            "natural_death_eligible_age": self.natural_death_eligible_age,
            "last_health_change": self.last_health_change,
            "years_with_disease_warning": self.years_with_disease_warning,
            "years_with_decline_warning": self.years_with_decline_warning,
            "last_disease_warning_age": self.last_disease_warning_age,
            "last_decline_warning_age": self.last_decline_warning_age,
        }

    def clamp_score(self, rules: dict) -> None:
        score_config = rules.get("health_lifetime", {}).get("health_score", {})
        minimum = int(score_config.get("min", 0))
        maximum = int(score_config.get("max", 100))
        self.health_score = max(minimum, min(maximum, self.health_score))
        self.physical = self.health_score
        self.mental = self.health_score
