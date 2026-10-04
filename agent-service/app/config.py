"""Runtime configuration for the agent-service, loaded from environment variables.

No secrets have defaults other than empty string — missing keys degrade to a clear
"no LLM provider configured" error surfaced at request time, never a silent fallback
to a hard-coded key.
"""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Google Gemini ---------------------------------------------------------
    # Keep these names aligned with backend/src/main/resources/application.yaml.
    google_genai_api_key: str = ""
    google_genai_chat_model: str = "gemini-3.8-flash"

    llm_temperature: float = 0.2
    llm_request_timeout_seconds: int = 60

    # --- Agent behaviour ---------------------------------------------------------
    max_review_iterations_default: int = 2

    # --- Networking ----------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Inbound auth: shared secret the Java backend sends when calling THIS service.
    # Optional for local dev (a warning is logged at startup if unset); strongly
    # recommended whenever this service is reachable from anywhere but a private network.
    agent_service_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
