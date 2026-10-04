"""Tools the LangGraph agent can call. Deliberately minimal: the only external side effect
available to the model is a read-only, repository-scoped vector search against code already
indexed by the Java backend. There is no file-write, shell, or arbitrary-HTTP tool, so even a
successful prompt-injection attempt inside an issue body has nothing destructive to reach for.
"""
from __future__ import annotations

import httpx
from pydantic import BaseModel

from app.schemas import CamelModel

MAX_QUERY_LENGTH = 300


class CodeSearchResult(CamelModel):
    file_path: str | None = None
    language: str | None = None
    content: str | None = None
    chunk_index: int | None = None
    score: float | None = None


class CodebaseSearchTool(BaseModel):
    """Bound to one run's repository + backend callback credentials."""

    repository_id: str
    internal_api_base_url: str
    internal_api_key: str

    model_config = {"frozen": True}

    def search(self, query: str, top_k: int = 8) -> list[CodeSearchResult]:
        safe_query = (query or "").strip()[:MAX_QUERY_LENGTH]
        if not safe_query:
            return []
        try:
            response = httpx.post(
                f"{self.internal_api_base_url}/agent/search",
                json={
                    "repositoryId": self.repository_id,
                    "query": safe_query,
                    "topK": top_k,
                },
                headers={"X-Internal-Api-Key": self.internal_api_key},
                timeout=20,
            )
            response.raise_for_status()
            return [CodeSearchResult.model_validate(item) for item in response.json()]
        except httpx.HTTPError:
            # A retrieval failure should degrade the run, not crash it.
            return []
