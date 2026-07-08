from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.application.game_command_service import game_service
from app.engine.simulation_context import LifeState, YearResult
from app.infrastructure.errors import DomainError

router = APIRouter(prefix="/games", tags=["games"])


class CreateLifeRequest(BaseModel):
    rule_version: str | None = None


class AdvanceYearRequest(BaseModel):
    player_choices: dict[str, Any] = Field(default_factory=dict)


class SubmitRandomEventChoiceRequest(BaseModel):
    choice_id: str


class RandomEventChoiceResponse(BaseModel):
    life_id: str
    choice_result: dict[str, Any]
    pending_random_event: dict[str, Any] | None
    state: LifeState


class LifeStateResponse(BaseModel):
    state: LifeState
    available_choices: list[dict[str, Any]]


@router.post("", response_model=LifeStateResponse)
def create_life(request: CreateLifeRequest) -> LifeStateResponse:
    try:
        state, choices = game_service.create_life(request.rule_version)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LifeStateResponse(state=state, available_choices=choices)


@router.get("/{life_id}", response_model=LifeStateResponse)
def get_life(life_id: str) -> LifeStateResponse:
    try:
        state, choices = game_service.get_life_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    return LifeStateResponse(state=state, available_choices=choices)


@router.post("/{life_id}/advance", response_model=YearResult)
def advance_one_year(life_id: str, request: AdvanceYearRequest) -> YearResult:
    try:
        return game_service.advance_one_year(life_id, request.player_choices)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{life_id}/pending-random-event")
def get_pending_random_event(life_id: str) -> dict[str, Any]:
    try:
        pending = game_service.get_pending_random_event(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    return {"life_id": life_id, "pending_random_event": pending}


@router.post("/{life_id}/random-event-choice", response_model=RandomEventChoiceResponse)
def submit_random_event_choice(
    life_id: str,
    request: SubmitRandomEventChoiceRequest,
) -> RandomEventChoiceResponse:
    try:
        payload = game_service.submit_random_event_choice(life_id, request.choice_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RandomEventChoiceResponse(**payload)
