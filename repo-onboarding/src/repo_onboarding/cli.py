"""Command-line entrypoint: `devpilot-onboard analyze <path-or-git-url>`.

Analyzes any repository on disk, or a git URL, and writes a grounded product + technical
onboarding report with a suggested learning path. A git URL is shallow-cloned into a
temporary directory using the caller's own `git` — this tool never handles, stores, or asks
for an auth token; whatever credential helper/SSH key already lets you `git clone` the repo
is what's used, exactly as if you'd cloned it yourself.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from repo_onboarding.agent.graph import build_graph
from repo_onboarding.config import get_settings
from repo_onboarding.providers import ProviderNotConfiguredError, get_chat_model
from repo_onboarding.report import render_markdown
from repo_onboarding.scanner import build_digest, scan_repository
from repo_onboarding.web_lookup import lookup_term


def _clone_if_url(target: str, tmp_root: Path) -> Path:
    if "://" not in target and not target.startswith("git@"):
        return Path(target)
    dest = tmp_root / "repo"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", target, str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git clone failed: {result.stderr.strip()}")
    return dest


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devpilot-onboard")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a repository and generate an onboarding report")
    analyze.add_argument("target", help="Local path or git URL (uses your own git credentials) to the repository")
    analyze.add_argument("-o", "--output", default=None, help="Write the Markdown report to this file (default: stdout)")
    analyze.add_argument("--json", dest="json_output", default=None, help="Also write the raw structured result as JSON to this file")
    analyze.add_argument("--provider", choices=["auto", "groq", "xai", "google"], default=None, help="Force an LLM provider (default: auto-detect from env)")
    analyze.add_argument("--no-web-lookup", action="store_true", help="Disable best-effort web glossary lookups")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.command != "analyze":
        return 1

    settings = get_settings()
    overrides = {}
    if args.provider:
        overrides["onboard_llm_provider"] = args.provider
    if args.no_web_lookup:
        overrides["enable_web_lookup"] = False
    if overrides:
        settings = settings.model_copy(update=overrides)

    with tempfile.TemporaryDirectory(prefix="devpilot-onboard-") as tmp_dir:
        repo_path = _clone_if_url(args.target, Path(tmp_dir))
        if not repo_path.is_dir():
            print(f"error: '{repo_path}' is not a directory", file=sys.stderr)
            return 1

        try:
            llm = get_chat_model(settings)
        except ProviderNotConfiguredError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(f"Scanning {repo_path} ...", file=sys.stderr)
        profile = scan_repository(
            repo_path,
            max_files=settings.max_files_scanned,
            max_file_bytes=settings.max_file_bytes,
            max_readme_chars=settings.max_readme_chars,
        )
        digest = build_digest(profile, max_chars=settings.max_digest_chars)

        web_lookup = None
        if settings.enable_web_lookup:
            def web_lookup(term: str) -> str | None:
                return lookup_term(term, timeout_seconds=settings.web_lookup_timeout_seconds)

        graph = build_graph(llm, web_lookup, max_web_lookups=settings.max_web_lookups)

        initial_state = {
            "repo_digest": digest,
            "file_index": [f.path for f in profile.files],
            "language_counts": profile.language_counts,
            "manifest_kinds": profile.manifest_kinds,
            "top_level_entries": profile.top_level_entries,
            "dependencies": profile.dependencies,
            "degraded_reasons": [],
        }

        print("Analyzing product + technical perspective (calls your configured LLM)...", file=sys.stderr)
        final_state = dict(initial_state)
        for update in graph.stream(initial_state, stream_mode="updates"):
            for node_name, partial in update.items():
                final_state.update(partial)
                print(f"  - {node_name} done", file=sys.stderr)

        report_md = render_markdown(profile, final_state)

        if args.output:
            Path(args.output).write_text(report_md, encoding="utf-8")
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(report_md)

        if args.json_output:
            Path(args.json_output).write_text(json.dumps(final_state, indent=2, default=str), encoding="utf-8")
            print(f"Structured result written to {args.json_output}", file=sys.stderr)

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
