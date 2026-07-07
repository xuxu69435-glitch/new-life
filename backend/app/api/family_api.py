from typing import Any

from fastapi import APIRouter, HTTPException

from app.application.game_command_service import game_service

router = APIRouter(prefix="/families", tags=["families"])


@router.get("/{life_id}")
def get_family_tree(life_id: str) -> dict[str, Any]:
    try:
        return game_service.get_family_tree(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
