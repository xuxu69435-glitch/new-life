from typing import Any

from app.engine.simulation_context import SimulationEventType
from app.modules.romance.models import RomanticCandidate, RomanticRelationship, RomanceState, clamp_score


class RomanceEventProcessor:
    def initialize(self, romance: RomanceState) -> RomanceState:
        romance.validate_statuses()
        return romance

    def process(
        self,
        event_type: SimulationEventType,
        payload: dict[str, Any],
        working: RomanceState,
        state_age: int,
    ) -> RomanceState:
        if event_type == SimulationEventType.ROMANCE_STATE_UPDATE_REQUESTED:
            patch = dict(payload.get("romance", {}))
            merged = {**working.to_life_state_dict(), **patch}
            return RomanceState.from_life_state_dict(merged)

        if event_type == SimulationEventType.ROMANCE_CANDIDATE_CREATED:
            candidate = RomanticCandidate(
                candidate_id=str(payload.get("candidate_id") or RomanceState.new_candidate_id()),
                source_person_id=str(payload.get("source_person_id", "")),
                name=str(payload.get("name") or "心动对象"),
                age=payload.get("age"),
                gender=str(payload.get("gender") or "unknown"),
                source=str(payload.get("source") or "random_event"),
                status=str(payload.get("status") or "candidate"),
                favor=int(payload.get("favor", 50)),
                trust=int(payload.get("trust", 40)),
                attraction=int(payload.get("attraction", 45)),
                conflict=int(payload.get("conflict", 0)),
                familiarity=int(payload.get("familiarity", 30)),
                created_age=int(payload.get("created_age", state_age)),
                last_interaction_age=int(payload.get("last_interaction_age", state_age)),
                tags=list(payload.get("tags", [])),
                from_social_relationship_id=str(payload.get("from_social_relationship_id", "")),
            )
            working.upsert_candidate(candidate)
            working.new_candidates_this_year.append(candidate.candidate_id)
            working.record_history(
                {
                    "age": state_age,
                    "change_type": "candidate_created",
                    "candidate_id": candidate.candidate_id,
                    "name": candidate.name,
                }
            )
            return working

        if event_type == SimulationEventType.ROMANCE_CANDIDATE_CHANGE_REQUESTED:
            candidate_id = str(payload.get("candidate_id") or "")
            candidates = working.get_candidate_models()
            target = candidates.get(candidate_id)
            if target is None and payload.get("name"):
                for item in candidates.values():
                    if item.name == payload.get("name"):
                        target = item
                        break
            if target is None:
                return working
            for field, delta_key in (
                ("favor", "favor_delta"),
                ("trust", "trust_delta"),
                ("attraction", "attraction_delta"),
                ("conflict", "conflict_delta"),
                ("familiarity", "familiarity_delta"),
            ):
                if delta_key in payload:
                    setattr(target, field, clamp_score(getattr(target, field) + int(payload[delta_key])))
                elif field in payload:
                    setattr(target, field, clamp_score(int(payload[field])))
            if "status" in payload:
                target.status = str(payload["status"])
            target.last_interaction_age = state_age
            working.upsert_candidate(target)
            working.record_change({"change_type": "candidate_updated", "candidate_id": target.candidate_id})
            return working

        if event_type == SimulationEventType.ROMANCE_RELATIONSHIP_STARTED:
            relationship = RomanticRelationship(
                relationship_id=str(payload.get("relationship_id") or RomanceState.new_relationship_id()),
                candidate_id=str(payload.get("candidate_id") or ""),
                partner_name=str(payload.get("partner_name") or payload.get("name") or "恋人"),
                status=str(payload.get("status") or "dating"),
                favor=int(payload.get("favor", 55)),
                trust=int(payload.get("trust", 50)),
                intimacy=int(payload.get("intimacy", 45)),
                conflict=int(payload.get("conflict", 0)),
                stability=int(payload.get("stability", 40)),
                started_age=int(payload.get("started_age", state_age)),
                last_changed_age=int(payload.get("last_changed_age", state_age)),
                source=str(payload.get("source") or "random_event"),
            )
            working.set_current_relationship(relationship)
            working.years_in_current_relationship = 0
            working.record_change(
                {
                    "change_type": "relationship_started",
                    "partner_name": relationship.partner_name,
                    "status": relationship.status,
                }
            )
            working.record_history(
                {
                    "age": state_age,
                    "change_type": "relationship_started",
                    "relationship_id": relationship.relationship_id,
                    "partner_name": relationship.partner_name,
                }
            )
            return working

        if event_type == SimulationEventType.ROMANCE_RELATIONSHIP_CHANGE_REQUESTED:
            relationship = working.get_current_relationship()
            if relationship is None:
                return working
            for field, delta_key in (
                ("favor", "favor_delta"),
                ("trust", "trust_delta"),
                ("intimacy", "intimacy_delta"),
                ("conflict", "conflict_delta"),
                ("stability", "stability_delta"),
            ):
                if delta_key in payload:
                    setattr(relationship, field, clamp_score(getattr(relationship, field) + int(payload[delta_key])))
                elif field in payload:
                    setattr(relationship, field, clamp_score(int(payload[field])))
            relationship.last_changed_age = state_age
            working.set_current_relationship(relationship)
            working.record_change({"change_type": "relationship_updated", "status": relationship.status})
            return working

        if event_type == SimulationEventType.ROMANCE_RELATIONSHIP_STATUS_CHANGE_REQUESTED:
            relationship = working.get_current_relationship()
            if relationship is None:
                return working
            if "status" in payload:
                relationship.status = str(payload["status"])
            if "engagement_intent" in payload:
                relationship.engagement_intent = bool(payload["engagement_intent"])
            relationship.last_changed_age = state_age
            working.set_current_relationship(relationship)
            working.record_change({"change_type": "status_change", "status": relationship.status})
            working.record_history(
                {
                    "age": state_age,
                    "change_type": "status_change",
                    "status": relationship.status,
                    "partner_name": relationship.partner_name,
                }
            )
            return working

        if event_type == SimulationEventType.ROMANCE_RELATIONSHIP_ENDED:
            relationship = working.get_current_relationship()
            if relationship is None:
                return working
            relationship.status = str(payload.get("status") or "ended")
            relationship.engagement_intent = False
            working.ended_relationships_this_year.append(relationship.relationship_id)
            working.set_current_relationship(None)
            working.record_change({"change_type": "relationship_ended", "partner_name": relationship.partner_name})
            working.record_history(
                {
                    "age": state_age,
                    "change_type": "relationship_ended",
                    "relationship_id": relationship.relationship_id,
                    "partner_name": relationship.partner_name,
                }
            )
            return working

        if event_type == SimulationEventType.ROMANCE_FLAG_SET_REQUESTED:
            working.romance_flags[str(payload["key"])] = payload.get("value", True)
            return working

        if event_type == SimulationEventType.ROMANCE_FLAG_REMOVE_REQUESTED:
            working.romance_flags.pop(str(payload["key"]), None)
            return working

        return working
