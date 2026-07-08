from app.modules.mainline.models import MainlineState


def get_mainline_rules(rules: dict) -> dict:
    return rules.get("mainline", {})


def build_default_mainline_state(rules: dict | None = None) -> MainlineState:
    return MainlineState(
        current_chapter="infant",
        current_stage="infant",
        current_guidance_text="健康成长是你当前阶段的核心目标。",
    )


def is_legal_special_chapter(chapter: str) -> bool:
    return chapter in {"prison", "legal_recovery"}
