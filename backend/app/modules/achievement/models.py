from typing import Any

from pydantic import BaseModel, Field


class AchievementState(BaseModel):
    unlocked_achievements: list[str] = Field(default_factory=list)
    achievement_progress: dict[str, Any] = Field(default_factory=dict)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    newly_unlocked_this_year: list[str] = Field(default_factory=list)
    achievement_history: list[dict[str, Any]] = Field(default_factory=list)
    achievement_points: int = 0
    last_achievement_change: str = ""
    achievement_flags: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_life_state_dict(cls, data: dict[str, Any] | None) -> "AchievementState":
        if not data:
            return cls()
        return cls.model_validate(data)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def has_milestone(self, milestone_id: str) -> bool:
        return any(item.get("milestone_id") == milestone_id for item in self.milestones)
