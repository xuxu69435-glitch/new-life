from __future__ import annotations

from typing import Any

from app.engine.simulation_context import LifeState
from app.infrastructure.rng import ServerRandom
from app.modules.career.models import CareerState
from app.modules.education.models import EducationState
from app.modules.family.models import FamilyState
from app.modules.romance.models import RomanticCandidate, RomanticRelationship, RomanceState, clamp_score
from app.modules.romance.rules import can_engagement, can_formal_dating, can_marriage_signal, get_romance_rules
from app.modules.social.models import SocialState


ROMANCE_NAME_POOL = ["苏晴", "林悦", "周婉", "陈诗", "赵宁", "许言", "顾清", "沈念"]


class RomanceAnnualProcessor:
    def __init__(self, romance_rules: dict[str, Any], rng: ServerRandom) -> None:
        self.rules = romance_rules
        self.rng = rng

    def apply_annual_changes(self, romance: RomanceState, state: LifeState, rules: dict) -> RomanceState:
        next_age = state.age + 1
        self._import_from_social(romance, state, next_age)
        self._maybe_convert_friend_to_candidate(romance, state, next_age)

        if self._has_active_dating(romance):
            self._advance_current_relationship(romance, next_age, rules, decay_multiplier=1)
        else:
            self._maybe_generate_candidates(romance, state, rules, next_age)
            self._maybe_start_relationship(romance, next_age, rules)

        self._update_single_years(romance)
        return romance

    def apply_restricted_decay(
        self,
        romance: RomanceState,
        next_age: int,
        rules: dict,
        *,
        mode: str,
    ) -> RomanceState:
        multiplier = 1
        if mode == "fugitive":
            multiplier = int(self.rules.get("fugitive_decay_multiplier", 3))
        if romance.get_current_relationship():
            self._advance_current_relationship(romance, next_age, rules, decay_multiplier=multiplier)
        self._update_single_years(romance)
        return romance

    def _import_from_social(self, romance: RomanceState, state: LifeState, next_age: int) -> None:
        if state.age < int(self.rules.get("min_candidate_age", 14)):
            return
        social = SocialState.from_life_state_dict(state.social)
        existing_source_ids = {
            str(item.get("source_person_id", ""))
            for item in romance.candidates
            if item.get("source_person_id")
        }
        existing_rel_ids = {
            str(item.get("from_social_relationship_id", ""))
            for item in romance.candidates
            if item.get("from_social_relationship_id")
        }
        chance = float(self.rules.get("candidate_from_social_chance", 0.35))

        for relationship in social.relationships:
            rel_type = str(relationship.get("relationship_type", ""))
            if rel_type != "romantic_candidate":
                continue
            rel_id = str(relationship.get("relationship_id", ""))
            person_id = str(relationship.get("person_id", ""))
            if rel_id in existing_rel_ids or person_id in existing_source_ids:
                continue
            if self.rng.random() > chance:
                continue
            person = social.get_person_models().get(person_id)
            name = person.name if person else "心动对象"
            status = "crush" if state.age < int(self.rules.get("min_formal_dating_age", 18)) else "candidate"
            candidate = RomanticCandidate(
                candidate_id=RomanceState.new_candidate_id(),
                source_person_id=person_id,
                name=name,
                age=person.age if person else None,
                gender=person.gender if person else "unknown",
                source="social",
                status=status,
                favor=int(relationship.get("closeness", 55)),
                trust=int(relationship.get("trust", 45)),
                attraction=int(relationship.get("closeness", 50)),
                conflict=int(relationship.get("conflict", 0)),
                familiarity=int(relationship.get("familiarity", 35)),
                created_age=next_age,
                last_interaction_age=next_age,
                from_social_relationship_id=rel_id,
            )
            romance.upsert_candidate(candidate)
            romance.new_candidates_this_year.append(candidate.candidate_id)
            romance.record_history(
                {
                    "age": next_age,
                    "change_type": "candidate_imported",
                    "candidate_id": candidate.candidate_id,
                    "source": "social",
                    "name": name,
                }
            )

    def _maybe_convert_friend_to_candidate(
        self,
        romance: RomanceState,
        state: LifeState,
        next_age: int,
    ) -> None:
        if state.age < int(self.rules.get("min_candidate_age", 14)):
            return
        if self._has_active_dating(romance):
            return
        if romance.active_candidate_count() >= int(self.rules.get("max_active_candidates", 5)):
            return
        chance = float(self.rules.get("friend_to_candidate_chance", 0.06))
        if self.rng.random() > chance:
            return

        social = SocialState.from_life_state_dict(state.social)
        for relationship in social.relationships:
            if relationship.get("relationship_type") not in {"friend", "best_friend"}:
                continue
            if int(relationship.get("closeness", 0)) < 70:
                continue
            if int(relationship.get("trust", 0)) < 55:
                continue
            if int(relationship.get("conflict", 0)) > 25:
                continue
            person_id = str(relationship.get("person_id", ""))
            if any(item.get("source_person_id") == person_id for item in romance.candidates):
                continue
            person = social.get_person_models().get(person_id)
            name = person.name if person else "心动对象"
            status = "crush" if state.age < int(self.rules.get("min_formal_dating_age", 18)) else "ambiguous"
            candidate = RomanticCandidate(
                candidate_id=RomanceState.new_candidate_id(),
                source_person_id=person_id,
                name=name,
                age=person.age if person else None,
                gender=person.gender if person else "unknown",
                source="social",
                status=status,
                favor=int(relationship.get("closeness", 60)),
                trust=int(relationship.get("trust", 55)),
                attraction=int(relationship.get("closeness", 58)),
                conflict=int(relationship.get("conflict", 5)),
                familiarity=int(relationship.get("familiarity", 50)),
                created_age=next_age,
                last_interaction_age=next_age,
                from_social_relationship_id=str(relationship.get("relationship_id", "")),
            )
            romance.upsert_candidate(candidate)
            romance.new_candidates_this_year.append(candidate.candidate_id)
            romance.record_history(
                {
                    "age": next_age,
                    "change_type": "friend_to_candidate",
                    "candidate_id": candidate.candidate_id,
                    "name": name,
                }
            )
            return

    def _maybe_generate_candidates(
        self,
        romance: RomanceState,
        state: LifeState,
        rules: dict,
        next_age: int,
    ) -> None:
        if state.age < int(self.rules.get("min_candidate_age", 14)):
            return
        if romance.active_candidate_count() >= int(self.rules.get("max_active_candidates", 5)):
            return

        education = EducationState.from_life_state_dict(state.education, rules)
        career = CareerState.from_life_state_dict(state.career, rules)
        family = FamilyState.from_life_state_dict(state.family)
        if family.has_spouse() or family.relationship_status in {"married", "dating"}:
            return

        bonus = min(0.1, romance.years_single * float(self.rules.get("single_year_candidate_bonus", 0.02)))
        teen = next_age < int(self.rules.get("min_formal_dating_age", 18))

        if education.is_enrolled and education.current_stage in {"primary", "middle", "high"}:
            chance = float(self.rules.get("school_crush_chance", 0.12)) + bonus
            if self.rng.random() <= chance:
                self._add_generated_candidate(romance, next_age, source="school", status="crush" if teen else "ambiguous")
                return

        if education.is_enrolled and education.current_stage in {"college", "graduate"}:
            chance = float(self.rules.get("university_romance_chance", 0.16)) + bonus
            if self.rng.random() <= chance:
                self._add_generated_candidate(
                    romance,
                    next_age,
                    source="university",
                    status="crush" if teen else "candidate",
                )
                return

        if career.employment_status == "employed" and can_formal_dating(next_age, rules):
            chance = float(self.rules.get("workplace_romance_chance", 0.10)) + bonus
            if self.rng.random() <= chance:
                self._add_generated_candidate(romance, next_age, source="work", status="candidate")

    def _add_generated_candidate(
        self,
        romance: RomanceState,
        next_age: int,
        *,
        source: str,
        status: str,
    ) -> None:
        name = self.rng.choice(ROMANCE_NAME_POOL)
        candidate = RomanticCandidate(
            candidate_id=RomanceState.new_candidate_id(),
            name=name,
            source=source,
            status=status,
            favor=self.rng.randint(45, 65),
            trust=self.rng.randint(35, 55),
            attraction=self.rng.randint(45, 60),
            familiarity=self.rng.randint(20, 40),
            created_age=next_age,
            last_interaction_age=next_age,
        )
        romance.upsert_candidate(candidate)
        romance.new_candidates_this_year.append(candidate.candidate_id)
        romance.record_history(
            {
                "age": next_age,
                "change_type": "candidate_created",
                "candidate_id": candidate.candidate_id,
                "source": source,
                "status": status,
                "name": name,
            }
        )

    def _maybe_start_relationship(self, romance: RomanceState, next_age: int, rules: dict) -> None:
        if not can_formal_dating(next_age, rules):
            return
        if romance.get_current_relationship() is not None:
            return

        favor_threshold = int(self.rules.get("dating_favor_threshold", 60))
        trust_threshold = int(self.rules.get("dating_trust_threshold", 45))
        attraction_threshold = int(self.rules.get("dating_attraction_threshold", 50))

        best: RomanticCandidate | None = None
        for candidate in romance.get_candidate_models().values():
            if candidate.status not in {"candidate", "ambiguous"}:
                continue
            if (
                candidate.favor >= favor_threshold
                and candidate.trust >= trust_threshold
                and candidate.attraction >= attraction_threshold
            ):
                if best is None or candidate.favor > best.favor:
                    best = candidate

        if best is None:
            return

        relationship = RomanticRelationship(
            relationship_id=RomanceState.new_relationship_id(),
            candidate_id=best.candidate_id,
            partner_name=best.name,
            status="dating",
            favor=best.favor,
            trust=best.trust,
            intimacy=clamp_score(best.favor - 5),
            conflict=best.conflict,
            stability=45,
            started_age=next_age,
            last_changed_age=next_age,
            years_together=0,
            source=best.source,
        )
        romance.set_current_relationship(relationship)
        best.status = "inactive"
        romance.upsert_candidate(best)
        romance.record_change(
            {
                "change_type": "relationship_started",
                "status": "dating",
                "partner_name": best.name,
            }
        )
        romance.record_history(
            {
                "age": next_age,
                "change_type": "relationship_started",
                "relationship_id": relationship.relationship_id,
                "partner_name": best.name,
                "status": "dating",
            }
        )

    def _advance_current_relationship(
        self,
        romance: RomanceState,
        next_age: int,
        rules: dict,
        *,
        decay_multiplier: int,
    ) -> None:
        relationship = romance.get_current_relationship()
        if relationship is None or not relationship.is_active_romance():
            return

        before = relationship.model_dump()
        decay = int(self.rules.get("relationship_decay_per_year", 2)) * decay_multiplier
        stable_decay = int(self.rules.get("stable_relationship_decay_per_year", 1)) * decay_multiplier
        conflict_decay = int(self.rules.get("conflict_decay_per_year", 1))
        stable_threshold = int(self.rules.get("engagement_stability_threshold", 75))
        breakup_threshold = int(self.rules.get("conflict_breakup_threshold", 75))
        cooling_threshold = int(self.rules.get("cooling_off_conflict_threshold", 55))

        use_stable_decay = relationship.stability >= stable_threshold or relationship.status == "engagement_intent"
        applied_decay = stable_decay if use_stable_decay else decay

        relationship.favor = clamp_score(relationship.favor - applied_decay + self.rng.randint(0, 1))
        relationship.trust = clamp_score(relationship.trust - applied_decay + self.rng.randint(0, 1))
        relationship.intimacy = clamp_score(relationship.intimacy - applied_decay + self.rng.randint(0, 1))
        relationship.conflict = clamp_score(max(0, relationship.conflict - conflict_decay))
        relationship.stability = clamp_score(relationship.stability + (1 if use_stable_decay else 0))
        relationship.years_together += 1
        relationship.last_changed_age = next_age
        romance.years_in_current_relationship = relationship.years_together

        if relationship.conflict >= breakup_threshold:
            relationship.status = "broken_up"
            relationship.engagement_intent = False
            romance.ended_relationships_this_year.append(relationship.relationship_id)
            romance.record_change({"change_type": "broken_up", "partner_name": relationship.partner_name})
            romance.record_history(
                {
                    "age": next_age,
                    "change_type": "broken_up",
                    "relationship_id": relationship.relationship_id,
                    "partner_name": relationship.partner_name,
                }
            )
        elif relationship.conflict >= cooling_threshold and relationship.status == "dating":
            relationship.status = "cooling_off"
            romance.record_change({"change_type": "cooling_off", "partner_name": relationship.partner_name})
            romance.record_history(
                {
                    "age": next_age,
                    "change_type": "cooling_off",
                    "relationship_id": relationship.relationship_id,
                    "partner_name": relationship.partner_name,
                }
            )
        elif (
            relationship.status == "dating"
            and can_engagement(next_age, rules)
            and relationship.stability >= stable_threshold
            and relationship.trust >= int(self.rules.get("engagement_trust_threshold", 70))
        ):
            relationship.status = "engagement_intent"
            relationship.engagement_intent = True
            romance.record_change(
                {
                    "change_type": "engagement_intent",
                    "partner_name": relationship.partner_name,
                }
            )
            romance.record_history(
                {
                    "age": next_age,
                    "change_type": "engagement_intent",
                    "relationship_id": relationship.relationship_id,
                    "partner_name": relationship.partner_name,
                }
            )
            if can_marriage_signal(next_age, rules):
                romance.romance_flags["marriage_candidate_signal"] = {
                    "partner_name": relationship.partner_name,
                    "candidate_id": relationship.candidate_id,
                    "relationship_id": relationship.relationship_id,
                    "age": next_age,
                }

        romance.set_current_relationship(relationship)
        if before != relationship.model_dump():
            romance.record_change(
                {
                    "change_type": "relationship_updated",
                    "partner_name": relationship.partner_name,
                    "status": relationship.status,
                }
            )

    def _update_single_years(self, romance: RomanceState) -> None:
        if romance.is_single() or not romance.get_current_relationship():
            romance.years_single += 1
            romance.years_in_current_relationship = 0
        else:
            romance.years_single = 0

    def _has_active_dating(self, romance: RomanceState) -> bool:
        rel = romance.get_current_relationship()
        return rel is not None and rel.status in {"dating", "cooling_off", "reconciled", "engagement_intent"}

    def build_family_signal(self, romance: RomanceState) -> dict[str, Any] | None:
        rel = romance.get_current_relationship()
        if rel is None:
            return None
        if rel.status == "engagement_intent" or romance.romance_flags.get("marriage_candidate_signal"):
            signal = dict(romance.romance_flags.get("marriage_candidate_signal", {}))
            signal.setdefault("signal_type", "engagement_intent")
            signal.setdefault("partner_name", rel.partner_name)
            signal.setdefault("candidate_id", rel.candidate_id)
            signal.setdefault("relationship_id", rel.relationship_id)
            return signal
        return None
