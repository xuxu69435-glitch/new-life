from typing import Any

from fastapi import APIRouter

from app.application.game_command_service import game_service

router = APIRouter(prefix="/inheritance", tags=["inheritance"])


@router.get("/{life_id}")
def get_inheritance_result(life_id: str) -> dict[str, Any]:
    return game_service.get_inheritance_result(life_id)
