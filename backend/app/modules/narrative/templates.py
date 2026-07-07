def annual_summary(
    age_after: int,
    is_dead: bool,
    death_reason: str | None,
    death_type: str | None = None,
    health_score_delta: int = 0,
    health_warnings: list[str] | None = None,
) -> str:
    lines: list[str] = []
    if health_score_delta != 0:
        sign = "+" if health_score_delta > 0 else ""
        lines.append(f"Health score changed by {sign}{health_score_delta}.")
    if health_warnings:
        lines.extend(f"Health warning: {warning}" for warning in health_warnings)
    if is_dead:
        death_label = death_type or "death"
        lines.append(f"Year {age_after}: life ended due to {death_label} ({death_reason}).")
        return " ".join(lines)
    lines.append(f"Year {age_after}: life moved forward.")
    return " ".join(lines)
