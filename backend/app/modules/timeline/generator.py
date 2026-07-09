from typing import Any

from app.engine.simulation_context import SimulationEvent, YearResult
from app.modules.timeline.constants import ENTRY_IMPORTANCE
from app.modules.timeline.models import LifeEventLog, LifeYearSnapshot, TimelineEntry


class EventLogBuilder:
    _MODULE_CATEGORY_MAP = {
        "random_events": "random_event",
        "legal": "legal_event",
        "mainline": "mainline_task",
        "achievement": "achievement",
        "family": "family",
        "social": "relationship",
        "romance": "relationship",
        "education": "education",
        "career": "career",
        "health": "health",
        "assets": "asset",
        "death": "death",
        "inheritance": "inheritance",
        "narrative": "narrative",
    }

    def build(self, result: YearResult, snapshot_id: str = "") -> list[LifeEventLog]:
        logs: list[LifeEventLog] = []
        age = result.age_after
        life_id = result.life_id

        for event in result.occurred_events:
            logs.append(self._from_simulation_event(life_id, age, event))

        for item in result.triggered_random_events:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="random_event",
                    event_category="random_event",
                    source_module="random_events",
                    source_event_id=str(item.get("event_id", "")),
                    title=str(item.get("name", "随机事件")),
                    description=str(item.get("narrative_text", "")),
                    payload={"event_id": item.get("event_id"), "category": item.get("category")},
                    priority=ENTRY_IMPORTANCE["random_event"],
                )
            )

        if result.legal_changes or result.pending_legal_event:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="legal_event",
                    event_category="legal_event",
                    source_module="legal",
                    title="法律事件",
                    description=str(result.legal_changes.get("summary", "本年发生法律相关变化。")),
                    payload={
                        "legal_changes": dict(result.legal_changes),
                        "pending_legal_event": result.pending_legal_event,
                    },
                    priority=ENTRY_IMPORTANCE["legal_event"],
                )
            )

        for task_id in result.completed_mainline_tasks_this_year:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="mainline_task",
                    event_category="mainline_task",
                    source_module="mainline",
                    source_event_id=task_id,
                    title=f"完成主线：{task_id}",
                    description="",
                    payload={"task_id": task_id, "status": "completed"},
                    priority=ENTRY_IMPORTANCE["mainline_task"],
                )
            )

        for item in result.newly_unlocked_achievements:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="achievement",
                    event_category="achievement",
                    source_module="achievement",
                    source_event_id=str(item.get("achievement_id", "")),
                    title=str(item.get("title", "成就解锁")),
                    description=str(item.get("description", "")),
                    payload={"achievement_id": item.get("achievement_id"), "points": item.get("points_gained", 0)},
                    priority=ENTRY_IMPORTANCE["achievement"],
                )
            )

        for item in result.milestones_this_year:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="milestone",
                    event_category="milestone",
                    source_module="achievement",
                    source_event_id=str(item.get("milestone_id", "")),
                    title=str(item.get("title", "里程碑")),
                    description=str(item.get("description", "")),
                    payload=dict(item),
                    priority=ENTRY_IMPORTANCE["milestone"],
                )
            )

        if result.is_dead:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="death",
                    event_category="death",
                    source_module="death",
                    title="死亡",
                    description=str(result.death_reason or "人生结束"),
                    payload={
                        "death_reason": result.death_reason,
                        "death_type": result.death_type,
                        "snapshot_id": snapshot_id,
                    },
                    priority=ENTRY_IMPORTANCE["death"],
                )
            )

        if result.inheritance_result:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="inheritance",
                    event_category="inheritance",
                    source_module="inheritance",
                    title="遗产结算",
                    description=f"净遗产 {result.inheritance_result.get('net_estate', 0)}",
                    payload=dict(result.inheritance_result),
                    priority=ENTRY_IMPORTANCE["inheritance"],
                )
            )

        if result.education_graduated_this_year or (
            result.education_stage_before != result.education_stage_after
        ):
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="education",
                    event_category="education",
                    source_module="education",
                    title="教育变化",
                    description=f"{result.education_stage_before} → {result.education_stage_after}",
                    payload=dict(result.education_changes),
                    priority=ENTRY_IMPORTANCE["education"],
                )
            )

        if result.career_status_before != result.career_status_after or result.career_income_change:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="career",
                    event_category="career",
                    source_module="career",
                    title="职业变化",
                    description=f"{result.career_status_before} → {result.career_status_after}",
                    payload={
                        "career_path": result.career_path,
                        "annual_income": result.annual_income,
                        "income_change": result.career_income_change,
                    },
                    priority=ENTRY_IMPORTANCE["career"],
                )
            )

        if result.married_this_year or result.child_born_this_year or result.family_history_records:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="family",
                    event_category="family",
                    source_module="family",
                    title="家庭变化",
                    description=self._family_summary(result),
                    payload={
                        "married_this_year": result.married_this_year,
                        "child_born_this_year": result.child_born_this_year,
                        "family_changes": dict(result.family_changes),
                    },
                    priority=ENTRY_IMPORTANCE["family"],
                )
            )

        if result.new_health_warnings:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="health",
                    event_category="health",
                    source_module="health",
                    title="健康警示",
                    description="; ".join(result.new_health_warnings),
                    payload={"warnings": list(result.new_health_warnings)},
                    priority=ENTRY_IMPORTANCE["health"],
                )
            )

        if result.changed_assets:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="asset",
                    event_category="asset",
                    source_module="assets",
                    title="资产变化",
                    description=str(result.changed_assets),
                    payload={"changed_assets": dict(result.changed_assets)},
                    priority=ENTRY_IMPORTANCE["asset"],
                )
            )

        if result.narrative_text or result.annual_summary_text:
            logs.append(
                LifeEventLog(
                    life_id=life_id,
                    age=age,
                    event_type="narrative",
                    event_category="narrative",
                    source_module="narrative",
                    title="年度叙事",
                    description=result.annual_summary_text or result.narrative_text,
                    payload={"narrative_result": result.narrative_result},
                    priority=ENTRY_IMPORTANCE["narrative"],
                )
            )

        return logs

    def _from_simulation_event(self, life_id: str, age: int, event: SimulationEvent) -> LifeEventLog:
        category = self._MODULE_CATEGORY_MAP.get(event.source_module, "system")
        event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        return LifeEventLog(
            life_id=life_id,
            age=age,
            event_type=event_type,
            event_category=category,
            source_module=event.source_module,
            source_event_id=event_type,
            title=event_type,
            description="",
            payload=dict(event.payload),
            priority=ENTRY_IMPORTANCE.get(category, ENTRY_IMPORTANCE["system"]),
        )

    def _family_summary(self, result: YearResult) -> str:
        parts: list[str] = []
        if result.married_this_year:
            parts.append("结婚")
        if result.child_born_this_year:
            parts.append("生育")
        if result.relationship_status_after:
            parts.append(f"关系：{result.relationship_status_after}")
        return "，".join(parts) if parts else "家庭关系发生变化"


