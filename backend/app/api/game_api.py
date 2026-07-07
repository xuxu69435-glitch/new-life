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
