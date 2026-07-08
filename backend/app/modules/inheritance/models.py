from pydantic import BaseModel, Field


class HeirShare(BaseModel):
    person_id: str
    relation: str
    share_ratio: float
    amount: float


class InheritanceResult(BaseModel):
    life_id: str
    deceased_person_id: str
    gross_estate: float
    tax_rate: float
    tax_amount: float
    net_estate: float
    heirs: list[HeirShare] = Field(default_factory=list)
    distribution: dict[str, float] = Field(default_factory=dict)
    unclaimed_amount: float = 0.0
    status: str = "settled"
    created_from_death_type: str | None = None
