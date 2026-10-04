"""Builds the LangGraph StateGraph for the Issue Resolution Agent.

Flow:
    classify_issue -> retrieve_context -> plan_fix -> draft_patch -> self_review
                                                            ^                |
                                                            +--- REVISE -----+
                                                                             v
                                                                         finalize

`self_review` loops back to `draft_patch` at most `max_review_iterations` times
(a bounded reflection/critic loop), then always proceeds to `finalize`.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langgraph.graph import END, StateGraph

from app.agent.prompts import (
    CLASSIFY_SYSTEM,
    CLASSIFY_USER,
    DRAFT_SYSTEM,
    DRAFT_USER,
    PLAN_SYSTEM,
    PLAN_USER,
    REVIEW_SYSTEM,
    REVIEW_USER,
)
from app.agent.state import AgentState
from app.tools import CodebaseSearchTool

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


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


def _degraded(state: AgentState, reason: str, **fields: Any) -> dict:
    """Builds a degraded-fallback node result, appending `reason` to any prior degraded_reasons."""
    return {
        **fields,
        "degraded": True,
        "degraded_reasons": (state.get("degraded_reasons") or []) + [reason],
    }


def build_graph(llm, search_tool: CodebaseSearchTool):
    graph = StateGraph(AgentState)

    def classify_issue(state: AgentState) -> dict:
        try:
            data = _invoke_json(
                llm,
                CLASSIFY_SYSTEM.format(repo=state["repository_full_name"]),
                CLASSIFY_USER.format(title=state["issue_title"], body=state["issue_body"] or "(empty)"),
            )
            return {
                "issue_type": str(data.get("issue_type", "bug")),
                "search_queries": [str(q) for q in data.get("search_queries", [])][:3] or [state["issue_title"]],
            }
        except Exception:
            return _degraded(
                state,
                "classify_issue: could not parse model output, using issue title as search query",
                issue_type="bug",
                search_queries=[state["issue_title"]],
            )

    def retrieve_context(state: AgentState) -> dict:
        queries = state.get("search_queries") or [state["issue_title"]]
        seen_files: set[str] = set()
        blocks: list[str] = []
        for query in queries[:3]:
            for result in search_tool.search(query, top_k=6):
                key = f"{result.file_path}:{result.chunk_index}"
                if key in seen_files:
                    continue
                seen_files.add(key)
                blocks.append(f"# {result.file_path or 'unknown file'}\n{result.content or ''}")
        context = "\n\n---\n\n".join(blocks)[:8000] if blocks else "(no matching code chunks found)"
        return {"retrieved_context": context, "files_referenced": sorted(seen_files)}

    def plan_fix(state: AgentState) -> dict:
        try:
            data = _invoke_json(
                llm,
                PLAN_SYSTEM.format(repo=state["repository_full_name"]),
                PLAN_USER.format(
                    issue_type=state.get("issue_type", "bug"),
                    title=state["issue_title"],
                    body=state["issue_body"] or "(empty)",
                    context=state.get("retrieved_context", ""),
                ),
            )
            plan = [str(p) for p in data.get("plan", [])] or ["Investigate further before making a change."]
            return {
                "summary": str(data.get("summary", "")),
                "root_cause": str(data.get("root_cause", "Unable to determine root cause with available context.")),
                "plan": plan,
            }
        except Exception:
            return _degraded(
                state,
                "plan_fix: could not parse model output",
                summary="The agent could not confidently analyze this issue from the available code context.",
                root_cause="Unable to determine root cause: the model response could not be parsed.",
                plan=["Have a maintainer manually triage this issue."],
            )

    def draft_patch(state: AgentState) -> dict:
        revision_note = ""
        if state.get("review_feedback"):
            revision_note = f"\n\nPrevious reviewer feedback to address:\n{state['review_feedback']}"
        try:
            data = _invoke_json(
                llm,
                DRAFT_SYSTEM.format(repo=state["repository_full_name"]),
                DRAFT_USER.format(
                    title=state["issue_title"],
                    root_cause=state.get("root_cause", ""),
                    plan="\n".join(f"- {p}" for p in state.get("plan", [])),
                    context=state.get("retrieved_context", ""),
                    revision_note=revision_note,
                ),
            )
            return {
                "proposed_diff": str(data.get("proposed_diff", "")),
                "pr_description": str(data.get("pr_description", "")),
                "test_suggestions": str(data.get("test_suggestions", "")),
            }
        except Exception:
            return _degraded(
                state,
                "draft_patch: could not parse model output",
                proposed_diff="(the agent could not generate a diff — manual investigation required)",
                pr_description=state.get("summary", ""),
                test_suggestions="Add regression tests once the root cause is confirmed manually.",
            )

    def self_review(state: AgentState) -> dict:
        try:
            data = _invoke_json(
                llm,
                REVIEW_SYSTEM,
                REVIEW_USER.format(
                    root_cause=state.get("root_cause", ""),
                    plan="\n".join(f"- {p}" for p in state.get("plan", [])),
                    diff=state.get("proposed_diff", ""),
                    pr_description=state.get("pr_description", ""),
                ),
            )
            verdict = str(data.get("verdict", "PASS")).upper()
            if verdict not in ("PASS", "REVISE"):
                verdict = "PASS"
            return {
                "review_verdict": verdict,
                "review_feedback": str(data.get("feedback", "")),
                "confidence": str(data.get("confidence", "medium")),
            }
        except Exception:
            return _degraded(
                state,
                "self_review: could not parse model output",
                review_verdict="PASS",
                review_feedback="",
                confidence="low",
            )

    def route_after_review(state: AgentState) -> str:
        revise_count = state.get("revise_count", 0)
        max_iterations = state.get("max_review_iterations", 2)
        if state.get("review_verdict") == "REVISE" and revise_count < max_iterations:
            return "draft_patch"
        return "finalize"

    def bump_revise_count(state: AgentState) -> dict:
        return {"revise_count": state.get("revise_count", 0) + 1}

    def finalize(state: AgentState) -> dict:
        return {}  # terminal node; final state is read directly by the caller

    graph.add_node("classify_issue", classify_issue)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("plan_fix", plan_fix)
    graph.add_node("draft_patch", draft_patch)
    graph.add_node("self_review", self_review)
    graph.add_node("bump_revise_count", bump_revise_count)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("classify_issue")
    graph.add_edge("classify_issue", "retrieve_context")
    graph.add_edge("retrieve_context", "plan_fix")
    graph.add_edge("plan_fix", "draft_patch")
    graph.add_edge("draft_patch", "self_review")
    graph.add_conditional_edges(
        "self_review", route_after_review, {"draft_patch": "bump_revise_count", "finalize": "finalize"}
    )
    graph.add_edge("bump_revise_count", "draft_patch")
    graph.add_edge("finalize", END)

    return graph.compile()
