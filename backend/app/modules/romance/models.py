from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.modules.romance.constants import CANDIDATE_SOURCES, CANDIDATE_STATUSES, RELATIONSHIP_STATUSES


def clamp_score(value: int | float, *, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(value)))


class RomanticCandidate(BaseModel):
    candidate_id: str
    source_person_id: str = ""
    name: str
    age: int | None = None
    gender: str = "unknown"
    source: str = "system"
    status: str = "candidate"
    favor: int = 50
    trust: int = 40
    attraction: int = 45
    conflict: int = 0
    familiarity: int = 30
    created_age: int = 0
    last_interaction_age: int = 0
    tags: list[str] = Field(default_factory=list)
    personality_tag: str = ""
    background: str = ""
    from_social_relationship_id: str = ""
    notes: str = ""

    def clamp_values(self) -> "RomanticCandidate":
        self.favor = clamp_score(self.favor)
        self.trust = clamp_score(self.trust)
        self.attraction = clamp_score(self.attraction)
        self.conflict = clamp_score(self.conflict)
        self.familiarity = clamp_score(self.familiarity)
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.clamp_values().model_dump()


class RomanticRelationship(BaseModel):
    relationship_id: str
    candidate_id: str
    partner_name: str
    status: str = "none"
    favor: int = 50
    trust: int = 45
    intimacy: int = 40
    conflict: int = 0
    stability: int = 40
    started_age: int = 0
    last_changed_age: int = 0
    years_together: int = 0
    source: str = "system"
    tags: list[str] = Field(default_factory=list)
    engagement_intent: bool = False
    breakup_risk: int = 20
    family_approval: int = 50
    notes: str = ""

    def clamp_values(self) -> "RomanticRelationship":
        self.favor = clamp_score(self.favor)
        self.trust = clamp_score(self.trust)
        self.intimacy = clamp_score(self.intimacy)
        self.conflict = clamp_score(self.conflict)
        self.stability = clamp_score(self.stability)
        self.breakup_risk = clamp_score(self.breakup_risk)
        self.family_approval = clamp_score(self.family_approval)
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.clamp_values().model_dump()

    def is_active_romance(self) -> bool:
        return self.status in {"crush", "ambiguous", "dating", "cooling_off", "reconciled", "engagement_intent"}


class RomanceState(BaseModel):
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    current_relationship: dict[str, Any] | None = None
    relationship_history: list[dict[str, Any]] = Field(default_factory=list)
    romance_flags: dict[str, Any] = Field(default_factory=dict)
    romance_summary: dict[str, Any] = Field(default_factory=dict)
    new_candidates_this_year: list[str] = Field(default_factory=list)
    romance_changes_this_year: list[dict[str, Any]] = Field(default_factory=list)
    ended_relationships_this_year: list[str] = Field(default_factory=list)
    last_romance_change: dict[str, Any] | None = None
    years_single: int = 0
    years_in_current_relationship: int = 0

    @classmethod
    def from_life_state_dict(cls, data: dict[str, Any] | None) -> "RomanceState":
        if not data:
            return cls()
        return cls.model_validate(data)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def get_candidate_models(self) -> dict[str, RomanticCandidate]:
        return {
            str(item["candidate_id"]): RomanticCandidate.model_validate(item)
            for item in self.candidates
            if item.get("candidate_id")
        }

    def get_current_relationship(self) -> RomanticRelationship | None:
        if not self.current_relationship:
            return None
        return RomanticRelationship.model_validate(self.current_relationship)

    def clear_year_tracking(self) -> None:
        self.new_candidates_this_year = []
        self.romance_changes_this_year = []
        self.ended_relationships_this_year = []

    def active_candidate_count(self) -> int:
        return sum(
            1
            for item in self.candidates
            if item.get("status") in {"candidate", "crush", "ambiguous"}
        )

    def has_romantic_candidate(self) -> bool:
        return self.active_candidate_count() > 0

    def is_dating(self) -> bool:
        rel = self.get_current_relationship()
        return rel is not None and rel.status == "dating"

    def is_single(self) -> bool:
        rel = self.get_current_relationship()
        return rel is None or rel.status in {"none", "ended", "broken_up"}

    def upsert_candidate(self, candidate: RomanticCandidate) -> None:
        payload = candidate.to_dict()
        for index, item in enumerate(self.candidates):
            if item.get("candidate_id") == candidate.candidate_id:
                self.candidates[index] = payload
                return
        self.candidates.append(payload)

    def set_current_relationship(self, relationship: RomanticRelationship | None) -> None:
        self.current_relationship = relationship.to_dict() if relationship else None

    def record_history(self, entry: dict[str, Any]) -> None:
        self.relationship_history.append(entry)
        self.last_romance_change = entry

    def record_change(self, change: dict[str, Any]) -> None:
        self.romance_changes_this_year.append(change)

    def validate_statuses(self) -> None:
        for item in self.candidates:
            if str(item.get("source", "system")) not in CANDIDATE_SOURCES:
                item["source"] = "system"
            if str(item.get("status", "candidate")) not in CANDIDATE_STATUSES:
                item["status"] = "candidate"
        if self.current_relationship:
            status = str(self.current_relationship.get("status", "none"))
            if status not in RELATIONSHIP_STATUSES:
                self.current_relationship["status"] = "none"

    @staticmethod
    def new_candidate_id() -> str:
        return f"rc-{uuid4().hex[:12]}"

    @staticmethod
    def new_relationship_id() -> str:
        return f"rr-{uuid4().hex[:12]}"
