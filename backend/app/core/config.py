from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "AI Knowledge Assistant"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./knowledge_assistant.db")

    # ===========================================
    # HUGGING FACE INFERENCE API CONFIGURATION
    # ===========================================
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")  # Required for HF Inference API
    HF_INFERENCE_ENDPOINT: str = os.getenv(
        "HF_INFERENCE_ENDPOINT", 
        "https://router.huggingface.co/hf-inference/models"
    )
    
    # Mistral AI Model Configuration
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")
    LLM_MAX_NEW_TOKENS: int = int(os.getenv("LLM_MAX_NEW_TOKENS", "1024"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "0.95"))
    LLM_REPETITION_PENALTY: float = float(os.getenv("LLM_REPETITION_PENALTY", "1.1"))
    
    # Embedding Model (BGE - local)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # ===========================================
    # QDRANT VECTOR DATABASE CONFIGURATION
    # ===========================================
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "knowledge_documents")
    QDRANT_USE_MEMORY: bool = os.getenv("QDRANT_USE_MEMORY", "true").lower() == "true"
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "./qdrant_data")
    
    # ===========================================
    # RAG CONFIGURATION
    # ===========================================
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))  # Words per chunk
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))  # Overlap words
    MAX_RETRIEVAL_DOCS: int = int(os.getenv("MAX_RETRIEVAL_DOCS", "5"))  # Max docs for RAG
    MIN_SIMILARITY_SCORE: float = float(os.getenv("MIN_SIMILARITY_SCORE", "0.5"))
    
    # ===========================================
    # RATE LIMITING & RETRY CONFIGURATION
    # ===========================================
    HF_MAX_RETRIES: int = int(os.getenv("HF_MAX_RETRIES", "3"))
    HF_RETRY_DELAY: float = float(os.getenv("HF_RETRY_DELAY", "1.0"))  # seconds
    HF_TIMEOUT: int = int(os.getenv("HF_TIMEOUT", "60"))  # seconds
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30"))
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))  # seconds
    
    # ===========================================
    # FILE UPLOAD CONFIGURATION
    # ===========================================
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".csv"]
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")

    # ===========================================
    # ANALYTICS & TELEMETRY
    # ===========================================
    ENABLE_ANALYTICS: bool = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ANALYTICS_RETENTION_DAYS: int = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))

    # ===========================================
    # CORS CONFIGURATION
    # ===========================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ]

    # ===========================================
    # REDIS/CELERY (Optional for background tasks)
    # ===========================================
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Legacy ChromaDB settings (for backward compatibility)
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars for backward compatibility


settings = Settings()
