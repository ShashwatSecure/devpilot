"""Smoke test for the LangGraph onboarding-analysis graph using a scripted fake LLM — no
network calls, no API key required. Validates node wiring, JSON-parsing resilience, the
deterministic detect_stack/web_enrichment steps, and the file-reference grounding step.

Run with: python -m pytest tests/test_graph_smoke.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repo_onboarding.agent.graph import build_graph  # noqa: E402


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


def _base_state() -> dict:
    return {
        "repo_digest": "Repository root: /demo\nLanguages by file count: Python (3)",
        "file_index": ["README.md", "src/main.py", "src/utils.py"],
        "dependencies": ["fastapi", "some-obscure-lib"],
        "degraded_reasons": [],
    }


def test_graph_completes_and_grounds_learning_path():
    responses = [
        json.dumps(
            {
                "problem_statement": "Solves demo problems.",
                "target_users": "Demo users.",
                "key_features": ["feature a"],
                "value_proposition": "Simple.",
            }
        ),
        json.dumps(
            {
                "architecture_summary": "A small demo app.",
                "key_components": [{"path": "src/main.py", "role": "entry point"}],
                "data_flow": "main -> utils",
                "notable_patterns": ["separation of concerns"],
            }
        ),
        json.dumps(
            {
                "steps": [
                    {
                        "order": 1,
                        "title": "Read the entry point",
                        "files": ["src/main.py", "src/does_not_exist.py"],
                        "rationale": "Start here.",
                        "difficulty": "beginner",
                    }
                ]
            }
        ),
    ]
    llm = FakeLLM(responses)

    def web_lookup(term: str) -> str | None:
        return "A somewhat obscure library." if term == "some-obscure-lib" else None

    graph = build_graph(llm, web_lookup, max_web_lookups=6)
    result = graph.invoke(_base_state())

    assert result["known_stack"] == ["fastapi"]
    assert result["unknown_terms"] == ["some-obscure-lib"]
    assert result["glossary"] == {"some-obscure-lib": "A somewhat obscure library."}

    assert result["problem_statement"] == "Solves demo problems."
    assert result["architecture_summary"] == "A small demo app."

    # The hallucinated path must be dropped by the grounding step; the real one kept.
    files = result["learning_steps"][0]["files"]
    assert files == ["src/main.py"]


def test_malformed_llm_output_degrades_gracefully():
    llm = FakeLLM(["not json", "still not json", "nope"])
    graph = build_graph(llm, web_lookup=None)
    result = graph.invoke(_base_state())

    assert result["degraded"] is True
    assert any("product_analysis" in reason for reason in result["degraded_reasons"])
    assert any("tech_analysis" in reason for reason in result["degraded_reasons"])
    assert any("learning_path" in reason for reason in result["degraded_reasons"])
    assert result["learning_steps"] == []
