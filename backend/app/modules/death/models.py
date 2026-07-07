from pydantic import BaseModel


class DeathDecision(BaseModel):
    confirmed: bool
    reason: str | None = None
