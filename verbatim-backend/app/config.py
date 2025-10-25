from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-preview-09-2025"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()
