from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LifeSaveRow(Base):
    __tablename__ = "life_saves"

    life_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, default="local_user")
    local_user_id: Mapped[str] = mapped_column(String(64), nullable=False, default="local_user")
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_dead: Mapped[bool] = mapped_column(default=False)
    current_age: Mapped[int] = mapped_column(Integer, default=0)
    current_generation: Mapped[int] = mapped_column(Integer, default=1)
    save_version: Mapped[str] = mapped_column(String(16), default="v1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("ix_life_saves_updated_at", "updated_at"),
        Index("ix_life_saves_user_id", "user_id"),
    )


class LifeCurrentStateRow(Base):
    __tablename__ = "life_current_states"

    life_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LifeYearSnapshotRow(Base):
    __tablename__ = "life_year_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    life_id: Mapped[str] = mapped_column(String(64), nullable=False)
    age_before: Mapped[int] = mapped_column(Integer, nullable=False)
    age_after: Mapped[int] = mapped_column(Integer, nullable=False)
    year_index: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    state_before_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state_after_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    year_result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    narrative_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    triggered_random_events_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    legal_events_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    mainline_changes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    achievement_changes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    milestones_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    death_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    inheritance_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot_version: Mapped[str] = mapped_column(String(16), default="v1")

    __table_args__ = (
        UniqueConstraint("life_id", "age_after", name="uq_life_year_snapshots_life_age"),
        Index("ix_life_year_snapshots_life_age_after", "life_id", "age_after"),
        Index("ix_life_year_snapshots_life_year_index", "life_id", "year_index"),
    )


class LifeEventLogRow(Base):
    __tablename__ = "life_event_logs"

    event_log_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    life_id: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_category: Mapped[str] = mapped_column(String(64), nullable=False)
    source_module: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_life_event_logs_life_age", "life_id", "age"),
        Index("ix_life_event_logs_event_type", "event_type"),
        Index("ix_life_event_logs_source_module", "source_module"),
    )


class TimelineEntryRow(Base):
    __tablename__ = "timeline_entries"

    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    life_id: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    entry_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    source_module: Mapped[str] = mapped_column(String(64), default="timeline")
    source_id: Mapped[str] = mapped_column(String(128), default="")
    importance: Mapped[int] = mapped_column(Integer, default=10)
    tags_json: Mapped[list[str]] = mapped_column(JSONB, default=list)
    display_text: Mapped[str] = mapped_column(Text, default="")
    related_snapshot_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_timeline_entries_life_age", "life_id", "age"),
        Index("ix_timeline_entries_entry_type", "entry_type"),
        Index("ix_timeline_entries_life_importance", "life_id", "importance"),
    )


class LifeInheritanceRow(Base):
    __tablename__ = "life_inheritance_results"

    life_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LifeHeirContinuationRow(Base):
    __tablename__ = "life_heir_continuations"

    source_life_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    record_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
