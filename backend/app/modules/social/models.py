from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.modules.social.constants import PERSON_ROLES, RELATIONSHIP_STATUSES, RELATIONSHIP_TYPES


def clamp_score(value: int | float, *, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(value)))


class SocialPerson(BaseModel):
    person_id: str
    name: str
    age: int | None = None
    gender: str = "unknown"
    role: str = "unknown"
    source: str = "system"
    is_active: bool = True
    created_age: int = 0
    last_seen_age: int = 0
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    personality_tag: str = ""
    ability_score: int = 50
    background: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class SocialRelationship(BaseModel):
    relationship_id: str
    person_id: str
    relationship_type: str
    closeness: int = 50
    trust: int = 50
    conflict: int = 0
    familiarity: int = 30
    status: str = "active"
    started_age: int = 0
    last_changed_age: int = 0
    source: str = "system"
    tags: list[str] = Field(default_factory=list)
    importance: int = 50
    last_interaction_age: int = 0
    notes: str = ""

    def clamp_values(self) -> "SocialRelationship":
        self.closeness = clamp_score(self.closeness)
        self.trust = clamp_score(self.trust)
        self.conflict = clamp_score(self.conflict)
        self.familiarity = clamp_score(self.familiarity)
        self.importance = clamp_score(self.importance)
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.clamp_values().model_dump()


class SocialState(BaseModel):
    persons: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    relationship_history: list[dict[str, Any]] = Field(default_factory=list)
    social_flags: dict[str, Any] = Field(default_factory=dict)
    social_summary: dict[str, Any] = Field(default_factory=dict)
    new_relationships_this_year: list[str] = Field(default_factory=list)
    changed_relationships_this_year: list[str] = Field(default_factory=list)
    removed_relationships_this_year: list[str] = Field(default_factory=list)
    last_social_change: dict[str, Any] | None = None

    @classmethod
    def from_life_state_dict(cls, data: dict[str, Any] | None) -> "SocialState":
        if not data:
            return cls()
        return cls.model_validate(data)

    def to_life_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def get_person_models(self) -> dict[str, SocialPerson]:
        return {
            str(item["person_id"]): SocialPerson.model_validate(item)
            for item in self.persons
            if item.get("person_id")
        }

    def get_relationship_models(self) -> dict[str, SocialRelationship]:
        return {
            str(item["relationship_id"]): SocialRelationship.model_validate(item)
            for item in self.relationships
            if item.get("relationship_id")
        }

    def clear_year_tracking(self) -> None:
        self.new_relationships_this_year = []
        self.changed_relationships_this_year = []
        self.removed_relationships_this_year = []

    def active_relationship_count(self) -> int:
        return sum(
            1
            for item in self.relationships
            if item.get("status") in {"active", "important"}
        )

    def friend_count(self) -> int:
        return sum(
            1
            for item in self.relationships
            if item.get("relationship_type") in {"friend", "best_friend"}
            and item.get("status") in {"active", "important"}
        )

    def has_relationship_type(self, relationship_type: str) -> bool:
        return any(
            item.get("relationship_type") == relationship_type
            and item.get("status") in {"active", "important"}
            for item in self.relationships
        )

    def count_relationship_type(self, relationship_type: str) -> int:
        return sum(
            1
            for item in self.relationships
            if item.get("relationship_type") == relationship_type
            and item.get("status") in {"active", "important", "distant"}
        )

    def upsert_person(self, person: SocialPerson) -> None:
        payload = person.to_dict()
        for index, item in enumerate(self.persons):
            if item.get("person_id") == person.person_id:
                self.persons[index] = payload
                return
        self.persons.append(payload)

    def upsert_relationship(self, relationship: SocialRelationship) -> None:
        payload = relationship.to_dict()
        for index, item in enumerate(self.relationships):
            if item.get("relationship_id") == relationship.relationship_id:
                self.relationships[index] = payload
                return
        self.relationships.append(payload)

    def record_history(self, entry: dict[str, Any]) -> None:
        self.relationship_history.append(entry)
        self.last_social_change = entry

    @staticmethod
    def new_person_id() -> str:
        return f"sp-{uuid4().hex[:12]}"

    @staticmethod
    def new_relationship_id() -> str:
        return f"sr-{uuid4().hex[:12]}"

    def validate_roles(self) -> None:
        for person in self.persons:
            role = str(person.get("role", "unknown"))
            if role not in PERSON_ROLES:
                person["role"] = "unknown"
        for relationship in self.relationships:
            rel_type = str(relationship.get("relationship_type", "other"))
            if rel_type not in RELATIONSHIP_TYPES:
                relationship["relationship_type"] = "other"
            status = str(relationship.get("status", "active"))
            if status not in RELATIONSHIP_STATUSES:
                relationship["status"] = "active"
