from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.infrastructure.errors import RandomEventEffectError
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.library_models import V1EventChoice, V1EventDefinition


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
