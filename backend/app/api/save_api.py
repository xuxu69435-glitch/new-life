from typing import Any

from fastapi import APIRouter, HTTPException

from app.application.game_command_service import game_service

router = APIRouter(prefix="/saves", tags=["saves"])


@router.get("")
def list_saves() -> dict[str, Any]:
    records = game_service.list_saves()
    return {"saves": records, "count": len(records)}


@router.get("/{life_id}")
def get_save(life_id: str) -> dict[str, Any]:
    try:
        return game_service.get_save_record(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Save not found") from exc
