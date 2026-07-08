from typing import Any

from pydantic import BaseModel, Field


class AchievementDefinition(BaseModel):
    achievement_id: str
    title: str
    description: str
    category: str
    tier: str = "bronze"
    trigger_conditions: dict[str, Any] = Field(default_factory=dict)
    progress_conditions: dict[str, Any] = Field(default_factory=dict)
    unlock_conditions: dict[str, Any] = Field(default_factory=dict)
    rewards: list[dict[str, Any]] = Field(default_factory=list)
    points: int = 0
    hidden: bool = False
    repeatable: bool = False
    milestone: bool = False
    narrative_text: str = ""
    implementation_status: str = "active"


class AchievementLibraryV1(BaseModel):
    version: str
    source: str = "achievement_system_v1"
    achievement_count: int = 0
    achievements: list[AchievementDefinition]

    def by_id(self) -> dict[str, AchievementDefinition]:
        return {item.achievement_id: item for item in self.achievements}

    def active_achievements(self) -> list[AchievementDefinition]:
        return [item for item in self.achievements if item.implementation_status == "active"]
