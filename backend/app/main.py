from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.rules.rule_loader import RuleLoader

app = FastAPI(title="Text Life Simulation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
