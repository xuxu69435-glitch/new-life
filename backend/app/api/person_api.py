from fastapi import APIRouter, HTTPException

from app.application.game_command_service import game_service
from app.engine.simulation_context import LifeState

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/{person_id}", response_model=LifeState)
def get_person(person_id: str) -> LifeState:
    state = game_service.get_person(person_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return state
