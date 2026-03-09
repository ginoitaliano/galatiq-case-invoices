#backend/config.py
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

#project root
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = Path(__file__).parent / ".env"

class Settings(BaseSettings):
    # Grok
    grok_api_key: Optional[str] = None
    grok_model: str = "grok-3"

    # Claude fallback
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Postgres
    database_url: Optional[str] = None

    # SQLite mock inventory
    sqlite_path: str = str(BASE_DIR / "data" / "inventory.db")

    # Invoice folder
    invoice_folder: str = str(BASE_DIR / "data" / "invoices")

    # Tesseract
    tesseract_path: Optional[str] = None

    # LangSmith
    langchain_tracing_v2: Optional[str] = None
    langchain_endpoint: Optional[str] = None    
    langchain_api_key: Optional[str] = None
    langchain_project: Optional[str] = None

    # Agent thresholds
    vp_approval_threshold: float = 10000.00
    extraction_confidence_threshold: float = 0.70

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"                       

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

