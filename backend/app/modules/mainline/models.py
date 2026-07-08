from typing import Any

from pydantic import BaseModel, Field


class MainlineState(BaseModel):
    current_chapter: str = "infant"
    current_stage: str = "infant"
    active_tasks: list[str] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    expired_tasks: list[str] = Field(default_factory=list)
    task_progress: dict[str, Any] = Field(default_factory=dict)
    chapter_history: list[dict[str, Any]] = Field(default_factory=list)
    last_mainline_change: str = ""
    mainline_flags: dict[str, Any] = Field(default_factory=dict)
    current_guidance_text: str = ""
    active_mainline_event: dict[str, Any] | None = None

    @classmethod
    def from_life_state_dict(cls, data: dict[str, Any] | None) -> "MainlineState":
        if not data:
            return cls()
        return cls.model_validate(data)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()
