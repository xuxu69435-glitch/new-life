from typing import Any

from pydantic import BaseModel, Field

from app.rules.models import RandomEventRule


class RandomEventEffect(BaseModel):
    type: str
    target: str = ""
    value: int | float | str | bool = 0
    reason: str = ""
    source_event_id: str = ""
    source_event_name: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)


class RandomEventDefinition(RandomEventRule):
    """Random event definition used by the random_events module."""

    label: str | None = None

    def display_name(self) -> str:
        return self.name or self.label or self.id

    def normalized_effects(self) -> list[RandomEventEffect]:
        return [RandomEventEffect.model_validate(dict(effect)) for effect in self.effects]

    def to_event_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.id,
            "name": self.display_name(),
            "category": self.category,
            "narrative_text": self.narrative_text,
        }
