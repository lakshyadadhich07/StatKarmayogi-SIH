import json
import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "StatKarmayogi"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL Connection String (psycopg 3)
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:password@localhost:5432/statkarmayogi_db"
    )

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = "statkarmayogi-super-secure-jwt-secret-key-min-32-bytes-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Document Upload & Processing Settings (Phase 4)
    UPLOAD_DIR: str = "storage/documents"
    MAX_UPLOAD_SIZE_MB: int = 20
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # Mistral AI Embeddings & ChromaDB Vector Store (Phase 4)
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_EMBEDDING_MODEL: str = "mistral-embed"
    CHROMA_PERSIST_DIRECTORY: str = "storage/chroma"
    CHROMA_COLLECTION_NAME: str = "statkarmayogi_chunks"

    # Mistral AI LLM & MCQ Generation Settings (Phase 5)
    MISTRAL_LLM_MODEL: str = "mistral-large-latest"
    MISTRAL_TEMPERATURE: float = 0.2
    DEFAULT_MCQ_VOLUME: int = 5
    MAX_MCQ_VOLUME: int = 20

    # Assessment & Scoring Settings (Phase 7)
    # Note: These are configurable prototype scoring thresholds and are not presented as official MoSPI competency thresholds.
    DEFAULT_ASSESSMENT_QUESTION_COUNT: int = 10
    MAX_ASSESSMENT_QUESTION_COUNT: int = 50
    ADVANCED_THRESHOLD: float = 80.0
    PROFICIENT_THRESHOLD: float = 65.0
    DEVELOPING_THRESHOLD: float = 50.0

    # iGOT Recommendation & Adapter Settings (Phase 8)
    MAX_RECOMMENDATIONS_PER_GAP: int = 2
    MAX_TOTAL_ACTIVE_RECOMMENDATIONS: int = 6
    IGOT_ADAPTER_TYPE: str = "mock"
    MOCK_IGOT_CATALOGUE_VERSION: str = "v1-prototype"

    # CORS Origins for frontend integration (Streamlit, React, etc.)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except Exception:
                    pass
            return [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent.parent / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
