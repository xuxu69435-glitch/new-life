from fastapi import APIRouter

from app.application.game_command_service import game_service
from app.engine.simulation_context import YearResult

router = APIRouter(prefix="/timelines", tags=["timelines"])


@router.get("/{life_id}", response_model=list[YearResult])
def get_timeline(life_id: str) -> list[YearResult]:
    return game_service.get_timeline(life_id)
