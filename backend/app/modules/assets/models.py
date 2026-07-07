from pydantic import BaseModel


class AssetState(BaseModel):
    cash: float = 0.0
    debt: float = 0.0
