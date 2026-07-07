from pydantic import BaseModel


class AttributeChange(BaseModel):
    key: str
    delta: int
