"""Pydantic request/response contract for the agent-service API.

The wire format is camelCase; Python code uses idiomatic snake_case attributes via
Pydantic v2 alias generation.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IssuePayload(CamelModel):
    number: int
    title: str
    body: str = ""


class AgentRunRequest(CamelModel):
    repository_id: str
    repository_full_name: str
    issue: IssuePayload
    internal_api_base_url: str
    internal_api_key: str
    max_review_iterations: int = Field(default=2, ge=0, le=5)


class AgentResult(CamelModel):
    issue_type: str
    summary: str
    root_cause: str
    plan: list[str]
    proposed_diff: str
    pr_description: str
    test_suggestions: str
    review_feedback: str
    confidence: str
    iterations: int
