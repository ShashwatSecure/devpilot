"""Renders the final onboarding state (+ deterministic repo profile) into a human-readable
Markdown report. Kept separate from the graph so the report format can change without
touching analysis logic, and so the CLI can also dump the raw structured state as JSON.
"""
from __future__ import annotations

from repo_onboarding.scanner import RepoProfile


def _para(lines: list[str], text: str) -> None:
    """Appends a text line followed by a blank line (a Markdown paragraph break)."""
    lines.append(text)
    lines.append("")


def render_markdown(profile: RepoProfile, state: dict) -> str:
    lines: list[str] = [f"# Onboarding Guide — {profile.root}", ""]

    if state.get("degraded"):
        _para(
            lines,
            "> ⚠️ One or more sections below were generated in degraded mode (the model "
            "output could not be fully parsed) — treat those as a starting point, not "
            "ground truth. See **Degradation notes** at the end.",
        )

    _para(lines, "## Product Perspective")
    _para(lines, f"**Problem statement:** {state.get('problem_statement') or '(unknown)'}")
    _para(lines, f"**Target users:** {state.get('target_users') or '(unknown)'}")
    if state.get("key_features"):
        lines.append("**Key features:**")
        lines.extend(f"- {feature}" for feature in state["key_features"])
        lines.append("")
    if state.get("value_proposition"):
        _para(lines, f"**Why this approach:** {state['value_proposition']}")

    _para(lines, "## Technical Perspective")
    _para(lines, f"**Architecture summary:** {state.get('architecture_summary') or '(unknown)'}")
    if profile.language_counts:
        by_count = sorted(profile.language_counts.items(), key=lambda kv: -kv[1])
        _para(lines, "**Languages detected:** " + ", ".join(f"{lang} ({n} files)" for lang, n in by_count))
    if profile.manifest_kinds:
        _para(lines, "**Build/package systems:** " + ", ".join(profile.manifest_kinds))
    if state.get("key_components"):
        lines.append("**Key components:**")
        lines.append("")
        lines.append("| Path | Role |")
        lines.append("|---|---|")
        for component in state["key_components"]:
            lines.append(f"| `{component.get('path', '')}` | {component.get('role', '')} |")
        lines.append("")
    if state.get("data_flow"):
        _para(lines, f"**Typical data flow:** {state['data_flow']}")
    if state.get("notable_patterns"):
        lines.append("**Notable patterns:**")
        lines.extend(f"- {pattern}" for pattern in state["notable_patterns"])
        lines.append("")

    _para(lines, "## Suggested Learning Path")
    steps = sorted(state.get("learning_steps", []), key=lambda s: s.get("order", 0))
    if not steps:
        _para(lines, "(no learning path could be generated)")
    for step in steps:
        difficulty = step.get("difficulty", "")
        lines.append(f"### {step.get('order', '?')}. {step.get('title', 'Untitled step')} ({difficulty})")
        lines.append("")
        for f in step.get("files", []):
            lines.append(f"- `{f}`")
        if step.get("files"):
            lines.append("")
        lines.append(step.get("rationale", ""))
        lines.append("")

    if state.get("glossary"):
        _para(lines, "## Glossary (web-enriched)")
        lines.extend(f"- **{term}**: {summary}" for term, summary in state["glossary"].items())
        lines.append("")

    if state.get("degraded_reasons"):
        _para(lines, "## Degradation notes")
        lines.extend(f"- {reason}" for reason in state["degraded_reasons"])
        lines.append("")

    return "\n".join(lines)
