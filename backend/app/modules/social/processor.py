from __future__ import annotations

from typing import Any

from app.engine.simulation_context import LifeState
from app.infrastructure.rng import ServerRandom
from app.modules.career.models import CareerState
from app.modules.education.models import EducationState
from app.modules.social.constants import SCHOOL_STAGES
from app.modules.social.models import SocialPerson, SocialRelationship, SocialState, clamp_score
from app.modules.social.rules import get_social_rules


NAME_POOLS: dict[str, list[str]] = {
    "friend": ["林晓", "周然", "陈悦", "赵航", "孙宁"],
    "classmate": ["王浩", "李婷", "张晨", "刘洋", "吴雪"],
    "teacher": ["王老师", "李老师", "陈老师", "赵老师"],
    "coworker": ["同事甲", "同事乙", "同事丙", "同事丁"],
    "leader": ["张经理", "李主管", "王总监"],
    "mentor": ["前辈老周", "前辈老吴", "前辈老郑"],
    "rival": ["竞争同事A", "竞争同事B"],
    "benefactor": ["贵人老林", "贵人老许"],
    "acquaintance": ["熟人甲", "熟人乙"],
}


class SocialAnnualProcessor:
    def __init__(self, social_rules: dict[str, Any], rng: ServerRandom) -> None:
        self.rules = social_rules
        self.rng = rng

    def apply_annual_changes(self, social: SocialState, state: LifeState, rules: dict) -> SocialState:
        next_age = state.age + 1
        self._apply_natural_decay(social, next_age, decay_multiplier=1)
        education = EducationState.from_life_state_dict(state.education, rules)
        career = CareerState.from_life_state_dict(state.career, rules)

        if self._can_generate_school_relationship(education):
            self._maybe_generate_school_relationship(social, education, next_age)

        if self._can_generate_work_relationship(career):
            self._maybe_generate_work_relationship(social, career, next_age)

        self._upgrade_and_break_relationships(social, next_age)
        return social

    def apply_restricted_decay(
        self,
        social: SocialState,
        next_age: int,
        mode: str,
    ) -> SocialState:
        multiplier = 1
        if mode == "fugitive":
            multiplier = int(self.rules.get("fugitive_decay_multiplier", 3))
        self._apply_natural_decay(social, next_age, decay_multiplier=multiplier)
        return social

    def _apply_natural_decay(self, social: SocialState, next_age: int, *, decay_multiplier: int) -> None:
        friendship_decay = int(self.rules.get("friendship_decay_per_year", 2)) * decay_multiplier
        important_decay = int(self.rules.get("important_relationship_decay_per_year", 1)) * decay_multiplier
        trust_decay = int(self.rules.get("trust_decay_per_year", 1)) * decay_multiplier
        conflict_decay = int(self.rules.get("conflict_decay_per_year", 1)) * decay_multiplier
        distant_threshold = int(self.rules.get("distant_closeness_threshold", 25))
        important_threshold = int(self.rules.get("important_relationship_threshold", 75))

        for rel_id, relationship in list(social.get_relationship_models().items()):
            if relationship.status == "broken":
                continue
            before = relationship.model_dump()
            is_important = (
                relationship.importance >= important_threshold
                or relationship.status == "important"
                or relationship.relationship_type == "best_friend"
            )
            decay = important_decay if is_important else friendship_decay
            relationship.closeness = clamp_score(relationship.closeness - decay)
            relationship.trust = clamp_score(relationship.trust - trust_decay)
            relationship.conflict = clamp_score(max(0, relationship.conflict - conflict_decay))
            relationship.familiarity = clamp_score(max(0, relationship.familiarity - 1))
            relationship.last_changed_age = next_age
            relationship.last_interaction_age = next_age

            if relationship.closeness <= distant_threshold and relationship.status == "active":
                relationship.status = "distant"
                social.changed_relationships_this_year.append(rel_id)
                social.record_history(
                    {
                        "age": next_age,
                        "relationship_id": rel_id,
                        "change_type": "became_distant",
                        "before": before,
                        "after": relationship.model_dump(),
                    }
                )

            social.upsert_relationship(relationship)

    def _upgrade_and_break_relationships(self, social: SocialState, next_age: int) -> None:
        best_friend_threshold = int(self.rules.get("best_friend_threshold", 85))
        rival_conflict_threshold = int(self.rules.get("rival_conflict_threshold", 70))
        broken_conflict_threshold = int(self.rules.get("broken_conflict_threshold", 85))

        for rel_id, relationship in list(social.get_relationship_models().items()):
            if relationship.status in {"broken"}:
                continue
            changed = False
            before = relationship.model_dump()

            if (
                relationship.relationship_type == "friend"
                and relationship.closeness >= best_friend_threshold
                and relationship.trust >= best_friend_threshold - 10
            ):
                relationship.relationship_type = "best_friend"
                relationship.status = "important"
                relationship.importance = clamp_score(max(relationship.importance, 80))
                changed = True

            if relationship.conflict >= broken_conflict_threshold:
                relationship.status = "broken"
                social.removed_relationships_this_year.append(rel_id)
                changed = True
            elif relationship.conflict >= rival_conflict_threshold and relationship.relationship_type not in {
                "rival",
                "best_friend",
            }:
                relationship.relationship_type = "rival"
                changed = True

            if changed:
                relationship.last_changed_age = next_age
                social.upsert_relationship(relationship)
                social.changed_relationships_this_year.append(rel_id)
                social.record_history(
                    {
                        "age": next_age,
                        "relationship_id": rel_id,
                        "change_type": "status_or_type_change",
                        "before": before,
                        "after": relationship.model_dump(),
                    }
                )

    def _can_generate_school_relationship(self, education: EducationState) -> bool:
        stage = str(education.current_stage or "")
        if stage not in SCHOOL_STAGES:
            return False
        if not education.is_enrolled:
            return False
        return True

    def _can_generate_work_relationship(self, career: CareerState) -> bool:
        return str(career.employment_status) == "employed"

    def _maybe_generate_school_relationship(
        self,
        social: SocialState,
        education: EducationState,
        next_age: int,
    ) -> None:
        if social.active_relationship_count() >= int(self.rules.get("max_active_relationships", 25)):
            return
        if self.rng.random() > float(self.rules.get("school_relationship_chance", 0.18)):
            return

        stage = str(education.current_stage)
        if stage in {"primary", "middle", "high"}:
            rel_type = "classmate" if self.rng.random() < 0.55 else "friend"
            role = rel_type
        else:
            rel_type = "mentor" if self.rng.random() < 0.25 else ("friend" if self.rng.random() < 0.5 else "classmate")
            role = rel_type

        if rel_type == "classmate" and social.count_relationship_type("classmate") >= 6:
            return
        if rel_type == "friend" and social.friend_count() >= 5:
            return

        self._create_relationship(
            social,
            relationship_type=rel_type,
            role=role,
            source="school",
            age=next_age,
            closeness=55,
            trust=50,
            familiarity=35,
        )

    def _maybe_generate_work_relationship(
        self,
        social: SocialState,
        career: CareerState,
        next_age: int,
    ) -> None:
        if social.active_relationship_count() >= int(self.rules.get("max_active_relationships", 25)):
            return
        if self.rng.random() > float(self.rules.get("work_relationship_chance", 0.16)):
            return

        roll = self.rng.random()
        if roll < 0.35:
            rel_type = "coworker"
        elif roll < 0.55:
            rel_type = "leader"
        elif roll < 0.75:
            rel_type = "mentor"
        elif roll < 0.9:
            rel_type = "benefactor"
        else:
            rel_type = "rival"

        if social.count_relationship_type(rel_type) >= 4:
            return

        closeness = 45
        trust = 45
        conflict = 0
        if rel_type == "rival":
            conflict = 55
            closeness = 35
        elif rel_type in {"mentor", "benefactor"}:
            trust = 65
            closeness = 50

        self._create_relationship(
            social,
            relationship_type=rel_type,
            role=rel_type,
            source="work",
            age=next_age,
            closeness=closeness,
            trust=trust,
            conflict=conflict,
            familiarity=30,
        )

    def _create_relationship(
        self,
        social: SocialState,
        *,
        relationship_type: str,
        role: str,
        source: str,
        age: int,
        closeness: int,
        trust: int,
        conflict: int = 0,
        familiarity: int = 30,
        name: str | None = None,
        person_id: str | None = None,
    ) -> SocialRelationship:
        resolved_name = name or self._pick_name(relationship_type)
        person = SocialPerson(
            person_id=person_id or SocialState.new_person_id(),
            name=resolved_name,
            age=max(age - 1, 8),
            role=role,
            source=source,
            created_age=age,
            last_seen_age=age,
        )
        relationship = SocialRelationship(
            relationship_id=SocialState.new_relationship_id(),
            person_id=person.person_id,
            relationship_type=relationship_type,
            closeness=closeness,
            trust=trust,
            conflict=conflict,
            familiarity=familiarity,
            status="active",
            started_age=age,
            last_changed_age=age,
            last_interaction_age=age,
            source=source,
            importance=55 if relationship_type in {"mentor", "benefactor", "best_friend"} else 45,
        ).clamp_values()

        social.upsert_person(person)
        social.upsert_relationship(relationship)
        social.new_relationships_this_year.append(relationship.relationship_id)
        social.record_history(
            {
                "age": age,
                "relationship_id": relationship.relationship_id,
                "person_id": person.person_id,
                "change_type": "created",
                "relationship_type": relationship_type,
                "name": person.name,
            }
        )
        return relationship

    def _pick_name(self, relationship_type: str) -> str:
        pool = NAME_POOLS.get(relationship_type, NAME_POOLS["acquaintance"])
        return pool[self.rng.randint(0, len(pool) - 1)]
