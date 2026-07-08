from typing import Any

from pydantic import BaseModel, Field


class CareerState(BaseModel):
    employment_status: str = "student"
    career_path: str = ""
    position_level: str = ""
    annual_income: float = 0.0
    years_worked: int = 0
    is_retired: bool = False
    last_income_change: float = 0.0
    history: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_life_state_dict(cls, career_data: dict[str, Any], rules: dict | None = None) -> "CareerState":
        if not career_data or "employment_status" not in career_data:
            from app.modules.career.rules import build_default_career_state

            return build_default_career_state(rules or {})
        payload = dict(career_data)
        if "annual_income" not in payload and "income" in payload:
            payload["annual_income"] = float(payload["income"])
        return cls.model_validate(payload)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()
