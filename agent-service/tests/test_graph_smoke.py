"""Smoke test for the LangGraph Issue Resolution Agent using a scripted fake LLM —
no network calls, no API key required. Validates node wiring, JSON-parsing resilience,
and the bounded self-review revise loop.

Run with: .venv/Scripts/python.exe -m pytest tests/test_graph_smoke.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.graph import build_graph  # noqa: E402
from app.tools import CodebaseSearchTool, CodeSearchResult  # noqa: E402


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    """Returns pre-scripted responses in call order, looping the last one once exhausted."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def invoke(self, messages) -> FakeMessage:
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return FakeMessage(self.responses[idx])


def _responses_pass_first_try() -> list[str]:
    return [
        json.dumps({"issue_type": "bug", "search_queries": ["parseConfig", "null pointer"]}),
        json.dumps(
            {
                "summary": "Config parser crashes on missing field.",
                "root_cause": "parseConfig() does not null-check the 'timeout' field.",
                "plan": ["Add a null check", "Default to 30s", "Add a regression test"],
            }
        ),
        json.dumps(
            {
                "proposed_diff": "--- a/Config.java\n+++ b/Config.java\n@@\n-int t = raw.timeout;\n+int t = raw.timeout != null ? raw.timeout : 30;",
                "pr_description": "Fixes NPE in Config parsing when timeout is omitted.",
                "test_suggestions": "- test parseConfig with missing timeout field",
            }
        ),
        json.dumps({"verdict": "PASS", "feedback": "", "confidence": "high"}),
    ]


def test_graph_completes_on_first_pass():
    llm = FakeLLM(_responses_pass_first_try())
    with patch.object(CodebaseSearchTool, "search", return_value=[
        CodeSearchResult(file_path="Config.java", language="java", content="class Config {}", chunk_index=0, score=0.9)
    ]):
        tool = CodebaseSearchTool(repository_id="r1", internal_api_base_url="http://x", internal_api_key="k")
        graph = build_graph(llm, tool)
        result = graph.invoke(
            {
                "repository_id": "r1",
                "repository_full_name": "acme/widgets",
                "issue_title": "NPE when timeout missing",
                "issue_body": "Crashes on startup if config.yaml has no timeout field",
                "max_review_iterations": 2,
                "revise_count": 0,
                "review_feedback": "",
                "degraded_reasons": [],
            }
        )

    assert result["review_verdict"] == "PASS"
    assert result["revise_count"] == 0
    assert "timeout" in result["root_cause"]
    assert len(result["plan"]) == 3


def test_graph_loops_once_then_passes():
    responses = [
        json.dumps({"issue_type": "bug", "search_queries": ["q1"]}),
        json.dumps({"summary": "s", "root_cause": "rc", "plan": ["p1"]}),
        json.dumps({"proposed_diff": "diff-v1", "pr_description": "pr-v1", "test_suggestions": "t1"}),
        json.dumps({"verdict": "REVISE", "feedback": "scope too broad", "confidence": "medium"}),
        json.dumps({"proposed_diff": "diff-v2", "pr_description": "pr-v2", "test_suggestions": "t2"}),
        json.dumps({"verdict": "PASS", "feedback": "", "confidence": "high"}),
    ]
    llm = FakeLLM(responses)
    with patch.object(CodebaseSearchTool, "search", return_value=[]):
        tool = CodebaseSearchTool(repository_id="r1", internal_api_base_url="http://x", internal_api_key="k")
        graph = build_graph(llm, tool)
        result = graph.invoke(
            {
                "repository_id": "r1",
                "repository_full_name": "acme/widgets",
                "issue_title": "issue",
                "issue_body": "body",
                "max_review_iterations": 2,
                "revise_count": 0,
                "review_feedback": "",
                "degraded_reasons": [],
            }
        )

    assert result["proposed_diff"] == "diff-v2"
    assert result["revise_count"] == 1
    assert result["review_verdict"] == "PASS"


def test_malformed_llm_output_degrades_gracefully():
    llm = FakeLLM(["not json at all", "still not json", "nope", "nope again"])
    with patch.object(CodebaseSearchTool, "search", return_value=[]):
        tool = CodebaseSearchTool(repository_id="r1", internal_api_base_url="http://x", internal_api_key="k")
        graph = build_graph(llm, tool)
        result = graph.invoke(
            {
                "repository_id": "r1",
                "repository_full_name": "acme/widgets",
                "issue_title": "issue",
                "issue_body": "body",
                "max_review_iterations": 2,
                "revise_count": 0,
                "review_feedback": "",
                "degraded_reasons": [],
            }
        )

    assert result["degraded"] is True
    assert result["review_verdict"] == "PASS"  # never blocks finalize even when degraded


if __name__ == "__main__":
    test_graph_completes_on_first_pass()
    test_graph_loops_once_then_passes()
    test_malformed_llm_output_degrades_gracefully()
    print("All smoke tests passed.")
