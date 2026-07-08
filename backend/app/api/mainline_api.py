from typing import Any

from fastapi import APIRouter, HTTPException

from app.application.game_command_service import game_service
from app.modules.mainline.models import MainlineState
from app.modules.mainline.service import MainlineService
from app.rules.rule_loader import RuleLoader

router = APIRouter(prefix="/games", tags=["mainline"])


@router.get("/{life_id}/mainline-state")
def get_mainline_state(life_id: str) -> dict[str, Any]:
    try:
        state, _ = game_service.get_life_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc

    rules = RuleLoader().load(state.rule_version)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    service = MainlineService()
    return {
        "life_id": life_id,
        "mainline": mainline.to_life_state_dict(),
        "active_tasks": service.get_active_task_summaries(mainline, rules),
        "current_guidance_text": mainline.current_guidance_text,
    }
