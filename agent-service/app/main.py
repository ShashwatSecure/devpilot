"""FastAPI entrypoint for the agent-service: a single streaming endpoint that runs the
Issue Resolution Agent LangGraph and reports its progress + final result over SSE.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agent.graph import build_graph
from app.config import Settings, get_settings
from app.providers import ProviderNotConfiguredError, get_chat_model
from app.schemas import AgentResult, AgentRunRequest
from app.tools import CodebaseSearchTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-service")

_NODE_MESSAGES = {
    "classify_issue": "Classifying the issue and drafting code-search queries...",
    "retrieve_context": "Searching the indexed codebase for relevant context...",
    "plan_fix": "Analyzing root cause and drafting a fix plan...",
    "draft_patch": "Drafting a proposed patch and PR description...",
    "self_review": "Self-reviewing the draft for correctness and safety...",
    "bump_revise_count": "Revising based on self-review feedback...",
    "finalize": "Finalizing the proposal...",
}


def verify_caller(x_agent_service_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.agent_service_api_key:
        return  # no key configured -> local-dev mode, already warned about at startup
    if x_agent_service_key != settings.agent_service_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent-service key")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    if not settings.agent_service_api_key:
        logger.warning(
            "AGENT_SERVICE_API_KEY is not set — this service will accept requests from any "
            "caller that can reach it on the network. Fine for local docker-compose, not for "
            "anything internet-reachable."
        )
    yield


app = FastAPI(title="DevPilot Agent Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "llm_provider": "google" if settings.google_genai_api_key else "not configured",
        "llm_model": settings.google_genai_chat_model,
    }


def _sse(event: str, data) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


async def _run_graph_stream(request: AgentRunRequest) -> AsyncGenerator[str, None]:
    settings = get_settings()
    try:
        llm = get_chat_model(settings)
    except ProviderNotConfiguredError as exc:
        yield _sse("error", {"message": str(exc)})
        return

    search_tool = CodebaseSearchTool(
        repository_id=request.repository_id,
        internal_api_base_url=request.internal_api_base_url,
        internal_api_key=request.internal_api_key,
    )
    graph = build_graph(llm, search_tool)

    initial_state = {
        "repository_id": request.repository_id,
        "repository_full_name": request.repository_full_name,
        "issue_title": request.issue.title,
        "issue_body": request.issue.body,
        "max_review_iterations": request.max_review_iterations,
        "revise_count": 0,
        "review_feedback": "",
        "degraded_reasons": [],
    }

    final_state: dict = dict(initial_state)
    try:
        for update in graph.stream(initial_state, stream_mode="updates"):
            for node_name, partial_state in update.items():
                final_state.update(partial_state)
                message = _NODE_MESSAGES.get(node_name, f"Running {node_name}...")
                yield _sse("progress", {"node": node_name, "message": message})
    except Exception as exc:  # noqa: BLE001 - surface any provider/runtime error to the caller
        logger.exception("Agent graph execution failed")
        yield _sse("error", {"message": f"Agent execution failed: {exc}"})
        return

    result = AgentResult(
        issue_type=final_state.get("issue_type", "bug"),
        summary=final_state.get("summary", ""),
        root_cause=final_state.get("root_cause", ""),
        plan=final_state.get("plan", []),
        proposed_diff=final_state.get("proposed_diff", ""),
        pr_description=final_state.get("pr_description", ""),
        test_suggestions=final_state.get("test_suggestions", ""),
        review_feedback=final_state.get("review_feedback", ""),
        confidence=final_state.get("confidence", "low" if final_state.get("degraded") else "medium"),
        iterations=final_state.get("revise_count", 0),
    )
    yield _sse("result", result.model_dump(by_alias=True))


@app.post("/agent/issue-resolution/run", dependencies=[Depends(verify_caller)])
async def run_issue_resolution(request: AgentRunRequest) -> StreamingResponse:
    return StreamingResponse(_run_graph_stream(request), media_type="text/event-stream")
