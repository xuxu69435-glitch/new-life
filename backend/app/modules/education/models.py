from pydantic import BaseModel


class EducationState(BaseModel):
    track: str = "not_started"
