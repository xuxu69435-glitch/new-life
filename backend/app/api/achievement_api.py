from typing import Any

from fastapi import APIRouter, HTTPException

from app.application.game_command_service import game_service
from app.modules.achievement.models import AchievementState
from app.modules.achievement.service import AchievementService
from app.rules.rule_loader import RuleLoader

router = APIRouter(prefix="/games", tags=["achievements"])


@router.get("/{life_id}/achievement-state")
def get_achievement_state(life_id: str) -> dict[str, Any]:
    try:
        state, _ = game_service.get_life_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc

    rules = RuleLoader().load(state.rule_version)
    achievement = AchievementState.from_life_state_dict(state.achievements)
    service = AchievementService()
    return {
        "life_id": life_id,
        "achievements": achievement.to_life_state_dict(),
        "achievement_list": service.get_public_achievements(achievement, rules),
        "total_points": achievement.achievement_points,
        "unlocked_count": len(achievement.unlocked_achievements),
    }


@router.get("/{life_id}/milestones")
def get_milestones(life_id: str) -> dict[str, Any]:
    try:
        state, _ = game_service.get_life_state(life_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Life not found") from exc

    achievement = AchievementState.from_life_state_dict(state.achievements)
    return {
        "life_id": life_id,
        "milestones": achievement.milestones,
    }
