# DevPilot — AI Agentic Issue Resolution for GitHub Repositories

> A full-stack, production-shaped project that combines **Retrieval-Augmented Generation**
> (chat with your codebase) with a **LangGraph multi-agent workflow** (autonomous GitHub
> issue triage and fix drafting) — built to be run end-to-end, not just described.

This file is the index. Read the numbered docs in order for the full story of what this
project is, the real-world problem it solves, how it's architected, and how to run it.

| # | Document | What's in it |
|---|----------|---------------|
| 01 | [01-PROBLEM-STATEMENT.md](01-PROBLEM-STATEMENT.md) | The real, daily engineering problem this solves and why an agentic approach fits it |
| 02 | [02-ARCHITECTURE.md](02-ARCHITECTURE.md) | System architecture, services, data flow, sequence diagrams |
| 03 | [03-AGENTIC-WORKFLOW-DESIGN.md](03-AGENTIC-WORKFLOW-DESIGN.md) | The LangGraph graph: nodes, state, the self-review/reflection loop, tool use |
| 04 | [04-LLM-PROVIDER-STRATEGY.md](04-LLM-PROVIDER-STRATEGY.md) | Groq vs. xAI Grok vs. Gemini — the free-tier provider abstraction |
| 05 | [05-SETUP-AND-RUNBOOK.md](05-SETUP-AND-RUNBOOK.md) | How to actually run everything locally, with or without Docker |
| 06 | [06-SECURITY-REVIEW.md](06-SECURITY-REVIEW.md) | OWASP-style review: prompt injection, auth boundaries, secrets, what was fixed |
| 07 | [07-IMPLEMENTATION-LOG.md](07-IMPLEMENTATION-LOG.md) | Problem → decision → solution log of everything built and fixed, in order |
| 08 | [08-RESUME-SUMMARY.md](08-RESUME-SUMMARY.md) | Resume-ready bullet points and interview talking points |
| 09 | [09-REPO-ONBOARDING-TOOL.md](09-REPO-ONBOARDING-TOOL.md) | `devpilot-onboard`: a standalone CLI that generates an onboarding guide for *any* repo |

## What DevPilot is

DevPilot started as a **"chat with your GitHub repository"** tool: you sign in with GitHub,
pick a repo, DevPilot indexes its source into a vector database, and you can ask questions
answered with citations back to the actual files (classic RAG).

This project extends it with a second, genuinely agentic capability: the
**Issue Resolution Agent**. Pick an open GitHub issue and a multi-step LangGraph agent will:

1. Classify the issue and draft code-search queries
2. Retrieve the relevant code from the same vector index used for chat
3. Diagnose a root cause and a step-by-step fix plan
4. Draft a proposed diff, PR description, and test suggestions
5. **Critique its own draft** (a bounded self-review/revise loop — genuine agentic reflection,
   not a single prompt-response)
6. Hand the whole proposal to a human for review — **it never commits, pushes, or posts
   anything without an explicit click**

## Stack

- **Next.js 16 / React 19 / TypeScript / Tailwind 4** — client (`client/`)
- **Spring Boot 4.1 / Java 21 / Spring Data JPA / Spring AI / PostgreSQL+pgvector** — backend (`backend/`)
- **FastAPI / LangGraph / LangChain (Python)** — the agent brain (`agent-service/`, new)
- **Groq, xAI Grok, or Google Gemini** — pluggable LLM providers, free-tier friendly

## A third capability: onboard yourself to *any* repo

`repo-onboarding/` is a standalone, pip-installable CLI (`devpilot-onboard`) built and
documented the same way as the rest of this project, but intentionally isolated: install it
once and point it at any repository you have access to (on disk, or a git URL) to get an
in-depth, evidence-grounded product + technical onboarding guide and a file-referenced
learning path — no dependency on the Java backend, Postgres, or agent-service. See
[09-REPO-ONBOARDING-TOOL.md](09-REPO-ONBOARDING-TOOL.md) and
[repo-onboarding/README.md](repo-onboarding/README.md).

## Where to start

If you just want to run it: [05-SETUP-AND-RUNBOOK.md](05-SETUP-AND-RUNBOOK.md).
If you want the design story: start at [01-PROBLEM-STATEMENT.md](01-PROBLEM-STATEMENT.md) and
read forward.
