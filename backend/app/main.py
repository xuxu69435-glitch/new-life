from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.achievement_api import router as achievement_router
from app.api.family_api import router as family_router
from app.api.game_api import router as game_router
from app.api.inheritance_api import router as inheritance_router
from app.api.legal_api import dev_router as legal_dev_router
from app.api.legal_api import router as legal_router
from app.api.mainline_api import router as mainline_router
from app.api.person_api import router as person_router
from app.api.rules_api import include_dev_rules_router
from app.api.save_api import router as save_router
from app.api.timeline_api import router as timeline_router
from app.infrastructure.config import settings
from app.infrastructure.save.db import init_database
from app.rules.rule_loader import RuleLoader

app = FastAPI(title="Text Life Simulation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)
app.include_router(save_router)
app.include_router(person_router)
app.include_router(timeline_router)
app.include_router(family_router)
app.include_router(inheritance_router)
app.include_router(legal_router)
app.include_router(mainline_router)
app.include_router(achievement_router)
if settings.enable_dev_routes:
    app.include_router(legal_dev_router)
include_dev_rules_router(app)


@app.on_event("startup")
def validate_default_rules_on_startup() -> None:
    loader = RuleLoader()
    loader.version_manager.ensure_default_available()
    loader.load_default()
    if settings.save_repository_type == "postgres" and settings.auto_create_tables:
        init_database(create_tables=True)
    if settings.save_repository_type == "sqlite":
        from app.infrastructure.save.sqlite_db import init_sqlite_database

        init_sqlite_database(create_tables=True)


def _check_rules_loaded() -> bool:
    try:
        loader = RuleLoader()
        loader.version_manager.ensure_default_available()
        loader.load_default()
        return True
    except Exception:
        return False


def _check_database_connected() -> bool:
    repo_type = settings.save_repository_type.strip().lower()
    if repo_type == "memory":
        return True
    if repo_type == "sqlite":
        try:
            from app.infrastructure.save.sqlite_db import get_sqlite_engine

            with get_sqlite_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    if repo_type == "postgres":
        try:
            from app.infrastructure.save.db import get_engine

            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    return True


@app.get("/health")
def health_check() -> dict[str, str | bool]:
    rules_loaded = _check_rules_loaded()
    database_connected = _check_database_connected()
    healthy = rules_loaded and database_connected
    return {
        "status": "ok" if healthy else "degraded",
        "environment": settings.environment,
        "repository_type": settings.save_repository_type,
        "rules_loaded": rules_loaded,
        "database_connected": database_connected,
        "default_rule_version": settings.default_rule_version,
    }
