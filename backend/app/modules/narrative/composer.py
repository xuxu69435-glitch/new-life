from typing import Any

from app.modules.narrative.models import AnnualNarrativeInput, AnnualNarrativeResult, DisplaySection
from app.rules.narrative_template_loader import NarrativeTemplateLoader


class AnnualNarrativeComposer:
    SECTION_OVERVIEW = "overview"
    SECTION_MAJOR = "major_events"
    SECTION_EDUCATION = "education"
    SECTION_CAREER = "career_assets"
    SECTION_FAMILY = "family"
    SECTION_HEALTH = "health"
    SECTION_LEGAL = "legal"
    SECTION_MAINLINE = "mainline"
    SECTION_CLOSING = "closing"

    SECTION_TITLES = {
        SECTION_OVERVIEW: "本年概览",
        SECTION_MAJOR: "重大事件",
        SECTION_EDUCATION: "学习和成长",
        SECTION_CAREER: "职业和资产",
        SECTION_FAMILY: "家庭关系",
        SECTION_HEALTH: "健康状态",
        SECTION_LEGAL: "法律状态",
        SECTION_MAINLINE: "主线目标",
        SECTION_CLOSING: "年度结语",
    }

    def __init__(self, template_loader: NarrativeTemplateLoader | None = None) -> None:
        self.template_loader = template_loader or NarrativeTemplateLoader()

    def compose(self, input_data: AnnualNarrativeInput) -> AnnualNarrativeResult:
        templates = self.template_loader.load()
        priority_events = self._collect_priority_events(input_data, templates)
        priority_events.sort(key=lambda item: item["rank"])

        opening_text = self._opening_text(input_data, templates)
        major_event_texts = [event["text"] for event in priority_events if event.get("major")]
        module_texts = self._module_texts(input_data, templates, priority_events)
        closing_text = self._closing_text(input_data, templates)
        tone = self._resolve_tone(input_data)
        tags = [event["type"] for event in priority_events]
        display_sections = self._build_sections(
            input_data,
            templates,
            opening_text,
            major_event_texts,
            module_texts,
            closing_text,
        )
        summary_text = self._build_summary(opening_text, major_event_texts, closing_text, input_data)

        return AnnualNarrativeResult(
            summary_text=summary_text,
            opening_text=opening_text,
            major_event_texts=major_event_texts,
            module_texts=module_texts,
            closing_text=closing_text,
            tone=tone,
            tags=tags,
            priority_events=priority_events,
            display_sections=display_sections,
        )

    def _collect_priority_events(
        self,
        input_data: AnnualNarrativeInput,
        templates: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ranks = templates.get("priority_ranks", {})
        events: list[dict[str, Any]] = []
        legal = input_data.legal_changes
        legal_before = input_data.legal_before

        if input_data.is_dead:
            death_tpl = templates["death_templates"]
            if input_data.death_type == "natural_death":
                text = death_tpl.get("natural_death", death_tpl["default"])
            elif input_data.death_type == "direct_death":
                text = death_tpl.get("direct_death", death_tpl["default"])
            else:
                text = death_tpl["default"].format(
                    death_reason=input_data.death_reason or "未知",
                )
            events.append(
                self._event("death", text, ranks.get("death", 1), major=True),
            )

        if input_data.inheritance_result and input_data.inheritance_result.get("status") != "not_available":
            gross = input_data.inheritance_result.get("gross_estate", 0)
            net = input_data.inheritance_result.get("net_estate", 0)
            text = templates["inheritance_templates"]["settlement"].format(
                gross=gross,
                net=net,
            )
            events.append(
                self._event("inheritance", text, ranks.get("inheritance", 2), major=True),
            )

        legal_event_id = str(legal.get("last_legal_event", ""))
        if legal_event_id and legal_event_id in templates["legal_templates"]:
            events.append(
                self._event(
                    "legal",
                    templates["legal_templates"][legal_event_id],
                    ranks.get("legal", 3),
                    major=True,
                ),
            )
        elif legal.get("is_fugitive"):
            events.append(
                self._event(
                    "legal",
                    templates["legal_templates"]["fugitive"],
                    ranks.get("legal", 3),
                    major=True,
                ),
            )
        elif legal.get("is_in_prison"):
            remaining = legal.get("sentence_remaining_years", 0)
            events.append(
                self._event(
                    "legal",
                    templates["legal_templates"]["in_prison"].format(remaining=remaining),
                    ranks.get("legal", 3),
                    major=True,
                ),
            )
        elif (
            legal_before.get("is_in_prison")
            and not legal.get("is_in_prison")
            and not legal.get("is_fugitive")
        ):
            events.append(
                self._event(
                    "legal",
                    templates["legal_templates"]["released"],
                    ranks.get("legal", 3),
                    major=True,
                ),
            )

        if input_data.pending_legal_event:
            event_id = str(input_data.pending_legal_event.get("event_id", ""))
            if event_id in templates["legal_templates"]:
                events.append(
                    self._event(
                        "legal_pending",
                        templates["legal_templates"][event_id],
                        ranks.get("legal", 3),
                        major=True,
                    ),
                )

        if input_data.married_this_year:
            events.append(
                self._event(
                    "family_marriage",
                    templates["family_templates"]["married"],
                    ranks.get("family_marriage", 4),
                    major=True,
                ),
            )

        if input_data.child_born_this_year:
            events.append(
                self._event(
                    "family_birth",
                    templates["family_templates"]["child_born"],
                    ranks.get("family_birth", 5),
                    major=True,
                ),
            )

        if (
            input_data.relationship_status_after == "divorced"
            and input_data.relationship_status_before != "divorced"
        ):
            events.append(
                self._event(
                    "family_divorce",
                    templates["family_templates"]["divorced"],
                    ranks.get("family_divorce", 6),
                    major=True,
                ),
            )

        if input_data.education_changes.get("graduated"):
            events.append(
                self._event(
                    "education_graduation",
                    templates["education_templates"]["graduation"],
                    ranks.get("education_graduation", 7),
                    major=True,
                ),
            )

        career_before = input_data.career_changes.get("status_before")
        career_after = input_data.career_changes.get("status_after")
        if career_after == "employed" and career_before != "employed":
            path = input_data.career_changes.get("career_path", "未知")
            events.append(
                self._event(
                    "career_employed",
                    templates["career_templates"]["employed"].format(career_path=path),
                    ranks.get("career_employed", 8),
                    major=True,
                ),
            )
        if career_after == "retired" and career_before != "retired":
            events.append(
                self._event(
                    "career_retired",
                    templates["career_templates"]["retired"],
                    ranks.get("career_retired", 9),
                    major=True,
                ),
            )

        health_delta = int(input_data.health_changes.get("health_score_delta", 0))
        if abs(health_delta) >= 5 or input_data.health_changes.get("warnings"):
            score_before = input_data.health_changes.get("health_score_before")
            score_after = input_data.health_changes.get("health_score_after")
            if score_before is not None and score_after is not None:
                text = templates["health_templates"]["score_change"].format(
                    score_before=score_before,
                    score_after=score_after,
                    delta=f"+{health_delta}" if health_delta > 0 else str(health_delta),
                )
            else:
                text = templates["health_templates"]["stable"]
            for warning in input_data.health_changes.get("warnings", []):
                text += " " + templates["health_templates"]["warning"].format(warning=warning)
            events.append(
                self._event("health_major", text, ranks.get("health_major", 10), major=False),
            )

        for event in input_data.triggered_random_events:
            text = templates["random_event_templates"]["triggered"].format(
                name=event.get("name", "未知事件"),
                text=event.get("narrative_text", event.get("event_text", "")),
            )
            events.append(
                self._event("random_event", text, ranks.get("random_event", 11), major=False),
            )

        if input_data.random_event_choice_result:
            choice = input_data.random_event_choice_result
            text = templates["random_event_templates"]["choice_result"].format(
                choice_text=choice.get("choice_text", ""),
                effects_text=choice.get("effects_text", ""),
            )
            events.append(
                self._event("random_event_choice", text, ranks.get("random_event", 11), major=False),
            )

        for task_id in input_data.completed_tasks_this_year:
            narrative = next(iter(input_data.mainline_narrative), "")
            text = templates["mainline_templates"]["task_completed"].format(
                task_id=task_id,
                text=narrative,
            )
            events.append(
                self._event(
                    "mainline_completed",
                    text,
                    ranks.get("mainline_completed", 12),
                    major=False,
                ),
            )

        if input_data.attribute_changes:
            parts = [
                f"{key}{'+' if value > 0 else ''}{value}"
                for key, value in input_data.attribute_changes.items()
            ]
            events.append(
                self._event(
                    "attribute_change",
                    "属性变化：" + "，".join(parts),
                    ranks.get("attribute_change", 13),
                    major=False,
                ),
            )

        if input_data.asset_changes:
            parts = [
                f"{key}{'+' if value > 0 else ''}{value}"
                for key, value in input_data.asset_changes.items()
            ]
            events.append(
                self._event(
                    "asset_change",
                    "资产变化：" + "，".join(parts),
                    ranks.get("asset_change", 14),
                    major=False,
                ),
            )

        return events

    def _opening_text(self, input_data: AnnualNarrativeInput, templates: dict[str, Any]) -> str:
        openings = templates["life_stage_openings"]
        if input_data.legal_changes.get("is_fugitive"):
            return openings["fugitive"]
        if input_data.legal_changes.get("is_in_prison"):
            return openings["prison"]
        stage_key = self._stage_key(input_data.life_stage, input_data.age_after)
        return openings.get(stage_key, openings.get("default", ""))

    def _closing_text(self, input_data: AnnualNarrativeInput, templates: dict[str, Any]) -> str:
        closings = templates["normal_year_closings"]
        if input_data.is_dead:
            return closings.get("death", closings["default"])
        if input_data.legal_changes.get("is_fugitive"):
            return closings.get("fugitive", closings["default"])
        if input_data.legal_changes.get("is_in_prison"):
            return closings.get("prison", closings["default"])
        if not input_data.major_flags.get("has_notable_events"):
            return closings.get("quiet", closings["default"])
        return closings["default"]

    def _module_texts(
        self,
        input_data: AnnualNarrativeInput,
        templates: dict[str, Any],
        priority_events: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        texts: dict[str, list[str]] = {
            "education": [],
            "career": [],
            "family": [],
            "health": [],
            "legal": [],
            "mainline": [],
            "random": [],
        }

        edu = input_data.education_changes
        if edu.get("stage_before") and edu.get("stage_after") and edu["stage_before"] != edu["stage_after"]:
            texts["education"].append(
                templates["education_templates"]["stage_change"].format(
                    stage_before=edu["stage_before"],
                    stage_after=edu["stage_after"],
                )
            )
        if edu.get("graduated"):
            texts["education"].append(templates["education_templates"]["graduation"])

        career = input_data.career_changes
        if career.get("status_before") and career.get("status_after"):
            if career["status_before"] != career["status_after"]:
                texts["career"].append(
                    templates["career_templates"]["status_change"].format(
                        status_before=career["status_before"],
                        status_after=career["status_after"],
                    )
                )
        income = float(career.get("career_income_change", 0) or 0)
        if income > 0:
            texts["career"].append(
                templates["career_templates"]["income"].format(income=int(income)),
            )

        for event in priority_events:
            event_type = event["type"]
            if event_type.startswith("family"):
                texts["family"].append(event["text"])
            elif event_type.startswith("legal"):
                texts["legal"].append(event["text"])
            elif event_type == "mainline_completed":
                texts["mainline"].append(event["text"])
            elif event_type.startswith("random"):
                texts["random"].append(event["text"])
            elif event_type == "health_major":
                texts["health"].append(event["text"])

        if input_data.mainline_changes.get("current_guidance_text"):
            texts["mainline"].append(
                templates["mainline_templates"]["guidance"].format(
                    text=input_data.mainline_changes["current_guidance_text"],
                )
            )

        if input_data.social_narrative:
            texts["social"] = list(input_data.social_narrative)
        if input_data.romance_narrative:
            texts["romance"] = list(input_data.romance_narrative)

        return {key: value for key, value in texts.items() if value}

    def _build_sections(
        self,
        input_data: AnnualNarrativeInput,
        templates: dict[str, Any],
        opening_text: str,
        major_event_texts: list[str],
        module_texts: dict[str, list[str]],
        closing_text: str,
    ) -> list[DisplaySection]:
        sections: list[DisplaySection] = []
        overview_tpl = templates["overview_templates"]
        if input_data.is_dead:
            overview = overview_tpl["death_centered"].format(age_after=input_data.age_after)
        elif input_data.legal_changes.get("is_in_prison") or input_data.legal_changes.get("is_fugitive"):
            overview = overview_tpl["legal_centered"].format(age_after=input_data.age_after)
        elif input_data.married_this_year or input_data.child_born_this_year:
            overview = overview_tpl["family_centered"].format(age_after=input_data.age_after)
        else:
            overview = overview_tpl["default"].format(age_after=input_data.age_after)

        sections.append(
            DisplaySection(
                section_id=self.SECTION_OVERVIEW,
                title=self.SECTION_TITLES[self.SECTION_OVERVIEW],
                content=f"{overview}\n{opening_text}",
            )
        )

        if major_event_texts:
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_MAJOR,
                    title=self.SECTION_TITLES[self.SECTION_MAJOR],
                    content="\n".join(major_event_texts),
                )
            )

        if module_texts.get("education"):
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_EDUCATION,
                    title=self.SECTION_TITLES[self.SECTION_EDUCATION],
                    content="\n".join(module_texts["education"]),
                )
            )

        career_lines = (module_texts.get("career") or []) + [
            line
            for line in [
                f"资产变化：{self._format_changes(input_data.asset_changes)}"
                if input_data.asset_changes
                else ""
            ]
            if line
        ]
        if career_lines:
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_CAREER,
                    title=self.SECTION_TITLES[self.SECTION_CAREER],
                    content="\n".join(career_lines),
                )
            )

        if module_texts.get("family"):
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_FAMILY,
                    title=self.SECTION_TITLES[self.SECTION_FAMILY],
                    content="\n".join(module_texts["family"]),
                )
            )

        if module_texts.get("social"):
            sections.append(
                DisplaySection(
                    section_id="social",
                    title="社交关系",
                    content="\n".join(module_texts["social"]),
                )
            )
        if module_texts.get("romance"):
            sections.append(
                DisplaySection(
                    section_id="romance",
                    title="情感恋爱",
                    content="\n".join(module_texts["romance"]),
                )
            )

        if module_texts.get("health"):
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_HEALTH,
                    title=self.SECTION_TITLES[self.SECTION_HEALTH],
                    content="\n".join(module_texts["health"]),
                )
            )

        if module_texts.get("legal"):
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_LEGAL,
                    title=self.SECTION_TITLES[self.SECTION_LEGAL],
                    content="\n".join(module_texts["legal"]),
                )
            )

        if module_texts.get("mainline"):
            sections.append(
                DisplaySection(
                    section_id=self.SECTION_MAINLINE,
                    title=self.SECTION_TITLES[self.SECTION_MAINLINE],
                    content="\n".join(module_texts["mainline"]),
                )
            )

        sections.append(
            DisplaySection(
                section_id=self.SECTION_CLOSING,
                title=self.SECTION_TITLES[self.SECTION_CLOSING],
                content=closing_text,
            )
        )
        return sections

    def _build_summary(
        self,
        opening_text: str,
        major_event_texts: list[str],
        closing_text: str,
        input_data: AnnualNarrativeInput,
    ) -> str:
        parts = [opening_text]
        if input_data.is_dead and major_event_texts:
            parts = major_event_texts[:1]
        elif major_event_texts:
            parts.extend(major_event_texts[:3])
        parts.append(closing_text)
        return "\n".join(part for part in parts if part)

    def _resolve_tone(self, input_data: AnnualNarrativeInput) -> str:
        if input_data.is_dead:
            return "solemn"
        if input_data.legal_changes.get("is_in_prison") or input_data.legal_changes.get("is_fugitive"):
            return "tense"
        if input_data.married_this_year or input_data.child_born_this_year:
            return "warm"
        return "normal"

    def _stage_key(self, life_stage: str, age: int) -> str:
        if life_stage == "infant":
            return "infant"
        if life_stage == "childhood" and age <= 12:
            return "childhood"
        if life_stage in {"teen", "childhood"} and age <= 17:
            return "teen"
        if age <= 22:
            return "college"
        if age <= 35:
            return "adult"
        if age <= 59:
            return "midlife"
        if life_stage == "elder" or age >= 60:
            return "elder"
        return "default"

    def _format_changes(self, changes: dict[str, float]) -> str:
        return "，".join(
            f"{key}{'+' if value > 0 else ''}{value}" for key, value in changes.items()
        )

    def _event(self, event_type: str, text: str, rank: int, *, major: bool) -> dict[str, Any]:
        return {"type": event_type, "text": text, "rank": rank, "major": major}
