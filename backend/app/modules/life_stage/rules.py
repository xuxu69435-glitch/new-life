def resolve_life_stage(age: int, rules: dict) -> str:
    for stage in rules.get("life_stages", []):
        if int(stage["min_age"]) <= age <= int(stage["max_age"]):
            return str(stage["name"])
    return "elder"
