from typing import Any

from app.modules.assets.models import AssetState
from app.modules.family.models import FamilyState
from app.modules.inheritance.models import HeirShare, InheritanceResult

INHERITANCE_RULE_NAMESPACE = "inheritance"


def get_inheritance_rules(rules: dict) -> dict[str, Any]:
    return rules.get(INHERITANCE_RULE_NAMESPACE, {})


def calculate_gross_estate(assets: AssetState) -> float:
    return assets.gross_estate_value()


def settle_estate(
    life_id: str,
    deceased_person_id: str,
    assets: AssetState,
    family: FamilyState,
    inheritance_rules: dict[str, Any],
    death_type: str | None = None,
) -> InheritanceResult:
    tax_rate = float(inheritance_rules["tax_rate"])
    gross_estate = calculate_gross_estate(assets)
    tax_amount = gross_estate * tax_rate
    net_estate = gross_estate - tax_amount

    heirs: list[HeirShare] = []
    distribution: dict[str, float] = {}
    unclaimed_amount = 0.0
    status = "settled"

    has_spouse = family.has_spouse()
    has_children = family.has_children()

    if gross_estate <= 0:
        return InheritanceResult(
            life_id=life_id,
            deceased_person_id=deceased_person_id,
            gross_estate=gross_estate,
            tax_rate=tax_rate,
            tax_amount=0.0,
            net_estate=0.0,
            heirs=[],
            distribution={},
            unclaimed_amount=0.0,
            status="zero_estate",
            created_from_death_type=death_type,
        )

    if has_spouse and has_children:
        partner_ratio = float(inheritance_rules["partner_share_ratio"])
        descendant_ratio = float(inheritance_rules["descendant_share_ratio"])
        partner_amount = net_estate * partner_ratio
        descendants_total = net_estate * descendant_ratio
        heirs.append(
            HeirShare(
                person_id=family.spouse.person_id,  # type: ignore[union-attr]
                relation="spouse",
                share_ratio=partner_ratio,
                amount=partner_amount,
            )
        )
        distribution[family.spouse.person_id] = partner_amount  # type: ignore[union-attr]
        child_share_ratio = descendant_ratio / len(family.children)
        child_amount = descendants_total / len(family.children)
        for child in family.children:
            heirs.append(
                HeirShare(
                    person_id=child.person_id,
                    relation="child",
                    share_ratio=child_share_ratio,
                    amount=child_amount,
                )
            )
            distribution[child.person_id] = child_amount
    elif has_spouse and inheritance_rules.get("no_descendants_to_partner", True):
        heirs.append(
            HeirShare(
                person_id=family.spouse.person_id,  # type: ignore[union-attr]
                relation="spouse",
                share_ratio=1.0,
                amount=net_estate,
            )
        )
        distribution[family.spouse.person_id] = net_estate  # type: ignore[union-attr]
    elif has_children and inheritance_rules.get("no_partner_to_descendants", True):
        child_share_ratio = 1.0 / len(family.children)
        child_amount = net_estate / len(family.children)
        for child in family.children:
            heirs.append(
                HeirShare(
                    person_id=child.person_id,
                    relation="child",
                    share_ratio=child_share_ratio,
                    amount=child_amount,
                )
            )
            distribution[child.person_id] = child_amount
    else:
        status = str(inheritance_rules.get("no_heirs_status", "unclaimed"))
        unclaimed_amount = net_estate

    return InheritanceResult(
        life_id=life_id,
        deceased_person_id=deceased_person_id,
        gross_estate=gross_estate,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        net_estate=net_estate,
        heirs=heirs,
        distribution=distribution,
        unclaimed_amount=unclaimed_amount,
        status=status,
        created_from_death_type=death_type,
    )
