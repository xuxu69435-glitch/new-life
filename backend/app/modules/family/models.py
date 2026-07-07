from pydantic import BaseModel, Field


class FamilyState(BaseModel):
    relations: list[dict] = Field(default_factory=list)
