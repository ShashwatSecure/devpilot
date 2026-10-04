# agent-service

FastAPI + LangGraph microservice implementing the DevPilot **Issue Resolution Agent**.
See the root-level docs for the full design:

- [../03-AGENTIC-WORKFLOW-DESIGN.md](../03-AGENTIC-WORKFLOW-DESIGN.md) — graph/node design
- [../04-LLM-PROVIDER-STRATEGY.md](../04-LLM-PROVIDER-STRATEGY.md) — Gemini provider setup
- [../05-SETUP-AND-RUNBOOK.md](../05-SETUP-AND-RUNBOOK.md) — how to run everything locally

## Quick start

```bash
cd agent-service
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # then fill in GOOGLE_GENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

`GET /health` reports the configured Gemini model. The service is stateless
and holds no GitHub token or database credentials — it only talks to the Java backend's
internal, read-only code-search endpoint using the shared `AGENT_INTERNAL_API_KEY`.
