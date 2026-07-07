def annual_summary(age_after: int, is_dead: bool, death_reason: str | None) -> str:
    if is_dead:
        return f"Year {age_after}: life ended because of {death_reason}."
    return f"Year {age_after}: life moved forward."
