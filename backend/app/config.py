from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./energy_tracker.db"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://energy-tracker-swart.vercel.app",
    ]
    cors_origin_regex: str = r"https://.*\.vercel\.app"

    class Config:
        env_file = ".env"


settings = Settings()