class TimelineGenerator:
    def generate(self, result: YearResult, snapshot: LifeYearSnapshot) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []
        age = result.age_after
        life_id = result.life_id
        snapshot_id = snapshot.snapshot_id

        summary_text = result.annual_summary_text or result.narrative_text or f"{age}岁的一年"
        entries.append(
            TimelineEntry(
                life_id=life_id,
                age=age,
                title=f"{age}岁 · 年度概览",
                summary=summary_text,
                entry_type="normal_summary",
                category="narrative",
                source_module="narrative",
                importance=ENTRY_IMPORTANCE["normal_summary"],
                tags=["annual_summary"],
                display_text=summary_text,
                related_snapshot_id=snapshot_id,
            )
        )

        for item in result.major_event_texts:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="重大事件",
                    summary=str(item),
                    entry_type="narrative",
                    category="narrative",
                    source_module="narrative",
                    importance=ENTRY_IMPORTANCE["narrative"] + 5,
                    tags=["major_event"],
                    display_text=str(item),
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.is_dead:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="死亡",
                    summary=str(result.death_reason or "人生结束"),
                    entry_type="death",
                    category="death",
                    source_module="death",
                    importance=ENTRY_IMPORTANCE["death"],
                    tags=["death"],
                    display_text=str(result.death_reason or "人生结束"),
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.inheritance_result:
            net_estate = result.inheritance_result.get("net_estate", 0)
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="遗产结算",
                    summary=f"净遗产 {net_estate}",
                    entry_type="inheritance",
                    category="inheritance",
                    source_module="inheritance",
                    importance=ENTRY_IMPORTANCE["inheritance"],
                    tags=["inheritance"],
                    display_text=f"净遗产 {net_estate}",
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.legal_changes or result.pending_legal_event:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="法律事件",
                    summary=str(result.legal_changes.get("summary", "法律状态发生变化")),
                    entry_type="legal_event",
                    category="legal_event",
                    source_module="legal",
                    importance=ENTRY_IMPORTANCE["legal_event"],
                    tags=["legal"],
                    display_text=str(result.legal_changes.get("summary", "法律状态发生变化")),
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.married_this_year or result.child_born_this_year:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="家庭重大事件",
                    summary=EventLogBuilder()._family_summary(result),
                    entry_type="family",
                    category="family",
                    source_module="family",
                    importance=ENTRY_IMPORTANCE["family"],
                    tags=["family"],
                    display_text=EventLogBuilder()._family_summary(result),
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.new_social_relationships or result.removed_social_relationships:
            for item in result.new_social_relationships:
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="社交关系",
                        summary=f"结识{item.get('person_name', '新朋友')}",
                        entry_type="social",
                        category="relationship",
                        source_module="social",
                        importance=ENTRY_IMPORTANCE["social"],
                        tags=["social", str(item.get("relationship_type", ""))],
                        display_text=f"结识{item.get('person_name', '新朋友')}",
                        related_snapshot_id=snapshot_id,
                    )
                )
            for rel_id in result.removed_social_relationships:
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="关系破裂",
                        summary=f"关系 {rel_id} 结束",
                        entry_type="social",
                        category="relationship",
                        source_module="social",
                        source_id=rel_id,
                        importance=ENTRY_IMPORTANCE["social"] + 5,
                        tags=["social", "broken"],
                        display_text="一段重要关系破裂。",
                        related_snapshot_id=snapshot_id,
                    )
                )
            for item in result.changed_social_relationships:
                if item.get("relationship_type") == "best_friend" or item.get("status") == "important":
                    entries.append(
                        TimelineEntry(
                            life_id=life_id,
                            age=age,
                            title="挚友",
                            summary=f"与{item.get('person_name', '朋友')}关系升级",
                            entry_type="social",
                            category="relationship",
                            source_module="social",
                            importance=ENTRY_IMPORTANCE["social"] + 3,
                            tags=["social", "best_friend"],
                            display_text=f"你与{item.get('person_name', '朋友')}成为挚友。",
                            related_snapshot_id=snapshot_id,
                        )
                    )
                elif item.get("relationship_type") == "rival":
                    entries.append(
                        TimelineEntry(
                            life_id=life_id,
                            age=age,
                            title="竞争关系",
                            summary=f"与{item.get('person_name', '同事')}矛盾加深",
                            entry_type="social",
                            category="relationship",
                            source_module="social",
                            importance=ENTRY_IMPORTANCE["social"] + 2,
                            tags=["social", "rival"],
                            display_text=f"你与{item.get('person_name', '同事')}的矛盾加深。",
                            related_snapshot_id=snapshot_id,
                        )
                    )

        if result.new_romantic_candidates or result.romance_changes or result.ended_romantic_relationships:
            for item in result.new_romantic_candidates:
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="情感变化",
                        summary=f"对{item.get('name', '某人')}产生好感",
                        entry_type="romance",
                        category="relationship",
                        source_module="romance",
                        importance=ENTRY_IMPORTANCE["romance"],
                        tags=["romance", "candidate"],
                        display_text=f"你对{item.get('name', '某人')}产生了好感。",
                        related_snapshot_id=snapshot_id,
                    )
                )
            current = result.current_romantic_relationship or {}
            status = str(current.get("status", ""))
            partner = str(current.get("partner_name", "恋人"))
            if status == "dating":
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="开始恋爱",
                        summary=f"与{partner}开始恋爱",
                        entry_type="romance",
                        category="relationship",
                        source_module="romance",
                        importance=ENTRY_IMPORTANCE["romance"] + 5,
                        tags=["romance", "dating"],
                        display_text=f"你与{partner}开始了一段恋爱关系。",
                        related_snapshot_id=snapshot_id,
                    )
                )
            elif status == "cooling_off":
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="关系冷淡",
                        summary=f"与{partner}关系冷淡",
                        entry_type="romance",
                        category="relationship",
                        source_module="romance",
                        importance=ENTRY_IMPORTANCE["romance"] + 3,
                        tags=["romance", "cooling_off"],
                        display_text=f"你与{partner}的关系进入冷淡期。",
                        related_snapshot_id=snapshot_id,
                    )
                )
            elif status == "engagement_intent":
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="订婚意向",
                        summary=f"与{partner}考虑未来",
                        entry_type="romance",
                        category="relationship",
                        source_module="romance",
                        importance=ENTRY_IMPORTANCE["romance"] + 8,
                        tags=["romance", "engagement_intent"],
                        display_text=f"你与{partner}开始认真考虑未来。",
                        related_snapshot_id=snapshot_id,
                    )
                )
            for rel_id in result.ended_romantic_relationships:
                entries.append(
                    TimelineEntry(
                        life_id=life_id,
                        age=age,
                        title="恋爱结束",
                        summary="结束一段恋爱关系",
                        entry_type="romance",
                        category="relationship",
                        source_module="romance",
                        importance=ENTRY_IMPORTANCE["romance"] + 6,
                        tags=["romance", "broken_up"],
                        display_text="你结束了一段恋爱关系。",
                        related_snapshot_id=snapshot_id,
                    )
                )

        if result.education_graduated_this_year or (
            result.education_stage_before != result.education_stage_after
        ):
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="教育变化",
                    summary=f"{result.education_stage_before} → {result.education_stage_after}",
                    entry_type="education",
                    category="education",
                    source_module="education",
                    importance=ENTRY_IMPORTANCE["education"],
                    tags=["education"],
                    display_text=f"{result.education_stage_before} → {result.education_stage_after}",
                    related_snapshot_id=snapshot_id,
                )
            )

        if result.career_status_before != result.career_status_after or result.career_income_change:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title="职业变化",
                    summary=f"收入 {result.annual_income}",
                    entry_type="career",
                    category="career",
                    source_module="career",
                    importance=ENTRY_IMPORTANCE["career"],
                    tags=["career"],
                    display_text=f"{result.career_status_before} → {result.career_status_after}",
                    related_snapshot_id=snapshot_id,
                )
            )

        for task_id in result.completed_mainline_tasks_this_year:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title=f"主线完成：{task_id}",
                    summary="",
                    entry_type="mainline_task",
                    category="mainline_task",
                    source_module="mainline",
                    source_id=task_id,
                    importance=ENTRY_IMPORTANCE["mainline_task"],
                    tags=["mainline"],
                    display_text=f"完成主线任务 {task_id}",
                    related_snapshot_id=snapshot_id,
                )
            )

        for item in result.newly_unlocked_achievements:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title=str(item.get("title", "成就解锁")),
                    summary=str(item.get("description", "")),
                    entry_type="achievement",
                    category="achievement",
                    source_module="achievement",
                    source_id=str(item.get("achievement_id", "")),
                    importance=ENTRY_IMPORTANCE["achievement"],
                    tags=["achievement"],
                    display_text=str(item.get("narrative_text", item.get("title", ""))),
                    related_snapshot_id=snapshot_id,
                )
            )

        for item in result.milestones_this_year:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title=str(item.get("title", "里程碑")),
                    summary=str(item.get("description", "")),
                    entry_type="milestone",
                    category="milestone",
                    source_module="achievement",
                    source_id=str(item.get("milestone_id", "")),
                    importance=ENTRY_IMPORTANCE["milestone"],
                    tags=["milestone"],
                    display_text=str(item.get("title", "")),
                    related_snapshot_id=snapshot_id,
                )
            )

        for item in result.triggered_random_events:
            entries.append(
                TimelineEntry(
                    life_id=life_id,
                    age=age,
                    title=str(item.get("name", "随机事件")),
                    summary=str(item.get("narrative_text", "")),
                    entry_type="random_event",
                    category="random_event",
                    source_module="random_events",
                    source_id=str(item.get("event_id", "")),
                    importance=ENTRY_IMPORTANCE["random_event"],
                    tags=["random_event"],
                    display_text=str(item.get("narrative_text", item.get("name", ""))),
                    related_snapshot_id=snapshot_id,
                )
            )

        entries.sort(key=lambda entry: (-entry.importance, entry.age))
        return entries
