from pathlib import Path


def test_frontend_does_not_hold_core_probability_or_settlement_rules() -> None:
    frontend_src = Path(__file__).resolve().parents[2] / "frontend" / "src"
    if not frontend_src.exists():
        return

    forbidden_tokens = [
        "Math.random",
        "direct_death_probability_limit",
        "natural_death_probability",
        "tax_rate",
        "inheritance_tax",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in frontend_src.rglob("*.ts*"))

    for token in forbidden_tokens:
        assert token not in source
