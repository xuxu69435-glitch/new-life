from typing import Any

from app.modules.social.models import SocialState


def build_social_summary(social: SocialState, age: int) -> dict[str, Any]:
    relationships = social.get_relationship_models()
    persons = social.get_person_models()
    friend_count = social.friend_count()
    important_count = sum(
        1
        for item in relationships.values()
        if item.status in {"important", "active"}
        and (
            item.importance >= 75
            or item.relationship_type in {"best_friend", "mentor", "benefactor"}
        )
    )

    recent_new = []
    for rel_id in social.new_relationships_this_year:
        rel = relationships.get(rel_id)
        if not rel:
            continue
        person = persons.get(rel.person_id)
        recent_new.append(
            {
                "relationship_id": rel_id,
                "person_name": person.name if person else "未知",
                "relationship_type": rel.relationship_type,
                "closeness": rel.closeness,
                "trust": rel.trust,
                "conflict": rel.conflict,
            }
        )

    recent_changed = []
    for rel_id in social.changed_relationships_this_year:
        rel = relationships.get(rel_id)
        if not rel:
            continue
        person = persons.get(rel.person_id)
        recent_changed.append(
            {
                "relationship_id": rel_id,
                "person_name": person.name if person else "未知",
                "relationship_type": rel.relationship_type,
                "status": rel.status,
                "closeness": rel.closeness,
                "trust": rel.trust,
                "conflict": rel.conflict,
            }
        )

    active_relationships = []
    for rel in relationships.values():
        if rel.status not in {"active", "important", "distant"}:
            continue
        person = persons.get(rel.person_id)
        active_relationships.append(
            {
                "relationship_id": rel.relationship_id,
                "person_id": rel.person_id,
                "person_name": person.name if person else "未知",
                "relationship_type": rel.relationship_type,
                "status": rel.status,
                "closeness": rel.closeness,
                "trust": rel.trust,
                "conflict": rel.conflict,
                "familiarity": rel.familiarity,
                "tags": list(rel.tags),
                "importance": rel.importance,
            }
        )

    return {
        "friend_count": friend_count,
        "important_relationship_count": important_count,
        "active_relationship_count": social.active_relationship_count(),
        "recent_new_count": len(recent_new),
        "recent_changed_count": len(recent_changed),
        "age": age,
        "recent_new_relationships": recent_new,
        "recent_changed_relationships": recent_changed,
        "active_relationships": active_relationships,
    }


def build_social_narrative_lines(social: SocialState) -> list[str]:
    lines: list[str] = []
    persons = social.get_person_models()
    for rel_id in social.new_relationships_this_year:
        rel = social.get_relationship_models().get(rel_id)
        if not rel:
            continue
        person = persons.get(rel.person_id)
        name = person.name if person else "新朋友"
        if rel.relationship_type in {"friend", "best_friend", "classmate"}:
            lines.append(f"今年你认识了新的朋友：{name}。")
        elif rel.relationship_type in {"mentor", "benefactor"}:
            lines.append(f"你在工作中遇到了愿意帮助你的人：{name}。")
        elif rel.relationship_type == "rival":
            lines.append(f"今年出现了新的竞争对象：{name}。")
    for rel_id in social.changed_relationships_this_year:
        rel = social.get_relationship_models().get(rel_id)
        if not rel:
            continue
        person = persons.get(rel.person_id)
        name = person.name if person else "某人"
        if rel.status == "distant":
            lines.append(f"你和{name}的关系逐渐疏远。")
        elif rel.relationship_type == "rival":
            lines.append(f"你和{name}的矛盾加深了。")
        elif rel.relationship_type == "best_friend":
            lines.append(f"你和{name}成为了挚友。")
    return lines
