from typing import Any

from pydantic import BaseModel, Field


class FamilyMember(BaseModel):
    person_id: str
    name: str = ""
    relation: str = ""
    playable: bool = False


class FamilyState(BaseModel):
    parents: list[FamilyMember] = Field(default_factory=list)
    spouse: FamilyMember | None = None
    children: list[FamilyMember] = Field(default_factory=list)
    generation: int = 1
    family_tree_id: str = ""

    @classmethod
    def from_life_state_dict(cls, family_data: dict[str, Any]) -> "FamilyState":
        if not family_data:
            return cls()

        spouse = family_data.get("spouse")
        return cls(
            parents=[FamilyMember.model_validate(member) for member in family_data.get("parents", [])],
            spouse=FamilyMember.model_validate(spouse) if spouse else None,
            children=[FamilyMember.model_validate(member) for member in family_data.get("children", [])],
            generation=int(family_data.get("generation", 1)),
            family_tree_id=str(family_data.get("family_tree_id", "")),
        )

    def to_life_state_dict(self) -> dict[str, Any]:
        return {
            "parents": [member.model_dump() for member in self.parents],
            "spouse": self.spouse.model_dump() if self.spouse else None,
            "children": [member.model_dump() for member in self.children],
            "generation": self.generation,
            "family_tree_id": self.family_tree_id,
        }

    def has_spouse(self) -> bool:
        return self.spouse is not None

    def has_children(self) -> bool:
        return len(self.children) > 0

    def playable_children(self) -> list[FamilyMember]:
        return [child for child in self.children if child.playable]
