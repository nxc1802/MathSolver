import os
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load from backend/.env if available
_env_path = Path(__file__).parents[1] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()



class ProviderCredentials(BaseModel):
    provider: str
    keys: List[str] = Field(default_factory=list)


def parse_comma_separated_keys(raw: str) -> List[str]:
    if not raw:
        return []
    keys = []
    for piece in raw.split(","):
        cleaned = piece.strip().strip("'\" ")
        if cleaned:
            keys.append(cleaned)
    return keys


class Settings(BaseModel):
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    llm_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("LLM_TIMEOUT_SECONDS", "120")))
    llm_cooldown_seconds: int = Field(default_factory=lambda: int(os.getenv("LLM_COOLDOWN_SECONDS", "60")))
    default_chat_model: str = Field(default_factory=lambda: os.getenv("DEFAULT_CHAT_MODEL", "gemini/gemini-2.5-flash"))

    def get_provider_credentials(self) -> Dict[str, ProviderCredentials]:
        """Parses API keys for all supported providers from environment variables."""
        credentials: Dict[str, ProviderCredentials] = {}

        # 1. Gemini / Google
        gemini_raw = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        gemini_keys = parse_comma_separated_keys(gemini_raw)
        # Also check indexed keys GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
        for i in range(1, 20):
            k = os.getenv(f"GEMINI_API_KEY_{i}") or os.getenv(f"GOOGLE_API_KEY_{i}")
            if k and k.strip() and k.strip() not in gemini_keys:
                gemini_keys.append(k.strip())
        credentials["gemini"] = ProviderCredentials(provider="gemini", keys=gemini_keys)

        # 2. OpenAI
        openai_raw = os.getenv("OPENAI_API_KEY") or ""
        openai_keys = parse_comma_separated_keys(openai_raw)
        for i in range(1, 10):
            k = os.getenv(f"OPENAI_API_KEY_{i}")
            if k and k.strip() and k.strip() not in openai_keys:
                openai_keys.append(k.strip())
        credentials["openai"] = ProviderCredentials(provider="openai", keys=openai_keys)

        # 3. Anthropic
        anthropic_raw = os.getenv("ANTHROPIC_API_KEY") or ""
        anthropic_keys = parse_comma_separated_keys(anthropic_raw)
        credentials["anthropic"] = ProviderCredentials(provider="anthropic", keys=anthropic_keys)

        # 4. OpenRouter
        openrouter_raw = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY_1") or ""
        openrouter_keys = parse_comma_separated_keys(openrouter_raw)
        credentials["openrouter"] = ProviderCredentials(provider="openrouter", keys=openrouter_keys)

        return credentials


settings = Settings()
