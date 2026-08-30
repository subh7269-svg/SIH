from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "TraceX — Bitcoin Investigation & Risk Intelligence"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Storage & DB
    DATABASE_URL: str = "sqlite:///./tracex.db"
    
    # Security & Auth
    JWT_SECRET: str = "tracex_investigative_secret_key_sih2026_offline_security"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    
    # Ingestion Limits
    UPLOAD_MAX_SIZE_MB: int = 100
    BATCH_INSERT_SIZE: int = 1000
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ML_ARTIFACT_DIR: Path = BASE_DIR / "ml" / "artifacts"
    GEOIP_DATA_PATH: Path = BASE_DIR / "backend" / "app" / "geoip" / "data" / "offline_subnets.json"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
