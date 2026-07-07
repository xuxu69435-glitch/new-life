from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite:///./text_life_sim.db"
    default_rule_version: str = "v1"
    enable_dev_routes: bool = True


settings = Settings()
