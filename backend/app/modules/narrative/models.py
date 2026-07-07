from pydantic import BaseModel


class NarrativeLine(BaseModel):
    text: str
