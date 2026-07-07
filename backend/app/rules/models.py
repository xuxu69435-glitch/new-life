from typing import Any

from pydantic import BaseModel, Field


class RandomEventRule(BaseModel):
    id: str
    name: str
    category: str
    stage: str = "any"
    probability: float
    direct_death: bool = False
    weight: float = 1.0
    conditions: dict[str, Any] = Field(default_factory=dict)
    effects: dict[str, Any] = Field(default_factory=dict)
    narrative_text: str = ""
    death_reason: str | None = None


class RuleSetSummary(BaseModel):
    version: str
    life_stage_count: int
    random_event_count: int
    direct_death_event_count: int
    direct_death_probability_total: float
    direct_death_probability_limit: float
    inheritance_tax_rate: float
