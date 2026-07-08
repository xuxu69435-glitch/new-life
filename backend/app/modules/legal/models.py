from typing import Any

from pydantic import BaseModel, Field


class LegalState(BaseModel):
    is_in_prison: bool = False
    sentence_total_years: int = 0
    sentence_remaining_years: int = 0
    years_served: int = 0
    rehabilitation_progress: int = 0
    consecutive_rehabilitation_years: int = 0
    sentence_reduction_counter: int = 0
    escape_attempt_count: int = 0
    escape_succeeded: bool = False
    is_fugitive: bool = False
    fugitive_years: int = 0
    recapture_risk_modifier: float = 1.0
    has_criminal_record: bool = False
    is_under_supervision: bool = False
    supervision_remaining_years: int = 0
    years_after_release: int = 0
    release_age: int | None = None
    release_year: int | None = None
    post_release_employment_penalty_year: int = 0
    research_job_ban_remaining_years: int = 0
    civil_service_banned: bool = False
    normal_job_locked: bool = False
    education_locked: bool = False
    career_locked: bool = False
    startup_restriction_active: bool = False
    rehabilitation_gain_multiplier: float = 1.0
    last_legal_event: str = ""
    legal_history: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_life_state_dict(cls, data: dict[str, Any] | None) -> "LegalState":
        if not data:
            return cls()
        return cls.model_validate(data)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def employment_penalty_rate(self, rules: dict) -> float:
        legal_rules = rules.get("legal", {})
        penalties = legal_rules.get("employment_penalty_by_year", {})
        year_key = str(self.post_release_employment_penalty_year)
        if self.post_release_employment_penalty_year <= 0:
            return 0.0
        if self.post_release_employment_penalty_year >= 6:
            return float(penalties.get("6", 0.0))
        return float(penalties.get(year_key, 0.0))
