"""Unit tests for the deterministic repo scanner — no network, no LLM."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repo_onboarding.scanner import build_digest, scan_repository  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_detects_languages_manifests_and_dependencies(tmp_path: Path):
    _write(tmp_path / "README.md", "# Demo\n\nA demo repo for testing the scanner.")
    _write(tmp_path / ".gitignore", "node_modules/\n*.log\n")
    _write(tmp_path / "package.json", '{"name": "demo", "dependencies": {"react": "^18.0.0", "some-obscure-lib": "1.0.0"}}')
    _write(tmp_path / "requirements.txt", "fastapi>=0.115\nsome_rare_package==2.0\n")
    _write(tmp_path / "src" / "main.py", "print('hello')\n")
    _write(tmp_path / "node_modules" / "junk" / "index.js", "// should be ignored\n")
    _write(tmp_path / "debug.log", "should be ignored via gitignore\n")

    profile = scan_repository(tmp_path)

    paths = {f.path for f in profile.files}
    assert "src/main.py" in paths
    assert "README.md" in paths
    assert not any(p.startswith("node_modules/") for p in paths)
    assert "debug.log" not in paths

    assert profile.language_counts.get("Python") == 1
    assert "Node.js / npm" in profile.manifest_kinds
    assert "pip (Python)" in profile.manifest_kinds

    assert "react" in profile.dependencies
    assert "some-obscure-lib" in profile.dependencies
    assert "fastapi" in profile.dependencies
    assert "some_rare_package" in profile.dependencies

    assert "README.md" in profile.doc_files
    assert "demo repo" in profile.doc_files["README.md"].lower()


def test_build_digest_includes_key_facts_and_respects_cap(tmp_path: Path):
    _write(tmp_path / "README.md", "# Demo\n\n" + ("word " * 5000))
    _write(tmp_path / "requirements.txt", "flask\n")

    profile = scan_repository(tmp_path)
    digest = build_digest(profile, max_chars=500)

    assert len(digest) <= 500
    assert "Repository root" in digest
