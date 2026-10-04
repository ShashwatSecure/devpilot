"""Shared state threaded through every node of the Issue Resolution Agent graph."""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # --- inputs (set once, before the graph starts) ---
    repository_id: str
    repository_full_name: str
    issue_title: str
    issue_body: str
    max_review_iterations: int

    # --- classify_issue ---
    issue_type: str
    search_queries: list[str]

    # --- retrieve_context ---
    retrieved_context: str
    files_referenced: list[str]

    # --- plan_fix ---
    summary: str
    root_cause: str
    plan: list[str]

    # --- draft_patch ---
    proposed_diff: str
    pr_description: str
    test_suggestions: str

    # --- self_review ---
    review_verdict: str  # "PASS" | "REVISE"
    review_feedback: str
    confidence: str
    revise_count: int

    # --- bookkeeping ---
    degraded: bool
    degraded_reasons: list[str]
