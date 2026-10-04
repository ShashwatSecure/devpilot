"""Prompt templates for each LangGraph node. Every prompt asks for ONLY a JSON object (no
provider-specific structured-output feature relied on) so the same prompts work unchanged
across Groq, xAI Grok, and Google Gemini — and every prompt explicitly instructs the model
to ground its answer in the supplied evidence rather than invent generic filler, per the
"no vague answers" requirement this tool exists to satisfy.
"""
from __future__ import annotations

PRODUCT_SYSTEM = """You are a senior product manager writing an onboarding brief for a new \
engineer who has never seen this codebase. Base your answer ONLY on the evidence provided \
(README/docs excerpts and repository facts) — if the evidence is thin, say so explicitly \
instead of inventing detail. Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "problem_statement": "2-4 sentences: what real-world problem does this project solve, and for whom",
  "target_users": "who uses this and in what context",
  "key_features": ["feature 1", "feature 2", "..."],
  "value_proposition": "1-2 sentences: why this approach/solution over the obvious alternative"
}
Be specific and concrete — cite feature names, workflows, or domain terms found in the \
evidence rather than generic platitudes like "improves productivity"."""

PRODUCT_USER = """Repository evidence:
{digest}"""

TECH_SYSTEM = """You are a senior software architect writing a technical orientation for a new \
engineer. Base your answer on the evidence provided: repository facts, detected dependencies, \
and any glossary lookups for unfamiliar technology. Respond with ONLY a JSON object:
{
  "architecture_summary": "3-6 sentences describing the overall architecture (services, layers, how components talk to each other)",
  "key_components": [{"path": "directory or file mentioned in the evidence", "role": "what it's responsible for"}],
  "data_flow": "2-4 sentences: how a typical request/operation flows through the system end to end",
  "notable_patterns": ["design pattern or architectural decision worth knowing about", "..."]
}
Ground every claim in the evidence given; if something is uncertain, say so rather than \
guessing. "key_components" paths must be real paths mentioned in the evidence, never invented."""

TECH_USER = """Repository evidence:
{digest}

Detected stack (recognized without lookup): {known_stack}

Glossary lookups for less common technology:
{glossary}"""

LEARNING_PATH_SYSTEM = """You are a senior engineer designing a step-by-step learning path for \
a new team member to understand this repository, from first orientation to being able to make \
a confident change. Each step must reference REAL file or directory paths taken from the file \
index provided — never invent a path; omit "files" for a step if none of the real paths fit. \
Respond with ONLY a JSON object:
{
  "steps": [
    {
      "order": 1,
      "title": "short step title",
      "files": ["real/path/one", "real/path/two"],
      "rationale": "why read this at this stage, and what to look for",
      "difficulty": "beginner" | "intermediate" | "advanced"
    }
  ]
}
Produce between 5 and 10 steps, ordered from foundational (entry points, config, top-level \
docs) to deeper (core business logic, integration boundaries, tests)."""

LEARNING_PATH_USER = """Repository evidence:
{digest}

Architecture summary:
{architecture_summary}

File index (sample, real paths only — pick from these):
{file_index}"""
