"""Builds the LangGraph StateGraph for repo onboarding analysis.

Flow:
    detect_stack -> web_enrichment -> product_analysis -> tech_analysis -> learning_path
                                                                                 |
                                                                                 v
                                                                     ground_learning_path

`detect_stack` and `web_enrichment` are deterministic/best-effort (no LLM call). The three
analysis nodes each call the configured LLM once. `ground_learning_path` is a deterministic
validation step: it drops any file reference the model hallucinated that isn't actually in
the scanned file index, so the generated learning path never points a reader at a file that
doesn't exist — the same "never trust unvalidated model output" discipline used by the
issue-resolution agent's JSON-parsing fallbacks.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from repo_onboarding.agent.prompts import (
    LEARNING_PATH_SYSTEM,
    LEARNING_PATH_USER,
    PRODUCT_SYSTEM,
    PRODUCT_USER,
    TECH_SYSTEM,
    TECH_USER,
)
from repo_onboarding.agent.state import OnboardingState
from repo_onboarding.scanner import KNOWN_TECH

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

WebLookup = Callable[[str], "str | None"]


def _extract_json(raw: str) -> dict[str, Any]:
    """Best-effort JSON extraction so the graph tolerates minor formatting slips (markdown
    fences, leading prose) from whichever provider is configured, instead of crashing."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            return json.loads(match.group(0))
        raise


def _invoke_json(llm, system: str, user: str) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = response.content if hasattr(response, "content") else str(response)
    return _extract_json(content)


def _degraded(state: OnboardingState, reason: str, **fields: Any) -> dict:
    """Builds a degraded-fallback node result, appending `reason` to any prior degraded_reasons."""
    return {
        **fields,
        "degraded": True,
        "degraded_reasons": (state.get("degraded_reasons") or []) + [reason],
    }


def build_graph(llm, web_lookup: WebLookup | None = None, *, max_web_lookups: int = 6):
    graph = StateGraph(OnboardingState)

    def detect_stack(state: OnboardingState) -> dict:
        known: list[str] = []
        unknown: list[str] = []
        for dep in state.get("dependencies", []):
            normalized = dep.lower()
            if any(k in normalized for k in KNOWN_TECH):
                known.append(dep)
            else:
                unknown.append(dep)
        return {"known_stack": known, "unknown_terms": unknown[:max_web_lookups]}

    def web_enrichment(state: OnboardingState) -> dict:
        glossary: dict[str, str] = {}
        if web_lookup is not None:
            for term in state.get("unknown_terms", [])[:max_web_lookups]:
                try:
                    summary = web_lookup(term)
                except Exception:
                    summary = None
                if summary:
                    glossary[term] = summary
        return {"glossary": glossary}

    def product_analysis(state: OnboardingState) -> dict:
        try:
            data = _invoke_json(llm, PRODUCT_SYSTEM, PRODUCT_USER.format(digest=state.get("repo_digest", "")))
            return {
                "problem_statement": str(data.get("problem_statement", "")),
                "target_users": str(data.get("target_users", "")),
                "key_features": [str(f) for f in data.get("key_features", [])],
                "value_proposition": str(data.get("value_proposition", "")),
            }
        except Exception:
            return _degraded(
                state,
                "product_analysis: could not parse model output",
                problem_statement="Could not confidently determine the product purpose from available docs.",
                target_users="Unknown",
                key_features=[],
                value_proposition="",
            )

    def tech_analysis(state: OnboardingState) -> dict:
        glossary_text = "\n".join(f"- {k}: {v}" for k, v in state.get("glossary", {}).items())
        try:
            data = _invoke_json(
                llm,
                TECH_SYSTEM,
                TECH_USER.format(
                    digest=state.get("repo_digest", ""),
                    known_stack=", ".join(state.get("known_stack", [])) or "(none detected)",
                    glossary=glossary_text or "(no external lookups)",
                ),
            )
            return {
                "architecture_summary": str(data.get("architecture_summary", "")),
                "key_components": [c for c in data.get("key_components", []) if isinstance(c, dict)],
                "data_flow": str(data.get("data_flow", "")),
                "notable_patterns": [str(p) for p in data.get("notable_patterns", [])],
            }
        except Exception:
            return _degraded(
                state,
                "tech_analysis: could not parse model output",
                architecture_summary="Could not confidently derive the architecture from available signals.",
                key_components=[],
                data_flow="",
                notable_patterns=[],
            )

    def learning_path(state: OnboardingState) -> dict:
        try:
            data = _invoke_json(
                llm,
                LEARNING_PATH_SYSTEM,
                LEARNING_PATH_USER.format(
                    digest=state.get("repo_digest", ""),
                    architecture_summary=state.get("architecture_summary", ""),
                    file_index="\n".join(state.get("file_index", [])[:400]),
                ),
            )
            steps = [s for s in data.get("steps", []) if isinstance(s, dict)]
            return {"learning_steps": steps}
        except Exception:
            return _degraded(state, "learning_path: could not parse model output", learning_steps=[])

    def ground_learning_path(state: OnboardingState) -> dict:
        known_files = set(state.get("file_index", []))
        cleaned = []
        for step in state.get("learning_steps", []):
            files = [f for f in step.get("files", []) if isinstance(f, str) and f in known_files]
            cleaned.append({**step, "files": files})
        return {"learning_steps": cleaned}

    graph.add_node("detect_stack", detect_stack)
    graph.add_node("web_enrichment", web_enrichment)
    graph.add_node("product_analysis", product_analysis)
    graph.add_node("tech_analysis", tech_analysis)
    graph.add_node("learning_path", learning_path)
    graph.add_node("ground_learning_path", ground_learning_path)

    graph.set_entry_point("detect_stack")
    graph.add_edge("detect_stack", "web_enrichment")
    graph.add_edge("web_enrichment", "product_analysis")
    graph.add_edge("product_analysis", "tech_analysis")
    graph.add_edge("tech_analysis", "learning_path")
    graph.add_edge("learning_path", "ground_learning_path")
    graph.add_edge("ground_learning_path", END)

    return graph.compile()
