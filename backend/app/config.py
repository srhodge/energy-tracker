from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./energy_tracker.db"
    anthropic_api_key: Optional[str] = None

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        # Heroku/Railway may provide postgres:// which SQLAlchemy rejects
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://energy-tracker-swart.vercel.app",
    ]
    cors_origin_regex: str = r"https://.*\.vercel\.app"

    class Config:
        env_file = ".env"


settings = Settings()
