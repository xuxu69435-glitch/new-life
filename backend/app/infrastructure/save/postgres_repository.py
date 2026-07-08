from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.engine.simulation_context import LifeState, YearResult
from app.infrastructure.save.db import init_database, session_scope
from app.infrastructure.save.orm_models import (
    LifeCurrentStateRow,
    LifeEventLogRow,
    LifeHeirContinuationRow,
    LifeInheritanceRow,
    LifeSaveRow,
    LifeYearSnapshotRow,
    TimelineEntryRow,
)
from app.modules.timeline.models import LifeEventLog, LifeSaveRecord, LifeYearSnapshot, TimelineEntry


def _parse_dt(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _record_to_row(record: LifeSaveRecord) -> dict[str, Any]:
    return {
        "life_id": record.life_id,
        "user_id": record.user_id,
        "local_user_id": record.local_user_id,
        "rule_version": record.rule_version,
        "is_dead": record.is_dead,
        "current_age": record.current_age,
        "current_generation": record.current_generation,
        "save_version": record.save_version,
        "metadata_json": dict(record.metadata),
        "updated_at": datetime.now(timezone.utc),
    }


def _row_to_record(row: LifeSaveRow) -> LifeSaveRecord:
    return LifeSaveRecord(
        life_id=row.life_id,
        user_id=row.user_id,
        local_user_id=row.local_user_id,
        rule_version=row.rule_version,
        created_at=_parse_dt(row.created_at),
        updated_at=_parse_dt(row.updated_at),
        is_dead=row.is_dead,
        current_age=row.current_age,
        current_generation=row.current_generation,
        save_version=row.save_version,
        metadata=dict(row.metadata_json or {}),
    )


def _snapshot_to_row(snapshot: LifeYearSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "life_id": snapshot.life_id,
        "age_before": snapshot.age_before,
        "age_after": snapshot.age_after,
        "year_index": snapshot.year_index,
        "rule_version": snapshot.rule_version,
        "state_before_json": dict(snapshot.state_before),
        "state_after_json": dict(snapshot.state_after),
        "year_result_json": dict(snapshot.year_result),
        "narrative_result_json": snapshot.narrative_result,
        "triggered_random_events_json": list(snapshot.triggered_random_events),
        "legal_events_json": list(snapshot.legal_events),
        "mainline_changes_json": dict(snapshot.mainline_changes),
        "achievement_changes_json": dict(snapshot.achievement_changes),
        "milestones_json": list(snapshot.milestones),
        "death_result_json": snapshot.death_result,
        "inheritance_result_json": snapshot.inheritance_result,
        "snapshot_version": snapshot.snapshot_version,
    }


def _row_to_snapshot(row: LifeYearSnapshotRow) -> LifeYearSnapshot:
    return LifeYearSnapshot(
        snapshot_id=row.snapshot_id,
        life_id=row.life_id,
        age_before=row.age_before,
        age_after=row.age_after,
        year_index=row.year_index,
        rule_version=row.rule_version,
        state_before=dict(row.state_before_json or {}),
        state_after=dict(row.state_after_json or {}),
        year_result=dict(row.year_result_json or {}),
        narrative_result=dict(row.narrative_result_json) if row.narrative_result_json else None,
        triggered_random_events=list(row.triggered_random_events_json or []),
        legal_events=list(row.legal_events_json or []),
        mainline_changes=dict(row.mainline_changes_json or {}),
        achievement_changes=dict(row.achievement_changes_json or {}),
        milestones=list(row.milestones_json or []),
        death_result=dict(row.death_result_json) if row.death_result_json else None,
        inheritance_result=dict(row.inheritance_result_json) if row.inheritance_result_json else None,
        created_at=_parse_dt(row.created_at),
        snapshot_version=row.snapshot_version,
    )


def _row_to_event_log(row: LifeEventLogRow) -> LifeEventLog:
    return LifeEventLog(
        event_log_id=row.event_log_id,
        life_id=row.life_id,
        age=row.age,
        event_type=row.event_type,
        event_category=row.event_category,
        source_module=row.source_module,
        source_event_id=row.source_event_id,
        title=row.title,
        description=row.description,
        payload=dict(row.payload_json or {}),
        priority=row.priority,
        created_at=_parse_dt(row.created_at),
    )


def _row_to_timeline_entry(row: TimelineEntryRow) -> TimelineEntry:
    return TimelineEntry(
        entry_id=row.entry_id,
        life_id=row.life_id,
        age=row.age,
        title=row.title,
        summary=row.summary,
        entry_type=row.entry_type,
        category=row.category,
        source_module=row.source_module,
        source_id=row.source_id,
        importance=row.importance,
        tags=list(row.tags_json or []),
        display_text=row.display_text,
        related_snapshot_id=row.related_snapshot_id,
        created_at=_parse_dt(row.created_at),
    )


class PostgresSaveRepository:
    def __init__(self, *, auto_init: bool = True) -> None:
        if auto_init:
            init_database(create_tables=True)

    def save_record(self, record: LifeSaveRecord) -> None:
        payload = _record_to_row(record)
        with session_scope() as session:
            stmt = insert(LifeSaveRow).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LifeSaveRow.life_id],
                set_={
                    "user_id": stmt.excluded.user_id,
                    "local_user_id": stmt.excluded.local_user_id,
                    "rule_version": stmt.excluded.rule_version,
                    "is_dead": stmt.excluded.is_dead,
                    "current_age": stmt.excluded.current_age,
                    "current_generation": stmt.excluded.current_generation,
                    "save_version": stmt.excluded.save_version,
                    "metadata_json": stmt.excluded.metadata_json,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    def get_record(self, life_id: str) -> LifeSaveRecord | None:
        with session_scope() as session:
            row = session.get(LifeSaveRow, life_id)
            return _row_to_record(row) if row else None

    def list_records(self) -> list[LifeSaveRecord]:
        with session_scope() as session:
            rows = session.scalars(select(LifeSaveRow).order_by(LifeSaveRow.updated_at.desc())).all()
            return [_row_to_record(row) for row in rows]

    def save_state(self, state: LifeState) -> None:
        payload = {
            "life_id": state.life_id,
            "state_json": state.model_dump(mode="json"),
            "updated_at": datetime.now(timezone.utc),
        }
        with session_scope() as session:
            stmt = insert(LifeCurrentStateRow).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LifeCurrentStateRow.life_id],
                set_={
                    "state_json": stmt.excluded.state_json,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    def get_state(self, life_id: str) -> LifeState:
        with session_scope() as session:
            row = session.get(LifeCurrentStateRow, life_id)
            if row is None:
                raise KeyError(life_id)
            return LifeState.model_validate(dict(row.state_json))

    def state_exists(self, life_id: str) -> bool:
        with session_scope() as session:
            row = session.get(LifeCurrentStateRow, life_id)
            return row is not None

    def append_year_result(self, result: YearResult) -> None:
        with session_scope() as session:
            existing = session.scalar(
                select(LifeYearSnapshotRow).where(
                    LifeYearSnapshotRow.life_id == result.life_id,
                    LifeYearSnapshotRow.age_after == result.age_after,
                )
            )
            year_result_json = result.model_dump(mode="json")
            if existing is not None:
                existing.year_result_json = year_result_json
            else:
                session.add(
                    LifeYearSnapshotRow(
                        snapshot_id=f"yr-{result.life_id}-{result.age_after}",
                        life_id=result.life_id,
                        age_before=result.age_before,
                        age_after=result.age_after,
                        year_index=result.age_after,
                        rule_version="v1",
                        state_before_json={"life_id": result.life_id, "age": result.age_before},
                        state_after_json={"life_id": result.life_id, "age": result.age_after},
                        year_result_json=year_result_json,
                    )
                )

    def get_year_results(self, life_id: str) -> list[YearResult]:
        with session_scope() as session:
            rows = session.scalars(
                select(LifeYearSnapshotRow)
                .where(LifeYearSnapshotRow.life_id == life_id)
                .order_by(LifeYearSnapshotRow.age_after.asc())
            ).all()
            results: list[YearResult] = []
            for row in rows:
                if row.year_result_json:
                    results.append(YearResult.model_validate(dict(row.year_result_json)))
            return results

    def get_year_result_by_age(self, life_id: str, age: int) -> YearResult | None:
        with session_scope() as session:
            row = session.scalar(
                select(LifeYearSnapshotRow).where(
                    LifeYearSnapshotRow.life_id == life_id,
                    LifeYearSnapshotRow.age_after == age,
                )
            )
            if row is None or not row.year_result_json:
                return None
            return YearResult.model_validate(dict(row.year_result_json))

    def append_snapshot(self, snapshot: LifeYearSnapshot) -> None:
        payload = _snapshot_to_row(snapshot)
        with session_scope() as session:
            stmt = insert(LifeYearSnapshotRow).values(**payload)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_life_year_snapshots_life_age",
                set_={
                    "snapshot_id": stmt.excluded.snapshot_id,
                    "age_before": stmt.excluded.age_before,
                    "year_index": stmt.excluded.year_index,
                    "rule_version": stmt.excluded.rule_version,
                    "state_before_json": stmt.excluded.state_before_json,
                    "state_after_json": stmt.excluded.state_after_json,
                    "year_result_json": stmt.excluded.year_result_json,
                    "narrative_result_json": stmt.excluded.narrative_result_json,
                    "triggered_random_events_json": stmt.excluded.triggered_random_events_json,
                    "legal_events_json": stmt.excluded.legal_events_json,
                    "mainline_changes_json": stmt.excluded.mainline_changes_json,
                    "achievement_changes_json": stmt.excluded.achievement_changes_json,
                    "milestones_json": stmt.excluded.milestones_json,
                    "death_result_json": stmt.excluded.death_result_json,
                    "inheritance_result_json": stmt.excluded.inheritance_result_json,
                    "snapshot_version": stmt.excluded.snapshot_version,
                },
            )
            session.execute(stmt)

    def get_snapshots(self, life_id: str) -> list[LifeYearSnapshot]:
        with session_scope() as session:
            rows = session.scalars(
                select(LifeYearSnapshotRow)
                .where(LifeYearSnapshotRow.life_id == life_id)
                .order_by(LifeYearSnapshotRow.age_after.asc())
            ).all()
            return [_row_to_snapshot(row) for row in rows]

    def get_snapshot_by_age(self, life_id: str, age: int) -> LifeYearSnapshot | None:
        with session_scope() as session:
            row = session.scalar(
                select(LifeYearSnapshotRow).where(
                    LifeYearSnapshotRow.life_id == life_id,
                    LifeYearSnapshotRow.age_after == age,
                )
            )
            return _row_to_snapshot(row) if row else None

    def append_event_logs(self, life_id: str, logs: list[LifeEventLog]) -> None:
        if not logs:
            return
        with session_scope() as session:
            for item in logs:
                payload = {
                    "event_log_id": item.event_log_id,
                    "life_id": life_id,
                    "age": item.age,
                    "event_type": item.event_type,
                    "event_category": item.event_category,
                    "source_module": item.source_module,
                    "source_event_id": item.source_event_id,
                    "title": item.title,
                    "description": item.description,
                    "payload_json": dict(item.payload),
                    "priority": item.priority,
                }
                stmt = insert(LifeEventLogRow).values(**payload)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[LifeEventLogRow.event_log_id],
                    set_={
                        "age": stmt.excluded.age,
                        "event_type": stmt.excluded.event_type,
                        "event_category": stmt.excluded.event_category,
                        "source_module": stmt.excluded.source_module,
                        "source_event_id": stmt.excluded.source_event_id,
                        "title": stmt.excluded.title,
                        "description": stmt.excluded.description,
                        "payload_json": stmt.excluded.payload_json,
                        "priority": stmt.excluded.priority,
                    },
                )
                session.execute(stmt)

    def get_event_logs(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        event_category: str | None = None,
    ) -> list[LifeEventLog]:
        with session_scope() as session:
            query = select(LifeEventLogRow).where(LifeEventLogRow.life_id == life_id)
            if age_min is not None:
                query = query.where(LifeEventLogRow.age >= age_min)
            if age_max is not None:
                query = query.where(LifeEventLogRow.age <= age_max)
            if event_category is not None:
                query = query.where(LifeEventLogRow.event_category == event_category)
            rows = session.scalars(query.order_by(LifeEventLogRow.age.asc())).all()
            return [_row_to_event_log(row) for row in rows]

    def append_timeline_entries(self, life_id: str, entries: list[TimelineEntry]) -> None:
        if not entries:
            return
        with session_scope() as session:
            for item in entries:
                payload = {
                    "entry_id": item.entry_id,
                    "life_id": life_id,
                    "age": item.age,
                    "title": item.title,
                    "summary": item.summary,
                    "entry_type": item.entry_type,
                    "category": item.category,
                    "source_module": item.source_module,
                    "source_id": item.source_id,
                    "importance": item.importance,
                    "tags_json": list(item.tags),
                    "display_text": item.display_text,
                    "related_snapshot_id": item.related_snapshot_id,
                }
                stmt = insert(TimelineEntryRow).values(**payload)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[TimelineEntryRow.entry_id],
                    set_={
                        "age": stmt.excluded.age,
                        "title": stmt.excluded.title,
                        "summary": stmt.excluded.summary,
                        "entry_type": stmt.excluded.entry_type,
                        "category": stmt.excluded.category,
                        "source_module": stmt.excluded.source_module,
                        "source_id": stmt.excluded.source_id,
                        "importance": stmt.excluded.importance,
                        "tags_json": stmt.excluded.tags_json,
                        "display_text": stmt.excluded.display_text,
                        "related_snapshot_id": stmt.excluded.related_snapshot_id,
                    },
                )
                session.execute(stmt)

    def get_timeline_entries(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        entry_type: str | None = None,
    ) -> list[TimelineEntry]:
        with session_scope() as session:
            query = select(TimelineEntryRow).where(TimelineEntryRow.life_id == life_id)
            if age_min is not None:
                query = query.where(TimelineEntryRow.age >= age_min)
            if age_max is not None:
                query = query.where(TimelineEntryRow.age <= age_max)
            if entry_type is not None:
                query = query.where(TimelineEntryRow.entry_type == entry_type)
            rows = session.scalars(
                query.order_by(TimelineEntryRow.importance.desc(), TimelineEntryRow.age.asc())
            ).all()
            return [_row_to_timeline_entry(row) for row in rows]

    def save_inheritance(self, life_id: str, result: dict[str, Any]) -> None:
        payload = {
            "life_id": life_id,
            "result_json": dict(result),
            "updated_at": datetime.now(timezone.utc),
        }
        with session_scope() as session:
            stmt = insert(LifeInheritanceRow).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LifeInheritanceRow.life_id],
                set_={
                    "result_json": stmt.excluded.result_json,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    def get_inheritance(self, life_id: str) -> dict[str, Any]:
        with session_scope() as session:
            row = session.get(LifeInheritanceRow, life_id)
            if row is None:
                return {"status": "not_available"}
            return dict(row.result_json)

    def save_heir_continuation(self, source_life_id: str, record: dict[str, Any]) -> None:
        payload = {
            "source_life_id": source_life_id,
            "record_json": dict(record),
            "updated_at": datetime.now(timezone.utc),
        }
        with session_scope() as session:
            stmt = insert(LifeHeirContinuationRow).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LifeHeirContinuationRow.source_life_id],
                set_={
                    "record_json": stmt.excluded.record_json,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    def get_heir_continuation(self, source_life_id: str) -> dict[str, Any] | None:
        with session_scope() as session:
            row = session.get(LifeHeirContinuationRow, source_life_id)
            return dict(row.record_json) if row else None

    def persist_year_bundle(
        self,
        *,
        snapshot: LifeYearSnapshot,
        year_result: YearResult,
        event_logs: list[LifeEventLog],
        timeline_entries: list[TimelineEntry],
    ) -> None:
        with session_scope() as session:
            snapshot_payload = _snapshot_to_row(snapshot)
            stmt = insert(LifeYearSnapshotRow).values(**snapshot_payload)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_life_year_snapshots_life_age",
                set_={
                    "snapshot_id": stmt.excluded.snapshot_id,
                    "age_before": stmt.excluded.age_before,
                    "year_index": stmt.excluded.year_index,
                    "rule_version": stmt.excluded.rule_version,
                    "state_before_json": stmt.excluded.state_before_json,
                    "state_after_json": stmt.excluded.state_after_json,
                    "year_result_json": stmt.excluded.year_result_json,
                    "narrative_result_json": stmt.excluded.narrative_result_json,
                    "triggered_random_events_json": stmt.excluded.triggered_random_events_json,
                    "legal_events_json": stmt.excluded.legal_events_json,
                    "mainline_changes_json": stmt.excluded.mainline_changes_json,
                    "achievement_changes_json": stmt.excluded.achievement_changes_json,
                    "milestones_json": stmt.excluded.milestones_json,
                    "death_result_json": stmt.excluded.death_result_json,
                    "inheritance_result_json": stmt.excluded.inheritance_result_json,
                    "snapshot_version": stmt.excluded.snapshot_version,
                },
            )
            session.execute(stmt)

            session.execute(
                delete(LifeEventLogRow).where(
                    LifeEventLogRow.life_id == snapshot.life_id,
                    LifeEventLogRow.age == snapshot.age_after,
                )
            )
            session.execute(
                delete(TimelineEntryRow).where(
                    TimelineEntryRow.life_id == snapshot.life_id,
                    TimelineEntryRow.age == snapshot.age_after,
                )
            )

            for item in event_logs:
                payload = {
                    "event_log_id": item.event_log_id,
                    "life_id": snapshot.life_id,
                    "age": item.age,
                    "event_type": item.event_type,
                    "event_category": item.event_category,
                    "source_module": item.source_module,
                    "source_event_id": item.source_event_id,
                    "title": item.title,
                    "description": item.description,
                    "payload_json": dict(item.payload),
                    "priority": item.priority,
                }
                session.execute(insert(LifeEventLogRow).values(**payload))

            for item in timeline_entries:
                payload = {
                    "entry_id": item.entry_id,
                    "life_id": snapshot.life_id,
                    "age": item.age,
                    "title": item.title,
                    "summary": item.summary,
                    "entry_type": item.entry_type,
                    "category": item.category,
                    "source_module": item.source_module,
                    "source_id": item.source_id,
                    "importance": item.importance,
                    "tags_json": list(item.tags),
                    "display_text": item.display_text,
                    "related_snapshot_id": item.related_snapshot_id,
                }
                session.execute(insert(TimelineEntryRow).values(**payload))
