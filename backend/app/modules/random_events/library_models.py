from typing import Any, Literal

from pydantic import BaseModel, Field

ImplementationStatus = Literal["active", "partial", "planned"]
PoolType = Literal["normal", "direct_death", "system", "social"]
RepeatPolicy = Literal["once", "repeatable", "max_once"]


class AgeRange(BaseModel):
    min: int = 0
    max: int = 120


class V1EventChoice(BaseModel):
    choice_id: str
    label: str
    choice_text: str
    effects_text: str
    effects: list[dict[str, Any]] = Field(default_factory=list)
    requires_confirmation: bool = False
    is_system_choice: bool = False


class V1EventDefinition(BaseModel):
    event_id: str
    name: str
    category: str
    age_range: AgeRange = Field(default_factory=AgeRange)
    life_stages: list[str] = Field(default_factory=list)
    trigger_conditions_text: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)
    weight_tier: str = ""
    weight: int = 0
    repeat_policy: str = "once"
    cooldown_years: int | None = None
    event_text: str = ""
    choices: list[V1EventChoice] = Field(default_factory=list)
    may_cause_death: bool = False
    affects_future: bool = False
    implementation_status: ImplementationStatus = "planned"
    unsupported_reasons: list[str] = Field(default_factory=list)
    source_text: str = ""
    pool_type: PoolType = "normal"

    def is_drawable(self) -> bool:
        return self.implementation_status in {"active", "partial"}

    def to_pending_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "category": self.category,
            "event_text": self.event_text,
            "choices": [
                {
                    "choice_id": choice.choice_id,
                    "label": choice.label,
                    "choice_text": choice.choice_text,
                    "requires_confirmation": choice.requires_confirmation,
                    "is_system_choice": choice.is_system_choice,
                }
                for choice in self.choices
            ],
        }


class PendingRandomEvent(BaseModel):
    event_id: str
    name: str
    category: str
    event_text: str
    choices: list[dict[str, Any]] = Field(default_factory=list)
    year_age: int = 0
    pool_type: PoolType = "normal"


class RandomEventLibraryV1(BaseModel):
    version: str = "v1"
    source: str = ""
    event_count: int = 0
    events: list[V1EventDefinition] = Field(default_factory=list)

    def by_id(self) -> dict[str, V1EventDefinition]:
        return {event.event_id: event for event in self.events}


class SocialEventDefinition(V1EventDefinition):
    title: str = ""
    sub_category: str = ""
    creates_person: bool = False
    target_relationship_types: list[str] = Field(default_factory=list)
    repeatable: bool = True


class SocialEventLibraryV1(BaseModel):
    version: str = "v1"
    source: str = ""
    event_count: int = 0
    events: list[SocialEventDefinition] = Field(default_factory=list)

    def by_id(self) -> dict[str, SocialEventDefinition]:
        return {event.event_id: event for event in self.events}
