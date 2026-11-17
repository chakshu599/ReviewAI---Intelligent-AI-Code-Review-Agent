"""Environment-backed application configuration."""

from functools import lru_cache
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    groq_timeout_seconds: float
    groq_max_retries: int
    max_diff_bytes: int
    max_files: int
    max_llm_context_chars: int
    github_token: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once; values remain configurable through the environment."""
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        groq_timeout_seconds=float(os.getenv("GROQ_TIMEOUT_SECONDS", "45")),
        groq_max_retries=max(0, int(os.getenv("GROQ_MAX_RETRIES", "2"))),
        max_diff_bytes=max(1024, int(os.getenv("MAX_DIFF_BYTES", "200000"))),
        max_files=max(1, int(os.getenv("MAX_FILES", "100"))),
        max_llm_context_chars=max(1000, int(os.getenv("MAX_LLM_CONTEXT_CHARS", "50000"))),
        github_token=os.getenv("GITHUB_TOKEN") or None,
    )
