from pydantic import BaseModel


class LifeStageRule(BaseModel):
    name: str
    min_age: int
    max_age: int
