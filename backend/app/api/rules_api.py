from typing import Any

from fastapi import APIRouter, HTTPException

from app.infrastructure.config import settings
from app.infrastructure.errors import DomainError
from app.rules.models import RuleSetSummary
from app.rules.rule_loader import RuleLoader

router = APIRouter(prefix="/dev/rules", tags=["dev-rules"])


def _get_loader() -> RuleLoader:
    return RuleLoader()


@router.get("/default-version")
def get_default_rule_version() -> dict[str, str]:
    loader = _get_loader()
    return {"default_rule_version": loader.version_manager.get_default_version()}


@router.get("/versions")
def list_rule_versions() -> dict[str, list[str]]:
    loader = _get_loader()
    return {"versions": loader.version_manager.list_versions()}


@router.get("/{rule_version}/summary", response_model=RuleSetSummary)
def get_rule_summary(rule_version: str) -> RuleSetSummary:
    try:
        return _get_loader().summarize(rule_version)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{rule_version}/validate")
def validate_rule_version(rule_version: str) -> dict[str, Any]:
    try:
        _get_loader().validate_version(rule_version)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"rule_version": rule_version, "valid": True}


def include_dev_rules_router(app: Any) -> None:
    if settings.enable_dev_routes:
        app.include_router(router)
