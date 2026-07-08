from typing import Any, Literal

from pydantic import BaseModel, Field

RelationshipStatus = Literal["single", "dating", "married", "divorced", "widowed"]


class FamilyMember(BaseModel):
    person_id: str
    name: str = ""
    relation: str = ""
    age: int = 0
    is_alive: bool = True
    playable: bool = False
    relation_score: int = 50
    generation: int = 1
    ability_score: int = 50


class FamilyState(BaseModel):
    parents: list[FamilyMember] = Field(default_factory=list)
    spouse: FamilyMember | None = None
    children: list[FamilyMember] = Field(default_factory=list)
    generation: int = 1
    family_tree_id: str = ""
    family_pressure: int = 30
    parent_child_relation: int = 70
    father_relation: int = 65
    mother_relation: int = 65
    partner_relation: int = 50
    relationship_status: RelationshipStatus = "single"
    dating_partner: FamilyMember | None = None
    marriage_year: int | None = None
    children_count: int = 0
    family_history: list[dict[str, Any]] = Field(default_factory=list)
    last_family_change: str = ""

    @classmethod
    def from_life_state_dict(cls, family_data: dict[str, Any]) -> "FamilyState":
        if not family_data:
            return cls()

        spouse = family_data.get("spouse")
        dating_partner = family_data.get("dating_partner")
        return cls(
            parents=[
                FamilyMember.model_validate({**member, "generation": member.get("generation", 1)})
                for member in family_data.get("parents", [])
            ],
            spouse=FamilyMember.model_validate(spouse) if spouse else None,
            children=[
                FamilyMember.model_validate({**member, "generation": member.get("generation", 1)})
                for member in family_data.get("children", [])
            ],
            generation=int(family_data.get("generation", 1)),
            family_tree_id=str(family_data.get("family_tree_id", "")),
            family_pressure=int(family_data.get("family_pressure", 30)),
            parent_child_relation=int(family_data.get("parent_child_relation", 70)),
            father_relation=int(family_data.get("father_relation", 65)),
            mother_relation=int(family_data.get("mother_relation", 65)),
            partner_relation=int(family_data.get("partner_relation", 50)),
            relationship_status=family_data.get("relationship_status", "single"),
            dating_partner=(
                FamilyMember.model_validate(dating_partner) if dating_partner else None
            ),
            marriage_year=family_data.get("marriage_year"),
            children_count=int(family_data.get("children_count", len(family_data.get("children", [])))),
            family_history=list(family_data.get("family_history", [])),
            last_family_change=str(family_data.get("last_family_change", "")),
        )

    def to_life_state_dict(self) -> dict[str, Any]:
        return {
            "parents": [member.model_dump() for member in self.parents],
            "spouse": self.spouse.model_dump() if self.spouse else None,
            "children": [member.model_dump() for member in self.children],
            "generation": self.generation,
            "family_tree_id": self.family_tree_id,
            "family_pressure": self.family_pressure,
            "parent_child_relation": self.parent_child_relation,
            "father_relation": self.father_relation,
            "mother_relation": self.mother_relation,
            "partner_relation": self.partner_relation,
            "relationship_status": self.relationship_status,
            "dating_partner": (
                self.dating_partner.model_dump() if self.dating_partner else None
            ),
            "marriage_year": self.marriage_year,
            "children_count": self.children_count,
            "family_history": list(self.family_history),
            "last_family_change": self.last_family_change,
        }

    def has_spouse(self) -> bool:
        return self.spouse is not None

    def is_married(self) -> bool:
        return self.relationship_status == "married" and self.spouse is not None

    def has_children(self) -> bool:
        return self.children_count > 0 or len(self.children) > 0

    def has_minor_children(self, current_age_threshold: int = 18) -> bool:
        return any(child.age < current_age_threshold for child in self.children)

    def playable_children(self) -> list[FamilyMember]:
        return [child for child in self.children if child.playable]

    def clamp_scores(self) -> None:
        self.family_pressure = max(0, min(100, self.family_pressure))
        self.parent_child_relation = max(0, min(100, self.parent_child_relation))
        self.father_relation = max(0, min(100, self.father_relation))
        self.mother_relation = max(0, min(100, self.mother_relation))
        self.partner_relation = max(0, min(100, self.partner_relation))
