"""Google Gemini chat model factory shared by the agent graph."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings


class ProviderNotConfiguredError(RuntimeError):
    """Raised when no LLM provider has a usable API key."""


def get_chat_model(settings: Settings):
    """Build a LangChain chat model using the configured Gemini settings."""
    if not settings.google_genai_api_key:
        raise ProviderNotConfiguredError("GOOGLE_GENAI_API_KEY is not configured.")

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        api_key=settings.google_genai_api_key,
        model=settings.google_genai_chat_model,
        temperature=settings.llm_temperature,
        timeout=settings.llm_request_timeout_seconds,
    )
