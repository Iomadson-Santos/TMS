import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/tms_db"
    SECRET_KEY: str = "dev-secret-key"
    DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if os.getenv("ENV") == "production":
    if settings.DATABASE_URL == "mysql+pymysql://root:root@localhost:3306/tms_db":
        raise RuntimeError("DATABASE_URL precisa ser configurada em produção")
    if settings.SECRET_KEY == "dev-secret-key":
        raise RuntimeError("SECRET_KEY precisa ser configurada em produção")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
