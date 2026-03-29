-- migrate:up

-- Task key sequence
CREATE SEQUENCE IF NOT EXISTS platform.task_key_seq START 1;

-- Agent repo assignments
CREATE TABLE IF NOT EXISTS platform.agent_repos (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    repo_url    TEXT NOT NULL,
    repo_name   VARCHAR(128) NOT NULL,
    assigned_by VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_name, repo_url)
);

CREATE INDEX IF NOT EXISTS idx_agent_repos_agent
    ON platform.agent_repos (agent_name);

-- Task management
CREATE TABLE IF NOT EXISTS platform.tasks (
    id                  SERIAL PRIMARY KEY,
    key                 VARCHAR(16) NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    description         TEXT,
    status              VARCHAR(16) NOT NULL DEFAULT 'backlog'
                        CHECK (status IN ('backlog', 'todo', 'in_progress', 'review', 'done', 'blocked')),
    priority            VARCHAR(8) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    assigned_to         VARCHAR(64),
    created_by          VARCHAR(64),
    result              TEXT,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    parent_task_id      INT REFERENCES platform.tasks(id) ON DELETE SET NULL,
    repo_id             INT REFERENCES platform.agent_repos(id) ON DELETE SET NULL,
    recurrence_minutes  INT,
    recurrence_count    INT NOT NULL DEFAULT 0,
    schedule_at         TIME,
    last_completed_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON platform.tasks (status);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned_status
    ON platform.tasks (assigned_to, status);

CREATE INDEX IF NOT EXISTS idx_tasks_priority
    ON platform.tasks (priority);

CREATE INDEX IF NOT EXISTS idx_tasks_tags
    ON platform.tasks USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_tasks_recurring
    ON platform.tasks (recurrence_minutes) WHERE recurrence_minutes IS NOT NULL;

-- migrate:down

DROP TABLE IF EXISTS platform.tasks;
DROP TABLE IF EXISTS platform.agent_repos;
DROP SEQUENCE IF EXISTS platform.task_key_seq;
