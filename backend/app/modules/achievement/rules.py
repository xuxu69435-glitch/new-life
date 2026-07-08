from app.modules.achievement.models import AchievementState


def get_achievement_rules(rules: dict) -> dict:
    return rules.get("achievements", {})


def build_default_achievement_state(rules: dict | None = None) -> AchievementState:
    state = AchievementState()
    state.milestones.append(
        {
            "milestone_id": "birth",
            "title": "出生",
            "age": 0,
            "year": 0,
            "source": "system",
            "description": "你来到了这个世界。",
        }
    )
    return state
