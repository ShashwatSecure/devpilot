"""LLM provider abstraction — identical strategy to agent-service/app/providers.py so the
same free-tier setup (Groq / xAI Grok / Google Gemini) works here without change. Kept as an
independent copy (not a shared import) so this package has zero dependency on agent-service
and can be installed completely standalone.
"""
from __future__ import annotations

from dataclasses import dataclass

from repo_onboarding.config import Settings


class ProviderNotConfiguredError(RuntimeError):
    """Raised when no LLM provider has a usable API key."""


@dataclass(frozen=True)
class ResolvedProvider:
    name: str
    model: str


def resolve_provider(settings: Settings) -> ResolvedProvider:
    # Order matters for "auto": first configured key wins, groq -> xai -> google.
    providers = {
        "groq": (settings.groq_api_key, settings.groq_model, "GROQ_API_KEY"),
        "xai": (settings.xai_api_key, settings.xai_model, "XAI_API_KEY"),
        "google": (settings.google_api_key, settings.google_model, "GOOGLE_API_KEY"),
    }

    requested = settings.onboard_llm_provider
    if requested in providers:
        api_key, model, env_var = providers[requested]
        _require(api_key, requested, env_var)
        return ResolvedProvider(requested, model)

    for name, (api_key, model, _) in providers.items():
        if api_key:
            return ResolvedProvider(name, model)

    raise ProviderNotConfiguredError(
        "No LLM provider configured. Set one of GROQ_API_KEY (recommended, free at "
        "console.groq.com), XAI_API_KEY, or GOOGLE_API_KEY — in your environment or a "
        "repo-onboarding/.env file."
    )


def _require(value: str, name: str, env_var: str) -> None:
    if not value:
        raise ProviderNotConfiguredError(
            f"ONBOARD_LLM_PROVIDER is set to '{name}' but {env_var} is not configured."
        )


def get_chat_model(settings: Settings):
    """Builds a LangChain chat model for the resolved provider. Imports are local so a
    missing optional dependency for an unused provider never breaks the other two."""
    provider = resolve_provider(settings)
    common = {
        "model": provider.model,
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_request_timeout_seconds,
    }

    if provider.name == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(api_key=settings.groq_api_key, **common)

    if provider.name == "xai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(api_key=settings.xai_api_key, base_url=settings.xai_base_url, **common)

    if provider.name == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(api_key=settings.google_api_key, **common)

    raise ProviderNotConfiguredError(f"Unknown provider '{provider.name}'")
