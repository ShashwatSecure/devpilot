"""devpilot-repo-onboarding: a standalone, pip-installable CLI that analyzes any repository
you have access to and produces a grounded product + technical onboarding guide.

Deliberately isolated from the rest of the DevPilot monorepo (no dependency on the Java
backend, Postgres, or the issue-resolution agent-service) so it can be installed and run
on its own, against any repository on disk or reachable via `git clone`.
"""
from __future__ import annotations

__version__ = "0.1.0"
