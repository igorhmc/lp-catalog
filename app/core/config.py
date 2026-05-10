from functools import lru_cache
import os
from typing import List

from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "LP Catalog")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "db")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "lp_catalog")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "lpuser")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "lpsecret")

    DISCOGS_TOKEN: str | None = os.getenv("DISCOGS_TOKEN")
    COVERS_DIR: str = os.getenv("COVERS_DIR", "/app/covers")
    ALLOWED_ORIGINS_RAW: str = os.getenv("ALLOWED_ORIGINS", "")
    AUTO_APPLY_MIGRATIONS: bool = os.getenv("AUTO_APPLY_MIGRATIONS", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def async_db_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = self.MYSQL_USER
        pwd = self.MYSQL_PASSWORD
        host = self.MYSQL_HOST
        port = self.MYSQL_PORT
        db = self.MYSQL_DATABASE
        return f"mysql+asyncmy://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"

    @property
    def sync_db_uri(self) -> str:
        if self.async_db_uri.startswith("sqlite+aiosqlite://"):
            return self.async_db_uri.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return self.async_db_uri.replace("+asyncmy", "+pymysql", 1)

    @property
    def cors_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS_RAW.strip():
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

    @property
    def allow_all_origins(self) -> bool:
        return "*" in self.cors_origins

@lru_cache
def get_settings() -> Settings:
    return Settings()
