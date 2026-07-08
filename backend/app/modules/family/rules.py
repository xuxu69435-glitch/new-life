from uuid import uuid4

from app.modules.family.models import FamilyMember, FamilyState


def get_family_rules(rules: dict) -> dict:
    return rules.get("family", {})


def build_default_family_state(rules: dict | None = None) -> FamilyState:
    family_rules = get_family_rules(rules or {})
    defaults = family_rules.get("defaults", {})
    family_tree_id = str(uuid4())

    parents = [
        FamilyMember(
            person_id=str(uuid4()),
            name="Father",
            relation="father",
            age=30,
            playable=False,
            relation_score=int(defaults.get("father_relation", 65)),
            generation=0,
        ),
        FamilyMember(
            person_id=str(uuid4()),
            name="Mother",
            relation="mother",
            age=30,
            playable=False,
            relation_score=int(defaults.get("mother_relation", 65)),
            generation=0,
        ),
    ]

    return FamilyState(
        parents=parents,
        spouse=None,
        children=[],
        generation=1,
        family_tree_id=family_tree_id,
        family_pressure=int(defaults.get("family_pressure", 30)),
        parent_child_relation=int(defaults.get("parent_child_relation", 70)),
        father_relation=int(defaults.get("father_relation", 65)),
        mother_relation=int(defaults.get("mother_relation", 65)),
        partner_relation=int(defaults.get("partner_relation", 50)),
        relationship_status="single",
        dating_partner=None,
        marriage_year=None,
        children_count=0,
        family_history=[],
        last_family_change="initialized",
    )
