from typing import Any
from uuid import uuid4

from app.engine.simulation_context import SimulationEventType
from app.modules.family.models import FamilyMember, FamilyState
from app.modules.family.rules import get_family_rules


class FamilyEventProcessor:
    """Applies family domain events to a working FamilyState snapshot."""

    def __init__(self) -> None:
        self.married_this_year = False
        self.child_born_this_year = False
        self.children_count_delta = 0
        self.relationship_status_before: str | None = None
        self.relationship_status_after: str | None = None
        self.partner_relation_delta = 0
        self.parent_child_relation_delta = 0
        self.family_pressure_delta = 0
        self.family_history_records: list[dict[str, Any]] = []

    def initialize(self, family: FamilyState) -> FamilyState:
        working = family.model_copy(deep=True)
        if self.relationship_status_before is None:
            self.relationship_status_before = working.relationship_status
        return working

    def process(
        self,
        event_type: SimulationEventType,
        payload: dict[str, Any],
        working: FamilyState,
        state_age: int,
        rules: dict,
    ) -> FamilyState:
        family_rules = get_family_rules(rules)

        if event_type == SimulationEventType.PARTNER_RELATION_CHANGE_REQUESTED:
            delta = int(payload.get("delta", 0))
            working.partner_relation += delta
            self.partner_relation_delta += delta

        elif event_type == SimulationEventType.PARENT_RELATION_CHANGE_REQUESTED:
            key = str(payload.get("key", "parent_child_relation"))
            delta = int(payload.get("delta", 0))
            if key == "father_relation":
                working.father_relation += delta
            elif key == "mother_relation":
                working.mother_relation += delta
            else:
                working.parent_child_relation += delta
                self.parent_child_relation_delta += delta

        elif event_type == SimulationEventType.FAMILY_PRESSURE_CHANGE_REQUESTED:
            delta = int(payload.get("delta", 0))
            working.family_pressure += delta
            self.family_pressure_delta += delta

        elif event_type == SimulationEventType.CHILD_RELATION_CHANGE_REQUESTED:
            child_id = str(payload.get("child_id", ""))
            delta = int(payload.get("delta", 0))
            for child in working.children:
                if child.person_id == child_id or not child_id:
                    child.relation_score = max(0, min(100, child.relation_score + delta))
                    if payload.get("ability_delta"):
                        child.ability_score = max(
                            0,
                            min(100, child.ability_score + int(payload["ability_delta"])),
                        )
                    break

        elif event_type == SimulationEventType.RELATIONSHIP_STATUS_CHANGE_REQUESTED:
            working.relationship_status = str(payload.get("status", working.relationship_status))

        elif event_type == SimulationEventType.PARTNER_CREATED:
            partner_name = str(payload.get("name") or "Partner")
            partner = FamilyMember(
                person_id=str(payload.get("person_id") or uuid4()),
                name=partner_name,
                relation="partner",
                age=int(payload.get("age", max(state_age - 2, 18))),
                relation_score=int(payload.get("relation_score", working.partner_relation)),
                generation=working.generation,
            )
            working.dating_partner = partner
            if working.relationship_status == "single":
                working.relationship_status = "dating"
            working.partner_relation = int(
                payload.get("relation_score", working.partner_relation)
            )
            self._record_history(
                working,
                "partner_created",
                {"partner_id": partner.person_id, "name": partner.name},
            )

        elif event_type == SimulationEventType.MARRIAGE_CREATED:
            marriage_rules = family_rules.get("marriage", {})
            partner = working.dating_partner
            if partner is None:
                partner = FamilyMember(
                    person_id=str(uuid4()),
                    name=str(payload.get("name") or "Spouse"),
                    relation="spouse",
                    age=max(state_age - 2, 18),
                    relation_score=int(
                        marriage_rules.get("default_partner_relation_after_marriage", 75)
                    ),
                    generation=working.generation,
                )
            else:
                partner = partner.model_copy(deep=True)
                partner.relation = "spouse"
                partner.relation_score = int(
                    payload.get(
                        "relation_score",
                        marriage_rules.get("default_partner_relation_after_marriage", 75),
                    )
                )

            working.spouse = partner
            working.dating_partner = None
            working.relationship_status = "married"
            working.marriage_year = state_age
            working.partner_relation = partner.relation_score
            self.married_this_year = True
            self._record_history(
                working,
                "marriage_created",
                {"spouse_id": partner.person_id, "year": state_age},
            )

        elif event_type == SimulationEventType.CHILD_CREATED:
            childbirth_rules = family_rules.get("childbirth", {})
            child_index = working.children_count + 1
            child_name = str(
                payload.get("name")
                or f"{childbirth_rules.get('default_child_name_prefix', 'Child')} {child_index}"
            )
            child = FamilyMember(
                person_id=str(payload.get("person_id") or uuid4()),
                name=child_name,
                relation="child",
                age=0,
                playable=False,
                relation_score=int(payload.get("relation_score", 60)),
                ability_score=int(payload.get("ability_score", 50)),
                generation=working.generation + 1,
            )
            working.children.append(child)
            working.children_count += 1
            self.child_born_this_year = True
            self.children_count_delta += 1
            self._record_history(
                working,
                "child_created",
                {"child_id": child.person_id, "name": child.name},
            )

        elif event_type == SimulationEventType.DIVORCE_CREATED:
            divorce_rules = family_rules.get("divorce", {})
            ex_spouse = working.spouse
            if ex_spouse is not None:
                self._record_history(
                    working,
                    "divorce_created",
                    {"ex_spouse_id": ex_spouse.person_id},
                )
            working.spouse = None
            working.dating_partner = None
            working.relationship_status = "divorced"
            working.marriage_year = None
            working.partner_relation = max(
                0,
                working.partner_relation + int(payload.get("partner_relation_delta", -8)),
            )
            split_cost = float(divorce_rules.get("asset_split_placeholder", 0))
            if split_cost:
                payload.setdefault("asset_split_cost", split_cost)

        elif event_type == SimulationEventType.FAMILY_RELATION_CHANGE_REQUESTED:
            key = str(payload.get("key", ""))
            delta = int(payload.get("delta", 0))
            if key == "partner_relation":
                working.partner_relation += delta
                self.partner_relation_delta += delta
            elif key == "parent_child_relation":
                working.parent_child_relation += delta
                self.parent_child_relation_delta += delta
            elif key == "family_pressure":
                working.family_pressure += delta
                self.family_pressure_delta += delta
            elif key == "father_relation":
                working.father_relation += delta
            elif key == "mother_relation":
                working.mother_relation += delta

        elif event_type == SimulationEventType.FAMILY_HISTORY_RECORDED:
            self._record_history(
                working,
                str(payload.get("event_type", "family_event")),
                dict(payload.get("details", {})),
            )

        elif event_type == SimulationEventType.FAMILY_STATE_UPDATE_REQUESTED:
            patch = dict(payload.get("family", {}))
            merged = {**working.to_life_state_dict(), **patch}
            working = FamilyState.from_life_state_dict(merged)

        working.clamp_scores()
        working.last_family_change = str(payload.get("reason", event_type.value))
        self.relationship_status_after = working.relationship_status
        return working

    def _record_history(
        self,
        working: FamilyState,
        event_type: str,
        details: dict[str, Any],
    ) -> None:
        record = {"event_type": event_type, **details}
        working.family_history.append(record)
        self.family_history_records.append(record)

    def summary(self) -> dict[str, Any]:
        return {
            "married_this_year": self.married_this_year,
            "child_born_this_year": self.child_born_this_year,
            "children_count_delta": self.children_count_delta,
            "relationship_status_before": self.relationship_status_before,
            "relationship_status_after": self.relationship_status_after,
            "partner_relation_delta": self.partner_relation_delta,
            "parent_child_relation_delta": self.parent_child_relation_delta,
            "family_pressure_delta": self.family_pressure_delta,
            "family_history_records": list(self.family_history_records),
        }
