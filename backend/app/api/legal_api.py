from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.application.game_command_service import game_service
from app.engine.simulation_context import LifeState
from app.infrastructure.config import settings
from app.infrastructure.errors import DomainError

router = APIRouter(prefix="/games", tags=["legal"])


class SubmitLegalChoiceRequest(BaseModel):
    choice_id: str


class TriggerSentencingRequest(BaseModel):
    sentence_years: int = Field(default=4, ge=1, le=50)


class LegalChoiceResponse(BaseModel):
    life_id: str
    choice_result: dict[str, Any]
    pending_legal_event: dict[str, Any] | None
    state: LifeState


@router.get("/{life_id}/legal-state")
def get_legal_state(life_id: str) -> dict[str, Any]:
    try:
        return game_service.get_legal_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc


@router.get("/{life_id}/pending-legal-event")
def get_pending_legal_event(life_id: str) -> dict[str, Any]:
    try:
        payload = game_service.get_legal_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    return {
        "life_id": life_id,
        "pending_legal_event": payload.get("pending_legal_event"),
    }


@router.post("/{life_id}/legal-choice", response_model=LegalChoiceResponse)
def submit_legal_choice(life_id: str, request: SubmitLegalChoiceRequest) -> LegalChoiceResponse:
    try:
        payload = game_service.submit_legal_choice(life_id, request.choice_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LegalChoiceResponse(**payload)


dev_router = APIRouter(prefix="/dev/legal", tags=["dev-legal"])


@dev_router.post("/{life_id}/sentence")
def trigger_sentencing(life_id: str, request: TriggerSentencingRequest) -> dict[str, Any]:
    if not settings.enable_dev_routes:
        raise HTTPException(status_code=404, detail="Dev routes disabled")
    try:
        return game_service.trigger_sentencing(life_id, request.sentence_years)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
