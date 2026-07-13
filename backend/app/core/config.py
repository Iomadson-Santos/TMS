import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "TMS API")
    app_version: str = os.getenv("APP_VERSION", "2.0.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./tms.db")

    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500",
        ).split(",")
        if origin.strip()
    ]

    secret_key: str = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.database_url.startswith("mysql://"):
        settings.database_url = settings.database_url.replace(
            "mysql://", "mysql+pymysql://", 1
        )
    return settings
