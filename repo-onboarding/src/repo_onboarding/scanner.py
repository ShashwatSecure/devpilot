"""Deterministic repository scanner: walks the file tree (gitignore-aware), classifies
languages by extension, detects build/package manifests, extracts declared dependency names
from common manifest formats, and pulls in bounded excerpts of README/architecture-style docs.

Nothing here calls an LLM — this module produces the *facts* that the LangGraph analysis
nodes reason over, so the report's tech section is always grounded in something real rather
than invented.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", "target", ".next", ".turbo", ".pytest_cache",
    ".mypy_cache", ".gradle", ".idea", ".vscode", "coverage", ".cache", ".tox",
}

LANGUAGE_BY_EXT = {
    ".py": "Python", ".java": "Java", ".kt": "Kotlin", ".ts": "TypeScript",
    ".tsx": "TypeScript (React)", ".js": "JavaScript", ".jsx": "JavaScript (React)",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".cpp": "C++", ".c": "C", ".h": "C/C++ Header", ".swift": "Swift", ".scala": "Scala",
    ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".md": "Markdown", ".html": "HTML", ".css": "CSS",
}

MANIFEST_FILES = {
    "package.json": "Node.js / npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "pom.xml": "Maven (Java)",
    "build.gradle": "Gradle (Java/Kotlin)",
    "build.gradle.kts": "Gradle (Kotlin DSL)",
    "requirements.txt": "pip (Python)",
    "pyproject.toml": "Python packaging",
    "Pipfile": "Pipenv (Python)",
    "go.mod": "Go modules",
    "Cargo.toml": "Cargo (Rust)",
    "Gemfile": "Bundler (Ruby)",
    "composer.json": "Composer (PHP)",
    "Dockerfile": "Docker",
    "docker-compose.yaml": "Docker Compose",
    "docker-compose.yml": "Docker Compose",
    "Makefile": "Make",
}

DOC_FILE_HINTS = ("readme", "architecture", "design", "contributing", "adr")

# Common frameworks/tools everyone building software already knows — anything detected in a
# repo's dependencies that ISN'T in this set is a candidate for a web glossary lookup.
KNOWN_TECH = {
    "react", "next", "vue", "angular", "svelte", "express", "fastapi", "flask", "django",
    "spring", "hibernate", "junit", "jest", "mocha", "pytest", "tailwind", "bootstrap",
    "redux", "graphql", "axios", "lodash", "webpack", "vite", "babel", "eslint", "typescript",
    "postgres", "mysql", "mongodb", "redis", "docker", "kubernetes", "langchain", "langgraph",
    "openai", "pydantic", "sqlalchemy", "numpy", "pandas", "requests", "httpx", "uvicorn",
    "gunicorn", "nginx", "kafka", "rabbitmq", "grpc", "protobuf", "jackson", "lombok",
    "mockito", "spring-boot", "spring-security", "spring-data", "node", "python", "java",
}

_DEP_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+")


@dataclass
class RepoFile:
    path: str
    language: str | None
    size: int


@dataclass
class RepoProfile:
    root: str
    files: list[RepoFile] = field(default_factory=list)
    language_counts: dict[str, int] = field(default_factory=dict)
    manifests: list[str] = field(default_factory=list)
    manifest_kinds: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    doc_files: dict[str, str] = field(default_factory=dict)
    top_level_entries: list[str] = field(default_factory=list)
    git_last_commits: list[str] = field(default_factory=list)
    git_remote: str | None = None
    truncated: bool = False


def _load_gitignore(root: Path) -> pathspec.PathSpec:
    patterns: list[str] = []
    gitignore = root / ".gitignore"
    if gitignore.is_file():
        try:
            patterns = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            patterns = []
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _redact_credentials(url: str) -> str:
    """Strips any userinfo (user:token@) component from a remote URL before it can ever be
    embedded in a prompt sent to an LLM or written into a report."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        _, _, host_and_path = rest.partition("@")
        return f"{scheme}://{host_and_path}"
    return url


def _read_git_metadata(root: Path) -> tuple[list[str], str | None]:
    if not (root / ".git").exists():
        return [], None
    commits: list[str] = []
    remote: str | None = None

    log = _run_git_command(["git", "log", "-n", "8", "--pretty=format:%h %s"], root)
    if log:
        commits = [line for line in log.splitlines() if line]

    rem = _run_git_command(["git", "remote", "get-url", "origin"], root)
    if rem:
        remote = _redact_credentials(rem)

    return commits, remote


