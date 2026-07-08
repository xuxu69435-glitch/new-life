from typing import Any

from pydantic import BaseModel, Field


class LegalEventChoice(BaseModel):
    choice_id: str
    label: str
    choice_text: str
    effects_text: str = ""
    requires_confirmation: bool = False
    is_system_choice: bool = False
    implementation_status: str = "active"


class LegalEventDefinition(BaseModel):
    event_id: str
    name: str
    pool_type: str
    event_text: str
    choices: list[LegalEventChoice] = Field(default_factory=list)
    implementation_status: str = "active"
    trigger_conditions_text: str = ""

    def to_pending_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "event_text": self.event_text,
            "pool_type": self.pool_type,
            "choices": [
                {
                    "choice_id": c.choice_id,
                    "label": c.label,
                    "choice_text": c.choice_text,
                    "requires_confirmation": c.requires_confirmation,
                    "is_system_choice": c.is_system_choice,
                    "implementation_status": c.implementation_status,
                }
                for c in self.choices
                if c.implementation_status == "active"
            ],
        }


class LegalEventLibraryV1(BaseModel):
    version: str = "v1"
    source: str = ""
    event_count: int = 0
    events: list[LegalEventDefinition] = Field(default_factory=list)

    def by_id(self) -> dict[str, LegalEventDefinition]:
        return {event.event_id: event for event in self.events}
