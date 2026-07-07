from pydantic import BaseModel


class CareerState(BaseModel):
    title: str = "none"
    income: float = 0.0
