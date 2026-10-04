-- Persists Issue Resolution Agent runs (LangGraph agent-service orchestrated from IssueAgentService).

CREATE TABLE IF NOT EXISTS agent_runs (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    repository_id          UUID NOT NULL REFERENCES repositories (id) ON DELETE CASCADE,
    issue_number            INTEGER NOT NULL,
    issue_title             VARCHAR(500) NOT NULL,
    issue_url               VARCHAR(500),
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    issue_type               VARCHAR(30),
    summary                 TEXT,
    root_cause              TEXT,
    plan_json                TEXT,
    proposed_diff            TEXT,
    pr_description           TEXT,
    test_suggestions         TEXT,
    review_feedback          TEXT,
    confidence               VARCHAR(20),
    iterations               INTEGER NOT NULL DEFAULT 0,
    github_comment_posted    BOOLEAN NOT NULL DEFAULT false,
    github_comment_url       VARCHAR(500),
    error_message            TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_user_repo ON agent_runs (user_id, repository_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_repo_issue ON agent_runs (repository_id, issue_number);
