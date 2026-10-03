from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

# backend/ directory is three levels up from this file (app/core/config.py)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "MoieRec API"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    SECRET_KEY: str = "moierec-development-secret-key-change-in-production"

    # TMDB integration
    TMDB_API_KEY: str = ""

    # Data paths (relative to project root by default)
    CATALOG_DB_PATH: str = "data/serving/catalog.sqlite"
    TMDB_CACHE_DB_PATH: str = "data/serving/tmdb_cache.sqlite"

    # CORS Origins — localhost:5173 only for this phase
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        # Resolve .env relative to backend/ directory regardless of CWD.
        # Try both the backend/ subdirectory .env and the project-root .env,
        # with backend/.env taking priority (listed last = higher priority in pydantic-settings).
        env_file=(
            str(_PROJECT_DIR / ".env"),
            str(_BACKEND_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
