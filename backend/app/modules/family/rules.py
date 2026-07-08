from uuid import uuid4

from app.modules.family.models import FamilyMember, FamilyState


def build_default_family_state(rules: dict | None = None) -> FamilyState:
    family_tree_id = str(uuid4())
    return FamilyState(
        parents=[
            FamilyMember(
                person_id=str(uuid4()),
                name="Parent A",
                relation="parent",
                playable=False,
            ),
            FamilyMember(
                person_id=str(uuid4()),
                name="Parent B",
                relation="parent",
                playable=False,
            ),
        ],
        spouse=None,
        children=[],
        generation=1,
        family_tree_id=family_tree_id,
    )
