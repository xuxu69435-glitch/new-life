from typing import Any

from pydantic import BaseModel, Field

from app.rules.models import RandomEventRule


class RandomEventDefinition(RandomEventRule):
    """Random event definition used by the random_events module."""

    label: str | None = None

    def display_name(self) -> str:
        return self.name or self.label or self.id

    def to_event_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.id,
            "name": self.display_name(),
            "category": self.category,
            "narrative_text": self.narrative_text,
        }
