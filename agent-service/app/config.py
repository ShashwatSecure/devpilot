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
    google_genai_api_key: str = ""
    google_genai_chat_model: str = "gemini-3.8-flash"

    llm_temperature: float = 0.2
    llm_request_timeout_seconds: int = 60

    # --- Agent behaviour ---------------------------------------------------------
    max_review_iterations_default: int = 2

    # --- Networking ----------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://devpilot:devpilot@localhost:5432/devpilot"

    # --- Local embeddings (Qwen3-Embedding-0.6B, run via sentence-transformers) -----
    # Native output dimension is 1024; the `embeddings` table's vector column must match.
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dimension: int = 1024

    # --- Guest sessions --------------------------------------------------------------
    session_cookie_name: str = "devpilot_session"
    session_secret: str = "dev-insecure-secret-change-me"
    session_ttl_hours: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
