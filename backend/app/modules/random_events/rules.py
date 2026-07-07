from app.modules.random_events.models import RandomEventDefinition


def eligible_event_pool(life_stage: str, rules: dict) -> list[RandomEventDefinition]:
    event_pool = rules.get("random_events", {}).get("event_pool", [])
    eligible: list[RandomEventDefinition] = []
    for raw_event in event_pool:
        payload = dict(raw_event)
        if "name" not in payload and "label" in payload:
            payload["name"] = payload["label"]
        if "category" not in payload:
            payload["category"] = "direct_death" if payload.get("direct_death") else "normal"
        event = RandomEventDefinition.model_validate(payload)
        if event.stage in {"any", life_stage}:
            eligible.append(event)
    return eligible
