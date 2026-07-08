from typing import Any

from pydantic import BaseModel, Field


class AssetState(BaseModel):
    cash: float = 0.0
    property_value: float = 0.0
    debt: float = 0.0
    net_worth: float = 0.0
    asset_transactions: list[dict[str, Any]] = Field(default_factory=list)

    def recalculate_net_worth(self) -> float:
        self.net_worth = self.cash + self.property_value - self.debt
        return self.net_worth

    @classmethod
    def from_life_state_dict(cls, assets_data: dict[str, Any], rules: dict | None = None) -> "AssetState":
        defaults = (rules or {}).get("default_assets", {})
        cash = float(assets_data.get("cash", defaults.get("cash", 0.0)))
        property_value = float(assets_data.get("property_value", defaults.get("property_value", 0.0)))
        debt = float(assets_data.get("debt", defaults.get("debt", 0.0)))
        transactions = list(assets_data.get("asset_transactions", defaults.get("asset_transactions", [])))
        state = cls(
            cash=cash,
            property_value=property_value,
            debt=debt,
            asset_transactions=transactions,
        )
        state.recalculate_net_worth()
        return state

    def to_life_state_dict(self) -> dict[str, Any]:
        self.recalculate_net_worth()
        return {
            "cash": self.cash,
            "property_value": self.property_value,
            "debt": self.debt,
            "net_worth": self.net_worth,
            "asset_transactions": list(self.asset_transactions),
        }

    def apply_deltas(self, deltas: dict[str, float]) -> None:
        for key, delta in deltas.items():
            if key in {"cash", "property_value", "debt"}:
                current = float(getattr(self, key))
                setattr(self, key, current + float(delta))
        self.recalculate_net_worth()

    def gross_estate_value(self) -> float:
        self.recalculate_net_worth()
        return max(self.net_worth, 0.0)
