"""Shared state threaded through every node of the repo-onboarding analysis graph."""
from __future__ import annotations

from typing import TypedDict


class OnboardingState(TypedDict, total=False):
    # --- inputs (set once, before the graph starts, from the deterministic scan) ---
    repo_digest: str
    file_index: list[str]
    language_counts: dict[str, int]
    manifest_kinds: list[str]
    top_level_entries: list[str]
    dependencies: list[str]

    # --- detect_stack ---
    known_stack: list[str]
    unknown_terms: list[str]

    # --- web_enrichment ---
    glossary: dict[str, str]

    # --- product_analysis ---
    problem_statement: str
    target_users: str
    key_features: list[str]
    value_proposition: str

    # --- tech_analysis ---
    architecture_summary: str
    key_components: list[dict]
    data_flow: str
    notable_patterns: list[str]

    # --- learning_path / ground_learning_path ---
    learning_steps: list[dict]

    # --- bookkeeping ---
    degraded: bool
    degraded_reasons: list[str]
