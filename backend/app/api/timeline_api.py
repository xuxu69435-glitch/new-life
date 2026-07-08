from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.application.game_command_service import game_service
from app.engine.simulation_context import YearResult

router = APIRouter(prefix="/timelines", tags=["timelines"])


@router.get("/{life_id}", response_model=list[YearResult])
def get_timeline(life_id: str) -> list[YearResult]:
    try:
        return game_service.get_timeline(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc


@router.get("/{life_id}/entries")
def get_timeline_entries(
    life_id: str,
    age_min: int | None = Query(default=None),
    age_max: int | None = Query(default=None),
    entry_type: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        entries = game_service.get_timeline_entries(
            life_id,
            age_min=age_min,
            age_max=age_max,
            entry_type=entry_type,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    return {"life_id": life_id, "entries": entries, "count": len(entries)}


@router.get("/{life_id}/years/{age}")
def get_year_snapshot(life_id: str, age: int) -> dict[str, Any]:
    try:
        return game_service.get_year_snapshot(life_id, age)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{life_id}/years/{age}/detail")
def get_year_detail(life_id: str, age: int) -> dict[str, Any]:
    try:
        return game_service.get_year_detail(life_id, age)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{life_id}/years/{age}/narrative")
def get_year_narrative(life_id: str, age: int) -> dict[str, Any]:
    try:
        return game_service.get_year_narrative(life_id, age)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{life_id}/years/{age}/result")
def get_year_result(life_id: str, age: int) -> dict[str, Any]:
    try:
        return game_service.get_year_result_by_age(life_id, age)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{life_id}/milestones")
def get_key_milestones(life_id: str) -> dict[str, Any]:
    try:
        milestones = game_service.get_key_milestones(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    return {"life_id": life_id, "milestones": milestones}
