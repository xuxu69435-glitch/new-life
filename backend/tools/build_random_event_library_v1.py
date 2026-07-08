#!/usr/bin/env python3
"""Generate random_event_library_v1.json from codex_random_event_v1_prompt.md section 十九."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
OUTPUT_PATH = BACKEND_DIR / "app" / "rules" / "data" / "random_event_library_v1.json"

SOURCE_CANDIDATES = [
    Path(r"e:\chrome\down\codex_random_event_v1_prompt.md"),
    BACKEND_DIR.parent / "docs" / "design" / "random_event_library_v1.md",
]

WEIGHT_TIER_MAP = {
    "低概率": 1,
    "中低概率": 3,
    "中概率": 5,
    "中高概率": 8,
    "高概率": 12,
    "极低概率": 1,
    "系统事件": 0,
}

CHOICE_LABELS = ["选项一", "选项二", "选项三", "选项四"]
CHOICE_SUFFIX = ["A", "B", "C", "D"]

CATEGORY_BY_EVENT: dict[str, str] = {}
for _eid, _cat in [
    *[(f"E{i:03d}", "birth_family") for i in range(1, 8)],
    *[(f"E{i:03d}", "infant") for i in range(8, 13)],
    *[(f"E{i:03d}", "primary") for i in range(13, 20)],
    *[(f"E{i:03d}", "junior_high") for i in range(20, 26)],
    *[(f"E{i:03d}", "senior_high") for i in range(26, 31)],
    *[(f"E{i:03d}", "college_grad") for i in range(31, 40)],
    *[(f"E{i:03d}", "career") for i in range(40, 51)],
    *[(f"E{i:03d}", "relationship_family") for i in range(51, 59)],
    *[(f"E{i:03d}", "health") for i in range(59, 66)],
    *[(f"E{i:03d}", "social_risk") for i in range(66, 76)],
    *[(f"E{i:03d}", "elder_legacy") for i in range(76, 81)],
]:
    CATEGORY_BY_EVENT[_eid] = _cat

DIRECT_DEATH_EVENTS = {"E067", "E068", "E070"}
SYSTEM_EVENTS = {"E065", "E080"}

PLANNED_EVENTS = {
    "E001", "E002", "E003", "E004", "E005", "E006", "E007",
    "E008", "E010", "E011",
    "E022",
    "E037", "E038", "E039",
    "E046", "E047", "E048",
    "E051", "E052", "E053", "E054", "E055", "E056", "E057", "E058",
    "E072", "E073",
    "E077", "E078",
    "E065", "E080",
}

ATTRIBUTE_TARGETS = {
    "智力": "intelligence",
    "学习能力": "intelligence",
    "自律": "self_discipline",
    "幸福感": "charm",
    "社交能力": "charm",
    "自信": "charm",
}

AGE_STAGE_RANGES = [
    ("infant", 0, 2),
    ("childhood", 3, 12),
    ("teen", 13, 17),
    ("adult", 18, 64),
    ("elder", 65, 200),
]


def load_source_text() -> str:
    for path in SOURCE_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "Source markdown not found. Expected one of: "
        + ", ".join(str(p) for p in SOURCE_CANDIDATES)
    )


def extract_event_section(source: str) -> str:
    start = source.find("E001出生体质偏弱")
    if start < 0:
        raise ValueError("Could not find E001 in source markdown")
    end = source.find("十五、直接死亡事件池", start)
    if end < 0:
        end = source.find("E080亲属争产")
        if end < 0:
            raise ValueError("Could not find end marker in source markdown")
        end = source.find("\n\n", source.find("选项三：进入后代人生", end))
    return source[start:end]


def parse_age_range(text: str) -> dict[str, int]:
    text = text.strip()
    if text == "死亡后结算事件":
        return {"min": -1, "max": -1}
    eq = re.fullmatch(r"(\d+)岁", text)
    if eq:
        age = int(eq.group(1))
        return {"min": age, "max": age}
    rng = re.fullmatch(r"(\d+)到(\d+)岁", text)
    if rng:
        return {"min": int(rng.group(1)), "max": int(rng.group(2))}
    plus = re.fullmatch(r"(\d+)岁以上", text)
    if plus:
        return {"min": int(plus.group(1)), "max": 200}
    raise ValueError(f"Unrecognized age range: {text!r}")


def life_stages_for_age_range(age_range: dict[str, int]) -> list[str]:
    if age_range["min"] == -1:
        return ["post_death"]
    stages: list[str] = []
    for name, lo, hi in AGE_STAGE_RANGES:
        if age_range["max"] >= lo and age_range["min"] <= hi:
            stages.append(name)
    return stages


def parse_cooldown(repeat_text: str) -> tuple[str, int | None]:
    text = repeat_text.strip()
    if text == "不可重复":
        return "once", None
    if text == "最多触发一次":
        return "once_max", None
    if text == "最多一次成功":
        return "once_success_max", None
    if text == "最多一次":
        return "once_max", None
    if "按子女数量" in text:
        return "repeatable_by_children", None
    m = re.search(r"冷却(\d+)年", text)
    cooldown = int(m.group(1)) if m else None
    if "最多连续3年" in text:
        return "repeatable_max_3_consecutive", cooldown
    if "最多2次" in text:
        return "repeatable_max_2", cooldown
    if "可重复" in text:
        return "repeatable", cooldown
    return text, cooldown


def parse_conditions(event_id: str, trigger_text: str, age_range: dict[str, int], weight_tier: str) -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    if event_id in SYSTEM_EVENTS or weight_tier == "系统事件":
        conditions["system_only"] = True
    if event_id in DIRECT_DEATH_EVENTS:
        conditions["pool"] = "direct_death"
    if age_range["min"] >= 0:
        conditions["min_age"] = age_range["min"]
        conditions["max_age"] = age_range["max"]
    if "健康低于" in trigger_text:
        m = re.search(r"健康低于(\d+)", trigger_text)
        if m:
            conditions["health_below"] = int(m.group(1))
    if "健康高于" in trigger_text:
        m = re.search(r"健康高于(\d+)", trigger_text)
        if m:
            conditions["health_above"] = int(m.group(1))
    if "家庭资产低于" in trigger_text:
        m = re.search(r"家庭资产低于(\d+)", trigger_text)
        if m:
            conditions["unsupported_condition"] = {
                "field": "family_asset_below",
                "value": int(m.group(1)),
                "text": trigger_text,
            }
    if "家庭资产高于" in trigger_text or "家庭资产大于" in trigger_text:
        m = re.search(r"家庭资产(?:高于|大于)(\d+)", trigger_text)
        if m:
            conditions["unsupported_condition"] = {
                "field": "family_asset_above",
                "value": int(m.group(1)),
                "text": trigger_text,
            }
    if "个人资产高于" in trigger_text:
        m = re.search(r"个人资产高于(\d+)", trigger_text)
        if m:
            conditions["asset_above"] = int(m.group(1))
    if "进入直接死亡事件池" in trigger_text:
        conditions["pool"] = "direct_death"
    if len(conditions) <= 2 and "unsupported_condition" not in conditions:
        if trigger_text and not all(k in conditions for k in ("min_age", "max_age", "system_only", "pool")):
            conditions["unsupported_condition"] = {"text": trigger_text}
    elif trigger_text and "unsupported_condition" not in conditions:
        extra_keys = set(conditions.keys()) - {"min_age", "max_age", "system_only", "pool"}
        if not extra_keys:
            conditions["unsupported_condition"] = {"text": trigger_text}
    return conditions


def _effect(
    effect_type: str,
    target: str,
    value: int | float | str | bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "type": effect_type,
        "target": target,
        "value": value,
        "reason": reason,
    }


def _unsupported(reason: str, raw: str) -> dict[str, Any]:
    return _effect("unsupported_effect", raw, 0, reason)


def parse_effects_clause(clause: str, event_id: str, choice_id: str) -> list[dict[str, Any]]:
    clause = clause.strip()
    if not clause:
        return []

    effects: list[dict[str, Any]] = []

    if "直接死亡" in clause:
        effects.append(
            _effect(
                "direct_death_candidate",
                "death",
                1,
                clause,
            )
        )
        return effects

    if clause in {
        "无直接损失",
        "资产不变",
        "家庭资产不变",
        "健康不变",
        "幸福感不变",
        "社交能力不变",
        "竞赛经历不变",
    }:
        return effects

    parts = re.split(r"[，,；;]", clause)
    for part in parts:
        part = part.strip()
        if not part or part in {
            "无直接损失",
            "资产不变",
            "家庭资产不变",
            "健康不变",
            "幸福感不变",
            "社交能力不变",
            "竞赛经历不变",
        }:
            continue

        health = re.fullmatch(r"健康([加减])(\d+)", part)
        if health:
            sign = 1 if health.group(1) == "加" else -1
            effects.append(_effect("health_change", "health_score", sign * int(health.group(2)), part))
            continue

        personal_asset = re.fullmatch(r"个人资产([加减])(\d+)", part)
        if personal_asset:
            sign = 1 if personal_asset.group(1) == "加" else -1
            effects.append(_effect("asset_change", "cash", sign * int(personal_asset.group(2)), part))
            continue

        family_asset = re.fullmatch(r"家庭资产([加减])(\d+)", part)
        if family_asset:
            effects.append(
                _unsupported("family cash not implemented", part)
            )
            continue

        attr = re.fullmatch(r"(智力|学习能力|自律|幸福感|社交能力|自信)([加减])(\d+)", part)
        if attr:
            sign = 1 if attr.group(2) == "加" else -1
            effects.append(
                _effect(
                    "attribute_change",
                    ATTRIBUTE_TARGETS[attr.group(1)],
                    sign * int(attr.group(3)),
                    part,
                )
            )
            continue

        stress = re.fullmatch(r"压力([加减])(\d+)", part)
        if stress:
            sign = 1 if stress.group(1) == "加" else -1
            effects.append(
                _effect(
                    "attribute_change",
                    "stress_resistance",
                    -sign * int(stress.group(2)),
                    part,
                )
            )
            continue

        flag_patterns = [
            (r"开启复读选项", "gaokao_retake_option", True),
            (r"进入创业路径", "startup_path", True),
            (r"退出创业路径", "startup_path", False),
            (r"进入求职路径", "job_seeking_path", True),
            (r"进入求职状态", "job_seeking", True),
            (r"进入婚姻状态", "married", True),
            (r"遗产规划开启", "estate_planning", True),
            (r"自然死亡判定继续", "natural_death_check_continue", True),
        ]
        matched_flag = False
        for pattern, key, value in flag_patterns:
            if re.search(pattern, part):
                effects.append(_effect("flag_set", key, value, part))
                matched_flag = True
                break
        if matched_flag:
            continue

        effects.append(_unsupported(f"not implemented: {part}", part))

    return effects


def parse_choice_effects(effects_text: str, event_id: str, choice_id: str) -> list[dict[str, Any]]:
    text = effects_text.strip()
    if text.startswith("效果："):
        text = text[3:].strip()
    return parse_effects_clause(text, event_id, choice_id)


def infer_implementation_status(event_id: str, choices: list[dict[str, Any]]) -> tuple[str, list[str]]:
    if event_id in PLANNED_EVENTS:
        reasons: list[str] = []
        if event_id in {"E065", "E080"}:
            reasons.append("system_only event")
        if event_id in DIRECT_DEATH_EVENTS:
            reasons.append("direct_death pool")
        if event_id in {"E037", "E038", "E039"}:
            reasons.append("grad school system not implemented")
        if event_id in {"E046", "E047", "E048"}:
            reasons.append("startup system not implemented")
        if event_id in {"E072", "E073"}:
            reasons.append("crime system not implemented")
        if event_id in {"E051", "E052", "E053", "E054", "E055", "E056", "E057", "E058", "E022"}:
            reasons.append("marriage/relationship system not implemented")
        if event_id in {"E055", "E056", "E057", "E077", "E078"}:
            reasons.append("children system not implemented")
        if event_id in {"E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E010", "E011"}:
            reasons.append("parents/family system not implemented")
        return "planned", reasons or ["dependency not implemented"]

    has_unsupported = any(
        effect.get("type") == "unsupported_effect"
        for choice in choices
        for effect in choice.get("effects", [])
    )
    if has_unsupported:
        return "partial", ["contains unsupported_effect"]
    return "active", []


def infer_pool_type(event_id: str, weight_tier: str) -> str:
    if event_id in SYSTEM_EVENTS or weight_tier == "系统事件":
        return "system"
    if event_id in DIRECT_DEATH_EVENTS:
        return "direct_death"
    return "normal"


def may_cause_death(event_id: str, event_text: str, choices: list[dict[str, Any]]) -> bool:
    if event_id in DIRECT_DEATH_EVENTS | {"E062", "E065"}:
        return True
    for choice in choices:
        for effect in choice.get("effects", []):
            if effect.get("type") == "direct_death_candidate":
                return True
        if "死亡风险" in choice.get("effects_text", ""):
            return True
    return False


def affects_future(event_id: str, choices: list[dict[str, Any]]) -> bool:
    if event_id in SYSTEM_EVENTS | DIRECT_DEATH_EVENTS:
        return True
    for choice in choices:
        text = choice.get("effects_text", "")
        if any(
            token in text
            for token in (
                "路径", "概率", "权重", "开启", "进入", "学历", "专业", "婚姻", "子女",
                "遗产", "创业", "复读", "升学", "挂科", "犯罪", "晋升", "离婚",
            )
        ):
            return True
        for effect in choice.get("effects", []):
            if effect.get("type") in {"flag_set", "direct_death_candidate", "unsupported_effect"}:
                return True
    return False


def parse_events(source_section: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n(?=E\d{3}[^\n]+\n\n)", source_section.strip())
    events: list[dict[str, Any]] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        header_match = re.match(r"(E\d{3})([^\n]+)\n\n", block)
        if not header_match:
            continue
        event_id = header_match.group(1)
        name = header_match.group(2).strip()
        body = block[header_match.end() :]

        fields: dict[str, str] = {}
        event_text = ""
        choices_raw: list[tuple[str, str, str]] = []
        notes: list[str] = []

        current_choice_label = ""
        current_choice_text = ""
        current_effects = ""

        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[一二三四五六七八九十]+、", line):
                break
            if re.match(r"^E\d{3}", line):
                break
            if line.startswith("年龄段："):
                fields["age_range_text"] = line.split("：", 1)[1].strip()
            elif line.startswith("触发条件："):
                fields["trigger_conditions_text"] = line.split("：", 1)[1].strip()
            elif line.startswith("出现权重："):
                fields["weight_tier"] = line.split("：", 1)[1].strip()
            elif line.startswith("是否可重复："):
                fields["repeat_policy_text"] = line.split("：", 1)[1].strip()
            elif line.startswith("事件文本："):
                event_text = line.split("：", 1)[1].strip()
            elif line.startswith("选项") and "：" in line:
                if current_choice_label:
                    choices_raw.append((current_choice_label, current_choice_text, current_effects))
                label_part, choice_text = line.split("：", 1)
                current_choice_label = label_part.replace("选项", "选项")
                if not label_part.startswith("选项"):
                    current_choice_label = label_part
                else:
                    for idx, lbl in enumerate(CHOICE_LABELS):
                        if label_part == lbl:
                            current_choice_label = lbl
                            break
                current_choice_text = choice_text.strip()
                current_effects = ""
            elif line.startswith("效果："):
                current_effects = line.split("：", 1)[1].strip()
            elif line.startswith("备注："):
                notes.append(line.split("：", 1)[1].strip())
            elif current_effects and not line.startswith("选项"):
                if re.match(r"^[一二三四五六七八九十]+、", line) or re.match(r"^E\d{3}", line):
                    break
                current_effects += "，" + line

        if current_choice_label:
            choices_raw.append((current_choice_label, current_choice_text, current_effects))

        age_range = parse_age_range(fields["age_range_text"])
        weight_tier = fields["weight_tier"]
        if event_id in SYSTEM_EVENTS:
            weight_tier = "系统事件"
        weight = WEIGHT_TIER_MAP[weight_tier]
        repeat_policy, cooldown_years = parse_cooldown(fields["repeat_policy_text"])
        pool_type = infer_pool_type(event_id, weight_tier)

        choices: list[dict[str, Any]] = []
        for idx, (label, choice_text, effects_text) in enumerate(choices_raw):
            suffix = CHOICE_SUFFIX[idx]
            choice_id = f"{event_id}_{suffix}"
            is_system = choice_text == "系统判定"
            effects = parse_choice_effects(effects_text, event_id, choice_id)
            choices.append(
                {
                    "choice_id": choice_id,
                    "label": label if label in CHOICE_LABELS else CHOICE_LABELS[idx],
                    "choice_text": choice_text,
                    "effects_text": effects_text,
                    "effects": effects,
                    "requires_confirmation": event_id in DIRECT_DEATH_EVENTS,
                    "is_system_choice": is_system,
                }
            )

        implementation_status, unsupported_reasons = infer_implementation_status(event_id, choices)
        if notes:
            unsupported_reasons = list(dict.fromkeys(unsupported_reasons + notes))

        source_text = block.strip()
        event_obj = {
            "event_id": event_id,
            "name": name,
            "category": CATEGORY_BY_EVENT[event_id],
            "age_range": age_range,
            "life_stages": life_stages_for_age_range(age_range),
            "trigger_conditions_text": fields.get("trigger_conditions_text", ""),
            "conditions": parse_conditions(
                event_id,
                fields.get("trigger_conditions_text", ""),
                age_range,
                weight_tier,
            ),
            "weight_tier": weight_tier,
            "weight": weight,
            "repeat_policy": repeat_policy,
            "cooldown_years": cooldown_years,
            "event_text": event_text,
            "choices": choices,
            "may_cause_death": may_cause_death(event_id, event_text, choices),
            "affects_future": affects_future(event_id, choices),
            "implementation_status": implementation_status,
            "unsupported_reasons": unsupported_reasons,
            "source_text": source_text,
            "pool_type": pool_type,
        }
        events.append(event_obj)

    events.sort(key=lambda item: item["event_id"])
    return events


def build_library() -> dict[str, Any]:
    source = load_source_text()
    section = extract_event_section(source)
    events = parse_events(section)
    return {
        "version": "v1",
        "source": "codex_random_event_v1_prompt.md section 十九",
        "event_count": len(events),
        "events": events,
    }


def summarize_statuses(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"active": 0, "partial": 0, "planned": 0}
    for event in events:
        status = event["implementation_status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> int:
    library = build_library()
    events = library["events"]
    expected_ids = {f"E{i:03d}" for i in range(1, 81)}
    actual_ids = {event["event_id"] for event in events}

    if len(events) != 80:
        print(f"ERROR: expected 80 events, got {len(events)}", file=sys.stderr)
        return 1
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        print(f"ERROR: ID mismatch missing={missing} extra={extra}", file=sys.stderr)
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(library, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = summarize_statuses(events)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Events: {len(events)}")
    print(f"active: {counts['active']}")
    print(f"partial: {counts['partial']}")
    print(f"planned: {counts['planned']}")
    print(f"direct_death: {sum(1 for e in events if e['pool_type'] == 'direct_death')}")
    print(f"system: {sum(1 for e in events if e['pool_type'] == 'system')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
