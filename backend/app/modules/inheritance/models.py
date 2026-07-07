from pydantic import BaseModel, Field


class InheritanceResult(BaseModel):
    gross_assets: float
    tax: float
    net_assets: float
    heirs: list[str] = Field(default_factory=list)
