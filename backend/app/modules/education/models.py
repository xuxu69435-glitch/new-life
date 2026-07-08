from typing import Any

from pydantic import BaseModel, Field


class EducationState(BaseModel):
    current_stage: str = "preschool"
    current_track: str = "standard"
    school_year: int = 0
    highest_level: str = "none"
    is_enrolled: bool = False
    is_graduated: bool = False
    graduation_age: int | None = None
    education_score: int = 0
    history: list[dict[str, Any]] = Field(default_factory=list)
    last_education_change: str = ""

    @classmethod
    def from_life_state_dict(cls, education_data: dict[str, Any], rules: dict) -> "EducationState":
        if not education_data:
            from app.modules.education.rules import build_default_education_state

            return build_default_education_state(rules)
        payload = dict(education_data)
        if "current_track" not in payload and "track" in payload:
            payload["current_track"] = payload["track"]
        return cls.model_validate(payload)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()
