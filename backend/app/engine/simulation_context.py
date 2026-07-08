from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.rng import ServerRandom


class SimulationEventType(str, Enum):
    ATTRIBUTE_CHANGE_REQUESTED = "AttributeChangeRequested"
    EDUCATION_PROGRESSED = "EducationProgressed"
    EDUCATION_STATE_UPDATE_REQUESTED = "EducationStateUpdateRequested"
    CAREER_PROGRESSED = "CareerProgressed"
    CAREER_STATE_UPDATE_REQUESTED = "CareerStateUpdateRequested"
    HEALTH_CHANGE_REQUESTED = "HealthChangeRequested"
    HEALTH_WARNING_CREATED = "HealthWarningCreated"
    HEALTH_STATE_UPDATE_REQUESTED = "HealthStateUpdateRequested"
    RANDOM_EVENT_TRIGGERED = "RandomEventTriggered"
    NATURAL_DEATH_CANDIDATE_CREATED = "NaturalDeathCandidateCreated"
    DIRECT_DEATH_CANDIDATE_CREATED = "DirectDeathCandidateCreated"
    INCOME_CHANGE_REQUESTED = "IncomeChangeRequested"
    FAMILY_RELATION_CHANGE_REQUESTED = "FamilyRelationChangeRequested"
    FAMILY_STATE_UPDATE_REQUESTED = "FamilyStateUpdateRequested"
    RELATIONSHIP_STATUS_CHANGE_REQUESTED = "RelationshipStatusChangeRequested"
    PARTNER_CREATED = "PartnerCreated"
    MARRIAGE_CREATED = "MarriageCreated"
    CHILD_CREATED = "ChildCreated"
    FAMILY_PRESSURE_CHANGE_REQUESTED = "FamilyPressureChangeRequested"
    PARENT_RELATION_CHANGE_REQUESTED = "ParentRelationChangeRequested"
    PARTNER_RELATION_CHANGE_REQUESTED = "PartnerRelationChangeRequested"
    CHILD_RELATION_CHANGE_REQUESTED = "ChildRelationChangeRequested"
    FAMILY_HISTORY_RECORDED = "FamilyHistoryRecorded"
    DIVORCE_CREATED = "DivorceCreated"
    INHERITANCE_REQUESTED = "InheritanceRequested"
    NARRATIVE_REQUESTED = "NarrativeRequested"
    FLAG_SET_REQUESTED = "FlagSetRequested"
    LIFE_STAGE_CHANGED = "LifeStageChanged"
    ASSET_CHANGE_REQUESTED = "AssetChangeRequested"
    UNSUPPORTED_EFFECT_RECORDED = "UnsupportedEffectRecorded"
    RANDOM_EVENT_CHOICE_APPLIED = "RandomEventChoiceApplied"
    LEGAL_STATE_UPDATE_REQUESTED = "LegalStateUpdateRequested"
    LEGAL_EVENT_TRIGGERED = "LegalEventTriggered"
    LEGAL_CHOICE_APPLIED = "LegalChoiceApplied"
    MAINLINE_STATE_UPDATE_REQUESTED = "MainlineStateUpdateRequested"


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
    assets: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    pending_random_event: dict[str, Any] | None = None
    legal: dict[str, Any] = Field(default_factory=dict)
    pending_legal_event: dict[str, Any] | None = None
    mainline: dict[str, Any] = Field(default_factory=dict)
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
    direct_death_candidate_created: bool = False
    triggered_random_events: list[dict[str, Any]] = Field(default_factory=list)
    random_event_attribute_changes: dict[str, int] = Field(default_factory=dict)
    random_event_health_changes: dict[str, int] = Field(default_factory=dict)
    random_event_asset_changes: dict[str, float] = Field(default_factory=dict)
    inheritance_result: dict[str, Any] | None = None
    education_stage_before: str | None = None
    education_stage_after: str | None = None
    education_graduated_this_year: bool = False
    education_changes: dict[str, Any] = Field(default_factory=dict)
    career_status_before: str | None = None
    career_status_after: str | None = None
    career_path: str | None = None
    position_level: str | None = None
    annual_income: float = 0.0
    career_income_change: float = 0.0
    occurred_events: list[SimulationEvent] = Field(default_factory=list)
    narrative_text: str = ""
    next_available_choices: list[dict[str, Any]] = Field(default_factory=list)
    pending_random_event: dict[str, Any] | None = None
    unsupported_random_event_effects: list[dict[str, Any]] = Field(default_factory=list)
    random_event_choice_result: dict[str, Any] | None = None
    relationship_status_before: str | None = None
    relationship_status_after: str | None = None
    partner_relation_delta: int = 0
    parent_child_relation_delta: int = 0
    family_pressure_delta: int = 0
    married_this_year: bool = False
    child_born_this_year: bool = False
    children_count_delta: int = 0
    family_history_records: list[dict[str, Any]] = Field(default_factory=list)
    family_changes: dict[str, Any] = Field(default_factory=dict)
    pending_legal_event: dict[str, Any] | None = None
    legal_changes: dict[str, Any] = Field(default_factory=dict)
    active_mainline_tasks: list[dict[str, Any]] = Field(default_factory=list)
    completed_mainline_tasks_this_year: list[str] = Field(default_factory=list)
    failed_mainline_tasks_this_year: list[str] = Field(default_factory=list)
    expired_mainline_tasks_this_year: list[str] = Field(default_factory=list)
    mainline_rewards: list[dict[str, Any]] = Field(default_factory=list)
    mainline_narrative: list[str] = Field(default_factory=list)
    current_guidance_text: str = ""
    mainline_changes: dict[str, Any] = Field(default_factory=dict)
    narrative_result: dict[str, Any] | None = None
    annual_summary_text: str = ""
    major_event_texts: list[str] = Field(default_factory=list)
    display_sections: list[dict[str, Any]] = Field(default_factory=list)


class SimulationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: LifeState
    player_choices: dict[str, Any] = Field(default_factory=dict)
    rule_version: str
    rng: ServerRandom
    event_bus: Any
    result_collector: Any
    rules: dict[str, Any] = Field(default_factory=dict)
