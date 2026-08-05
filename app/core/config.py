from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "multimodal-document-intelligence"
    ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str  # used by alembic

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # S3 / MinIO
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "documents"
    S3_REGION: str = "us-east-1"

    # Anthropic (vision extraction)
    ANTHROPIC_API_KEY: str
    ANTHROPIC_VISION_MODEL: str = "claude-haiku-4-5-20251001"

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # Pipeline
    OCR_CONFIDENCE_THRESHOLD: float = 0.6  # below this, escalate to vision model
    MAX_UPLOAD_SIZE_MB: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()