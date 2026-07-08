from typing import Any

from app.engine.simulation_context import LifeState, YearResult
from app.modules.timeline.models import LifeEventLog, LifeSaveRecord, LifeYearSnapshot, TimelineEntry


class InMemorySaveRepository:
    def __init__(self) -> None:
        self._records: dict[str, LifeSaveRecord] = {}
        self._states: dict[str, LifeState] = {}
        self._year_results: dict[str, list[YearResult]] = {}
        self._snapshots: dict[str, list[LifeYearSnapshot]] = {}
        self._event_logs: dict[str, list[LifeEventLog]] = {}
        self._timeline_entries: dict[str, list[TimelineEntry]] = {}
        self._inheritance: dict[str, dict[str, Any]] = {}
        self._heir_continuations: dict[str, dict[str, Any]] = {}

    def save_record(self, record: LifeSaveRecord) -> None:
        self._records[record.life_id] = record

    def get_record(self, life_id: str) -> LifeSaveRecord | None:
        return self._records.get(life_id)

    def list_records(self) -> list[LifeSaveRecord]:
        return list(self._records.values())

    def save_state(self, state: LifeState) -> None:
        self._states[state.life_id] = state

    def get_state(self, life_id: str) -> LifeState:
        if life_id not in self._states:
            raise KeyError(life_id)
        return self._states[life_id]

    def state_exists(self, life_id: str) -> bool:
        return life_id in self._states

    def append_year_result(self, result: YearResult) -> None:
        self._year_results.setdefault(result.life_id, []).append(result)

    def get_year_results(self, life_id: str) -> list[YearResult]:
        return list(self._year_results.get(life_id, []))

    def get_year_result_by_age(self, life_id: str, age: int) -> YearResult | None:
        for result in self._year_results.get(life_id, []):
            if result.age_after == age:
                return result
        return None

    def append_snapshot(self, snapshot: LifeYearSnapshot) -> None:
        self._snapshots.setdefault(snapshot.life_id, []).append(snapshot)

    def get_snapshots(self, life_id: str) -> list[LifeYearSnapshot]:
        return list(self._snapshots.get(life_id, []))

    def get_snapshot_by_age(self, life_id: str, age: int) -> LifeYearSnapshot | None:
        for snapshot in self._snapshots.get(life_id, []):
            if snapshot.age_after == age:
                return snapshot
        return None

    def append_event_logs(self, life_id: str, logs: list[LifeEventLog]) -> None:
        if logs:
            self._event_logs.setdefault(life_id, []).extend(logs)

    def get_event_logs(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        event_category: str | None = None,
    ) -> list[LifeEventLog]:
        logs = list(self._event_logs.get(life_id, []))
        if age_min is not None:
            logs = [item for item in logs if item.age >= age_min]
        if age_max is not None:
            logs = [item for item in logs if item.age <= age_max]
        if event_category is not None:
            logs = [item for item in logs if item.event_category == event_category]
        return logs

    def append_timeline_entries(self, life_id: str, entries: list[TimelineEntry]) -> None:
        if entries:
            self._timeline_entries.setdefault(life_id, []).extend(entries)

    def get_timeline_entries(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        entry_type: str | None = None,
    ) -> list[TimelineEntry]:
        entries = list(self._timeline_entries.get(life_id, []))
        if age_min is not None:
            entries = [item for item in entries if item.age >= age_min]
        if age_max is not None:
            entries = [item for item in entries if item.age <= age_max]
        if entry_type is not None:
            entries = [item for item in entries if item.entry_type == entry_type]
        entries.sort(key=lambda item: (-item.importance, item.age))
        return entries

    def save_inheritance(self, life_id: str, result: dict[str, Any]) -> None:
        self._inheritance[life_id] = result

    def get_inheritance(self, life_id: str) -> dict[str, Any]:
        return self._inheritance.get(life_id, {"status": "not_available"})

    def save_heir_continuation(self, source_life_id: str, record: dict[str, Any]) -> None:
        self._heir_continuations[source_life_id] = record

    def get_heir_continuation(self, source_life_id: str) -> dict[str, Any] | None:
        return self._heir_continuations.get(source_life_id)
