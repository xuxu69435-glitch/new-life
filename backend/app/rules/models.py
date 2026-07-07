from typing import Any

from pydantic import BaseModel, Field, field_validator


class RandomEventRule(BaseModel):
    id: str
    name: str
    category: str
    stage: str = "any"
    probability: float
    direct_death: bool = False
    weight: float = 1.0
    conditions: dict[str, Any] = Field(default_factory=dict)
    effects: list[dict[str, Any]] = Field(default_factory=list)
    narrative_text: str = ""
    death_reason: str | None = None

    @field_validator("effects", mode="before")
    @classmethod
    def normalize_effects(cls, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, dict):
            if not value:
                return []
            raise ValueError("Random event effects must be a list.")
        if not isinstance(value, list):
            raise ValueError("Random event effects must be a list.")
        return value


class RuleSetSummary(BaseModel):
    version: str
    life_stage_count: int
    random_event_count: int
    direct_death_event_count: int
    direct_death_probability_total: float
    direct_death_probability_limit: float
    inheritance_tax_rate: float
