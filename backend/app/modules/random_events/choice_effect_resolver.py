from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.infrastructure.errors import RandomEventEffectError
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.library_models import V1EventChoice, V1EventDefinition
from app.modules.romance.constants import ROMANCE_EFFECT_TYPES
from app.modules.social.constants import SOCIAL_EFFECT_TYPES


FAMILY_EFFECT_TYPES = {
    "family_relation_change",
    "relationship_status_change",
    "partner_relation_change",
    "parent_relation_change",
    "family_pressure_change",
    "child_created",
    "child_relation_change",
    "spouse_created",
    "marriage_created",
    "divorce_created",
    "family_history_recorded",
    "partner_created",
}


class RandomEventChoiceEffectResolver:
    def __init__(self, effect_resolver: RandomEventEffectResolver | None = None) -> None:
        self.effect_resolver = effect_resolver or RandomEventEffectResolver()

    def resolve_choice(
        self,
        event: V1EventDefinition,
        choice: V1EventChoice,
        context: SimulationContext,
    ) -> list[tuple[SimulationEventType, dict[str, Any]]]:
        resolved: list[tuple[SimulationEventType, dict[str, Any]]] = []
        metadata = {
            "source_event_id": event.event_id,
            "source_event_name": event.name,
            "choice_id": choice.choice_id,
        }
        for raw_effect in choice.effects:
            effect_type = str(raw_effect.get("type", "")).strip()
            if effect_type == "unsupported_effect":
                resolved.append(
                    (
                        SimulationEventType.UNSUPPORTED_EFFECT_RECORDED,
                        {
                            "event_id": event.event_id,
                            "choice_id": choice.choice_id,
                            "target": raw_effect.get("target", ""),
                            "reason": raw_effect.get("reason", ""),
                            "effects_text": choice.effects_text,
                        },
                    )
                )
                continue

            if effect_type in FAMILY_EFFECT_TYPES:
                resolved.append(self._resolve_family_effect(raw_effect, metadata))
                continue

            if effect_type in SOCIAL_EFFECT_TYPES:
                enriched = self._enrich_social_effect(raw_effect, context)
                resolved.append(self._resolve_social_effect(enriched, metadata))
                continue

            if effect_type in ROMANCE_EFFECT_TYPES:
                resolved.append(self._resolve_romance_effect(raw_effect, metadata))
                continue

            pseudo_event = self._as_legacy_event(event, choice, raw_effect)
            resolved.extend(self.effect_resolver.resolve(pseudo_event, context))
        return resolved

    def _resolve_family_effect(
        self,
        raw_effect: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[SimulationEventType, dict[str, Any]]:
        effect_type = str(raw_effect.get("type", "")).strip()
        value = raw_effect.get("value", 0)
        target = str(raw_effect.get("target", ""))
        reason = str(raw_effect.get("reason", ""))
        payload = {**metadata, "reason": reason}

        if effect_type == "family_relation_change":
            return SimulationEventType.FAMILY_RELATION_CHANGE_REQUESTED, {
                **payload,
                "key": target,
                "delta": int(value),
            }
        if effect_type == "relationship_status_change":
            return SimulationEventType.RELATIONSHIP_STATUS_CHANGE_REQUESTED, {
                **payload,
                "status": str(value or target),
            }
        if effect_type == "partner_relation_change":
            return SimulationEventType.PARTNER_RELATION_CHANGE_REQUESTED, {
                **payload,
                "delta": int(value),
            }
        if effect_type == "parent_relation_change":
            return SimulationEventType.PARENT_RELATION_CHANGE_REQUESTED, {
                **payload,
                "key": target or "parent_child_relation",
                "delta": int(value),
            }
        if effect_type == "family_pressure_change":
            return SimulationEventType.FAMILY_PRESSURE_CHANGE_REQUESTED, {
                **payload,
                "delta": int(value),
            }
        if effect_type in {"partner_created", "spouse_created"}:
            return SimulationEventType.PARTNER_CREATED, {
                **payload,
                "name": raw_effect.get("name", "Partner"),
                "relation_score": int(raw_effect.get("relation_score", value or 60)),
            }
        if effect_type == "marriage_created":
            return SimulationEventType.MARRIAGE_CREATED, {
                **payload,
                "name": raw_effect.get("name"),
                "relation_score": int(raw_effect.get("relation_score", value or 0)) or None,
            }
        if effect_type == "child_created":
            return SimulationEventType.CHILD_CREATED, {
                **payload,
                "name": raw_effect.get("name"),
                "ability_score": int(raw_effect.get("ability_score", 50)),
                "relation_score": int(raw_effect.get("relation_score", 60)),
            }
        if effect_type == "child_relation_change":
            return SimulationEventType.CHILD_RELATION_CHANGE_REQUESTED, {
                **payload,
                "child_id": raw_effect.get("child_id", ""),
                "delta": int(value),
                "ability_delta": int(raw_effect.get("ability_delta", 0)),
            }
        if effect_type == "divorce_created":
            return SimulationEventType.DIVORCE_CREATED, {
                **payload,
                "partner_relation_delta": int(raw_effect.get("partner_relation_delta", value or -8)),
            }
        if effect_type == "family_history_recorded":
            return SimulationEventType.FAMILY_HISTORY_RECORDED, {
                **payload,
                "event_type": target or "family_event",
                "details": dict(raw_effect.get("details", {})),
            }

        raise RandomEventEffectError(f"Unknown family effect type: {effect_type}")

    def _resolve_social_effect(
        self,
        raw_effect: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[SimulationEventType, dict[str, Any]]:
        from app.engine.simulation_context import SimulationEventType

        effect_type = str(raw_effect.get("type", "")).strip()
        payload = {**metadata, **dict(raw_effect.get("payload", {}))}
        for key in (
            "person_id",
            "name",
            "role",
            "source",
            "relationship_id",
            "relationship_type",
            "type",
            "status",
            "upgrade_to",
            "closeness",
            "trust",
            "conflict",
            "familiarity",
            "closeness_delta",
            "trust_delta",
            "conflict_delta",
            "familiarity_delta",
            "importance",
            "key",
            "value",
        ):
            if key in raw_effect and key not in payload:
                payload[key] = raw_effect[key]

        if effect_type == "social_person_created":
            return SimulationEventType.SOCIAL_PERSON_CREATED, payload
        if effect_type == "social_relationship_created":
            return SimulationEventType.SOCIAL_RELATIONSHIP_CREATED, payload
        if effect_type == "social_relationship_change":
            return SimulationEventType.SOCIAL_RELATIONSHIP_CHANGE_REQUESTED, payload
        if effect_type == "social_relationship_status_change":
            return SimulationEventType.SOCIAL_RELATIONSHIP_STATUS_CHANGE_REQUESTED, payload
        if effect_type == "social_flag_set":
            return SimulationEventType.SOCIAL_FLAG_SET_REQUESTED, payload
        if effect_type == "social_flag_remove":
            return SimulationEventType.SOCIAL_FLAG_REMOVE_REQUESTED, payload
        raise RandomEventEffectError(f"Unknown social effect type: {effect_type}")

    def _resolve_romance_effect(
        self,
        raw_effect: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[SimulationEventType, dict[str, Any]]:
        effect_type = str(raw_effect.get("type", "")).strip()
        payload = {**metadata, **dict(raw_effect.get("payload", {}))}
        for key in (
            "candidate_id",
            "name",
            "source",
            "status",
            "relationship_id",
            "partner_name",
            "candidate_id",
            "favor",
            "trust",
            "attraction",
            "intimacy",
            "conflict",
            "stability",
            "favor_delta",
            "trust_delta",
            "attraction_delta",
            "intimacy_delta",
            "conflict_delta",
            "stability_delta",
            "engagement_intent",
            "key",
            "value",
        ):
            if key in raw_effect and key not in payload:
                payload[key] = raw_effect[key]

        if effect_type == "romance_candidate_created":
            return SimulationEventType.ROMANCE_CANDIDATE_CREATED, payload
        if effect_type == "romance_candidate_change":
            return SimulationEventType.ROMANCE_CANDIDATE_CHANGE_REQUESTED, payload
        if effect_type == "romance_relationship_started":
            return SimulationEventType.ROMANCE_RELATIONSHIP_STARTED, payload
        if effect_type == "romance_relationship_change":
            return SimulationEventType.ROMANCE_RELATIONSHIP_CHANGE_REQUESTED, payload
        if effect_type == "romance_relationship_status_change":
            return SimulationEventType.ROMANCE_RELATIONSHIP_STATUS_CHANGE_REQUESTED, payload
        if effect_type == "romance_relationship_ended":
            return SimulationEventType.ROMANCE_RELATIONSHIP_ENDED, payload
        if effect_type == "romance_flag_set":
            return SimulationEventType.ROMANCE_FLAG_SET_REQUESTED, payload
        if effect_type == "romance_flag_remove":
            return SimulationEventType.ROMANCE_FLAG_REMOVE_REQUESTED, payload
        raise RandomEventEffectError(f"Unknown romance effect type: {effect_type}")

    def _enrich_social_effect(
        self,
        raw_effect: dict[str, Any],
        context: SimulationContext,
    ) -> dict[str, Any]:
        from app.modules.social.models import SocialState

        effect = dict(raw_effect)
        if effect.get("relationship_id"):
            return effect
        if context is None:
            return effect
        rel_type = str(effect.get("relationship_type") or effect.get("type") or "").strip()
        if not rel_type:
            return effect

        social_data = context.state.social
        if context.result_collector._social_working is not None:
            social_data = context.result_collector._social_working.to_life_state_dict()
        social = SocialState.from_life_state_dict(social_data)

        candidates = [
            item
            for item in social.relationships
            if item.get("relationship_type") == rel_type
            and item.get("status") in {"active", "important", "distant"}
        ]
        if not candidates:
            return effect

        best = max(candidates, key=lambda item: int(item.get("closeness", 0)))
        effect["relationship_id"] = str(best.get("relationship_id", ""))
        return effect

    def _as_legacy_event(
        self,
        event: V1EventDefinition,
        choice: V1EventChoice,
        raw_effect: dict[str, Any],
    ):
        from app.modules.random_events.models import RandomEventDefinition

        effect_type = str(raw_effect.get("type", "")).strip()
        if effect_type not in RandomEventEffectResolver.ALLOWED_EFFECT_TYPES:
            raise RandomEventEffectError(
                f"Unknown choice effect type '{effect_type}' for event '{event.event_id}'."
            )

        return RandomEventDefinition(
            id=event.event_id,
            name=event.name,
            category=event.category,
            stage="any",
            probability=0.0,
            direct_death=effect_type == "direct_death_candidate",
            effects=[raw_effect],
            narrative_text=choice.effects_text,
            death_reason=str(raw_effect.get("reason") or event.name),
        )
