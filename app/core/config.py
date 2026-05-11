from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str
    ENVIRONMENT: str
    UPLOAD_DIR: str = "storage/uploads"
    CLEANED_TEXT_DIR: str = "storage/cleaned"

    FIRST_ADMIN_EMAIL: str
    FIRST_ADMIN_PASSWORD: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: str
    LANGGRAPH_CHECKPOINT_DATABASE_URL: str
    
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_URL: str

    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_URL: str
    QDRANT_GOLD_COLLECTION: str = "adgs_gold_documents"
    QDRANT_VECTOR_SIZE: int = 384

    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_VECTOR_SIZE: int = 384

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()