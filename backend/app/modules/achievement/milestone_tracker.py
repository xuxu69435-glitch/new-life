from typing import Any

from app.engine.simulation_context import LifeState
from app.modules.achievement.models import AchievementState
from app.modules.career.models import CareerState
from app.modules.education.models import EducationState
from app.modules.family.models import FamilyState
from app.modules.legal.models import LegalState


class MilestoneTracker:
    MILESTONE_DEFS: list[dict[str, Any]] = [
        {"id": "enter_primary", "title": "进入小学", "stage": "primary_school"},
        {"id": "enter_middle", "title": "进入初中", "stage": "middle_school"},
        {"id": "enter_high", "title": "进入高中", "stage": "high_school"},
        {"id": "enter_college", "title": "进入大学", "stage": "college"},
        {"id": "first_job", "title": "第一次工作", "career_status": "employed"},
        {"id": "first_dating", "title": "第一次恋爱", "relationship": "dating"},
        {"id": "marriage", "title": "结婚", "relationship": "married"},
        {"id": "childbirth", "title": "生育子女", "children_min": 1},
        {"id": "imprisonment", "title": "入狱", "legal": "in_prison"},
        {"id": "release", "title": "出狱", "legal": "released"},
        {"id": "retirement", "title": "退休", "career_status": "retired"},
        {"id": "age_60", "title": "达到60岁", "age_min": 60},
        {"id": "age_90", "title": "达到90岁", "age_min": 90},
        {"id": "death", "title": "死亡", "is_dead": True},
        {"id": "inheritance", "title": "留下遗产", "inheritance": True},
        {"id": "heir_continuation", "title": "继续后代人生", "flag": "heir_continuation_unlocked"},
    ]

    def detect(
        self,
        before: LifeState,
        after: LifeState,
        achievement: AchievementState,
        *,
        inheritance_result: dict[str, Any] | None = None,
        married_this_year: bool = False,
        child_born_this_year: bool = False,
    ) -> list[dict[str, Any]]:
        new_milestones: list[dict[str, Any]] = []
        education = EducationState.from_life_state_dict(after.education, {})
        career = CareerState.from_life_state_dict(after.career, {})
        family = FamilyState.from_life_state_dict(after.family)
        legal = LegalState.from_life_state_dict(after.legal)
        legal_before = LegalState.from_life_state_dict(before.legal)

        for item in self.MILESTONE_DEFS:
            milestone_id = item["id"]
            if achievement.has_milestone(milestone_id):
                continue
            if "stage" in item and education.current_stage == item["stage"]:
                new_milestones.append(self._record(item, after.age))
            elif "career_status" in item and career.employment_status == item["career_status"]:
                new_milestones.append(self._record(item, after.age))
            elif "relationship" in item and family.relationship_status == item["relationship"]:
                new_milestones.append(self._record(item, after.age))
            elif "children_min" in item and family.children_count >= int(item["children_min"]):
                new_milestones.append(self._record(item, after.age))
            elif item.get("legal") == "in_prison" and legal.is_in_prison:
                new_milestones.append(self._record(item, after.age))
            elif (
                item.get("legal") == "released"
                and legal_before.is_in_prison
                and not legal.is_in_prison
                and not legal.is_fugitive
            ):
                new_milestones.append(self._record(item, after.age))
            elif "age_min" in item and after.age >= int(item["age_min"]):
                new_milestones.append(self._record(item, after.age))
            elif item.get("is_dead") and after.is_dead:
                new_milestones.append(self._record(item, after.age))
            elif (
                item.get("inheritance")
                and inheritance_result
                and float(inheritance_result.get("net_estate", 0.0)) > 0
            ):
                new_milestones.append(self._record(item, after.age))
            elif item.get("flag") and achievement.achievement_flags.get(item["flag"]):
                new_milestones.append(self._record(item, after.age))

        if married_this_year and not achievement.has_milestone("marriage"):
            new_milestones.append(self._record({"id": "marriage", "title": "结婚"}, after.age))
        if child_born_this_year and not achievement.has_milestone("childbirth"):
            new_milestones.append(self._record({"id": "childbirth", "title": "生育子女"}, after.age))

        return new_milestones

    def _record(self, item: dict[str, Any], age: int) -> dict[str, Any]:
        return {
            "milestone_id": item["id"],
            "title": item["title"],
            "age": age,
            "year": age,
            "source": "achievement",
            "description": item["title"],
        }
