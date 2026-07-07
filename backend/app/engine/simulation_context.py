from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.rng import ServerRandom


class SimulationEventType(str, Enum):
    ATTRIBUTE_CHANGE_REQUESTED = "AttributeChangeRequested"
    HEALTH_CHANGE_REQUESTED = "HealthChangeRequested"
    HEALTH_WARNING_CREATED = "HealthWarningCreated"
    HEALTH_STATE_UPDATE_REQUESTED = "HealthStateUpdateRequested"
    RANDOM_EVENT_TRIGGERED = "RandomEventTriggered"
    NATURAL_DEATH_CANDIDATE_CREATED = "NaturalDeathCandidateCreated"
    DIRECT_DEATH_CANDIDATE_CREATED = "DirectDeathCandidateCreated"
    INCOME_CHANGE_REQUESTED = "IncomeChangeRequested"
    FAMILY_RELATION_CHANGE_REQUESTED = "FamilyRelationChangeRequested"
    INHERITANCE_REQUESTED = "InheritanceRequested"
    NARRATIVE_REQUESTED = "NarrativeRequested"
    LIFE_STAGE_CHANGED = "LifeStageChanged"
    ASSET_CHANGE_REQUESTED = "AssetChangeRequested"


class LifeState(BaseModel):
    life_id: str
    person_id: str
    age: int = 0
    life_stage: str = "infant"
    is_dead: bool = False
    death_reason: str | None = None
    attributes: dict[str, int] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    family: dict[str, Any] = Field(default_factory=dict)
    education: dict[str, Any] = Field(default_factory=dict)
    career: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, float] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    rule_version: str = "v1"


class SimulationEvent(BaseModel):
    event_type: SimulationEventType
    source_module: str
    payload: dict[str, Any] = Field(default_factory=dict)


class YearResult(BaseModel):
    life_id: str
    age_before: int
    age_after: int
    is_dead: bool
    death_reason: str | None = None
    death_type: str | None = None
    changed_attributes: dict[str, int] = Field(default_factory=dict)
    changed_health: dict[str, int] = Field(default_factory=dict)
    changed_assets: dict[str, float] = Field(default_factory=dict)
    health_score_before: int | None = None
    health_score_after: int | None = None
    health_level_before: str | None = None
    health_level_after: str | None = None
    health_score_delta: int = 0
    new_health_warnings: list[str] = Field(default_factory=list)
    natural_death_candidate_created: bool = False
    occurred_events: list[SimulationEvent] = Field(default_factory=list)
    narrative_text: str = ""
    next_available_choices: list[dict[str, Any]] = Field(default_factory=list)


class SimulationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: LifeState
    player_choices: dict[str, Any] = Field(default_factory=dict)
    rule_version: str
    rng: ServerRandom
    event_bus: Any
    result_collector: Any
    rules: dict[str, Any] = Field(default_factory=dict)
