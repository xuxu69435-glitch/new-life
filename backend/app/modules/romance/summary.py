from typing import Any

from app.modules.romance.models import RomanceState


def build_romance_summary(romance: RomanceState, age: int) -> dict[str, Any]:
    current = romance.get_current_relationship()
    status = "single"
    partner_name = ""
    if current is not None:
        status = current.status
        partner_name = current.partner_name

    recent_candidates = []
    candidate_models = romance.get_candidate_models()
    for candidate_id in romance.new_candidates_this_year[-3:]:
        candidate = candidate_models.get(candidate_id)
        if candidate:
            recent_candidates.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "name": candidate.name,
                    "status": candidate.status,
                    "favor": candidate.favor,
                    "trust": candidate.trust,
                    "attraction": candidate.attraction,
                }
            )

    active_candidates = []
    for candidate in candidate_models.values():
        if candidate.status in {"candidate", "crush", "ambiguous"}:
            active_candidates.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "name": candidate.name,
                    "status": candidate.status,
                    "favor": candidate.favor,
                    "trust": candidate.trust,
                    "attraction": candidate.attraction,
                    "conflict": candidate.conflict,
                    "familiarity": candidate.familiarity,
                    "tags": candidate.tags,
                }
            )

    current_view: dict[str, Any] | None = None
    if current is not None:
        current_view = {
            "relationship_id": current.relationship_id,
            "partner_name": current.partner_name,
            "status": current.status,
            "favor": current.favor,
            "trust": current.trust,
            "intimacy": current.intimacy,
            "conflict": current.conflict,
            "stability": current.stability,
            "years_together": current.years_together,
            "engagement_intent": current.engagement_intent,
        }

    return {
        "status": status,
        "candidate_count": romance.active_candidate_count(),
        "current_partner_name": partner_name,
        "years_single": romance.years_single,
        "years_in_current_relationship": romance.years_in_current_relationship,
        "recent_candidates": recent_candidates,
        "active_candidates": active_candidates[:5],
        "current_relationship": current_view,
        "recent_changes": list(romance.romance_changes_this_year[-5:]),
        "history_highlights": list(romance.relationship_history[-5:]),
        "age": age,
    }


def build_romance_narrative_lines(romance: RomanceState) -> list[str]:
    lines: list[str] = []
    candidate_models = romance.get_candidate_models()
    for candidate_id in romance.new_candidates_this_year:
        candidate = candidate_models.get(candidate_id)
        if candidate:
            lines.append(f"今年你对{candidate.name}产生了好感。")

    for change in romance.romance_changes_this_year:
        change_type = str(change.get("change_type", ""))
        partner = str(change.get("partner_name", ""))
        if change_type in {"candidate_created", "candidate_imported", "friend_to_candidate"}:
            continue
        if change_type == "relationship_started":
            lines.append(f"你和{partner or '对方'}开始了一段恋爱关系。")
        elif change_type == "cooling_off":
            lines.append(f"你和{partner or '恋人'}的关系进入冷淡期。")
        elif change_type == "broken_up":
            lines.append(f"你结束了与{partner or '恋人'}的恋爱关系。")
        elif change_type == "engagement_intent":
            lines.append(f"你和{partner or '恋人'}开始认真考虑未来。")
        elif change_type == "relationship_ended":
            lines.append(f"你结束了一段恋爱关系。")

    if not lines and romance.new_candidates_this_year:
        lines.append("今年你的情感世界出现了新的变化。")
    return lines[:3]
