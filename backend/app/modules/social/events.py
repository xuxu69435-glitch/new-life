from typing import Any

from app.engine.simulation_context import SimulationEventType
from app.modules.social.models import SocialPerson, SocialRelationship, SocialState, clamp_score
from app.modules.social.rules import clamp_relationship_values


class SocialEventProcessor:
    def initialize(self, social: SocialState) -> SocialState:
        social.validate_roles()
        return social

    def process(
        self,
        event_type: SimulationEventType,
        payload: dict[str, Any],
        working: SocialState,
        state_age: int,
    ) -> SocialState:
        if event_type == SimulationEventType.SOCIAL_STATE_UPDATE_REQUESTED:
            patch = dict(payload.get("social", {}))
            merged = {**working.to_life_state_dict(), **patch}
            return SocialState.from_life_state_dict(merged)

        if event_type == SimulationEventType.SOCIAL_PERSON_CREATED:
            person = SocialPerson(
                person_id=str(payload.get("person_id") or SocialState.new_person_id()),
                name=str(payload.get("name") or "新朋友"),
                age=payload.get("age"),
                gender=str(payload.get("gender") or "unknown"),
                role=str(payload.get("role") or "friend"),
                source=str(payload.get("source") or "random_event"),
                created_age=int(payload.get("created_age", state_age)),
                last_seen_age=int(payload.get("last_seen_age", state_age)),
                tags=list(payload.get("tags", [])),
                description=str(payload.get("description", "")),
            )
            working.upsert_person(person)
            return working

        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CREATED:
            relationship = SocialRelationship(
                relationship_id=str(payload.get("relationship_id") or SocialState.new_relationship_id()),
                person_id=str(payload.get("person_id") or ""),
                relationship_type=str(payload.get("relationship_type") or "friend"),
                closeness=int(payload.get("closeness", 55)),
                trust=int(payload.get("trust", 50)),
                conflict=int(payload.get("conflict", 0)),
                familiarity=int(payload.get("familiarity", 35)),
                status=str(payload.get("status") or "active"),
                started_age=int(payload.get("started_age", state_age)),
                last_changed_age=int(payload.get("last_changed_age", state_age)),
                last_interaction_age=int(payload.get("last_interaction_age", state_age)),
                source=str(payload.get("source") or "random_event"),
                tags=list(payload.get("tags", [])),
                importance=int(payload.get("importance", 50)),
                notes=str(payload.get("notes", "")),
            ).clamp_values()

            if not relationship.person_id:
                person = SocialPerson(
                    person_id=SocialState.new_person_id(),
                    name=str(payload.get("name") or "新朋友"),
                    role=str(payload.get("role") or relationship.relationship_type),
                    source=relationship.source,
                    created_age=state_age,
                    last_seen_age=state_age,
                )
                working.upsert_person(person)
                relationship.person_id = person.person_id
            else:
                persons = working.get_person_models()
                if relationship.person_id not in persons:
                    working.upsert_person(
                        SocialPerson(
                            person_id=relationship.person_id,
                            name=str(payload.get("name") or "新朋友"),
                            role=str(payload.get("role") or relationship.relationship_type),
                            source=relationship.source,
                            created_age=state_age,
                            last_seen_age=state_age,
                        )
                    )

            working.upsert_relationship(relationship)
            working.new_relationships_this_year.append(relationship.relationship_id)
            working.record_history(
                {
                    "age": state_age,
                    "relationship_id": relationship.relationship_id,
                    "change_type": "created",
                    "relationship_type": relationship.relationship_type,
                    "source": relationship.source,
                }
            )
            return working

        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_CHANGE_REQUESTED:
            target_type = str(payload.get("relationship_type") or payload.get("type") or "")
            rel_id = str(payload.get("relationship_id") or "")
            relationships = working.get_relationship_models()
            target = relationships.get(rel_id)
            if target is None and target_type:
                for item in relationships.values():
                    if item.relationship_type == target_type and item.status in {"active", "important"}:
                        target = item
                        break
            if target is None:
                return working

            before = target.model_dump()
            if "closeness_delta" in payload:
                target.closeness = clamp_score(target.closeness + int(payload["closeness_delta"]))
            if "trust_delta" in payload:
                target.trust = clamp_score(target.trust + int(payload["trust_delta"]))
            if "conflict_delta" in payload:
                target.conflict = clamp_score(target.conflict + int(payload["conflict_delta"]))
            if "familiarity_delta" in payload:
                target.familiarity = clamp_score(target.familiarity + int(payload["familiarity_delta"]))
            if "closeness" in payload:
                target.closeness = clamp_score(int(payload["closeness"]))
            if "trust" in payload:
                target.trust = clamp_score(int(payload["trust"]))
            if "conflict" in payload:
                target.conflict = clamp_score(int(payload["conflict"]))
            target.last_changed_age = state_age
            target.last_interaction_age = state_age
            target.clamp_values()
            working.upsert_relationship(target)
            working.changed_relationships_this_year.append(target.relationship_id)
            working.record_history(
                {
                    "age": state_age,
                    "relationship_id": target.relationship_id,
                    "change_type": "value_change",
                    "before": before,
                    "after": target.model_dump(),
                }
            )
            return working

        if event_type == SimulationEventType.SOCIAL_RELATIONSHIP_STATUS_CHANGE_REQUESTED:
            rel_id = str(payload.get("relationship_id") or "")
            target_type = str(payload.get("relationship_type") or payload.get("type") or "")
            relationships = working.get_relationship_models()
            target = relationships.get(rel_id)
            if target is None and target_type:
                for item in relationships.values():
                    if item.relationship_type == target_type:
                        target = item
                        break
            if target is None:
                return working
            before = target.model_dump()
            if "status" in payload:
                target.status = str(payload["status"])
            if "relationship_type" in payload and "upgrade_to" not in payload:
                target.relationship_type = str(payload["relationship_type"])
            if "upgrade_to" in payload:
                target.relationship_type = str(payload["upgrade_to"])
            target.last_changed_age = state_age
            working.upsert_relationship(target)
            working.changed_relationships_this_year.append(target.relationship_id)
            if target.status == "broken":
                working.removed_relationships_this_year.append(target.relationship_id)
            working.record_history(
                {
                    "age": state_age,
                    "relationship_id": target.relationship_id,
                    "change_type": "status_change",
                    "before": before,
                    "after": target.model_dump(),
                }
            )
            return working

        if event_type == SimulationEventType.SOCIAL_FLAG_SET_REQUESTED:
            working.social_flags[str(payload["key"])] = payload.get("value", True)
            return working

        if event_type == SimulationEventType.SOCIAL_FLAG_REMOVE_REQUESTED:
            working.social_flags.pop(str(payload["key"]), None)
            return working

        return working

    def summary(self) -> dict[str, Any]:
        return {}
