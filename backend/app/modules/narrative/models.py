from typing import Any

from pydantic import BaseModel, Field


class AnnualNarrativeInput(BaseModel):
    life_id: str
    age_before: int
    age_after: int
    life_stage: str
    is_dead: bool = False
    death_type: str | None = None
    death_reason: str | None = None
    triggered_random_events: list[dict[str, Any]] = Field(default_factory=list)
    pending_random_event: dict[str, Any] | None = None
    random_event_choice_result: dict[str, Any] | None = None
    education_changes: dict[str, Any] = Field(default_factory=dict)
    career_changes: dict[str, Any] = Field(default_factory=dict)
    family_changes: dict[str, Any] = Field(default_factory=dict)
    health_changes: dict[str, Any] = Field(default_factory=dict)
    asset_changes: dict[str, float] = Field(default_factory=dict)
    attribute_changes: dict[str, int] = Field(default_factory=dict)
    legal_changes: dict[str, Any] = Field(default_factory=dict)
    legal_before: dict[str, Any] = Field(default_factory=dict)
    pending_legal_event: dict[str, Any] | None = None
    mainline_changes: dict[str, Any] = Field(default_factory=dict)
    completed_tasks_this_year: list[str] = Field(default_factory=list)
    mainline_narrative: list[str] = Field(default_factory=list)
    inheritance_result: dict[str, Any] | None = None
    major_flags: dict[str, Any] = Field(default_factory=dict)
    married_this_year: bool = False
    child_born_this_year: bool = False
    relationship_status_before: str | None = None
    relationship_status_after: str | None = None
    social_changes: dict[str, Any] = Field(default_factory=dict)
    social_narrative: list[str] = Field(default_factory=list)
    romance_changes: dict[str, Any] = Field(default_factory=dict)
    romance_narrative: list[str] = Field(default_factory=list)


class DisplaySection(BaseModel):
    section_id: str
    title: str
    content: str


class AnnualNarrativeResult(BaseModel):
    summary_text: str
    opening_text: str
    major_event_texts: list[str] = Field(default_factory=list)
    module_texts: dict[str, list[str]] = Field(default_factory=dict)
    closing_text: str = ""
    tone: str = "normal"
    tags: list[str] = Field(default_factory=list)
    priority_events: list[dict[str, Any]] = Field(default_factory=list)
    display_sections: list[DisplaySection] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
