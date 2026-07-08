from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.application.game_command_service import HeirContinuationError, game_service
from app.infrastructure.errors import DomainError

router = APIRouter(prefix="/inheritance", tags=["inheritance"])


class ContinueAsHeirRequest(BaseModel):
    heir_person_id: str


@router.get("/{life_id}")
def get_inheritance_result(life_id: str) -> dict[str, Any]:
    try:
        return game_service.get_inheritance_result(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc


@router.get("/{life_id}/playable-heirs")
def get_playable_heirs(life_id: str) -> dict[str, Any]:
    try:
        return game_service.get_playable_heirs(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc


@router.post("/{life_id}/continue-as-heir")
def continue_as_heir(life_id: str, request: ContinueAsHeirRequest) -> dict[str, Any]:
    try:
        return game_service.continue_as_heir(life_id, request.heir_person_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    except HeirContinuationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
