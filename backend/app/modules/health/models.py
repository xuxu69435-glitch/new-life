from pydantic import BaseModel


class HealthState(BaseModel):
    physical: int = 100
    mental: int = 100