def _run_git_command(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


# --- dependency extraction: best-effort, per manifest format ------------------------------

def _extract_requirements_txt(content: str) -> list[str]:
    names = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = _DEP_NAME_RE.match(line)
        if match:
            names.append(match.group(0))
    return names


def _extract_package_json(content: str) -> list[str]:
    try:
        data = json.loads(content)
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    return list(data.get("dependencies", {}) or {}) + list(data.get("devDependencies", {}) or {})


def _extract_pom_xml(content: str) -> list[str]:
    return re.findall(r"<artifactId>([\w.\-]+)</artifactId>", content)


def _extract_go_mod(content: str) -> list[str]:
    names = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("module ") or line in ("require (", ")"):
            continue
        if line.startswith("require "):
            line = line[len("require "):]
        parts = line.split()
        first = parts[0] if parts else ""
        if "/" in first:
            names.append(first.split("/")[-1])
    return names


def _extract_pyproject_toml(content: str) -> list[str]:
    # Best-effort regex extraction (no toml parser dependency) matching both PEP 621
    # `"name>=1.0"` array entries and Poetry `name = "^1.0"` table entries.
    names = set(re.findall(r'"([A-Za-z0-9_.\-]+)\s*[<>=!~^]', content))
    names.update(re.findall(r'(?m)^([A-Za-z0-9_.\-]+)\s*=\s*"[\^~]?[\d*]', content))
    return sorted(names)


def _extract_gradle(content: str) -> list[str]:
    return re.findall(
        r'(?:implementation|api|compileOnly|testImplementation|runtimeOnly)[\s(]+["\']'
        r'[\w.\-]+:([\w.\-]+)',
        content,
    )


def _extract_cargo_toml(content: str) -> list[str]:
    names = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_deps = stripped.startswith("[dependencies")
            continue
        if in_deps and "=" in stripped:
            names.append(stripped.split("=", 1)[0].strip().strip('"'))
    return names


_MANIFEST_EXTRACTORS = {
    "requirements.txt": _extract_requirements_txt,
    "package.json": _extract_package_json,
    "pom.xml": _extract_pom_xml,
    "go.mod": _extract_go_mod,
    "pyproject.toml": _extract_pyproject_toml,
    "build.gradle": _extract_gradle,
    "build.gradle.kts": _extract_gradle,
    "Cargo.toml": _extract_cargo_toml,
}


def scan_repository(
    root: Path,
    *,
    max_files: int = 4000,
    max_file_bytes: int = 200_000,
    max_readme_chars: int = 12_000,
) -> RepoProfile:
    root = root.resolve()
    profile = RepoProfile(root=str(root))
    spec = _load_gitignore(root)

    with suppress(OSError):
        profile.top_level_entries = sorted(
            p.name + ("/" if p.is_dir() else "")
            for p in root.iterdir()
            if p.name not in DEFAULT_IGNORE_DIRS
        )

    scanned = 0
    dependencies: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        pruned = []
        for d in dirnames:
            if d in DEFAULT_IGNORE_DIRS:
                continue
            rel_dir = (Path(dirpath) / d).relative_to(root).as_posix() + "/"
            if spec.match_file(rel_dir):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        if scanned >= max_files:
            profile.truncated = True
            break

        for filename in sorted(filenames):
            if scanned >= max_files:
                profile.truncated = True
                break

            file_path = Path(dirpath) / filename
            rel = file_path.relative_to(root)
            rel_str = rel.as_posix()
            if spec.match_file(rel_str):
                continue

            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            scanned += 1
            ext = file_path.suffix.lower()
            language = LANGUAGE_BY_EXT.get(ext)
            profile.files.append(RepoFile(path=rel_str, language=language, size=size))
            if language:
                profile.language_counts[language] = profile.language_counts.get(language, 0) + 1

            if filename in MANIFEST_FILES:
                profile.manifests.append(rel_str)
                kind = MANIFEST_FILES[filename]
                if kind not in profile.manifest_kinds:
                    profile.manifest_kinds.append(kind)

                extractor = _MANIFEST_EXTRACTORS.get(filename)
                if extractor and size <= max_file_bytes:
                    with suppress(OSError):
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        dependencies.update(extractor(content))

            lower_name = filename.lower()
            is_doc_hint = any(hint in lower_name for hint in DOC_FILE_HINTS)
            if is_doc_hint and len(rel.parts) <= 3 and ext in (".md", ".rst", ".txt"):
                if size <= max_file_bytes:
                    with suppress(OSError):
                        text = file_path.read_text(encoding="utf-8", errors="ignore")
                        profile.doc_files[rel_str] = text[:max_readme_chars]

    profile.dependencies = sorted(dependencies)[:300]
    profile.git_last_commits, profile.git_remote = _read_git_metadata(root)
    return profile


def build_digest(profile: RepoProfile, *, max_chars: int = 20_000) -> str:
    """Condenses the profile into the text block fed to every LLM prompt: structured facts
    first, then bounded doc excerpts. Kept small on purpose to control token usage/cost."""
    lines = [f"Repository root: {profile.root}"]
    if profile.git_remote:
        lines.append(f"Git remote: {profile.git_remote}")
    if profile.git_last_commits:
        lines.append("Recent commits:")
        lines.extend(f"  - {c}" for c in profile.git_last_commits)
    if profile.top_level_entries:
        lines.append("Top-level entries: " + ", ".join(profile.top_level_entries))
    if profile.language_counts:
        by_count = sorted(profile.language_counts.items(), key=lambda kv: -kv[1])
        lines.append("Languages by file count: " + ", ".join(f"{lang} ({n})" for lang, n in by_count))
    if profile.manifest_kinds:
        lines.append("Detected build/package systems: " + ", ".join(profile.manifest_kinds))
    if profile.dependencies:
        lines.append("Declared dependencies: " + ", ".join(profile.dependencies[:80]))
    if profile.truncated:
        lines.append("(note: repository is large — file scan was truncated at the configured limit)")

    for doc_path, content in profile.doc_files.items():
        lines.append(f"\n--- {doc_path} ---\n{content}")

    return "\n".join(lines)[:max_chars]
