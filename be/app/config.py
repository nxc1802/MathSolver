from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_env: str = "development"
    debug: bool = True
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    
    # MegaLLM API
    megallm_api_key: str = ""
    megallm_base_url: str = "https://api.megallm.io/v1"
    megallm_model: str = "deepseek-r1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
