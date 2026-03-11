"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings — loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === App ===
    APP_NAME: str = "AgenticP1"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    TRUSTED_HOSTS: List[str] = []

    # === LLM ===
    LLM_PROVIDER: Literal["groq", "ollama", "together", "openai"] = "groq"
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: Optional[SecretStr] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    TOGETHER_API_KEY: Optional[SecretStr] = None
    OPENAI_API_KEY: Optional[SecretStr] = None

    # === STT (Speech-to-Text) ===
    STT_PROVIDER: Literal["groq_whisper", "faster_whisper", "vosk"] = "groq_whisper"
    WHISPER_MODEL_SIZE: Literal["tiny", "small", "medium", "large"] = "tiny"
    VOSK_MODEL_PATH: str = "./data/models/vosk"

    # === TTS (Text-to-Speech) ===
    TTS_PROVIDER: Literal["piper", "gtts", "edge_tts"] = "gtts"
    PIPER_VOICE: str = "en_US-amy-low"
    PIPER_MODEL_PATH: str = "./data/models/piper"
    EDGE_TTS_VOICE: str = "en-US-JennyNeural"
    TTS_LANGUAGE: str = "en"

    # === Telephony ===
    TELEPHONY_PROVIDER: Literal["telnyx", "twilio"] = "telnyx"
    TELNYX_API_KEY: Optional[SecretStr] = None
    TELNYX_CONNECTION_ID: Optional[str] = None
    TELNYX_PHONE_NUMBER: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[SecretStr] = None
    TWILIO_AUTH_TOKEN: Optional[SecretStr] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # === Database ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/agenticp1.db"

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # === Auth ===
    JWT_SECRET: SecretStr = Field(default="change-this-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    JWT_REFRESH_EXPIRY_DAYS: int = 7

    # === Knowledge Base ===
    CHROMA_PERSIST_DIR: str = "./data/chromadb"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # === Billing ===
    STRIPE_API_KEY: Optional[SecretStr] = None
    STRIPE_WEBHOOK_SECRET: Optional[SecretStr] = None

    # === Call Settings ===
    CALL_MAX_DURATION_SECONDS: int = 1800  # 30 min
    SILENCE_THRESHOLD_SECONDS: float = 2.0
    INTERRUPTION_THRESHOLD_SECONDS: float = 0.5
    RECORDINGS_DIR: str = "./data/recordings"

    @field_validator("CORS_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_list(cls, v: str | list) -> list:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
