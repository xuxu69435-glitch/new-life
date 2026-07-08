from typing import Any

from pydantic import BaseModel, Field


class MainlineTask(BaseModel):
    task_id: str
    title: str
    description: str
    chapter: str
    life_stages: list[str] = Field(default_factory=list)
    min_age: int = 0
    max_age: int = 200
    activation_conditions: dict[str, Any] = Field(default_factory=dict)
    completion_conditions: dict[str, Any] = Field(default_factory=dict)
    failure_conditions: dict[str, Any] = Field(default_factory=dict)
    expiration_conditions: dict[str, Any] = Field(default_factory=dict)
    rewards: list[dict[str, Any]] = Field(default_factory=list)
    on_complete_text: str = ""
    on_failed_text: str = ""
    is_required: bool = False
    can_expire: bool = False
    repeatable: bool = False
    implementation_status: str = "active"
    priority: int = 100
    task_category: str = "normal"


class MainlineTaskLibraryV1(BaseModel):
    version: str
    source: str = "mainline_system_v1"
    task_count: int = 0
    tasks: list[MainlineTask]

    def by_id(self) -> dict[str, MainlineTask]:
        return {task.task_id: task for task in self.tasks}

    def active_tasks(self) -> list[MainlineTask]:
        return [task for task in self.tasks if task.implementation_status == "active"]
