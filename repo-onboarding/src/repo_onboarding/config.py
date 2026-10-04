"""Runtime configuration for the repo-onboarding CLI, loaded from environment variables or a
local .env file. Same philosophy as agent-service/app/config.py: no secrets have defaults
other than empty string, and a missing key degrades to a clear error at the point of use
rather than a silent fallback.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["auto", "groq", "xai", "google"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    onboard_llm_provider: ProviderName = "auto"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    xai_api_key: str = ""
    xai_model: str = "grok-2-latest"
    xai_base_url: str = "https://api.x.ai/v1"

    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    llm_temperature: float = 0.2
    llm_request_timeout_seconds: int = 60

    # --- Repo scanning bounds (keep the tool lightweight even on huge repos) ---
    max_files_scanned: int = 4000
    max_file_bytes: int = 200_000
    max_readme_chars: int = 12_000
    max_digest_chars: int = 20_000

    # --- Web enrichment: best-effort, degrades silently if disabled/unreachable ---
    enable_web_lookup: bool = True
    max_web_lookups: int = 6
    web_lookup_timeout_seconds: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
