"""Patch family-related V1 events with structured conditions and effects."""
import json
from pathlib import Path

LIBRARY_PATH = Path(__file__).resolve().parents[1] / "app" / "rules" / "data" / "random_event_library_v1.json"

ACTIVE_EVENTS = {
    "E004", "E007", "E051", "E052", "E053", "E054", "E055", "E056", "E057", "E058",
}
PARTIAL_EVENTS = {"E005", "E006", "E077", "E078", "E079", "E080"}


def patch_event(events_by_id: dict, event_id: str, **updates) -> None:
    event = events_by_id[event_id]
    event.update(updates)


def main() -> None:
    library = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    events_by_id = {event["event_id"]: event for event in library["events"]}

    patch_event(
        events_by_id,
        "E004",
        conditions={"min_age": 0, "max_age": 18, "family_pressure_min": 60},
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E004_A",
                "label": "选项一",
                "choice_text": "保持沉默",
                "effects_text": "幸福感减5",
                "effects": [
                    {"type": "attribute_change", "target": "charm", "value": -5, "reason": "幸福感减5"},
                    {"type": "family_pressure_change", "target": "family_pressure", "value": 3, "reason": "家庭压力上升"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E004_B",
                "label": "选项二",
                "choice_text": "主动安慰父母",
                "effects_text": "亲子关系加3，幸福感减2",
                "effects": [
                    {"type": "parent_relation_change", "target": "parent_child_relation", "value": 3, "reason": "亲子关系加3"},
                    {"type": "attribute_change", "target": "charm", "value": -2, "reason": "幸福感减2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E004_C",
                "label": "选项三",
                "choice_text": "逃避家庭氛围",
                "effects_text": "亲子关系减5，独立性加3",
                "effects": [
                    {"type": "parent_relation_change", "target": "parent_child_relation", "value": -5, "reason": "亲子关系减5"},
                    {"type": "flag_set", "target": "independence", "value": 3, "reason": "独立性加3"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E007",
        conditions={"min_age": 3, "max_age": 18},
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E007_A",
                "label": "选项一",
                "choice_text": "接受新环境",
                "effects_text": "适应力加4，幸福感减2",
                "effects": [
                    {"type": "flag_set", "target": "adaptability", "value": 4, "reason": "适应力加4"},
                    {"type": "attribute_change", "target": "charm", "value": -2, "reason": "幸福感减2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E007_B",
                "label": "选项二",
                "choice_text": "怀念旧环境",
                "effects_text": "幸福感减5，社交能力减2",
                "effects": [
                    {"type": "attribute_change", "target": "charm", "value": -5, "reason": "幸福感减5"},
                    {"type": "attribute_change", "target": "charm", "value": -2, "reason": "社交能力减2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E007_C",
                "label": "选项三",
                "choice_text": "主动结交新朋友",
                "effects_text": "社交能力加5，幸福感加1",
                "effects": [
                    {"type": "attribute_change", "target": "charm", "value": 5, "reason": "社交能力加5"},
                    {"type": "attribute_change", "target": "charm", "value": 1, "reason": "幸福感加1"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E051",
        conditions={
            "min_age": 18,
            "max_age": 45,
            "relationship_status_in": ["single"],
            "attribute_above": {"key": "charm", "value": 40},
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E051_A",
                "label": "选项一",
                "choice_text": "主动追求",
                "effects_text": "恋爱概率提高，幸福感加4，压力加2",
                "effects": [
                    {"type": "partner_created", "target": "dating_partner", "value": 1, "name": "Partner", "relation_score": 60},
                    {"type": "relationship_status_change", "target": "relationship_status", "value": "dating"},
                    {"type": "attribute_change", "target": "charm", "value": 4, "reason": "幸福感加4"},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -2, "reason": "压力加2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E051_B",
                "label": "选项二",
                "choice_text": "慢慢了解",
                "effects_text": "恋爱概率中等，社交能力加2",
                "effects": [
                    {"type": "partner_created", "target": "dating_partner", "value": 1, "name": "Partner", "relation_score": 55},
                    {"type": "relationship_status_change", "target": "relationship_status", "value": "dating"},
                    {"type": "attribute_change", "target": "charm", "value": 2, "reason": "社交能力加2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E051_C",
                "label": "选项三",
                "choice_text": "错过机会",
                "effects_text": "幸福感减2，恋爱概率归零",
                "effects": [
                    {"type": "attribute_change", "target": "charm", "value": -2, "reason": "幸福感减2"},
                    {"type": "flag_set", "target": "dating_chance", "value": 0, "reason": "恋爱概率归零"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E052",
        conditions={
            "min_age": 18,
            "max_age": 50,
            "relationship_status_in": ["dating"],
            "partner_relation_min": 60,
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E052_A",
                "label": "选项一",
                "choice_text": "继续经营关系",
                "effects_text": "伴侣关系加5，幸福感加4",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 5},
                    {"type": "attribute_change", "target": "charm", "value": 4, "reason": "幸福感加4"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E052_B",
                "label": "选项二",
                "choice_text": "谈论结婚",
                "effects_text": "结婚概率提高，压力加3",
                "effects": [
                    {"type": "flag_set", "target": "marriage_chance", "value": 1, "reason": "结婚概率提高"},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -3, "reason": "压力加3"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E052_C",
                "label": "选项三",
                "choice_text": "保持现状",
                "effects_text": "关系小幅提升，变化较小",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 2},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E053",
        conditions={
            "min_age": 18,
            "max_age": 60,
            "relationship_status_in": ["dating", "married"],
            "attribute_below": {"key": "stress_resistance", "value": 40},
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E053_A",
                "label": "选项一",
                "choice_text": "认真沟通",
                "effects_text": "伴侣关系加4，压力减2",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 4},
                    {"type": "attribute_change", "target": "stress_resistance", "value": 2, "reason": "压力减2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E053_B",
                "label": "选项二",
                "choice_text": "冷处理",
                "effects_text": "伴侣关系减5，压力不变",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -5},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E053_C",
                "label": "选项三",
                "choice_text": "激烈争吵",
                "effects_text": "伴侣关系减10，分手或离婚风险提高",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -10},
                    {"type": "flag_set", "target": "breakup_risk", "value": 1, "reason": "分手或离婚风险提高"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E054",
        conditions={
            "min_age": 22,
            "max_age": 50,
            "relationship_status_in": ["dating"],
            "partner_relation_min": 70,
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E054_A",
                "label": "选项一",
                "choice_text": "结婚",
                "effects_text": "进入婚姻状态，个人资产减20000，幸福感加8",
                "effects": [
                    {"type": "marriage_created", "target": "spouse", "value": 1},
                    {"type": "asset_change", "target": "cash", "value": -20000, "reason": "个人资产减20000"},
                    {"type": "attribute_change", "target": "charm", "value": 8, "reason": "幸福感加8"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E054_B",
                "label": "选项二",
                "choice_text": "暂缓",
                "effects_text": "伴侣关系减2，压力减2",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -2},
                    {"type": "attribute_change", "target": "stress_resistance", "value": 2, "reason": "压力减2"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E054_C",
                "label": "选项三",
                "choice_text": "拒绝婚姻",
                "effects_text": "伴侣关系减8，可能分手",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -8},
                    {"type": "flag_set", "target": "breakup_risk", "value": 1, "reason": "可能分手"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E055",
        conditions={
            "min_age": 24,
            "max_age": 45,
            "relationship_status_in": ["married"],
            "health_above": 40,
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E055_A",
                "label": "选项一",
                "choice_text": "要孩子",
                "effects_text": "子女数量加1，家庭资产减30000，幸福感加8，压力加10",
                "effects": [
                    {"type": "child_created", "target": "children", "value": 1},
                    {"type": "asset_change", "target": "cash", "value": -30000, "reason": "养育初始成本"},
                    {"type": "attribute_change", "target": "charm", "value": 8, "reason": "幸福感加8"},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -10, "reason": "压力加10"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E055_B",
                "label": "选项二",
                "choice_text": "暂时不要",
                "effects_text": "压力减2，伴侣关系可能小幅变化",
                "effects": [
                    {"type": "attribute_change", "target": "stress_resistance", "value": 2, "reason": "压力减2"},
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 1},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E055_C",
                "label": "选项三",
                "choice_text": "明确不要",
                "effects_text": "伴侣关系根据伴侣观念变化，资产不变",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -2},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E056",
        conditions={
            "min_age": 30,
            "max_age": 60,
            "has_children": True,
            "children_count_min": 1,
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E056_A",
                "label": "选项一",
                "choice_text": "高投入培养",
                "effects_text": "家庭资产减15000，子女能力加6，压力加5",
                "effects": [
                    {"type": "asset_change", "target": "cash", "value": -15000, "reason": "高投入培养"},
                    {"type": "child_relation_change", "target": "child_ability", "value": 0, "ability_delta": 6},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -5, "reason": "压力加5"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E056_B",
                "label": "选项二",
                "choice_text": "普通投入",
                "effects_text": "家庭资产减5000，子女能力加2",
                "effects": [
                    {"type": "asset_change", "target": "cash", "value": -5000, "reason": "普通投入"},
                    {"type": "child_relation_change", "target": "child_ability", "value": 0, "ability_delta": 2},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E056_C",
                "label": "选项三",
                "choice_text": "低投入",
                "effects_text": "家庭资产不变，子女能力减2，亲子关系减3",
                "effects": [
                    {"type": "child_relation_change", "target": "child_ability", "value": 0, "ability_delta": -2},
                    {"type": "parent_relation_change", "target": "parent_child_relation", "value": -3, "reason": "亲子关系减3"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E057",
        conditions={
            "min_age": 25,
            "max_age": 60,
            "relationship_status_in": ["married", "dating"],
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E057_A",
                "label": "选项一",
                "choice_text": "共同承担",
                "effects_text": "伴侣关系加5，家庭资产减10000，压力加5",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 5},
                    {"type": "asset_change", "target": "cash", "value": -10000, "reason": "家庭资产减10000"},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -5, "reason": "压力加5"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E057_B",
                "label": "选项二",
                "choice_text": "要求尽快找工作",
                "effects_text": "伴侣关系减4，家庭资产减5000",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -4},
                    {"type": "asset_change", "target": "cash", "value": -5000, "reason": "家庭资产减5000"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E057_C",
                "label": "选项三",
                "choice_text": "发生争执",
                "effects_text": "伴侣关系减8，压力加6",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -8},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -6, "reason": "压力加6"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    patch_event(
        events_by_id,
        "E058",
        conditions={
            "min_age": 28,
            "max_age": 65,
            "relationship_status_in": ["married"],
            "partner_relation_max": 35,
        },
        implementation_status="active",
        unsupported_reasons=[],
        choices=[
            {
                "choice_id": "E058_A",
                "label": "选项一",
                "choice_text": "尝试修复",
                "effects_text": "伴侣关系加8，个人资产减5000，压力加4",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": 8},
                    {"type": "asset_change", "target": "cash", "value": -5000, "reason": "个人资产减5000"},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -4, "reason": "压力加4"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E058_B",
                "label": "选项二",
                "choice_text": "协议离婚",
                "effects_text": "婚姻结束，资产按规则分割，幸福感减8",
                "effects": [
                    {"type": "divorce_created", "target": "spouse", "value": 1},
                    {"type": "asset_change", "target": "cash", "value": -5000, "reason": "资产分割占位"},
                    {"type": "attribute_change", "target": "charm", "value": -8, "reason": "幸福感减8"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
            {
                "choice_id": "E058_C",
                "label": "选项三",
                "choice_text": "继续拖延",
                "effects_text": "伴侣关系减5，压力加8",
                "effects": [
                    {"type": "partner_relation_change", "target": "partner_relation", "value": -5},
                    {"type": "attribute_change", "target": "stress_resistance", "value": -8, "reason": "压力加8"},
                ],
                "requires_confirmation": False,
                "is_system_choice": False,
            },
        ],
    )

    for event_id in PARTIAL_EVENTS:
        if event_id in events_by_id:
            events_by_id[event_id]["implementation_status"] = "partial"
            events_by_id[event_id]["unsupported_reasons"] = [
                "advanced family/legal system placeholder"
            ]

    LIBRARY_PATH.write_text(
        json.dumps(library, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Patched family events in", LIBRARY_PATH)
    print("Active:", sorted(ACTIVE_EVENTS))
    print("Partial:", sorted(PARTIAL_EVENTS))


if __name__ == "__main__":
    main()
